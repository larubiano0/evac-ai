"""What-if floods for one prediction scenario: which ground looks safe in this flood but floods if it is bigger.

Every corridor cell of an escape.FloodScenario is scored under n flood heights within the engine's +-30% height
band (FloodEnvelope.height_band) by the neural stand-in for area_fb (engine/surrogate.py), on the IBM Telum
on-chip AI accelerator when it is available. Output: per-cell 10th / 90th percentile risk, and a map overlay:
  purple = safe in this flood (P <= UNSAFE_P) but unsafe in a bigger one (90th percentile P > UNSAFE_P),
  red    = unsafe at every likely height (10th percentile P > UNSAFE_P).
"""
import io
import time

import numpy as np

from engine import damage_model as dm
from engine import escape as esc
from engine.surrogate import Surrogate

_NET = None


def net():
    global _NET
    if _NET is None:
        _NET = Surrogate()
    return _NET


def compute(S, n=100):
    """Run the what-if floods on scenario S (escape.FloodScenario). Cached on S per n."""
    cache = S.__dict__.setdefault("_whatif", {})
    if n in cache:
        return cache[n]
    T, V = S.V.T, S.V
    idx = np.flatnonzero(np.isfinite(S.p))
    rr, cc = np.unravel_index(idx, T.shape)
    x, y = T.transform * (cc + 0.5, rr + 0.5)
    lon, lat = V.inv.transform(x, y)
    N = net()
    X, _, ok, _ = dm.features(S.ctx, np.c_[lon, lat], ["building"] * len(idx), S.F, names=N.features)
    X, idx = np.asarray(X[ok], np.float32), idx[ok]
    t0 = time.perf_counter()
    base = N.predict(X)
    band = N.height_ensemble(X, n=n)
    run_s = time.perf_counter() - t0
    u = esc.UNSAFE_P
    cls = np.zeros(len(X), np.uint8)
    cls[(base <= u) & (band["p_hi"] > u)] = 1                       # safe now, unsafe in a bigger flood
    cls[band["p_lo"] > u] = 2                                        # unsafe at every likely height
    grid = np.zeros(T.shape, np.uint8)
    grid.flat[idx] = cls
    cell_km2 = abs(T.transform.a * T.transform.e) / 1e6
    res = {"grid": grid, "flood_heights": n, "cells": int(len(X)), "predictions": int(len(X) * (n + 1)),
           "run_s": round(run_s, 2), "backend": N.backend,
           "predictions_per_s": int(len(X) * (n + 1) / run_s),
           "safe_now_unsafe_if_bigger_km2": round(float((cls == 1).sum() * cell_km2), 2),
           "safe_now_unsafe_if_bigger_cells": int((cls == 1).sum()),
           "unsafe_any_height_km2": round(float((cls == 2).sum() * cell_km2), 2),
           "height_band": "+-30%", "unsafe_p": u}
    cache[n] = res
    return res


def png(S, res):
    """The overlay as an RGBA PNG warped to Web Mercator + its lon/lat bounds (Leaflet imageOverlay)."""
    from PIL import Image
    from rasterio.warp import reproject, Resampling, calculate_default_transform, transform_bounds
    T, g = S.V.T, res["grid"]
    rows, cols = np.where(g > 0)
    if not len(rows):
        rows, cols = np.where(np.isfinite(S.p))
    r0, r1, c0, c1 = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1
    src = g[r0:r1, c0:c1]
    src_tf = T.transform * T.transform.translation(c0, r0)
    h, w = src.shape
    left, top = src_tf * (0, 0)
    right, bottom = src_tf * (w, h)
    dst_tf, dw, dh = calculate_default_transform(T.crs, "EPSG:3857", w, h, left, bottom, right, top)
    dst = np.zeros((dh, dw), np.uint8)
    reproject(src, dst, src_transform=src_tf, src_crs=T.crs, dst_transform=dst_tf, dst_crs="EPSG:3857",
              resampling=Resampling.nearest, src_nodata=0, dst_nodata=0)
    rgba = np.zeros((dh, dw, 4), np.uint8)
    rgba[dst == 1] = (124, 58, 237, 220)                             # purple: floods only if the flood is bigger
    rgba[dst == 2] = (215, 38, 61, 90)                               # faint red: floods at any likely height
    buf = io.BytesIO()
    Image.fromarray(rgba, "RGBA").save(buf, "PNG")
    x0, y1 = dst_tf * (0, 0)
    x1, y0 = dst_tf * (dw, dh)
    b = transform_bounds("EPSG:3857", "EPSG:4326", x0, y0, x1, y1)
    return buf.getvalue(), [[b[1], b[0]], [b[3], b[2]]]
