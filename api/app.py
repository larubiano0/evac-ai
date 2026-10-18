"""evac-ai API (FastAPI). Run on the VM from the repo root:
    ~/venv/bin/uvicorn api.app:app --host 127.0.0.1 --port 8000
Open via SSH tunnel:  ssh -L 8000:localhost:8000 linux1@<VM_IP>   ->  http://localhost:8000
"""
import json, glob, os, platform, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from engine.scenario import Valley, Scenario, TF
from engine.flood import hhmm_to_min
from engine import alerts

ROOT = os.path.join(os.path.dirname(__file__), "..")
app = FastAPI(title="evac-ai: time to safety")
V = None
REPLAYS = {os.path.basename(p)[:-5]: json.load(open(p)) for p in sorted(glob.glob(f"{ROOT}/replay/*.json"))}
EXTRA_PEOPLE = {"oct11": {"Jagat": 100}}    # stranded trekkers (MCAP via Onlinekhabar, Oct 11)
# Replays this server can compute: the loaded Valley is the Budhi Gandaki build (data/proc). aug26 needs the
# Trishuli build + Trishuli OSM files in the Valley format; until then it is refused instead of being run on the
# wrong grid. Validation numbers for aug26: docs/validation.md.
VALLEY_REPLAYS = {"oct11"}
CACHE = {}


def valley():
    global V
    if V is None:
        V = Valley(proc=f"{ROOT}/data/proc", raw=f"{ROOT}/data/raw")
    return V


def scenario(replay, src=None, burst=None):
    key = (replay, src, burst)
    if key not in CACHE:
        if replay not in REPLAYS:
            raise HTTPException(404, f"unknown replay {replay}")
        if replay not in VALLEY_REPLAYS:
            raise HTTPException(501, f"replay {replay} needs a valley build this server has not loaded")
        rep = REPLAYS[replay]
        env = scenario(replay).F if src else None          # new source -> reuse calibrated envelope
        CACHE[key] = Scenario(valley(), rep, source_lonlat=src, extra_people=EXTRA_PEOPLE.get(replay),
                              envelope=env, burst_hhmm=burst)
    return CACHE[key]


def _near_bridges(S, s, bridges, radius_m=2500):
    x0, y0 = TF.transform(s["lon"], s["lat"]); out = []
    for b in bridges:
        x, y = TF.transform(b["lon"], b["lat"])
        d = np.hypot(x - x0, y - y0)
        if d <= radius_m:
            out.append((d, b))
    return [b for d, b in sorted(out, key=lambda t: t[0])]


def _damage(S, sett, bridges):
    """Damage model (agent-lcpizani, models/damage) on this scenario: NEW keys only, nothing existing changes.
    Per settlement: mean P(destroyed) and expected destroyed buildings over its buildings in the 500 m corridor;
    per bridge at risk: P(destroyed) at its river crossing. Probabilities are calibrated but low for October-sized
    floods, so the UI ranks and colours by them instead of thresholding at 0.5. Cached on the scenario."""
    if not hasattr(S, "_dmg"):
        try:
            from engine import damage_model as dm
            S._dmg = dm.predict_scenario(S)
        except Exception as e:                                # missing model files must not break /api/scenario
            S._dmg = {"error": f"{type(e).__name__}: {e}"}
    res = S._dmg
    if "error" in res:
        return {"available": False, "error": res["error"]}
    V, p = S.V, res["p_building"]
    place = {(float(V.p_ll[i, 0]), float(V.p_ll[i, 1])): i for i in range(len(V.p_ll))}
    for s in sett:
        m = (V.b_place == place.get((s["lon"], s["lat"]), -2)) & np.isfinite(p)
        s["n_scored"] = int(m.sum())
        s["p_destroyed_mean"] = round(float(p[m].mean()), 4) if m.any() else None
        s["expected_destroyed"] = round(float(p[m].sum()), 1) if m.any() else None
    pb = {b["id"]: b["p_destroyed"] for b in res["bridges"]}
    for b in bridges:
        b["p_destroyed"] = pb.get(b["id"])
    return {"available": True, "version": res["version"], "runtime_s": round(res["runtime_s"], 2),
            "expected_destroyed_total": round(float(np.nansum(p[V.b_place >= 0])), 1),
            "buildings_scored": int(np.isfinite(p).sum()),
            "note": "P(destroyed) from a model trained on Aug 26 damage tags (spatial-holdout AUC 0.968/0.818); "
                    "rank and colour, do not threshold at 0.5"}


