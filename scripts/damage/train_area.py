"""Impacted-AREA model: P(this 30 m cell is inside the flood/debris footprint | a flood comes down this river path).

Training data: the per-cell tables from scripts/damage/events/build_area_table.py (labels = published satellite
flood/debris extents only; sources in docs/data/events/SOURCES_area_<event>.md):
  aug26  UNOSAT FL20260826NPL        Bhotekoshi-Trishuli, Nepal   (Sentinel-2 + PlanetScope, 26-28 Aug 2026)
  oct11  UNOSAT FL20261011NPL        Budhi Gandaki, Nepal         (Sentinel-2, 11 Oct 2026)
  ahr    CEMS EMSR517 AOI15 MONIT01  Ahr, Germany                 (aerial 0.12 m 16 Jul + Pleiades 20 Jul 2021)
  derna  UNOSAT FL20230912LBY (S2)   Wadi Derna, Libya            (Sentinel-2, 12 Sep 2023)
Rows <= 500 m from the flood path (dm.MAX_DIST_M), the corridor prediction mode scores.

Candidates (all decided before any result was seen):
  terrain   HistGradientBoosting on FA = local terrain only (no river position, no Nepal-only landslide count, no
            kind: every row is a cell), monotone: P may only fall as HAND or distance grows. All floods usable.
  fb        same + freeboard = HAND - that flood's height line at the cell's river km. The line is the flood preset
            prediction mode already uses (models/damage/flood_presets.json, built from real observations of that
            flood), so this exists only for aug26 and oct11.
Baselines on the same rows: the app's current P (damage model v2 on cells as "building", preset envelope, exactly
engine/escape.py FloodScenario), HAND alone, distance alone, -freeboard alone (= the engine footprint rule ranked).
Each training flood gets equal total sample weight. Probabilities are Platt-calibrated on out-of-fold predictions
(inner leave-one-flood-out over the training floods; 'fb' with one training flood: 5-fold by 10 km river blocks).

Tests:
  A. leave-one-flood-out (terrain), all four floods: ROC AUC, PR AUC, Brier.
  B. the app case, Oct 11 never seen: terrain trained on aug26+ahr+derna, fb trained on aug26; v2 = app P.
     95% CI of (candidate AUC - v2 AUC) by block bootstrap over 2 km river blocks (cells are spatially correlated).
Rule (fixed before running): a candidate may replace v2 as prediction mode's P grid only if on test B its ROC AUC
>= v2's AND its Brier <= v2's. If both pass, the higher AUC wins. Otherwise the app keeps v2.
The final model of a passing candidate is refit on every flood it can use and written to models/area/.

Run on the VM:  python3 -I scripts/damage/train_area.py --repo ~/work-agent-lcpizani/repo
"""
import argparse, json, os, platform, sys, time
from datetime import datetime, timezone
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--repo", default=os.path.expanduser("~/work-agent-lcpizani/repo"))
ap.add_argument("--events", default=os.path.expanduser("~/work-agent-lcpizani/events"))
ap.add_argument("--out", default=None, help="metrics/model dir (default <repo>/models/area)")
ap.add_argument("--boot", type=int, default=300)
a = ap.parse_args()
sys.path.insert(0, a.repo)
sys.path.insert(0, os.path.join(a.repo, "scripts", "damage"))

import joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, average_precision_score, brier_score_loss
from engine import damage_model as dm
from engine.terrain import Terrain
import train_eval as te

OUT = a.out or os.path.join(a.repo, "models", "area")
os.makedirs(OUT, exist_ok=True)
EVENTS = ["aug26", "oct11", "ahr", "derna"]
PRESET = {"aug26": "aug26", "oct11": "oct11"}
FA = ["hand", "dist_channel_m", "slope_deg", "valley_width_m", "channel_slope", "bend_curv", "outside_bend"]
FB = FA + ["freeboard"]
MONO = {"hand": -1, "dist_channel_m": -1}


