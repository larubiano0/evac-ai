"""Train and evaluate the damage model (packet B): v1 (local terrain) and v2 (+ freeboard).

Spatial holdout by river km: split at the median river km of the positives, drop a 2 km gap on each side,
train on one side and test on the other, in both directions. Baselines on the same test rows:
  hand_rank      rank by -HAND (any height threshold)
  footprint_rule the engine's rule HAND <= envelope height(km), a 0/1 score (v2 envelope)
  freeboard_rank rank by -freeboard (the same rule with a continuous margin)
  logreg         logistic regression on the v1 features (sanity check)
The Aug 26 flood line for freeboard is reconstructed from damage marks (p90 HAND of affected buildings per
5 km bin), fitted on the TRAIN side only in each holdout direction (see openspec design D7).
Feature sets (engine/damage_model.py FEATURES_V1/V2) were chosen by scripts/damage/ablation.py.
Final v1/v2 are fitted on all rows <= 500 m. Writes models/damage/{v1,v2}.joblib, metrics.json,
aug26_damage_envelope.json, train_pred_sample.json.

Run on the VM from the repo root:  python3 scripts/damage/train_eval.py
"""
import argparse, json, os, platform, sys, time
from datetime import datetime, timezone
import numpy as np
import joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.inspection import permutation_importance

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from engine import damage_model as dm
from engine.flood import FloodEnvelope

GAP_KM = 2.0
BIN_KM, MIN_POS, Q = 5.0, 30, 0.90
HGB = dict(max_depth=4, learning_rate=0.05, max_iter=300, l2_regularization=1.0, random_state=0)


def fit_envelope(km, hand, y, is_building):
    """Damage-mark flood line: p90 HAND of affected buildings per BIN_KM bin with >= MIN_POS positives."""
    m = (y == 1) & is_building
    knots = []
    for lo in np.arange(0.0, np.nanmax(km) + BIN_KM, BIN_KM):
        s = m & (km >= lo) & (km < lo + BIN_KM)
        if s.sum() >= MIN_POS:
            knots.append((float(lo + BIN_KM / 2), float(np.quantile(hand[s], Q)), int(s.sum())))
    if not knots:
        raise RuntimeError("no bin has enough positives to reconstruct the flood line")
    return FloodEnvelope([(0.0, 0.0), (1.0, 1.0)], [(k, h) for k, h, _ in knots]), knots


def hgb(names):
    return HistGradientBoostingClassifier(categorical_features=[names.index("kind")], **HGB)


def mat(cols, names):
    return np.column_stack([cols[n] for n in names])


def metrics(y, score, kind=None):
    """Ranking metrics; ties in the score are broken randomly-but-fixed so binary rules are fair."""
    y = np.asarray(y); score = np.asarray(score, float)
    out = {"n": int(len(y)), "positives": int(y.sum()), "roc_auc": float(roc_auc_score(y, score)),
           "pr_auc": float(average_precision_score(y, score)), "base_rate": float(y.mean())}
    order = np.lexsort((np.random.default_rng(0).random(len(y)), -score))
    ys = y[order]
    for f in (0.10, 0.20, 0.30):
        k = int(round(f * len(y)))
        out[f"recall_top{int(f * 100)}pct"] = float(ys[:k].sum() / max(y.sum(), 1))
    k = int(y.sum())
    out["flagged_at_k_eq_positives"] = {"k": k, "flagged": int(ys[:k].sum()), "of": k,
                                        "precision": float(ys[:k].mean()) if k else None}
    if kind is not None:
        for kd in ("building", "bridge"):
            s = kind == kd
            if s.sum() and 0 < y[s].sum() < s.sum():
                out[f"roc_auc_{kd}"] = float(roc_auc_score(y[s], score[s]))
                out[f"n_{kd}"] = int(s.sum()); out[f"positives_{kd}"] = int(y[s].sum())
    return out


