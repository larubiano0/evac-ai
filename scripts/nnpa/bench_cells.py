"""CPU vs Telum NNPA (zDNN) scoring of the real per-cell batch from profile_scenario.py.

    SNAPML_ZDNN_LIB=.../libzdnn.so.0 EVAC_BUILD_DIR=... venv-snap/bin/python scripts/nnpa/bench_cells.py

The production model (models/area/area_fb.joblib) is sklearn HistGradientBoosting, 300 trees of depth 4, which
Snap ML cannot load directly. So we fit a Snap ML booster of the same shape on the same cell features, with
area_fb's own 0/1 call as the target (a distillation, not a new model), then time on the same rows:
  1. sklearn HGB predict_proba (what production runs),
  2. Snap ML on CPU (its default tree predictor; "compress_trees" asserted in 1.17.2 on s390x),
  3. Snap ML on the NNPA (tree_format="zdnn_tensors").
Each timing = best of 5 after one warm-up call. Prints one JSON line per batch.
"""
import json
import os
import sys
import time

import joblib
import numpy as np
from sklearn.metrics import roc_auc_score

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
REPO = os.path.join(os.path.dirname(__file__), "..", "..")


def best(fn, X, n=5):
    fn(X)
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn(X)
        ts.append(time.perf_counter() - t0)
    return min(ts)


def main():
    import snapml
    build = os.environ.get("EVAC_BUILD_DIR", ".")
    hgb = joblib.load(os.path.join(REPO, "models/area/area_fb.joblib"))["model"]
    for v in ("trishuli", "budhi"):
        X = np.load(os.path.join(build, f"nnpa_cells_{v}.npz"))["X"].astype(np.float32)
        p_ref = hgb.predict_proba(X)[:, 1]
        y = (p_ref >= np.median(p_ref)).astype(np.float32)
        snap = snapml.BoostingMachineClassifier(num_round=300, max_depth=4, learning_rate=0.05, n_jobs=3,
                                                random_state=0)
        t0 = time.perf_counter()
        snap.fit(X, y)
        fit_s = time.perf_counter() - t0
        out = {"valley": v, "rows": len(X), "features": X.shape[1], "snap_fit_s": round(fit_s, 2)}
        batches = {"": X, "_x10": np.tile(X, (10, 1))}
        for tag, Xb in batches.items():
            out["rows" + tag] = len(Xb)
            out["cpu_sklearn_hgb_s" + tag] = round(best(hgb.predict_proba, Xb), 4)
            out["cpu_snap_s" + tag] = round(best(snap.predict_proba, Xb), 4)
        p_cpu = snap.predict_proba(X)[:, 1]
        snap.optimize_trees(tree_format="zdnn_tensors")
        for tag, Xb in batches.items():
            out["nnpa_snap_s" + tag] = round(best(snap.predict_proba, Xb), 4)
        p_nnpa = snap.predict_proba(X)[:, 1]
        out["auc_vs_area_fb_call_cpu"] = round(roc_auc_score(y, p_cpu), 4)
        out["auc_vs_area_fb_call_nnpa"] = round(roc_auc_score(y, p_nnpa), 4)
        out["max_abs_diff_cpu_vs_nnpa"] = float(np.abs(p_cpu - p_nnpa).max())
        print(json.dumps(out), flush=True)


if __name__ == "__main__":
    main()