def presets():
    return json.load(open(os.path.join(a.repo, "models", "damage", "flood_presets.json")))["presets"]


def envelope(key):
    from engine.flood import FloodEnvelope       # same construction as engine/escape.py envelope()
    p = presets()[key]
    return FloodEnvelope([tuple(x) for x in p["arrival_knots"]], [tuple(h) for h in p["height_knots"]],
                         decay_km=1e12, floor_m=0.0)


def load(ev):
    t = np.load(os.path.join(a.events, ev, "area_table.npz"))
    assert list(t["cols"]) == dm.FEATURES_ALL, list(t["cols"])
    c = {n: t["X"][:, i] for i, n in enumerate(dm.FEATURES_ALL)}
    m = c["dist_channel_m"] <= dm.MAX_DIST_M
    d = {"cols": {k: v[m] for k, v in c.items()}, "y": t["y"][m].astype(int), "lonlat": t["lonlat"][m],
         "label_source": str(t["label_source"])}
    if ev in PRESET:
        F = envelope(PRESET[ev])
        d["cols"]["freeboard"] = d["cols"]["hand"] - np.asarray(F.height(d["cols"]["river_km"]), float)
        d["F"] = F
    return d


def mat(d, names):
    return np.column_stack([d["cols"][n] for n in names]).astype(float)


def model(names):
    return HistGradientBoostingClassifier(monotonic_cst=[MONO.get(n, 0) for n in names], **te.HGB)


def weights(parts):
    n = sum(len(p["y"]) for p in parts)
    return np.concatenate([np.full(len(p["y"]), n / (len(parts) * len(p["y"]))) for p in parts])


def fit(parts, names):
    X = np.vstack([mat(p, names) for p in parts]); y = np.concatenate([p["y"] for p in parts])
    return model(names).fit(X, y, sample_weight=weights(parts))


def oof_platt(parts, names):
    """Platt (a, b) on out-of-fold raw scores: inner leave-one-flood-out, or river-block folds for one flood."""
    zs, ys, ws = [], [], []
    if len(parts) > 1:
        for i, p in enumerate(parts):
            m = fit([q for j, q in enumerate(parts) if j != i], names)
            zs.append(dm.logit(m.predict_proba(mat(p, names))[:, 1])); ys.append(p["y"])
            ws.append(np.full(len(p["y"]), 1.0 / len(p["y"])))
    else:
        p = parts[0]
        blk = (np.floor(p["cols"]["river_km"] / 10.0).astype(int)) % 5
        for f in range(5):
            tr, ts = blk != f, blk == f
            sub = lambda m_: {"cols": {k: v[m_] for k, v in p["cols"].items()}, "y": p["y"][m_]}
            m = fit([sub(tr)], names)
            zs.append(dm.logit(m.predict_proba(mat(sub(ts), names))[:, 1])); ys.append(p["y"][ts])
            ws.append(np.ones(int(ts.sum())))
    lr = LogisticRegression(C=1e6, max_iter=1000).fit(np.concatenate(zs)[:, None], np.concatenate(ys),
                                                      sample_weight=np.concatenate(ws))
    return float(lr.coef_[0, 0]), float(lr.intercept_[0])


def calib(raw, ab):
    return dm.sigmoid(ab[0] * dm.logit(raw) + ab[1])


def scores(y, p):
    return {"n": int(len(y)), "positives": int(y.sum()), "base_rate": round(float(y.mean()), 4),
            "roc_auc": round(float(roc_auc_score(y, p)), 4), "pr_auc": round(float(average_precision_score(y, p)), 4),
            "brier": round(float(brier_score_loss(y, np.clip(p, 0, 1))), 4) if np.all((p >= 0) & (p <= 1)) else None}


