"""Build the flood-type presets for prediction mode (models/damage/flood_presets.json).

A preset = arrival(km) and height(km) curves in km downstream of the flood source, taken ONLY from real
observations of one past flood, so a new trigger anywhere can reuse that flood's behaviour:

  oct11  Budhi Gandaki, 11 Oct 2026 (replay/oct11.json, sources inside):
         arrival: the 'calibration' first_arrival observations (Jagat/Salleri 04:00, Arughat 06:30; burst 03:45)
         height:  Salleri 25 m (upper end of the reported 20-25 m); Arughat 8.43 m = the gauge's peak stage,
                  used as an UPPER BOUND on height above the channel (normal stage unknown and >= 0), so the
                  flood is never understated
  aug26  Bhotekoshi-Trishuli, 26 Aug 2026:
         arrival: replay/aug26.json 'calibration' first_arrival observations inside the Trishuli grid
                  (Syabrubesi 08:50, Betrawati 09:20, Malekhu 11:26; burst 08:37). Points outside the grid
                  (Kali Khola, Devghat) are skipped: their km cannot be measured on this grid
         height:  reconstructed from real damage marks (models/damage/aug26_damage_envelope.json)
Beyond the last height observation the height is held constant (no invented decay rate); before the first
it is held at the first value (np.interp). Arrival beyond the last knot uses the last observed wave speed.
"""
import json, os, sys
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
from engine.terrain import Terrain
from engine.flood import hhmm_to_min
from engine import damage_model as dm

DATA = os.path.join(REPO, "data") if os.path.isdir(os.path.join(REPO, "data", "proc")) else "/home/linux1/evac-ai/data"


def km_measure(proc, src_lonlat, radius):
    T = Terrain(proc)
    ctx = dm.PathContext(T, T.downstream_path(*T.snap_to_channel(*T.rc(*dm.Transformer.from_crs(
        4326, T.crs.to_epsg(), always_xy=True).transform(*src_lonlat)), radius=radius)))

    def km_of(lon, lat):
        x, y = ctx.tf.transform(lon, lat)
        r, c, ok = ctx.cells([x], [y])
        if not ok[0]:
            return None
        d = ctx.drain[r[0], c[0]]
        return None if d < 0 else float(ctx.km_path[ctx.pos[d]])
    return km_of, float(ctx.km_path[-1])


def arrivals(rep, km_of):
    t0 = hhmm_to_min(rep["burst_time"]); out, used = [(0.0, 0.0)], []
    for o in rep["observations"]:
        if o.get("use") != "calibration" or "first_arrival" not in o:
            continue
        km = km_of(o["lon"], o["lat"])
        if km is None:
            used.append({"place": o["place"], "skipped": "outside this grid"}); continue
        out.append((km, float(hhmm_to_min(o["first_arrival"]) - t0)))
        used.append({"place": o["place"], "km": round(km, 2), "minutes_after_burst": out[-1][1], "src": o["src"]})
    return sorted(out), used


def main():
    presets = {}
    # --- Oct 11, Budhi Gandaki
    rep = json.load(open(os.path.join(REPO, "replay", "oct11.json")))
    km_of, L = km_measure(f"{DATA}/proc", (rep["source"]["lon"], rep["source"]["lat"]), radius=10)
    ak, used = arrivals(rep, km_of)
    obs = {o["place"]: o for o in rep["observations"]}
    sal = obs["Paiyu/Bagar/Ghattekhola/Jagat/Salleri"]; aru = obs["Arughat"]
    hk = [(km_of(sal["lon"], sal["lat"]), float(max(sal["peak_height_m"])), "Salleri: upper end of reported 20-25 m"),
          (km_of(aru["lon"], aru["lat"]), float(aru["gauge_peak_m"]), "Arughat: gauge peak stage 8.43 m used as upper bound")]
    presets["oct11"] = {"label": "Landslide/avalanche-dam burst (Budhi Gandaki, 11 Oct 2026)", "native_valley": "budhi",
                        "burst_time": rep["burst_time"], "path_km": L,
                        "arrival_knots": ak, "arrival_observations": used,
                        "height_knots": [(k, h) for k, h, _ in hk], "height_notes": [n for _, _, n in hk],
                        "sources": rep["sources"]}
    # --- Aug 26, Bhotekoshi-Trishuli
    rep = json.load(open(os.path.join(REPO, "replay", "aug26.json")))
    km_of, L = km_measure(f"{DATA}/proc_trishuli", (rep["source"]["lon"], rep["source"]["lat"]), radius=15)
    ak, used = arrivals(rep, km_of)
    env = json.load(open(os.path.join(dm.MODEL_DIR, "aug26_damage_envelope.json")))
    presets["aug26"] = {"label": "Glacier/ice-rock avalanche debris flood (Bhotekoshi-Trishuli, 26 Aug 2026)",
                        "native_valley": "trishuli", "burst_time": rep["burst_time"], "path_km": L,
                        "arrival_knots": ak, "arrival_observations": used,
                        "height_knots": [(k["km"], k["height_m"]) for k in env["knots"]],
                        "height_notes": [env["method"] + " (" + env["note"].split(".")[0] + ")"],
                        "sources": rep["sources"] + ["OSM damage:event=2026NepalFlood (HOT), see data/docs/osm_damage_labels.md"]}
    for k, p in presets.items():
        if len(p["arrival_knots"]) < 2:
            raise RuntimeError(f"{k}: fewer than 2 arrival knots")
    json.dump({"rules": __doc__.split("\n\n", 1)[1].strip(), "presets": presets},
              open(os.path.join(dm.MODEL_DIR, "flood_presets.json"), "w"), indent=2)
    for k, p in presets.items():
        print(k, "arrival", [(round(a, 1), round(b)) for a, b in p["arrival_knots"]],
              "height", [(round(a, 1), round(b, 1)) for a, b in p["height_knots"]])


if __name__ == "__main__":
    main()