def reliability(y, p, bins=10):
    edges = np.linspace(0, 1, bins + 1); out = []
    for a, b in zip(edges[:-1], edges[1:]):
        s = (p >= a) & (p < b if b < 1 else p <= b)
        if s.sum():
            out.append({"bin": [round(a, 1), round(b, 1)], "n": int(s.sum()), "mean_p": float(p[s].mean()),
                        "observed": float(y[s].mean())})
    return out


def holdout(cols, y, kind, split, train_low, with_v2, importance=True):
    km, hand = cols["river_km"], cols["hand"]
    tr = (km < split - GAP_KM) if train_low else (km > split + GAP_KM)
    te = (km > split + GAP_KM) if train_low else (km < split - GAP_KM)
    res = {"train": {"n": int(tr.sum()), "positives": int(y[tr].sum())},
           "test": {"n": int(te.sum()), "positives": int(y[te].sum())}}
    X1 = mat(cols, dm.FEATURES_V1)
    t = time.time()
    m1 = hgb(dm.FEATURES_V1).fit(X1[tr], y[tr]); res["train_s_v1"] = round(time.time() - t, 2)
    p1 = m1.predict_proba(X1[te])[:, 1]
    res["_oof"] = {"test_mask": te, "v1": p1}
    res["v1"] = metrics(y[te], p1, kind[te]); res["v1"]["reliability"] = reliability(y[te], p1)
    res["hand_rank"] = metrics(y[te], -hand[te], kind[te])
    lr = make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000)).fit(X1[tr], y[tr])
    res["logreg"] = metrics(y[te], lr.predict_proba(X1[te])[:, 1], kind[te])
    if importance:
        pi = permutation_importance(m1, X1[te], y[te], scoring="roc_auc", n_repeats=5, random_state=0, n_jobs=1)
        res["v1"]["perm_importance_auc_drop"] = {n: round(float(v), 4) for n, v in
                                                 sorted(zip(dm.FEATURES_V1, pi.importances_mean), key=lambda z: -z[1])}
    if with_v2:
        env, knots = fit_envelope(km[tr], hand[tr], y[tr], kind[tr] == "building")
        fb = hand - env.height(km)
        X2 = mat({**cols, "freeboard": fb}, dm.FEATURES_V2)
        t = time.time()
        m2 = hgb(dm.FEATURES_V2).fit(X2[tr], y[tr]); res["train_s_v2"] = round(time.time() - t, 2)
        p2 = m2.predict_proba(X2[te])[:, 1]
        res["_oof"]["v2"] = p2
        res["v2"] = metrics(y[te], p2, kind[te]); res["v2"]["reliability"] = reliability(y[te], p2)
        res["footprint_rule"] = metrics(y[te], (fb[te] <= 0).astype(float), kind[te])
        res["freeboard_rank"] = metrics(y[te], -fb[te], kind[te])
        res["envelope_knots_train_side"] = [{"km": k, "height_m": round(h, 2), "n_pos": n} for k, h, n in knots]
        if importance:
            pi = permutation_importance(m2, X2[te], y[te], scoring="roc_auc", n_repeats=5, random_state=0, n_jobs=1)
            res["v2"]["perm_importance_auc_drop"] = {n: round(float(v), 4) for n, v in
                                                     sorted(zip(dm.FEATURES_V2, pi.importances_mean), key=lambda z: -z[1])}
    return res


def subset(cols, m):
    return {k: v[m] for k, v in cols.items()}