def hand_bands(y, h, p=None):
    out = []
    for lo, hi in [(-np.inf, 2), (2, 5), (5, 10), (10, 20), (20, 50), (50, np.inf)]:
        m = (h >= lo) & (h < hi)
        row = {"hand_m": f"[{lo},{hi})", "n": int(m.sum()), "observed": round(float(y[m].mean()), 3) if m.any() else None}
        if p is not None and m.any():
            row["predicted_mean"] = round(float(p[m].mean()), 3)
        out.append(row)
    return out


def block_boot_diff(y, s1, s2, km, n, block_km=2.0):
    rng = np.random.default_rng(0)
    b = np.floor(km / block_km).astype(int)
    ub = np.unique(b); groups = [np.flatnonzero(b == u) for u in ub]
    diffs = []
    for _ in range(n):
        idx = np.concatenate([groups[i] for i in rng.integers(0, len(groups), len(groups))])
        if 0 < y[idx].sum() < len(idx):
            diffs.append(roc_auc_score(y[idx], s1[idx]) - roc_auc_score(y[idx], s2[idx]))
    return {"mean": round(float(np.mean(diffs)), 4), "ci95": [round(float(np.percentile(diffs, q)), 4) for q in (2.5, 97.5)],
            "n_blocks": int(len(ub)), "n_boot": len(diffs)}


def app_p_v2(ev, d):
    """The P prediction mode uses today on these cells: v2 on cell centres as 'building' with the preset envelope."""
    t = np.load(os.path.join(a.events, ev, "area_table.npz"))
    rep = json.load(open(os.path.join(a.events, ev, "area_build_report.json")))
    T = Terrain(rep["proc"])
    sx, sy = dm.Transformer.from_crs(4326, 32645, always_xy=True).transform(*rep["terrain"]["source_lonlat"])
    r, c = T.snap_to_channel(*T.rc(sx, sy), radius=15)
    path = T.downstream_path(r, c)
    assert len(path) == rep["terrain"]["path_cells"], "path differs from the table's"
    ctx = dm.PathContext(T, path)
    return dm.predict(dm.load("v2", os.path.join(a.repo, "models", "damage")), ctx, d["lonlat"],
                      ["building"] * len(d["y"]), d["F"])


