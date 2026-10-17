"""Packet D, Aug 26 numbers on the Trishuli build. Run on L1CC from a repo copy with its OWN data/:
    AREA=trishuli timeout 300 python3 docs/validation/run_aug26.py   ->  docs/validation/aug26_results.json
Arrival leave-one-out (+ cross-event transfer), footprint vs. OSM damage tags, people without time per trigger.
Heights: no gauge height lies inside the grid (Kali Khola, Devghat are west of it), so the flood line is
lcpizani's reconstruction from damage marks (models/damage/aug26_damage_envelope.json). Footprint numbers with that
line are IN-SAMPLE (circular); the cross-side numbers fit the line on one half of the river and test on the other.
"""
import csv, json, os, platform, sys, time
sys.path.insert(0, ".")
os.environ.setdefault("AREA", "trishuli")                     # pipeline/g.sh -> data/grassdb/trishuli
import numpy as np
from scipy import ndimage
from engine.terrain import Terrain
from engine.scenario import Valley, Scenario, TF, INV
from engine.flood import FloodEnvelope, hhmm_to_min

OUT, RAW, PROC = "docs/validation/aug26_results.json", "data/raw_trishuli", "data/proc_trishuli"
LABEL_EVENTS = {"2026NepalFlood", "8·26吉隆口岸泥石流"}
rep = json.load(open("replay/aug26.json")); t0 = hhmm_to_min(rep["burst_time"])
res = {"host": {"machine": platform.machine(), "byteorder": sys.byteorder}}

# ---------- OSM extracts (data/processed/osm, committed) -> the Overpass-style files Valley reads ----------
T = Terrain(PROC)
(x0, y1), (x1, y0) = T.xy(0, 0), T.xy(T.shape[0] - 1, T.shape[1] - 1)
lo0, la0 = INV.transform(x0, y0); lo1, la1 = INV.transform(x1, y1)
inbox = lambda lo, la: lo0 - 0.01 <= lo <= lo1 + 0.01 and la0 - 0.01 <= la <= la1 + 0.01
os.makedirs(RAW, exist_ok=True)
lab = []
with open("data/processed/osm/buildings.csv", encoding="utf-8") as f:
    B = []
    for r in csv.DictReader(f):
        lo, la = float(r["lon"]), float(r["lat"])
        if inbox(lo, la):
            B.append({"center": {"lon": lo, "lat": la}})
            lab.append(r["damage"] if r["damage_event"] in LABEL_EVENTS else "")
json.dump({"elements": B}, open(f"{RAW}/osm_trishuli_buildings.json", "w"))
P = [{"lon": g["geometry"]["coordinates"][0], "lat": g["geometry"]["coordinates"][1], "tags": g["properties"]}
     for g in json.load(open("data/processed/osm/places.geojson", encoding="utf-8"))["features"]
     if g["geometry"]["type"] == "Point" and inbox(*g["geometry"]["coordinates"][:2])]
json.dump({"elements": P}, open(f"{RAW}/osm_trishuli_places.json", "w"))
BR = []
for i, g in enumerate(json.load(open("data/processed/osm/roads.geojson", encoding="utf-8"))["features"]):
    p = g["properties"]
    if p.get("bridge") in (None, "no") or g["geometry"]["type"] != "LineString":
        continue
    cs = g["geometry"]["coordinates"]
    if any(inbox(*c[:2]) for c in cs):
        BR.append({"id": p.get("osm_id", i), "tags": p, "geometry": [{"lon": c[0], "lat": c[1]} for c in cs]})
json.dump({"elements": BR}, open(f"{RAW}/osm_trishuli_bridges.json", "w"))

t = time.time(); V = Valley(area="trishuli", proc=PROC, raw=RAW); res["valley_load_s"] = round(time.time() - t, 2)
T = V.T                                              # one Terrain in memory (shared VM)
# Valley drops buildings outside the grid; rebuild the same mask to align the damage labels
ll = np.array([(b["center"]["lon"], b["center"]["lat"]) for b in B]); x, y = TF.transform(ll[:, 0], ll[:, 1])
rc = np.array([T.rc(a, b) for a, b in zip(x, y)])
ok = (rc[:, 0] >= 0) & (rc[:, 0] < T.shape[0]) & (rc[:, 1] >= 0) & (rc[:, 1] < T.shape[1])
lab = np.array(lab)[ok]; assert len(lab) == len(V.b_flat)
pos_lab = np.isin(lab, ["destroyed", "damaged"]); destroyed = lab == "destroyed"

# ---------- envelope: observed arrivals (in-grid) + damage-mark flood line ----------
env = json.load(open("models/damage/aug26_damage_envelope.json"))
HK = [(k["km"], k["height_m"]) for k in env["knots"]]


class Probe:                                         # km_of without running r.walk (same code as Scenario)
    pass


pr = Probe(); pr.V = V
r, c = T.snap_to_channel(*T.rc(*TF.transform(rep["source"]["lon"], rep["source"]["lat"])), )     # same snap as Scenario (radius 10)
path = T.downstream_path(r, c); prc = np.array(np.unravel_index(path, T.shape))
kmp = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(prc, axis=1)) * 30.0)]) / 1000
hand, drain = T.hand_to(path); ix = np.full(T.nxt.size, -1); ix[path] = np.arange(len(path))
pr.km = np.where(drain >= 0, kmp[ix[np.maximum(drain, 0)]], np.nan)
km_of = lambda lo, la: Scenario.km_of(pr, lo, la)
res["path_km"] = round(float(kmp[-1]), 1)

