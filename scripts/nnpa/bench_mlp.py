"""Gate for a dense neural surrogate: the same MLP forward pass on the CPU (numpy/OpenBLAS, fp32, all vCPUs) vs
the Telum NNPA (zDNN, scripts/nnpa/zdnn_mlp.c), same weights, same rows.

    python3 scripts/nnpa/bench_mlp.py path/to/zdnn_mlp.so [rows] [n_in] [width] [depth]

Prints one JSON line: best-of-5 seconds after a warm-up, rows/s, speed-up, and the NNPA-vs-CPU output difference
(the accelerator computes in its 16-bit DLFloat format, so small differences are expected).
"""
import ctypes as C
import json
import sys
import time

import numpy as np


def cpu_mlp(x, W, B):
    h = x
    for i, (w, b) in enumerate(zip(W, B)):
        h = h @ w + b
        h = np.maximum(h, 0, out=h) if i < len(W) - 1 else 1 / (1 + np.exp(-h))
    return h


def best(fn, n=5):
    fn()
    ts = []
    for _ in range(n):
        t0 = time.perf_counter()
        fn()
        ts.append(time.perf_counter() - t0)
    return min(ts)


def main():
    so = sys.argv[1]
    rows, n_in, width, depth = (int(a) for a in (sys.argv[2:] + ["262144", "16", "256", "3"][len(sys.argv) - 2:]))
    lib = C.CDLL(so)
    assert lib.nnpa_available(), "NNPA not available"
    m = 1024
    s = rows // m
    rows = s * m
    rng = np.random.default_rng(0)
    dims = [n_in] + [width] * depth + [1]
    W = [(rng.standard_normal((a, b)) * np.sqrt(2 / a)).astype(np.float32) for a, b in zip(dims, dims[1:])]
    B = [(rng.standard_normal(b) * 0.1).astype(np.float32) for b in dims[1:]]
    x = rng.standard_normal((rows, n_in)).astype(np.float32)

    t_cpu = best(lambda: cpu_mlp(x, W, B))
    y_cpu = cpu_mlp(x, W, B)

    fp = C.POINTER(C.c_float)
    out = np.empty((rows, 1), np.float32)
    times = (C.c_double * 2)()
    Wp = (fp * len(W))(*[w.ctypes.data_as(fp) for w in W])
    Bp = (fp * len(B))(*[b.ctypes.data_as(fp) for b in B])
    lib.mlp_nnpa.argtypes = [fp, C.c_uint32, C.c_uint32, C.c_int, C.POINTER(C.c_int), C.POINTER(fp), C.POINTER(fp),
                             fp, C.c_int, C.POINTER(C.c_double)]
    rc = lib.mlp_nnpa(x.ctypes.data_as(fp), s, m, len(W), (C.c_int * len(dims))(*dims), Wp, Bp,
                      out.ctypes.data_as(fp), 5, times)
    assert rc == 0, "zdnn call failed"
    flops = 2 * rows * sum(a * b for a, b in zip(dims, dims[1:]))
    print(json.dumps({
        "rows": rows, "layers": dims, "nnpa_max_dim": lib.nnpa_max_dim(),
        "cpu_numpy_s": round(t_cpu, 4), "nnpa_end_to_end_s": round(times[0], 4), "nnpa_layers_only_s": round(times[1], 4),
        "speedup_end_to_end": round(t_cpu / times[0], 2),
        "cpu_rows_per_s": int(rows / t_cpu), "nnpa_rows_per_s": int(rows / times[0]),
        "cpu_gflops": round(flops / t_cpu / 1e9, 1), "nnpa_gflops_end_to_end": round(flops / times[0] / 1e9, 1),
        "max_abs_diff": float(np.abs(out - y_cpu).max()), "mean_abs_diff": float(np.abs(out - y_cpu).mean()),
    }))


if __name__ == "__main__":
    main()
