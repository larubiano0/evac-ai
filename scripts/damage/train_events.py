"""Retrain the damage model on three real floods (v3) and test whether it transfers.

Events (all real labels, see docs/data/events/SOURCES_*.md and docs/models/damage.md):
  aug26  Bhotekoshi-Trishuli, Nepal, 26 Aug 2026  OSM/HOT damage tags (buildings + bridges)
  ahr    Ahr valley, Germany, 14-15 Jul 2021       4TU damage grades, rater 1, y = D1+ (buildings)
  derna  Wadi Derna, Libya, 10-11 Sep 2023         UNOSAT damaged buildings + OSM negatives (buildings)
Rows <= 500 m from the flood channel (dm.MAX_DIST_M), as for v1/v2.

Features: FEATURES_X = v1 features minus ls_500m (the 2015 landslide inventory exists only for Nepal, so it is 0
for Ahr/Derna and would just encode "which event"); v3 adds freeboard (FEATURES_X2). Each event's flood line for
freeboard is its own damage-mark envelope (train_eval.fit_envelope), fitted only on rows used for training.
Each event gets equal total sample weight, so Nepal's 23k rows do not drown Derna's 1.2k.

Tests (decided before looking at results):
  A. leave-one-event-out, FEATURES_X (no freeboard: the test event's flood line would come from its labels)
  B. Nepal spatial holdout (same split/gap as train_eval.py), both directions:
       v2           Nepal train side only, FEATURES_V2            (the model the app uses now)
       nepal_only_x Nepal train side only, FEATURES_X2            (control: effect of dropping ls_500m)
       v3           Nepal train side + all of Ahr + Derna, FEATURES_X2
  C. Oct 11 Budhi Gandaki (never trained on): scripts/damage/oct11_check.py, only if v3 passes B.
Rule: the app switches from v2 to v3 only if v3's mean B AUC >= v2's and C is not worse.
  A2 (added AFTER seeing A, labelled post-hoc): leave-one-event-out on buildings only with monotone constraints
     (risk may only fall with HAND and with distance), all features vs HAND + distance only.
Writes models/damage/events_metrics.json; the v3 model goes to ~/work-agent-lcpizani/out/v3.joblib (not the
app's model dir) because it did not pass B (see docs/models/damage.md).

Run on the VM from the repo root:  python3 scripts/damage/train_events.py
"""
import json, os, platform, sys, time
from datetime import datetime, timezone
import numpy as np
import joblib
from sklearn.linear_model import LogisticRegression

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from engine import damage_model as dm
import train_eval as te

W = os.path.expanduser("~/work-agent-lcpizani")
TABLES = {"aug26": f"{W}/out/table_trishuli.npz", "ahr": f"{W}/events/ahr/table.npz", "derna": f"{W}/events/derna/table.npz"}
FEATURES_X = [f for f in dm.FEATURES_V1 if f != "ls_500m"]
FEATURES_X2 = FEATURES_X + ["freeboard"]


def load_event(path):
    t = np.load(path)
    assert list(t["cols"]) == dm.FEATURES_ALL, list(t["cols"])
    cols = {n: t["X"][:, i] for i, n in enumerate(dm.FEATURES_ALL)}
    m = cols["dist_channel_m"] <= dm.MAX_DIST_M
    return {"cols": {k: v[m] for k, v in cols.items()}, "y": t["y"][m].astype(int), "kind": t["kind"][m]}


def with_freeboard(ev, fit_mask=None):
    """Add freeboard from this event's damage-mark envelope fitted on rows fit_mask (default all)."""
    c, y, k = ev["cols"], ev["y"], ev["kind"]
    fm = np.ones(len(y), bool) if fit_mask is None else fit_mask
    env, knots = te.fit_envelope(c["river_km"][fm], c["hand"][fm], y[fm], k[fm] == "building")
    return {**c, "freeboard": c["hand"] - env.height(c["river_km"])}, knots


def stack(parts, names):
    """parts: list of (cols, y, kind). Returns X, y, kind, weights (equal total weight per part)."""
    X = np.vstack([te.mat(c, names) for c, _, _ in parts])
    y = np.concatenate([yy for _, yy, _ in parts]); kind = np.concatenate([kk for _, _, kk in parts])
    w = np.concatenate([np.full(len(yy), len(y) / (len(parts) * len(yy))) for _, yy, _ in parts])
    return X, y, kind, w


def fit(names, X, y, w):
    return te.hgb(names).fit(X, y, sample_weight=w)


def short(m):
    return {k: m[k] for k in ("n", "positives", "roc_auc", "pr_auc", "recall_top20pct", "base_rate")
            } | {k: m[k] for k in m if k.startswith("roc_auc_")}