obs = []
for o in rep["observations"]:
    tt = o.get("first_arrival")
    obs.append({"place": o["place"].split(" (")[0], "km": round(float(km_of(o["lon"], o["lat"])), 2), "reported": tt,
                "reported_min": hhmm_to_min(tt) - t0 if tt else None, "use": o["use"]})
cal = [o for o in obs if o["use"] == "calibration" and o["reported"] and np.isfinite(o["km"])]
curve = lambda kn: FloodEnvelope([(0.0, 0.0)] + kn, [(0.0, 1.0), (1.0, 1.0)])
AK = [(o["km"], o["reported_min"]) for o in cal]
full = curve(AK)
oct_knots = json.load(open("models/damage/flood_presets.json"))["presets"]["oct11"]["arrival_knots"]
oct_curve = FloodEnvelope(oct_knots, [(0.0, 1.0), (1.0, 1.0)])
for o in obs:
    if o["reported_min"] is None or not np.isfinite(o["km"]):
        continue
    p = float(full.arrival(o["km"])); o["pred_all_min"] = round(p, 1); o["err_all_min"] = round(p - o["reported_min"], 1)
    o["pred_with_oct11_curve_min"] = round(float(oct_curve.arrival(o["km"])), 1)
    if o in cal:
        rest = [(q["km"], q["reported_min"]) for q in cal if q is not o]
        pl = float(curve(rest).arrival(o["km"])); o["pred_loo_min"] = round(pl, 1); o["err_loo_min"] = round(pl - o["reported_min"], 1)
res["arrival"] = obs
res["arrival_knots"] = AK

# ---------- footprint vs. OSM damage tags (no r.walk needed) ----------
dist_m = ndimage.distance_transform_edt(~np.isin(np.arange(T.nxt.size), path).reshape(T.shape)) * 30.0
bkm, bh, bd = pr.km.flat[V.b_flat], hand.flat[V.b_flat], dist_m.flat[V.b_flat]
corr = np.isfinite(bkm) & (bd <= 500)


def p90_knots(mask):
    out = []
    for k0 in np.arange(0, kmp[-1], 5.0):
        m = mask & pos_lab & (bkm >= k0) & (bkm < k0 + 5)
        if m.sum() >= 30:
            out.append((k0 + 2.5, float(np.percentile(bh[m], 90))))
    return out


def fp_stats(F, test, band="hi"):
    h = F.height_band_at(np.nan_to_num(bkm))[2 if band == "hi" else 1]
    inside = np.isfinite(bkm) & (bh <= h)
    t = test
    return {"band": band, "labelled_affected": int((pos_lab & t).sum()), "labelled_destroyed": int((destroyed & t).sum()),
            "affected_inside": round(float((inside & pos_lab & t).sum() / max((pos_lab & t).sum(), 1)), 3),
            "destroyed_inside": round(float((inside & destroyed & t).sum() / max((destroyed & t).sum(), 1)), 3),
            "footprint_buildings": int((inside & t).sum()),
            "footprint_unlabelled_share": round(float((inside & t & ~pos_lab).sum() / max((inside & t).sum(), 1)), 3)}


FP = {"all_labelled_in_grid": int(pos_lab.sum()), "draining_to_path": int((pos_lab & np.isfinite(bkm)).sum()),
      "in_500m_corridor": int((pos_lab & corr).sum())}
Fin = FloodEnvelope(AK, HK)
FP["in_sample_corridor"] = [fp_stats(Fin, corr, b) for b in ("mid", "hi")]
FP["in_sample_all_draining"] = [fp_stats(Fin, np.isfinite(bkm), b) for b in ("mid", "hi")]
split = 51.789
up, dn = corr & (bkm <= split - 1), corr & (bkm >= split + 1)
FP["cross_side"] = {"train_up_test_down": fp_stats(FloodEnvelope(AK, p90_knots(up)), dn),
                    "train_down_test_up": fp_stats(FloodEnvelope(AK, p90_knots(dn)), up),
                    "knots_up": p90_knots(up), "knots_down": p90_knots(dn)}
res["footprint"] = FP

# ---------- full scenario: r.walk + slack per trigger ----------
t = time.time(); S = Scenario(V, rep, envelope=Fin); res["scenario_new_s"] = round(time.time() - t, 2)
res["walk_s"] = round(S.walk_s, 2); res["n_buildings"] = int(len(V.b_flat)); res["n_bridges"] = len(V.bridge_meta)
res["triggers"] = {k: {"time": v["time"], **S.summary(v["time"])} for k, v in rep["triggers"].items()}
res["settlements_0915"] = [{k: s[k] for k in ("name", "status", "slack_min", "people_at_risk", "people_without_time",
                                              "river_km", "arrival_early", "walk_min_median", "walk_min_max")}
                           for s in S.settlements("09:15")]
fl = S.flood.flat[V.b_flat]
res["engine_footprint_check"] = {"affected_inside": round(float((fl & pos_lab).sum() / pos_lab.sum()), 3),
                                 "footprint_buildings": int(fl.sum()),
                                 "footprint_unlabelled_share": round(float((fl & ~pos_lab).sum() / fl.sum()), 3)}
json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: res[k] for k in ("valley_load_s", "scenario_new_s", "walk_s", "triggers", "engine_footprint_check")}))
