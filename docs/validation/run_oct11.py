"""Packet D, Oct 11 numbers. Run on L1CC from a repo copy with its OWN data/ (r.walk writes GRASS rasters):
    timeout 300 python3 docs/validation/run_oct11.py   ->  docs/validation/oct11_results.json
Arrival leave-one-out, settlements and bridges vs. reports, people without time per trigger, latency.
"""
import json, os, platform, resource, sys, time
sys.path.insert(0, ".")
import numpy as np
from engine.scenario import Valley, Scenario, TF
from engine.flood import FloodEnvelope, hhmm_to_min
from engine import alerts

OUT = "docs/validation/oct11_results.json"
rep = json.load(open("replay/oct11.json"))
t0 = hhmm_to_min(rep["burst_time"])
res = {"host": {"machine": platform.machine(), "byteorder": sys.byteorder}}

t = time.time(); V = Valley(); res["valley_load_s"] = round(time.time() - t, 2)
t = time.time(); S = Scenario(V, rep, extra_people={"Jagat": 100})
res["scenario_new_s"] = round(time.time() - t, 2); res["walk_s"] = round(S.walk_s, 2)

# ---------- a. arrival times: in-sample and leave-one-out ----------
obs = []
for o in rep["observations"]:
    tt = o.get("first_arrival") or o.get("arrival_reported")
    obs.append({"place": o["place"].split("/")[0], "km": round(float(S.km_of(o["lon"], o["lat"])), 2),
                "reported": tt, "reported_min": hhmm_to_min(tt) - t0, "use": o["use"]})
cal = [o for o in obs if o["use"] == "calibration"]


def curve(knots):
    return FloodEnvelope([(0.0, 0.0)] + knots, [(0.0, 1.0), (1.0, 1.0)])


full = curve([(o["km"], o["reported_min"]) for o in cal])
for o in obs:
    p = float(full.arrival(o["km"]))
    o["pred_all_min"] = round(p, 1); o["err_all_min"] = round(p - o["reported_min"], 1)
    o["in_band"] = bool(0.75 * p <= o["reported_min"] <= 1.25 * p)
    if o["use"] == "calibration":
        rest = [(q["km"], q["reported_min"]) for q in cal if q is not o]
        if rest:
            pl = float(curve(rest).arrival(o["km"]))
            o["pred_loo_min"] = round(pl, 1); o["err_loo_min"] = round(pl - o["reported_min"], 1)
res["arrival"] = obs

# ---------- b/e. people without time per trigger; settlements per warning ----------
res["triggers"] = {k: {"time": v["time"], **S.summary(v["time"])} for k, v in rep["triggers"].items()}
REPORTED = ["Paiyu", "Bagar", "Ghatte", "Jagat", "Salleri", "Sirdibas", "Nyak", "Machhakhola", "Dobhan", "Soti",
            "Arughat", "Shanti", "Syauli"]
res["settlements"] = {}
for w in ("03:30", "06:40"):
    sett = S.settlements(w)
    res["settlements"][w] = [{k: s[k] for k in ("name", "status", "slack_min", "people_at_risk", "people_without_time",
                                                "buildings_at_risk", "river_km", "arrival_early", "walk_min_median",
                                                "walk_min_max")} for s in sett]
at_risk = {s["name"] for s in res["settlements"]["06:40"]}
match = {}
for tok in REPORTED + ["Philim"]:
    names = sorted({n for n in V.p_name if tok.lower() in n.lower()})
    match[tok] = {"osm_places": names, "predicted_at_risk": sorted(n for n in names if n in at_risk)}
res["reported_places"] = match

# ---------- c. bridges ----------
br = S.bridges_at_risk()
res["bridges_at_risk"] = [{"label": b["label"], "name": b["name"], "kind": b["kind"], "river_km": round(b["river_km"], 1),
                           "lon": b["lon"], "lat": b["lat"]} for b in br]
res["bridges_total_osm"] = len(V.bridge_meta)

# ---------- f. latency ----------
def payload(S, w):           # same work as api.app.payload (api not imported: it loads prediction mode too)
    sett = S.settlements(w); bridges = S.bridges_at_risk(); wmin = hhmm_to_min(w) - S.t0
    for s in sett:
        x0, y0 = TF.transform(s["lon"], s["lat"])
        near = [b for b in bridges if np.hypot(*(np.array(TF.transform(b["lon"], b["lat"])) - (x0, y0))) <= 2500]
        s["alerts"] = alerts.build(s, near, w, wmin)
    S.path_geojson()
    return sett

lat = []
for _ in range(3):
    t = time.time(); payload(S, "06:40"); lat.append(time.time() - t)
res["cached_payload_s"] = [round(x, 3) for x in lat]
k = int(np.searchsorted(S.km_path, 10.0))                      # new trigger 10 km down the path, reused envelope
x, y = V.T.xy(*np.unravel_index(S.path[k], V.T.shape)); from engine.scenario import INV
t = time.time(); S2 = Scenario(V, rep, source_lonlat=INV.transform(x, y), envelope=S.F); payload(S2, "06:40")
res["new_trigger_s"] = round(time.time() - t, 2); res["new_trigger_walk_s"] = round(S2.walk_s, 2)
res["peak_rss_mb"] = {"python": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss // 1024,
                      "grass_children": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss // 1024}
res["n_buildings"] = int(len(V.b_flat))
json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
print(json.dumps({k: res[k] for k in ("valley_load_s", "scenario_new_s", "cached_payload_s", "new_trigger_s", "peak_rss_mb")}))
