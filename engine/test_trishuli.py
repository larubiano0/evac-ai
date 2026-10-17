"""Check the Trishuli build: path from the Lhende/Bhotekoshi at the border passes the Aug 26 towns."""
import sys; sys.path.insert(0, ".")
import numpy as np
from pyproj import Transformer
from engine.terrain import Terrain
tf = Transformer.from_crs(4326, 32645, always_xy=True)
T = Terrain("data/proc_trishuli")
print("D8 downhill frac:", round(T.check_directions()[0], 4))
r, c = T.snap_to_channel(*T.rc(*tf.transform(85.383, 28.276)), radius=15)   # Rasuwagadhi border crossing
path = T.downstream_path(r, c); prc = np.array(np.unravel_index(path, T.shape))
km = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(prc, axis=1)) * 30)]) / 1000
hand, drain = T.hand_to(path); pos = np.full(T.nxt.size, -1); pos[path] = np.arange(len(path))
print(f"path {km[-1]:.1f} km, elev {T.dem.flat[path[0]]:.0f} -> {T.dem.flat[path[-1]]:.0f} m")
for n, ll in {"Timure": (85.371, 28.256), "Syabrubesi": (85.342, 28.161), "Betrawati": (85.187, 27.972),
              "Trishuli Bazar/Bidur": (85.150, 27.905), "Galchhi": (84.928, 27.795)}.items():
    rr, cc = T.rc(*tf.transform(*ll)); d = drain[rr, cc]
    print(f"  {n:22s} HAND={hand[rr,cc]:7.1f} m  km={km[pos[d]] if d >= 0 else float('nan'):6.1f}")
