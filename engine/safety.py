"""Time to safety on foot, via GRASS r.walk (Naismith/Langmuir anisotropic walking time).

r.walk's output at cell X = time to walk FROM the start cells TO X (verified, see
pipeline/test_rwalk_direction.sh). We need X -> safe ground, so we run it on the NEGATED DEM
with safe cells as start: each step then has the same climb as the real escape.
The flood channel (buffered by 1 cell) is a barrier (null friction) except at OSM bridge cells.
"""
import json, os, subprocess, time
import numpy as np
import rasterio
from scipy import ndimage
from pyproj import Transformer

G = os.path.join(os.path.dirname(__file__), "..", "pipeline", "g.sh")


def _g(*args):
    r = subprocess.run([G, *args], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"GRASS {args[0]} failed: {r.stderr[-800:]}")
    return r.stdout


def _write(path, arr, T, dtype, nodata):
    with rasterio.open(path, "w", driver="GTiff", height=arr.shape[0], width=arr.shape[1], count=1,
                       dtype=dtype, crs=T.crs, transform=T.transform, nodata=nodata, compress="deflate") as w:
        w.write(arr.astype(dtype), 1)


def bridge_cells(T, osm_bridges_path, step_m=10.0):
    """Flat indices of grid cells covered by OSM bridge ways (densified)."""
    tf = Transformer.from_crs(4326, 32645, always_xy=True)
    out = set()
    for e in json.load(open(osm_bridges_path))["elements"]:
        g = e.get("geometry") or []
        xy = [tf.transform(p["lon"], p["lat"]) for p in g]
        for (x0, y0), (x1, y1) in zip(xy, xy[1:]):
            n = max(int(np.hypot(x1 - x0, y1 - y0) / step_m), 1)
            for t in np.linspace(0, 1, n + 1):
                r, c = T.rc(x0 + t * (x1 - x0), y0 + t * (y1 - y0))
                if 0 <= r < T.shape[0] and 0 <= c < T.shape[1]:
                    out.add(r * T.shape[1] + c)
    return np.array(sorted(out), dtype=np.int64)


def time_to_safety(T, safe, channel_idx, bridges_idx, work="data/proc/work", max_cost_s=4 * 3600):
    """Seconds to walk from every cell to the nearest safe cell (NaN if unreachable within max_cost)."""
    os.makedirs(work, exist_ok=True); t0 = time.time()
    ch = np.zeros(T.shape, bool); ch.flat[channel_idx] = True
    barrier = ndimage.binary_dilation(ch, iterations=1)
    br = np.zeros(T.shape, bool); br.flat[bridges_idx] = True
    barrier &= ~ndimage.binary_dilation(br, iterations=1)          # bridges cut through the barrier
    _write(f"{work}/fric.tif", np.where(barrier, -1, 0), T, "int16", -1)
    _write(f"{work}/safe.tif", np.where(safe & ~barrier, 1, 0), T, "uint8", 0)
    _g("r.in.gdal", "-o", f"input={work}/fric.tif", "output=fric", "--overwrite", "--quiet")
    _g("r.in.gdal", "-o", f"input={work}/safe.tif", "output=safe", "--overwrite", "--quiet")
    _g("g.region", "raster=dem", "--quiet")
    _g("r.mapcalc", "expression=negdem = -dem", "--overwrite", "--quiet")
    _g("r.walk", "elevation=negdem", "friction=fric", "start_raster=safe", "output=tts", "outdir=tdir",
       f"max_cost={max_cost_s}", "memory=2500", "--overwrite", "--quiet")
    _g("r.out.gdal", "-cf", "input=tdir", f"output={work}/tdir.tif", "format=GTiff", "type=Float32",
       "createopt=COMPRESS=DEFLATE", "--overwrite", "--quiet")
    _g("r.out.gdal", "-cf", "input=tts", f"output={work}/tts.tif", "format=GTiff", "type=Float32",
       "createopt=COMPRESS=DEFLATE", "--overwrite", "--quiet")
    with rasterio.open(f"{work}/tts.tif") as r:
        tts = r.read(1).astype(np.float64); nd = r.nodata
    if nd is not None:
        tts[tts == nd] = np.nan
    tts[tts < 0] = np.nan
    # Cells r.walk could not reach (inside the 1-cell barrier strip, or enclosed bars) take the value of
    # the nearest reached cell plus straight-line walking at 1 m/s. Count them for transparency.
    miss = np.isnan(tts)
    if miss.any() and (~miss).any():
        dist, (ri, ci) = ndimage.distance_transform_edt(miss, return_indices=True)
        filled = tts[ri, ci] + dist * 30.0 / 1.0
        tts = np.where(miss, filled, tts)
        time_to_safety.nearest = (ri, ci)          # for filled cells: nearest cell r.walk reached
    time_to_safety.filled_cells = int(miss.sum())
    with rasterio.open(f"{work}/tdir.tif") as r:
        time_to_safety.tdir = r.read(1).astype(np.float32)     # degrees CCW from East, toward the next cell
    return tts, time.time() - t0


def trace_route(tdir, tts, r, c, near=None, max_steps=2000):
    """Follow r.walk movement directions from (r,c) to safe ground (tts==0). Returns list of (r,c)."""
    out = [(r, c)]
    if near is not None and not np.isfinite(tdir[r, c]) and tts[r, c] > 0:
        r, c = int(near[0][r, c]), int(near[1][r, c]); out.append((r, c))   # step out of the barrier strip
    for _ in range(max_steps):
        if not np.isfinite(tts[r, c]) or tts[r, c] <= 0:
            break
        a = tdir[r, c]
        if not np.isfinite(a):
            break
        dr, dc = -int(round(np.sin(np.radians(a)))), int(round(np.cos(np.radians(a))))
        if dr == 0 and dc == 0:
            break
        r, c = r + dr, c + dc
        if not (0 <= r < tts.shape[0] and 0 <= c < tts.shape[1]):
            break
        out.append((r, c))
    return out
