"""Distill area_fb (300 boosted trees) into a dense MLP for the Telum NNPA (engine/surrogate.py).

    EVAC_BUILD_DIR=... python3 scripts/nnpa/train_surrogate.py

Training rows = the real 30 m corridor cells of both valleys (saved by profile_scenario.py), each with its flood
height scaled by a random factor in [0.7, 1.3] (FloodEnvelope.height_band), so the net learns area_fb across the
whole what-if range. Target = area_fb's raw logit; area_fb's Platt calibration and the input standardisation are
folded into the weights, so the saved net outputs the same calibrated P as dm.predict(). Trains on the CPU
(sklearn); the NNPA is for inference. Writes models/surrogate/area_fb_mlp.npz + metrics.json.
"""
import json
import os
import sys
import time

import joblib
import numpy as np
from sklearn.metrics import roc_auc_score
from sklearn.neural_network import MLPRegressor

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
sys.path.insert(0, REPO)
from engine.surrogate import Surrogate  # noqa: E402

HIDDEN = (256, 256, 256)


def main():
    build = os.environ.get("EVAC_BUILD_DIR", ".")
    bundle = joblib.load(os.path.join(REPO, "models/area/area_fb.joblib"))
    hgb, cal, feats = bundle["model"], bundle["calibration"], list(bundle["features"])
    ih, ifb = feats.index("hand"), feats.index("freeboard")
    rng = np.random.default_rng(0)
    X = np.concatenate([np.load(os.path.join(build, f"nnpa_cells_{v}.npz"))["X"] for v in ("trishuli", "budhi")])
    X = np.repeat(X.astype(np.float32), 2, axis=0)                  # two random flood heights per cell
    s = rng.uniform(0.7, 1.3, len(X)).astype(np.float32)
    X[:, ifb] = X[:, ih] - s * (X[:, ih] - X[:, ifb])
    p_raw = np.clip(hgb.predict_proba(X)[:, 1], 1e-4, 1 - 1e-4)
    z = np.log(p_raw / (1 - p_raw)).astype(np.float32)
    idx = rng.permutation(len(X))
    n_test = len(X) // 10
    te, tr = idx[:n_test], idx[n_test:]
    mu, sd = X[tr].mean(0), X[tr].std(0) + 1e-6

    net = MLPRegressor(hidden_layer_sizes=HIDDEN, activation="relu", batch_size=4096, learning_rate_init=2e-3,
                       max_iter=30, early_stopping=True, n_iter_no_change=4, random_state=0)
    t0 = time.perf_counter()
    net.fit((X[tr] - mu) / sd, z[tr])
    fit_s = time.perf_counter() - t0

    W = [w.astype(np.float64) for w in net.coefs_]
    B = [b.astype(np.float64) for b in net.intercepts_]
    B[0] = B[0] - (mu / sd) @ W[0]                                  # fold standardisation into layer 0
    W[0] = W[0] / sd[:, None]
    W[-1], B[-1] = cal["a"] * W[-1], cal["a"] * B[-1] + cal["b"]    # fold Platt calibration into the last layer
    out_dir = os.path.join(REPO, "models", "surrogate")
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "area_fb_mlp.npz")
    np.savez(path, n_layers=len(W), features=np.array(feats),
             **{f"W{i}": w.astype(np.float32) for i, w in enumerate(W)},
             **{f"b{i}": b.astype(np.float32) for i, b in enumerate(B)})

    def platt(p):
        q = np.clip(p, 1e-6, 1 - 1e-6)
        return 1 / (1 + np.exp(-(cal["a"] * np.log(q / (1 - q)) + cal["b"])))

    p_ref = platt(p_raw[te])
    p_net = Surrogate(path, lib="").predict_cpu(X[te])
    call = p_ref >= 0.5
    m = {"teacher": "models/area/area_fb.joblib (calibrated P)", "hidden": HIDDEN, "train_rows": int(len(tr)),
         "test_rows": int(n_test), "epochs": int(net.n_iter_), "fit_s_cpu": round(fit_s, 1),
         "mae_p": round(float(np.abs(p_net - p_ref).mean()), 4),
         "p95_abs_err_p": round(float(np.percentile(np.abs(p_net - p_ref), 95)), 4),
         "corr_p": round(float(np.corrcoef(p_net, p_ref)[0, 1]), 4),
         "auc_vs_area_fb_call": round(float(roc_auc_score(call, p_net)), 4) if 0 < call.mean() < 1 else None,
         "same_call_at_0.5": round(float(((p_net >= 0.5) == call).mean()), 4),
         "height_scale_range": [0.7, 1.3]}
    json.dump(m, open(os.path.join(out_dir, "metrics.json"), "w"), indent=1)
    print(json.dumps(m))


if __name__ == "__main__":
    main()