def main():
    t0 = time.time()
    D = {ev: load(ev) for ev in EVENTS}
    res = {"created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "arch": platform.machine(),
           "rows_le_500m": {ev: {"n": int(len(d["y"])), "y1": int(d["y"].sum()), "label_source": d["label_source"]}
                            for ev, d in D.items()},
           "features_terrain": FA, "features_fb": FB, "monotone": MONO, "hgb": te.HGB,
           "rule": "replace v2 only if on Oct 11 (unseen): AUC >= v2 AND Brier <= v2; both pass -> higher AUC"}

    # A. leave-one-flood-out, terrain
    A = {}
    for ev in EVENTS:
        tr = [D[e] for e in EVENTS if e != ev]
        m = fit(tr, FA); ab = oof_platt(tr, FA)
        d = D[ev]; p = calib(m.predict_proba(mat(d, FA))[:, 1], ab)
        A[ev] = {"terrain": scores(d["y"], p),
                 "hand_only_auc": round(float(roc_auc_score(d["y"], -d["cols"]["hand"])), 4),
                 "dist_only_auc": round(float(roc_auc_score(d["y"], -d["cols"]["dist_channel_m"])), 4),
                 "hand_bands": hand_bands(d["y"], d["cols"]["hand"], p)}
        print("A", ev, A[ev]["terrain"], A[ev]["hand_only_auc"], A[ev]["dist_only_auc"], flush=True)
    res["A_leave_one_flood_out"] = A

    # B. Oct 11 unseen, the app case
    d = D["oct11"]; y = d["y"]; km = d["cols"]["river_km"]
    pv2 = app_p_v2("oct11", d)
    ok = np.isfinite(pv2)
    tr_t = [D["aug26"], D["ahr"], D["derna"]]
    mt = fit(tr_t, FA); abt = oof_platt(tr_t, FA); pt = calib(mt.predict_proba(mat(d, FA))[:, 1], abt)
    mf = fit([D["aug26"]], FB); abf = oof_platt([D["aug26"]], FB); pf = calib(mf.predict_proba(mat(d, FB))[:, 1], abf)
    B = {"rows_with_v2_score": int(ok.sum()), "rows": int(len(y)),
         "v2_app": scores(y[ok], pv2[ok]), "terrain": scores(y[ok], pt[ok]), "fb": scores(y[ok], pf[ok]),
         "hand_only": scores(y[ok], -d["cols"]["hand"][ok]), "dist_only": scores(y[ok], -d["cols"]["dist_channel_m"][ok]),
         "footprint_rule_minus_freeboard": scores(y[ok], -d["cols"]["freeboard"][ok]),
         "auc_diff_vs_v2_block_bootstrap": {
             "terrain": block_boot_diff(y[ok], pt[ok], pv2[ok], km[ok], a.boot),
             "fb": block_boot_diff(y[ok], pf[ok], pv2[ok], km[ok], a.boot)},
         "hand_bands": {"v2_app": hand_bands(y[ok], d["cols"]["hand"][ok], pv2[ok]),
                        "terrain": hand_bands(y[ok], d["cols"]["hand"][ok], pt[ok]),
                        "fb": hand_bands(y[ok], d["cols"]["hand"][ok], pf[ok])},
         "expected_affected_km2": {"observed": round(float(y[ok].sum()) * 900 / 1e6, 2),
                                   "v2_app": round(float(pv2[ok].sum()) * 900 / 1e6, 2),
                                   "terrain": round(float(pt[ok].sum()) * 900 / 1e6, 2),
                                   "fb": round(float(pf[ok].sum()) * 900 / 1e6, 2)}}
    # Aug 26 for reference only (v2 was trained on Aug 26 buildings, so this is not a fair test for v2)
    d26 = D["aug26"]; pv2_26 = app_p_v2("aug26", d26); ok26 = np.isfinite(pv2_26)
    B["aug26_reference_not_a_test"] = {"v2_app": scores(d26["y"][ok26], pv2_26[ok26]),
                                       "terrain_lofo": A["aug26"]["terrain"]}
    passed = {k: B[k]["roc_auc"] >= B["v2_app"]["roc_auc"] and B[k]["brier"] <= B["v2_app"]["brier"] for k in ("terrain", "fb")}
    winner = max([k for k, v in passed.items() if v], key=lambda k: B[k]["roc_auc"], default=None)
    B["passes_rule"] = passed; B["decision"] = winner or "keep v2"
    res["B_oct11_unseen_app_case"] = B
    print("B", json.dumps({k: B[k] for k in ("v2_app", "terrain", "fb", "hand_only", "passes_rule", "decision")}), flush=True)

    if winner:
        parts = [D[e] for e in (EVENTS if winner == "terrain" else ["aug26", "oct11"])]
        names = FA if winner == "terrain" else FB
        m = fit(parts, names); ab = oof_platt(parts, names)
        bundle = {"version": f"area_{winner}", "features": names, "model": m, "calibration": {"a": ab[0], "b": ab[1]},
                  "trained_on": [p["label_source"] for p in parts], "arch": platform.machine(),
                  "created_utc": res["created_utc"], "target": "cell centre inside observed flood/debris extent",
                  "note": "s390x pickle; needs an envelope (freeboard) if 'freeboard' in features"}
        joblib.dump(bundle, os.path.join(OUT, f"area_{winner}.joblib"))
        res["final_model"] = {"file": f"models/area/area_{winner}.joblib", "trained_on": bundle["trained_on"], "platt": ab}
    res["runtime_s"] = round(time.time() - t0, 1)
    json.dump(res, open(os.path.join(OUT, "metrics.json"), "w"), indent=2)
    print("done", res["runtime_s"], "s; decision:", B["decision"])


if __name__ == "__main__":
    main()
