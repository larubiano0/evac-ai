import sys; sys.path.insert(0, ".")
import numpy as np
from pyproj import Transformer
from engine.terrain import Terrain
tf = Transformer.from_crs(4326, 32645, always_xy=True)
T = Terrain("data/proc_trishuli")
r, c = T.snap_to_channel(*T.rc(*tf.transform(85.383, 28.276)), radius=15)
path = T.downstream_path(r, c); hand, drain = T.hand_to(path)
for n, (la, lo) in {"Timure": (28.2528, 85.3667), "Betrawati": (27.9731, 85.186), "Trishuli": (27.9232, 85.148)}.items():
    rr, cc = T.rc(*tf.transform(lo, la)); d = drain[rr, cc]
    dr, dc = np.unravel_index(d, T.shape)
    win = T.dem[rr-17:rr+18, cc-17:cc+18]; sw = T.streams[rr-17:rr+18, cc-17:cc+18]
    print(f"{n}: dem={T.dem[rr,cc]:.0f} drain->({dr},{dc}) dem={T.dem[dr,dc]:.0f} dist={np.hypot(dr-rr,dc-cc)*30:.0f} m | "
          f"min dem within 500 m={win.min():.0f} | min stream dem within 500 m={win[sw].min() if sw.any() else -1:.0f} | "
          f"on-path cells within 500 m={sum(1 for i in path if abs(i//T.shape[1]-rr)<17 and abs(i%T.shape[1]-cc)<17)}")
