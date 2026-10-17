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


def payload(S, warn):
    t = time.time()
    sett = S.settlements(warn); bridges = S.bridges_at_risk()
    wmin = hhmm_to_min(warn) - S.t0
    for s in sett:
        s["alerts"] = alerts.build(s, _near_bridges(S, s, bridges), warn, wmin)
    return {"replay": S.rep["event"], "burst_time": S.rep["burst_time"] if S.t0 == hhmm_to_min(S.rep["burst_time"]) else None,
            "warning": warn, "summary": S.summary(warn), "settlements": sett,
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


@app.get("/predict")
def predict_page():
    return FileResponse(f"{ROOT}/web/predict.html")


@app.get("/")
def index():
    return FileResponse(f"{ROOT}/web/index.html")


app.mount("/static", StaticFiles(directory=f"{ROOT}/web"), name="static")