def main():
    t_all = time.time()
    ev = {k: load_event(p) for k, p in TABLES.items()}
    out = {"version_trained": datetime.now(timezone.utc).isoformat(timespec="seconds"), "arch": platform.machine(),
           "features_x": FEATURES_X, "features_v3": FEATURES_X2, "hgb_params": te.HGB,
           "weighting": "equal total sample weight per event",
           "rows": {k: {"n": int(len(e["y"])), "positives": int(e["y"].sum()),
                        "bridges": int((e["kind"] == "bridge").sum())} for k, e in ev.items()}}

    # ---- A. leave one event out (no freeboard) ----
    A = {}
    for test in ev:
        trn = [k for k in ev if k != test]
        X, y, kind, w = stack([(ev[k]["cols"], ev[k]["y"], ev[k]["kind"]) for k in trn], FEATURES_X)
        m = fit(FEATURES_X, X, y, w)
        Xt = te.mat(ev[test]["cols"], FEATURES_X); yt, kt = ev[test]["y"], ev[test]["kind"]
        r = {"trained_on": trn, "pooled": short(te.metrics(yt, m.predict_proba(Xt)[:, 1], kt)),
             "hand_rank": short(te.metrics(yt, -ev[test]["cols"]["hand"], kt)),
             "dist_rank": short(te.metrics(yt, -ev[test]["cols"]["dist_channel_m"], kt))}
        for one in trn:                                   # each single training event alone
            X1 = te.mat(ev[one]["cols"], FEATURES_X)
            m1 = fit(FEATURES_X, X1, ev[one]["y"], np.ones(len(X1)))
            r[f"only_{one}"] = short(te.metrics(yt, m1.predict_proba(Xt)[:, 1], kt))
        A[test] = r
    out["A_leave_one_event_out"] = A

    # ---- A2 (post-hoc): buildings only, monotone in HAND and distance ----
    from sklearn.ensemble import HistGradientBoostingClassifier
    evb = {}
    for k, e in ev.items():
        b_ = e["kind"] == "building"
        evb[k] = ({c: v[b_] for c, v in e["cols"].items()}, e["y"][b_], e["kind"][b_])
    fb = [f for f in FEATURES_X if f != "kind"]
    A2 = {}
    for name, feats, mc in (("unconstrained", fb, None),
                            ("monotone_hand_dist", fb, [-1 if f in ("hand", "dist_channel_m") else 0 for f in fb]),
                            ("hand_dist_only_monotone", ["hand", "dist_channel_m"], [-1, -1])):
        A2[name] = {}
        for test in evb:
            X, y, _, w = stack([evb[k] for k in evb if k != test], feats)
            m = HistGradientBoostingClassifier(monotonic_cst=mc, **te.HGB).fit(X, y, sample_weight=w)
            A2[name][test] = float(te.metrics(evb[test][1], m.predict_proba(te.mat(evb[test][0], feats))[:, 1])["roc_auc"])
    A2["hand_rank"] = {t_: float(te.metrics(evb[t_][1], -evb[t_][0]["hand"])["roc_auc"]) for t_ in evb}
    out["A2_post_hoc_monotone_buildings"] = A2

    # ---- B. Nepal spatial holdout ----
    n = ev["aug26"]; km = n["cols"]["river_km"]
    split = float(np.median(km[n["y"] == 1]))
    others = {}
    for k in ("ahr", "derna"):
        c, knots = with_freeboard(ev[k])
        others[k] = (c, ev[k]["y"], ev[k]["kind"]); out.setdefault("envelopes", {})[k] = knots
    B, oof = {}, {"v2": [], "nepal_only_x": [], "v3": [], "y": []}
    for d, low in (("upstream_to_downstream", True), ("downstream_to_upstream", False)):
        tr = (km < split - te.GAP_KM) if low else (km > split + te.GAP_KM)
        ts = (km > split + te.GAP_KM) if low else (km < split - te.GAP_KM)
        cn, _ = with_freeboard(n, tr)
        sub = lambda m_: {k: v[m_] for k, v in cn.items()}
        yt, kt = n["y"][ts], n["kind"][ts]
        r = {"train_nepal": {"n": int(tr.sum()), "positives": int(n["y"][tr].sum())},
             "test": {"n": int(ts.sum()), "positives": int(yt.sum())}}
        for name, feats, parts in (("v2", dm.FEATURES_V2, [(sub(tr), n["y"][tr], n["kind"][tr])]),
                                   ("nepal_only_x", FEATURES_X2, [(sub(tr), n["y"][tr], n["kind"][tr])]),
                                   ("v3", FEATURES_X2, [(sub(tr), n["y"][tr], n["kind"][tr])] + list(others.values()))):
            X, y, _, w = stack(parts, feats)
            p = fit(feats, X, y, w).predict_proba(te.mat(sub(ts), feats))[:, 1]
            r[name] = short(te.metrics(yt, p, kt)); oof[name].append(p)
        r["hand_rank"] = short(te.metrics(yt, -cn["hand"][ts], kt))
        oof["y"].append(yt)
        B[d] = r
    for name in ("v2", "nepal_only_x", "v3"):
        B[f"mean_auc_{name}"] = float(np.mean([B[d][name]["roc_auc"] for d in ("upstream_to_downstream", "downstream_to_upstream")]))
    out["B_nepal_spatial_holdout"] = B

    # ---- final v3 on everything, Platt-calibrated on B's Nepal out-of-fold v3 predictions ----
    p_oof, y_oof = np.concatenate(oof["v3"]), np.concatenate(oof["y"])
    z = dm.logit(p_oof).reshape(-1, 1)
    lr = LogisticRegression(C=1e6, max_iter=1000).fit(z, y_oof)
    a, b = float(lr.coef_[0, 0]), float(lr.intercept_[0])
    pc = dm.sigmoid(a * z[:, 0] + b)
    out["calibration_v3"] = {"a": a, "b": b, "fitted_on": "Nepal out-of-fold spatial-holdout v3 predictions",
                             "brier_before": float(np.mean((p_oof - y_oof) ** 2)),
                             "brier_after": float(np.mean((pc - y_oof) ** 2)),
                             "reliability_after": te.reliability(y_oof, pc)}
    cn_all, knots_n = with_freeboard(n)
    X, y, kind, w = stack([(cn_all, n["y"], n["kind"])] + list(others.values()), FEATURES_X2)
    t0 = time.time(); mod = fit(FEATURES_X2, X, y, w); out["train_final_v3_s"] = round(time.time() - t0, 2)
    bundle = {"model": mod, "features": FEATURES_X2, "version": "v3",
              "meta": {k: out[k] for k in ("version_trained", "arch", "hgb_params", "weighting")} |
                      {"events": list(TABLES), "rows": out["rows"], "corridor_max_dist_m": dm.MAX_DIST_M},
              "calibration": {"a": a, "b": b}}
    os.makedirs(f"{W}/out", exist_ok=True)
    joblib.dump(bundle, f"{W}/out/v3.joblib")
    out["timing_total_s"] = round(time.time() - t_all, 1)
    json.dump(out, open(os.path.join(dm.MODEL_DIR, "events_metrics.json"), "w"), indent=2)

    print("rows", out["rows"])
    print("== A. leave one event out (ROC AUC on the held-out event)")
    for t_, r in A.items():
        extra = "  ".join(f"{k} {v['roc_auc']:.3f}" for k, v in r.items() if k.startswith("only_"))
        print(f"  test {t_:6s} pooled {r['pooled']['roc_auc']:.3f}  {extra}  | HAND {r['hand_rank']['roc_auc']:.3f}"
              f"  distance {r['dist_rank']['roc_auc']:.3f}  (base rate {r['pooled']['base_rate']:.2f})")
    print("== A2 (post-hoc) buildings only, ROC AUC on the held-out event")
    for name, r in A2.items():
        print(f"  {name:26s} " + "  ".join(f"{t_} {v:.3f}" for t_, v in r.items()))
    print("== B. Nepal spatial holdout (ROC AUC)")
    for d in ("upstream_to_downstream", "downstream_to_upstream"):
        r = B[d]
        print(f"  {d:24s} v2 {r['v2']['roc_auc']:.3f}  nepal_only_x {r['nepal_only_x']['roc_auc']:.3f}  "
              f"v3 {r['v3']['roc_auc']:.3f}  HAND {r['hand_rank']['roc_auc']:.3f}"
              + (f"  | bridges v2 {r['v2'].get('roc_auc_bridge', float('nan')):.3f} v3 {r['v3'].get('roc_auc_bridge', float('nan')):.3f}"))
    print(f"  mean: v2 {B['mean_auc_v2']:.3f}  nepal_only_x {B['mean_auc_nepal_only_x']:.3f}  v3 {B['mean_auc_v3']:.3f}")
    c = out["calibration_v3"]
    print(f"v3 calibration a={a:.3f} b={b:.3f} brier {c['brier_before']:.4f} -> {c['brier_after']:.4f}")
    print("total", out["timing_total_s"], "s")


if __name__ == "__main__":
    main()