def platt(holdouts, y, ver):
    """Platt scaling p_cal = sigmoid(a*logit(p) + b), fitted on the pooled out-of-fold (spatial) predictions."""
    p = np.concatenate([h["_oof"][ver] for h in holdouts])
    yy = np.concatenate([y[h["_oof"]["test_mask"]] for h in holdouts])
    z = dm.logit(p).reshape(-1, 1)
    lr = LogisticRegression(C=1e6, max_iter=1000).fit(z, yy)
    a, b = float(lr.coef_[0, 0]), float(lr.intercept_[0])
    pc = dm.sigmoid(a * z[:, 0] + b)
    return {"a": a, "b": b, "fitted_on": "pooled out-of-fold spatial-holdout predictions (both directions)",
            "n": int(len(yy)), "reliability_before": reliability(yy, p), "reliability_after": reliability(yy, pc),
            "brier_before": float(np.mean((p - yy) ** 2)), "brier_after": float(np.mean((pc - yy) ** 2))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default=os.path.expanduser("~/work-agent-lcpizani/out/table_trishuli.npz"))
    a = ap.parse_args()
    t_all = time.time()
    t = np.load(a.table)
    names = list(t["cols"])
    assert names == dm.FEATURES_ALL, names
    cols_all = {n: t["X"][:, i] for i, n in enumerate(names)}
    y_all, kind_all, des_all = t["y"].astype(int), t["kind"], t["destroyed_only"].astype(int)
    m = cols_all["dist_channel_m"] <= dm.MAX_DIST_M
    cols, y, kind, des = subset(cols_all, m), y_all[m], kind_all[m], des_all[m]
    split = float(np.median(cols["river_km"][y == 1]))

    out = {"version_trained": datetime.now(timezone.utc).isoformat(timespec="seconds"), "arch": platform.machine(),
           "python": platform.python_version(), "event": "Aug 26 2026 Bhotekoshi-Trishuli (OSM damage labels)",
           "corridor_max_dist_m": dm.MAX_DIST_M, "split_km": split, "gap_km": GAP_KM,
           "envelope_method": f"p{int(Q * 100)} HAND of affected buildings per {BIN_KM:g} km bin (>= {MIN_POS} positives)",
           "hgb_params": HGB, "features_v1": dm.FEATURES_V1, "features_v2": dm.FEATURES_V2,
           "feature_selection": "scripts/damage/ablation.py (models/damage/ablation.json): mean holdout ROC AUC",
           "rows": {"n": int(len(y)), "positives": int(y.sum()),
                    "buildings": int((kind == "building").sum()), "bridges": int((kind == "bridge").sum())}}
    out["holdout_500m"] = {"upstream_to_downstream": holdout(cols, y, kind, split, True, True),
                           "downstream_to_upstream": holdout(cols, y, kind, split, False, True)}
    hs = list(out["holdout_500m"].values())
    calib = {ver: platt(hs, y, ver) for ver in ("v1", "v2")}
    out["calibration"] = calib
    for h in hs:
        h.pop("_oof")
    split2 = float(np.median(cols_all["river_km"][y_all == 1]))
    keep2 = ("train", "test", "v1", "hand_rank", "logreg")
    out["holdout_2km"] = {d: {k: v for k, v in holdout(cols_all, y_all, kind_all, split2, lo, False, False).items()
                              if k in keep2}
                          for d, lo in (("upstream_to_downstream", True), ("downstream_to_upstream", False))}
    keep = ~((y == 1) & (des == 0))                      # destroyed-only: drop damaged-but-standing buildings
    out["holdout_500m_destroyed_only"] = {
        d: {k: v for k, v in holdout(subset(cols, keep), des[keep], kind[keep], split, lo, False, False).items()
            if k in ("train", "test", "v1", "hand_rank")}
        for d, lo in (("upstream_to_downstream", True), ("downstream_to_upstream", False))}

    # final models on all rows <= 500 m
    os.makedirs(dm.MODEL_DIR, exist_ok=True)
    env, knots = fit_envelope(cols["river_km"], cols["hand"], y, kind == "building")
    cols_fb = {**cols, "freeboard": cols["hand"] - env.height(cols["river_km"])}
    meta = {k: out[k] for k in ("version_trained", "arch", "event", "corridor_max_dist_m", "hgb_params")}
    meta["n_rows"], meta["n_positives"] = int(len(y)), int(y.sum())
    timing = {}
    rng = np.random.default_rng(1); sample = np.sort(rng.choice(len(y), 300, replace=False))
    preds = {"rows_lonlat": t["lonlat"][m][sample].tolist(), "kind": kind[sample].tolist()}
    for ver, nn in (("v1", dm.FEATURES_V1), ("v2", dm.FEATURES_V2)):
        XX = mat(cols_fb, nn)
        t0 = time.time(); mod = hgb(nn).fit(XX, y); timing[f"train_final_{ver}_s"] = round(time.time() - t0, 3)
        bundle = {"model": mod, "features": nn, "version": ver, "meta": meta,
                  "calibration": {"a": calib[ver]["a"], "b": calib[ver]["b"]}}
        t0 = time.time(); p = dm.calibrated(bundle, mod.predict_proba(XX)[:, 1])
        timing[f"predict_all_{ver}_s"] = round(time.time() - t0, 3)
        if ver == "v2":
            bundle["aug26_envelope_knots"] = [(k, h) for k, h, _ in knots]
        joblib.dump(bundle, os.path.join(dm.MODEL_DIR, f"{ver}.joblib"))
        preds[f"p_{ver}"] = [round(float(v), 6) for v in p[sample]]
        out[f"final_{ver}"] = {"n_iter": int(mod.n_iter_), "train_auc_in_sample": float(roc_auc_score(y, p))}
    json.dump({"method": out["envelope_method"], "fitted_on": "all Aug 26 rows <= 500 m",
               "knots": [{"km": k, "height_m": round(h, 2), "n_pos": n} for k, h, n in knots],
               "note": "Reconstructed from damage marks because replay/aug26.json has no usable height knot inside "
                       "the Trishuli grid. Engine FloodEnvelope interpolation: held constant before the first knot, "
                       "decays to 3 m (30 km scale) after the last."},
              open(os.path.join(dm.MODEL_DIR, "aug26_damage_envelope.json"), "w"), indent=2)
    json.dump(preds, open(os.path.join(dm.MODEL_DIR, "train_pred_sample.json"), "w"))
    out["timing_s"] = {**timing, "total_script": round(time.time() - t_all, 2)}
    json.dump(out, open(os.path.join(dm.MODEL_DIR, "metrics.json"), "w"), indent=2)

    for d, r in out["holdout_500m"].items():
        print(f"== {d}: train {r['train']} test {r['test']}")
        for k in ("v1", "v2", "logreg", "hand_rank", "footprint_rule", "freeboard_rank"):
            v = r[k]
            print(f"  {k:15s} AUC {v['roc_auc']:.3f}  PR-AUC {v['pr_auc']:.3f}  top20% recall {v['recall_top20pct']:.3f}  "
                  f"flagged {v['flagged_at_k_eq_positives']['flagged']}/{v['flagged_at_k_eq_positives']['of']}"
                  + (f"  bridge AUC {v['roc_auc_bridge']:.3f}" if "roc_auc_bridge" in v else ""))
        print("  v2 importance:", list(r["v2"]["perm_importance_auc_drop"].items())[:5])
    for d, r in out["holdout_2km"].items():
        print(f"== 2km {d}: v1 AUC {r['v1']['roc_auc']:.3f}  hand {r['hand_rank']['roc_auc']:.3f}")
    for d, r in out["holdout_500m_destroyed_only"].items():
        print(f"== destroyed-only {d}: v1 AUC {r['v1']['roc_auc']:.3f}  hand {r['hand_rank']['roc_auc']:.3f}")
    print("knots", [(round(k, 1), round(h, 1)) for k, h, _ in knots])
    print("final", out["final_v1"], out["final_v2"])
    for ver in ("v1", "v2"):
        c = calib[ver]
        print(f"calibration {ver}: a={c['a']:.3f} b={c['b']:.3f} brier {c['brier_before']:.4f} -> {c['brier_after']:.4f}")
        print("   after:", " ".join(f"[{r['bin'][0]:.1f}] p={r['mean_p']:.2f}/obs={r['observed']:.2f} (n={r['n']})"
                                    for r in c["reliability_after"]))
    print("timing", out["timing_s"])


if __name__ == "__main__":
    main()
