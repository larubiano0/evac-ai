"""End-to-end smoke test on the Oct 11 replay: calibrate -> footprint -> time to safety (VM, repo root)."""
import sys, json, time
sys.path.insert(0, ".")
import numpy as np
from pyproj import Transformer
from engine.terrain import Terrain
from engine.flood import calibrate_from_replay
from engine.safety import time_to_safety, bridge_cells

tf = Transformer.from_crs(4326, 32645, always_xy=True)
rep = json.load(open("replay/oct11.json"))
T = Terrain()
r, c = T.snap_to_channel(*T.rc(*tf.transform(rep["source"]["lon"], rep["source"]["lat"])))
path = T.downstream_path(r, c)
rc_path = np.array(np.unravel_index(path, T.shape))
km_path = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(rc_path, axis=1)) * 30.0)]) / 1000
hand, drain = T.hand_to(path)
pos = np.full(T.nxt.size, -1); pos[path] = np.arange(len(path))
km = np.where(drain >= 0, km_path[pos[np.maximum(drain, 0)]], np.nan)

def km_of(lon, lat):
    rr, cc = T.rc(*tf.transform(lon, lat)); return km[rr, cc]

F = calibrate_from_replay(rep, km_of)
print("arrival knots (km, min):", F.ak.round(1).tolist()); print("height knots (km, m):", F.hk.round(1).tolist())
print("wave speeds km/h:", [(a, b, round(v, 1)) for a, b, v in F.wave_speed_kmh()])
h_lo, h_mid, h_hi = F.height_band_at(np.nan_to_num(km))
flood_hi = (drain >= 0) & (hand <= h_hi)
safe = ~flood_hi & ((drain < 0) | (hand > h_hi + 5.0))      # 5 m margin above conservative height
print(f"footprint(hi) cells: {flood_hi.sum()}  ({flood_hi.sum()*900/1e6:.1f} km2); safe cells {safe.mean():.1%}")
br = bridge_cells(T, "data/raw/osm_budhi_bridges.json"); print("bridge cells:", len(br))
tts, dt = time_to_safety(T, safe, path, br); print(f"r.walk time-to-safety: {dt:.1f}s")
places = {"Sirdibas": (84.8891, 28.3809), "Salleri": (84.8884, 28.3601), "Jagat": (84.8959, 28.3514),
          "Dobhan": (84.9059, 28.2955), "Khorlabesi": (84.8831, 28.2544), "Machhakhola": (84.8738, 28.2293),
          "Soti Khola": (84.8547, 28.1353), "Arkhet": (84.8356, 28.0973), "Arughat buspark": (84.8116, 28.0384)}
t0 = 3 * 60 + 45
for n, ll in places.items():
    rr, cc = T.rc(*tf.transform(*ll)); a = F.arrival(km[rr, cc])
    print(f"  {n:16s} km={km[rr,cc]:5.1f} HAND={hand[rr,cc]:5.1f} H_hi={h_hi[rr,cc]:5.1f} flooded={bool(flood_hi[rr,cc])!s:5s} "
          f"arrival={int((t0+a)//60):02d}:{int((t0+a)%60):02d} walk_to_safe={tts[rr,cc]/60:5.1f} min")
np.save("data/proc/work/oct11_tts.npy", tts.astype(np.float32))
