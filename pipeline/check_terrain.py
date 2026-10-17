"""Sanity checks: (1) DEM streams align with OSM Budhi Gandaki, (2) HAND values at known places are plausible."""
import json, numpy as np, rasterio
from pyproj import Transformer
from scipy import ndimage
P = "../data/proc/"; R = "../data/raw/"
tf = Transformer.from_crs(4326, 32645, always_xy=True)
hand = rasterio.open(P + "hand.tif"); H = hand.read(1).astype("float64"); H[np.abs(H) > 1e6] = np.nan
S = rasterio.open(P + "streams.tif").read(1); stream = (S > 0) & (S != -2147483648)
print(f"HAND valid {np.isfinite(H).mean():.1%}  p5/p50/p95 = {np.nanpercentile(H,[5,50,95]).round(1)}  stream cells {stream.sum()}")
# distance (m) from every cell to nearest DEM stream cell
dist = ndimage.distance_transform_edt(~stream) * 30.0
def rc(lon, lat):
    x, y = tf.transform(lon, lat); r, c = hand.index(x, y); return r, c
ww = json.load(open(R + "osm_budhi_waterways.json"))["elements"]
pts = [(g["lon"], g["lat"]) for e in ww if e["tags"].get("name", "").startswith("Budhi Ga") for g in e["geometry"]]
d = np.array([dist[rc(*p)] for p in pts if 0 <= rc(*p)[0] < H.shape[0] and 0 <= rc(*p)[1] < H.shape[1]])
print(f"OSM Budhi Gandaki vertices: {len(d)}; distance to DEM stream p50={np.median(d):.0f} m p90={np.percentile(d,90):.0f} m max={d.max():.0f} m")
places = {"Arughat bridge": (84.8089, 28.0416), "Arughat buspark": (84.8116, 28.0384), "Soti Khola": (84.8547, 28.1353),
          "Arkhet": (84.8356, 28.0973), "Machhakhola": (84.8738, 28.2293), "Khorlabesi": (84.8831, 28.2544),
          "Dobhan": (84.9059, 28.2955), "Jagat": (84.8959, 28.3514), "Salleri": (84.8884, 28.3601),
          "Sirdibas": (84.8891, 28.3809), "Philim": (84.8966, 28.3933), "Chumling": (84.9627, 28.4740),
          "Chhekampar": (85.0422, 28.4896), "Gumda (ridge village)": (84.8237, 28.1999)}
for n, (lo, la) in places.items():
    r, c = rc(lo, la); print(f"  {n:24s} HAND={H[r,c]:7.1f} m  dist_to_stream={dist[r,c]:5.0f} m")