def payload(S, warn):
    t = time.time()
    sett = S.settlements(warn); bridges = S.bridges_at_risk()
    wmin = hhmm_to_min(warn) - S.t0
    for s in sett:
        s["alerts"] = alerts.build(s, _near_bridges(S, s, bridges), warn, wmin)
    damage = _damage(S, sett, bridges)
    return {"replay": S.rep["event"], "burst_time": S.rep["burst_time"] if S.t0 == hhmm_to_min(S.rep["burst_time"]) else None,
            "warning": warn, "summary": S.summary(warn), "settlements": sett, "damage_model": damage,
            "bridges_at_risk": [{k: v for k, v in b.items() if k != "geometry"} | {"geometry": b["geometry"]} for b in bridges],
            "path": S.path_geojson(), "wave_speeds_kmh": S.F.wave_speed_kmh(),
            "timing": {"scenario_compute_s": round(S.runtime_s, 2), "walk_s": round(S.walk_s, 2),
                       "response_s": round(time.time() - t, 2)},
            "host": {"machine": platform.machine(), "byteorder": sys.byteorder, "node": platform.node()}}


@app.get("/api/replays")
def replays():
    return {k: {"event": v["event"], "burst_time": v["burst_time"], "triggers": v["triggers"]} for k, v in REPLAYS.items()}


@app.get("/api/scenario")
def get_scenario(replay: str = "oct11", warn: str = "06:40"):
    return payload(scenario(replay), warn)


@app.get("/api/footprint")
def footprint(replay: str = "oct11", lon: float = None, lat: float = None, burst: str = None):
    src = (lon, lat) if lon is not None else None
    return scenario(replay, src, burst).footprint_geojson()


@app.get("/api/compare")
def compare(replay: str = "oct11"):
    S = scenario(replay)
    return {k: {**v, **S.summary(v["time"])} for k, v in REPLAYS[replay]["triggers"].items()}


class Trigger(BaseModel):
    lon: float
    lat: float
    burst: str          # HH:MM when the blockage burst / flood started
    warn: str           # HH:MM when the warning goes out
    replay: str = "oct11"   # which calibrated envelope to reuse


@app.post("/api/trigger")
def trigger(t: Trigger):
    S = scenario(t.replay, (round(t.lon, 4), round(t.lat, 4)), t.burst)
    return payload(S, t.warn)


# ---------------- prediction mode (agent-lcpizani): any trigger, every point, safest path + confidence ----------------
import threading
from typing import Optional
from fastapi.responses import Response
from engine import escape as esc

_PRED, _PRED_ORDER, _PRED_LOCK = {}, [], threading.Lock()


def _pred_scenario(valley_key, lon=None, lat=None, preset=None):
    if valley_key not in esc.VALLEYS:
        raise HTTPException(404, f"unknown valley {valley_key}")
    if preset is not None and preset not in esc.presets():
        raise HTTPException(404, f"unknown flood type {preset}")
    trig = (round(lon, 4), round(lat, 4)) if lon is not None and lat is not None else None
    sid = f"{valley_key}|{trig}|{preset}"
    with _PRED_LOCK:
        if sid not in _PRED:
            try:
                _PRED[sid] = esc.FloodScenario(valley_key, trig, preset)
            except ValueError as e:
                raise HTTPException(400, str(e))
            _PRED_ORDER.append(sid)
            while len(_PRED_ORDER) > 4:                       # keep memory bounded on the shared VM
                _PRED.pop(_PRED_ORDER.pop(0), None)
    return sid, _PRED[sid]


class PredictScenario(BaseModel):
    valley: str = "budhi"
    lon: Optional[float] = None       # trigger point (any river cell); default = the preset's real source
    lat: Optional[float] = None
    preset: Optional[str] = None      # flood type calibrated on a real flood: oct11 | aug26


