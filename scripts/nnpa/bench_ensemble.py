"""What-if flood heights for one real scenario: CPU vs Telum NNPA, and how close the neural stand-in is.

    EVAC_NNPA_LIB=.../zdnn_mlp.so EVAC_BUILD_DIR=... python3 scripts/nnpa/bench_ensemble.py [valley] [n]

Scores every 30 m corridor cell of the valley's prediction scenario (saved by profile_scenario.py) under n flood
heights within the engine's +-30% band, three ways:
  1. area_fb, the production 300-tree model, on the CPU (the exact answer, what this costs today),
  2. the neural stand-in (models/surrogate/area_fb_mlp.npz) on the CPU (numpy/OpenBLAS),
  3. the same neural stand-in on the NNPA (zDNN).
Prints one JSON line: wall time and cells/s for each, and the error of the per-cell bands vs the exact answer.
"""
import json
import os
import sys
import time

import joblib
import numpy as np

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, REPO)
from engine import damage_model as dm  # noqa: E402
from engine.surrogate import Surrogate  # noqa: E402


def main():
    valley = sys.argv[1] if len(sys.argv) > 1 else "trishuli"
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 100
    X = np.load(os.path.join(os.environ.get("EVAC_BUILD_DIR", "."), f"nnpa_cells_{valley}.npz"))["X"].astype(np.float32)
    bundle = joblib.load(os.path.join(REPO, "models/area/area_fb.joblib"))
    net = Surrogate()
    assert net.backend == "nnpa", "set EVAC_NNPA_LIB to the built zdnn_mlp.so"

    def exact(rows):
        return dm.calibrated(bundle, bundle["model"].predict_proba(rows)[:, 1]).astype(np.float32)

    runs = {}
    for name, fn in (("cpu_area_fb_trees", exact), ("cpu_neural", net.predict_cpu), ("nnpa_neural", net.predict_nnpa)):
        net.height_ensemble(X[:4096], n=2, predict=fn)                 # warm-up
        t0 = time.perf_counter()
        runs[name] = net.height_ensemble(X, n=n, predict=fn)
        runs[name]["s"] = time.perf_counter() - t0
    ref = runs["cpu_area_fb_trees"]
    out = {"valley": valley, "cells": len(X), "flood_heights": n, "rows_scored": len(X) * n}
    for name, r in runs.items():
        out[name + "_s"] = round(r["s"], 2)
        out[name + "_rows_per_s"] = int(len(X) * n / r["s"])
    out["speedup_nnpa_vs_cpu_trees"] = round(ref["s"] / runs["nnpa_neural"]["s"], 1)
    out["speedup_nnpa_vs_cpu_neural"] = round(runs["cpu_neural"]["s"] / runs["nnpa_neural"]["s"], 1)
    for name in ("cpu_neural", "nnpa_neural"):
        r = runs[name]
        for k in ("p_mean", "p_lo", "p_hi"):
            out[f"{name}_{k}_mae"] = round(float(np.abs(r[k] - ref[k]).mean()), 4)
        out[f"{name}_band_off_by_0.1_share"] = round(float(((np.abs(r["p_lo"] - ref["p_lo"]) > 0.1) |
                                                             (np.abs(r["p_hi"] - ref["p_hi"]) > 0.1)).mean()), 4)
    w = ref["p_hi"] - ref["p_lo"]
    out["exact_band_width_mean"] = round(float(w.mean()), 3)
    out["exact_cells_band_wider_than_0.2_share"] = round(float((w > 0.2).mean()), 3)
    net.close()
    print(json.dumps(out))


if __name__ == "__main__":
    main()
