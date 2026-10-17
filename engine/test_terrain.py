"""Sanity test of engine.terrain on the Budhi Gandaki grid (run from repo root on the VM)."""
import sys, time
sys.path.insert(0, ".")
import numpy as np
from pyproj import Transformer
from engine.terrain import Terrain

tf = Transformer.from_crs(4326, 32645, always_xy=True)
t0 = time.time(); T = Terrain(); print(f"load {time.time()-t0:.1f}s shape={T.shape}")
down_ok, moved = T.check_directions()
print(f"D8 check: {down_ok:.4f} of moving cells go downhill-or-flat; {moved:.3f} of cells have a successor")

# Oct 11 source area: Syar Khola near Chumling (approx.; refine with ICIMOD source location)
r, c = T.rc(*tf.transform(84.9627, 28.4740)); r, c = T.snap_to_channel(r, c)
path = T.downstream_path(r, c)
seg = np.hypot(*np.diff(np.array(np.unravel_index(path, T.shape)), axis=1)) * 30.0
dist_km = np.concatenate([[0], np.cumsum(seg)]) / 1000
print(f"path from source: {len(path)} cells, {dist_km[-1]:.1f} km, elev {T.dem.flat[path[0]]:.0f} -> {T.dem.flat[path[-1]]:.0f} m")

t0 = time.time(); hand, drain = T.hand_to(path); print(f"HAND to path: {time.time()-t0:.1f}s, reached {np.isfinite(hand).mean():.1%} of cells")
pos = {int(i): k for k, i in enumerate(path)}
places = {"Chumling": (84.9627, 28.4740), "Philim": (84.8966, 28.3933), "Sirdibas": (84.8891, 28.3809),
          "Salleri": (84.8884, 28.3601), "Jagat": (84.8959, 28.3514), "Dobhan": (84.9059, 28.2955),
          "Khorlabesi": (84.8831, 28.2544), "Machhakhola": (84.8738, 28.2293), "Soti Khola": (84.8547, 28.1353),
          "Arkhet": (84.8356, 28.0973), "Arughat buspark": (84.8116, 28.0384), "Arughat bridge": (84.8089, 28.0416),
          "Gumda (ridge)": (84.8237, 28.1999)}
for n, ll in places.items():
    rr, cc = T.rc(*tf.transform(*ll)); d = drain[rr, cc]
    km = dist_km[pos[int(d)]] if d >= 0 else float("nan")
    print(f"  {n:16s} HAND={hand[rr,cc]:7.1f} m   river-km from source={km:6.1f}")