class PredictEscape(BaseModel):
    sid: str
    lon: float                        # where you are
    lat: float
    minutes_after_start: float        # the time now, in minutes after the flood started


@app.get("/api/predict/options")
def predict_options():
    return {"valleys": {k: {"name": v["name"], "default_preset": v["default_preset"]} for k, v in esc.VALLEYS.items()},
            "presets": {k: {"label": p["label"], "native_valley": p["native_valley"], "burst_time": p["burst_time"]}
                        for k, p in esc.presets().items()},
            "rules": {"unsafe_p": esc.UNSAFE_P, "search_radius_m": esc.SEARCH_RADIUS_M}}


@app.post("/api/predict/scenario")
def predict_scenario(q: PredictScenario):
    t = time.time()
    sid, S = _pred_scenario(q.valley, q.lon, q.lat, q.preset)
    with _PRED_LOCK:
        png, bounds = S.p_png() if not hasattr(S, "_png") else S._png
        S._png = (png, bounds)
    return {"sid": sid, **S.describe(), "p_overlay": {"url": f"/api/predict/p.png?sid={sid}", "bounds": bounds},
            "path_geojson": {"type": "LineString", "coordinates": [[s["lon"], s["lat"]] for s in S.describe()["stations"]]},
            "response_s": round(time.time() - t, 2),
            "host": {"machine": platform.machine(), "byteorder": sys.byteorder}}


@app.get("/api/predict/p.png")
def predict_png(sid: str):
    S = _PRED.get(sid)
    if S is None:
        raise HTTPException(404, "unknown or expired scenario; POST /api/predict/scenario again")
    if not hasattr(S, "_png"):
        S._png = S.p_png()
    return Response(S._png[0], media_type="image/png")


@app.post("/api/predict/escape")
def predict_escape(q: PredictEscape):
    S = _PRED.get(q.sid)
    if S is None:
        raise HTTPException(404, "unknown or expired scenario; POST /api/predict/scenario again")
    return {**S.escape(q.lon, q.lat, q.minutes_after_start),
            "host": {"machine": platform.machine(), "byteorder": sys.byteorder}}


# ---------------- what-if floods on the IBM Telum on-chip AI accelerator (agent-aayush-nnpa; engine/whatif.py) ----------------
_WHATIF_LOCK = threading.Lock()


@app.get("/api/predict/whatif")
def predict_whatif(valley: str = "budhi", preset: Optional[str] = None, n: int = 100):
    from engine import whatif
    n = max(10, min(int(n), 200))
    t = time.time()
    sid, S = _pred_scenario(valley, None, None, preset)
    with _WHATIF_LOCK:                                    # one accelerator job at a time
        r = whatif.compute(S, n)
        if "_png" not in r:
            r["_png"] = whatif.png(S, r)
    out = {k: v for k, v in r.items() if k not in ("grid", "_png")}
    return {"sid": sid, **out, "overlay": {"url": f"/api/predict/whatif.png?sid={sid}&n={n}", "bounds": r["_png"][1]},
            "response_s": round(time.time() - t, 2)}


@app.get("/api/predict/whatif.png")
def predict_whatif_png(sid: str, n: int = 100):
    S = _PRED.get(sid)
    r = getattr(S, "_whatif", {}).get(n) if S is not None else None
    if r is None or "_png" not in r:
        raise HTTPException(404, "unknown or expired what-if; GET /api/predict/whatif again")
    return Response(r["_png"][0], media_type="image/png")


@app.get("/predict")
def predict_page():
    return FileResponse(f"{ROOT}/web/predict.html")


@app.get("/go")
def go_page():                                    # resident "Go" view (agent-aayush-go): GPS, one instruction, offline
    return FileResponse(f"{ROOT}/web/go.html", headers={"Cache-Control": "no-cache"})


@app.get("/go-sw.js")
def go_sw():                                      # its service worker, served from / so it may control /go
    return FileResponse(f"{ROOT}/web/go-sw.js", media_type="text/javascript", headers={"Cache-Control": "no-cache"})


@app.get("/")
def index():
    return FileResponse(f"{ROOT}/web/index.html")


app.mount("/static", StaticFiles(directory=f"{ROOT}/web"), name="static")
