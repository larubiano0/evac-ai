"""Neural stand-in for the impacted-area model (area_fb), run on the IBM Telum on-chip AI accelerator (NNPA).

Why: one flood scenario needs one P per 30 m cell (~100k cells), and area_fb (300 boosted trees) does that in
0.6 s on the CPU. But the flood height is uncertain (FloodEnvelope.height_band = +-30%), and showing that
uncertainty means scoring every cell under many flood heights: 100 heights x 126k cells = 12.6M rows per map.
A dense neural network distilled from area_fb (scripts/nnpa/train_surrogate.py) does that batch on the NNPA
an order of magnitude faster than the CPU (docs/linuxone-ai.md).

    net = Surrogate()                       # models/surrogate/area_fb_mlp.npz
    p = net.predict(X)                      # X = area_fb feature rows; calibrated P, same scale as area_fb
    band = net.height_ensemble(X, n=100)    # {"p_mean", "p_lo", "p_hi", ...} per cell
Backend: the NNPA when EVAC_NNPA_LIB points at a built scripts/nnpa/zdnn_mlp.so and the chip has it, else numpy.
"""
import ctypes as C
import os

import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEIGHTS = os.path.join(REPO, "models", "surrogate", "area_fb_mlp.npz")
CHUNK_M = 1024          # rows per stack entry; one NNPA call scores CHUNK_S * CHUNK_M rows
CHUNK_S = 128


class Surrogate:
    def __init__(self, path=WEIGHTS, lib=None):
        z = np.load(path, allow_pickle=False)
        n = int(z["n_layers"])
        self.W = [np.ascontiguousarray(z[f"W{i}"], np.float32) for i in range(n)]
        self.B = [np.ascontiguousarray(z[f"b{i}"], np.float32) for i in range(n)]
        self.features = [str(f) for f in z["features"]]
        self.i_hand, self.i_fb = self.features.index("hand"), self.features.index("freeboard")
        self._lib, self._net = None, None
        lib = lib or os.environ.get("EVAC_NNPA_LIB")
        if lib and os.path.exists(lib):
            try:
                self._open_nnpa(lib)
            except OSError:
                self._lib = None
        self.backend = "nnpa" if self._net else "cpu"

    # ---------------- backends ----------------
    def _open_nnpa(self, so):
        L = C.CDLL(so)
        if not L.nnpa_available():
            return
        fp = C.POINTER(C.c_float)
        L.nnpa_create.restype = C.c_void_p
        L.nnpa_create.argtypes = [C.c_uint32, C.c_uint32, C.c_int, C.POINTER(C.c_int), C.POINTER(fp), C.POINTER(fp)]
        L.nnpa_run.argtypes = [C.c_void_p, fp, fp, C.POINTER(C.c_double)]
        L.nnpa_free.argtypes = [C.c_void_p]
        dims = [self.W[0].shape[0]] + [w.shape[1] for w in self.W]
        Wp = (fp * len(self.W))(*[w.ctypes.data_as(fp) for w in self.W])
        Bp = (fp * len(self.B))(*[b.ctypes.data_as(fp) for b in self.B])
        net = L.nnpa_create(CHUNK_S, CHUNK_M, len(self.W), (C.c_int * len(dims))(*dims), Wp, Bp)
        if net:
            self._lib, self._net, self._fp = L, net, fp

    def predict_cpu(self, X):
        h = np.asarray(X, np.float32)
        for i, (w, b) in enumerate(zip(self.W, self.B)):
            h = h @ w + b
            if i < len(self.W) - 1:
                np.maximum(h, 0, out=h)
        return (1 / (1 + np.exp(-h[:, 0]))).astype(np.float32)

    def predict_nnpa(self, X):
        X = np.asarray(X, np.float32)
        rows, step = len(X), CHUNK_S * CHUNK_M
        out = np.empty(rows, np.float32)
        buf = np.zeros((step, X.shape[1]), np.float32)
        res = np.empty((step, 1), np.float32)
        for i in range(0, rows, step):
            k = min(step, rows - i)
            buf[:k] = X[i:i + k]
            if k < step:
                buf[k:] = 0
            if self._lib.nnpa_run(self._net, buf.ctypes.data_as(self._fp), res.ctypes.data_as(self._fp), None):
                raise RuntimeError("zDNN call failed")
            out[i:i + k] = res[:k, 0]
        return out

    def predict(self, X):
        return self.predict_nnpa(X) if self._net else self.predict_cpu(X)

    # ---------------- what-if floods ----------------
    def height_rows(self, X, scales):
        """Feature rows for each flood-height scale: freeboard = hand - scale * (flood height at the cell)."""
        X = np.asarray(X, np.float32)
        h = X[:, self.i_hand] - X[:, self.i_fb]              # flood height (m) this cell sees in the base flood
        out = np.repeat(X[None], len(scales), axis=0)
        out[:, :, self.i_fb] = X[None, :, self.i_hand] - np.asarray(scales, np.float32)[:, None] * h[None]
        return out.reshape(-1, X.shape[1])

    def height_ensemble(self, X, n=100, band=0.30, seed=0, predict=None, members_per_batch=8):
        """Score every cell under n flood heights drawn uniformly within +-band (FloodEnvelope.height_band) of
        the scenario's own height. Returns per-cell mean, 10th/90th percentile and P(P >= 0.5)."""
        scales = np.random.default_rng(seed).uniform(1 - band, 1 + band, n).astype(np.float32)
        predict = predict or self.predict
        P = np.empty((n, len(X)), np.float32)
        for j in range(0, n, members_per_batch):
            sc = scales[j:j + members_per_batch]
            P[j:j + len(sc)] = predict(self.height_rows(X, sc)).reshape(len(sc), len(X))
        lo, hi = np.percentile(P, [10, 90], axis=0)
        return {"p_mean": P.mean(0), "p_lo": lo.astype(np.float32), "p_hi": hi.astype(np.float32),
                "p_flooded_share": (P >= 0.5).mean(0).astype(np.float32), "scales": scales, "backend": self.backend}

    def close(self):
        if self._net:
            self._lib.nnpa_free(self._net)
            self._net = None
