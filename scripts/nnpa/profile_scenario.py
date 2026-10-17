"""Profile one cold prediction-mode scenario: how much of FloodScenario() is area-model inference?

    EVAC_BUILD_DIR=... python scripts/nnpa/profile_scenario.py trishuli [budhi ...]

Wraps the model call (HistGradientBoostingClassifier.predict_proba), the feature builder (dm.features) and
the corridor context (dm.context_for) with wall-clock timers, runs FloodScenario cold under cProfile, and
prints a JSON line per valley plus the top cumulative functions. Writes the cell feature batch to
$EVAC_BUILD_DIR/nnpa_cells_<valley>.npz so the CPU-vs-NNPA benchmark scores the exact same rows.
"""
import cProfile
import io
import json
import os
import pstats
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from engine import damage_model as dm  # noqa: E402
from engine import escape  # noqa: E402

T = {}


def timed(name, fn):
    def wrap(*a, **k):
        t0 = time.perf_counter()
        try:
            return fn(*a, **k)
        finally:
            T[name] = T.get(name, 0.0) + time.perf_counter() - t0
    return wrap


def main(valleys):
    dm.features = timed("features", dm.features)
    dm.context_for = timed("context_for", dm.context_for)
    escape.dm.features, escape.dm.context_for = dm.features, dm.context_for
    bundle = escape.area_model()
    model = bundle["model"]
    batches = []
    orig = model.predict_proba

    def proba(X):
        batches.append(np.asarray(X))
        return orig(X)
    model.predict_proba = timed("predict_proba", proba)
    out = os.environ.get("EVAC_BUILD_DIR", ".")
    for v in valleys:
        T.clear()
        batches.clear()
        pr = cProfile.Profile()
        t0 = time.perf_counter()
        pr.enable()
        S = escape.FloodScenario(v)
        pr.disable()
        total = time.perf_counter() - t0
        cells = int(np.isfinite(S.p).sum())
        rows = [len(b) for b in batches]
        cell_X = batches[0] if batches else np.empty((0, len(bundle["features"])))
        np.savez_compressed(os.path.join(out, f"nnpa_cells_{v}.npz"), X=cell_X, features=bundle["features"])
        print(json.dumps({"valley": v, "total_s": round(total, 2), "cells_scored": cells,
                          "predict_proba_rows": rows,
                          **{k + "_s": round(t, 3) for k, t in T.items()},
                          "inference_share": round(T.get("predict_proba", 0) / total, 4)}))
        s = io.StringIO()
        pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(18)
        print(s.getvalue()[-3500:])


if __name__ == "__main__":
    main(sys.argv[1:] or ["trishuli", "budhi"])
