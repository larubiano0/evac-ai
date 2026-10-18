"""Bake a viewer bundle (schema evac-ai/scenario@1, see docs/viewer/data-schema.md) from claude-luis's engine.

Run from the root of a repo copy whose data/proc and data/raw hold the engine inputs:
    python3 viewer/bake/bake_scenario.py oct11 <out_dir>
(viewer/bake/run_on_vm.sh sets this up on the L1CC VM without touching ~/evac-ai.)

Rasters are written as explicit little-endian uint16 ('<u2'): the VM is s390x (big-endian).
"""
import datetime, json, os, platform, re, sys, time
import numpy as np

sys.path.insert(0, os.getcwd())
from engine.scenario import Valley, Scenario, TF, DISSEMINATION_MIN, PERSONS_PER_BUILDING   # noqa: E402
from engine.flood import hhmm_to_min                                    # noqa: E402

SCHEMA = "evac-ai/scenario@1"
EXTRA_PEOPLE = {"oct11": {"Jagat": 100}}       # same as api/app.py (stranded trekkers)
NODATA, CAP = 65535, 65534
KM_STEP = 0.1                                  # envelope lookup spacing (km)
SCALE = {"dem": 0.25, "hand": 0.1, "riverkm": 0.01, "walk": 0.1}
WARN_LABELS = {"community_relay": "Community relay", "police_informed": "Police informed",
               "ndrrma_official": "NDRRMA informed", "official_sms": "Official SMS"}
BRIDGE_ROUTE_M = 45.0                          # an at-risk bridge within this distance of a route vertex is on the route


def quantize(a, scale):
    """float array (NaN = no data) -> little-endian uint16 with NODATA."""
    out = np.full(a.shape, NODATA, dtype="<u2")
    ok = np.isfinite(a)
    out[ok] = np.clip(np.round(a[ok] / scale), 0, CAP).astype("<u2")
    return out


def write_layer(path, arr_u16, shape):
    assert arr_u16.dtype == np.dtype("<u2") and arr_u16.shape == shape
    arr_u16.tofile(path)
    back = np.fromfile(path, dtype="<u2").reshape(shape)
    assert np.array_equal(back, arr_u16), f"round-trip failed for {path}"


def lookup(arr, km):
    """Linear interpolation in an array sampled every KM_STEP (same math as the shader)."""
    f = np.clip(km / KM_STEP, 0, len(arr) - 1)
    i0 = np.floor(f).astype(int); i1 = np.minimum(i0 + 1, len(arr) - 1)
    return arr[i0] + (arr[i1] - arr[i0]) * (f - i0)


def descend(tts, r, c, max_steps=2000):
    """Steepest descent on the time-to-safety surface from (r, c) to safe ground."""
    ny, nx = tts.shape
    path = [(r, c)]
    for _ in range(max_steps):
        v = tts[r, c]
        if not np.isfinite(v) or v <= 0:
            break
        best, bv = None, v
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rr, cc = r + dr, c + dc
                if (dr or dc) and 0 <= rr < ny and 0 <= cc < nx and np.isfinite(tts[rr, cc]) and tts[rr, cc] < bv:
                    best, bv = (rr, cc), tts[rr, cc]
        if best is None:
            break
        r, c = best
        path.append(best)
    return path


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "x"


def main(replay_id, out):
    t_start = time.time()
    os.makedirs(out, exist_ok=True)
    rep = json.load(open(f"replay/{replay_id}.json"))
    V = Valley()
    S = Scenario(V, rep, extra_people=EXTRA_PEOPLE.get(replay_id))
    T = V.T
    ny, nx = T.shape
    tr = T.transform
    assert abs(tr.a - abs(tr.e)) < 1e-6 and tr.b == 0 and tr.d == 0, "expected square, north-up cells"
    dx, x_left, y_top = float(tr.a), float(tr.c), float(tr.f)
    t0 = int(S.t0)

    # ---------- raster layers ----------
    dem = T.dem
    assert np.isfinite(dem).all() and dem.min() > 0, "DEM has no-data cells or non-positive values"
    km = np.where(np.isfinite(S.km), S.km, np.nan)
    hand = np.where(np.isfinite(S.hand), np.maximum(S.hand, 0.0), np.nan)
    walk_min = S.tts / 60.0
    layers = {"dem": quantize(dem, SCALE["dem"]), "hand": quantize(hand, SCALE["hand"]),
              "riverkm": quantize(km, SCALE["riverkm"]), "walk": quantize(walk_min, SCALE["walk"])}
    for name, a in layers.items():
        write_layer(f"{out}/{name}.u16.bin", a, (ny, nx))

    # ---------- flood envelope lookup (engine: early arrival, conservative height) ----------
    km_max = float(S.km_path[-1])
    ks = np.arange(0.0, km_max + 1.5 * KM_STEP, KM_STEP)
    arr_lo = np.asarray(S.F.arrival(ks)) * (1 - S.F.time_band)      # == Scenario.a_lo
    h_hi = np.asarray(S.F.height_band_at(ks)[2])                      # == Scenario.h_hi
    assert np.all(np.diff(arr_lo) >= 0), "arrival must not decrease downstream"

    # footprint parity, using the quantized layers exactly as the shader does
    kq, hq = layers["riverkm"], layers["hand"]
    okq = (kq != NODATA) & (hq != NODATA)
    kmq = kq[okq] * SCALE["riverkm"]
    baked_fp = int(np.sum(hq[okq] * SCALE["hand"] <= lookup(h_hi, kmq)))
    engine_fp = int(S.flood.sum())

    # ---------- warnings, headline ----------
    warnings, headline = {}, {}
    for wid, w in rep["triggers"].items():
        warnings[wid] = {"label": WARN_LABELS.get(wid, wid.replace("_", " ").capitalize()),
                         "desc": w.get("desc", ""), "t_min": hhmm_to_min(w["time"])}
        sm = S.summary(w["time"])
        headline[wid] = {k: v for k, v in sm.items() if k != "warning"}
    default_warning = "community_relay" if "community_relay" in warnings else next(iter(warnings))

    # ---------- bridges at risk ----------
    bridges = []
    for b in S.bridges_at_risk():
        x, y = TF.transform(b["lon"], b["lat"])
        if not np.isfinite(b["river_km"]):
            continue
        bridges.append({"id": str(b["id"]), "label": b.get("label") or b["name"] or "bridge",
                        "x": round(x, 1), "y": round(y, 1), "river_km": round(b["river_km"], 2),
                        "arrival_min": round(t0 + b["arrival_minutes_after_burst"], 2)})
    bxy = np.array([[b["x"], b["y"]] for b in bridges]) if bridges else np.zeros((0, 2))

    # ---------- settlements: effective walk so that slack equals the engine's slack_min ----------
    first_warn = rep["triggers"][default_warning]["time"]
    at_risk, b_arr, b_walk, _ = S.buildings(first_warn)               # arrival and walk do not depend on the warning
    engine_by_warn = {wid: {(s["name"], round(s["lon"], 6), round(s["lat"], 6)): s
                            for s in S.settlements(w["time"])} for wid, w in rep["triggers"].items()}
    extra = EXTRA_PEOPLE.get(replay_id, {})
    settlements, used_ids, units_by_sid = [], set(), {}
    for p in np.unique(V.b_place[at_risk & (V.b_place >= 0)]):
        m = at_risk & (V.b_place == p)
        key = (V.p_name[p], round(float(V.p_ll[p, 0]), 6), round(float(V.p_ll[p, 1]), 6))
        eng = {wid: d[key] for wid, d in engine_by_warn.items()}
        diff = b_arr[m] - b_walk[m]
        k_lim = float(diff.min())
        arrival_e = float(b_arr[m].min())
        walk_eff = arrival_e - k_lim
        # people units: one per at-risk building (engine: PERSONS_PER_BUILDING), trekkers on the limiting building
        lim = int(np.argmin(diff))
        units = [[float(t0 + a), float(w), PERSONS_PER_BUILDING] for a, w in zip(b_arr[m], b_walk[m])]
        units[lim][2] += float(extra.get(V.p_name[p], 0))
        e0 = eng[default_warning]
        if e0.get("route"):            # engine escape route (r.walk movement directions), lon/lat
            route = [[round(v, 1) for v in TF.transform(lo, la)] for lo, la in e0["route"]]
        else:                          # older engine: steepest descent on the time surface from the limiting building
            lim_flat = int(V.b_flat[np.flatnonzero(m)[int(np.argmin(diff))]])
            route = [[round(v, 1) for v in T.xy(r, c)] for r, c in descend(S.tts, *np.unravel_index(lim_flat, T.shape))]
        bridge = None
        if len(bxy) and len(route) > 1:
            rxy = np.array(route)
            d = np.hypot(rxy[:, None, 0] - bxy[None, :, 0], rxy[:, None, 1] - bxy[None, :, 1])
            hit = np.argwhere(d <= BRIDGE_ROUTE_M)
            if len(hit):
                i, j = hit[np.argmin(hit[:, 0])]
                bridge = {"id": bridges[j]["id"], "frac": round(float(i) / (len(route) - 1), 4)}
        x, y = TF.transform(*V.p_ll[p])
        sid = slug(V.p_name[p])
        while sid in used_ids:
            sid += "-2"
        used_ids.add(sid)
        units_by_sid[sid] = units
        settlements.append({
            "id": sid, "name": V.p_name[p], "name_ne": e0.get("name_ne") or V.p_name[p],
            "x": round(x, 1), "y": round(y, 1), "pop": float(e0["people_at_risk"]),
            "buildings": int(m.sum()),
            "river_km": round(float(e0["river_km"]), 2),
            "arrival_min": round(t0 + arrival_e, 3), "walk_min": round(walk_eff, 3),
            "route_walk_min": round(float(e0.get("walk_min_max", walk_eff)), 3),
            "route_len_m": round(float(e0.get("route_len_m", 0.0)), 1),
            "route_climb_m": round(float(e0.get("route_climb_m", 0.0)), 1),
            "engine_slack": {wid: round(float(e["slack_min"]), 3) for wid, e in eng.items()},
            "engine": {wid: {"people_without_time": float(e["people_without_time"]), "status": e["status"],
                             "slack_min": round(float(e["slack_min"]), 3)} for wid, e in eng.items()},
            "route": route, "bridge": bridge})
    settlements.sort(key=lambda s: s["arrival_min"])
    sidx = {s["id"]: i for i, s in enumerate(settlements)}
    units_out = [[sidx[sid], a, w, n] for sid, us in units_by_sid.items() for a, w, n in us]
    units_out.sort(key=lambda u: (u[0], u[1]))
    assert len(settlements) == len(next(iter(engine_by_warn.values()))), "settlement count differs from engine"

    # settlements whose state would be changed by the bridge rule (engine does not model bridge timing)
    bridge_by_id = {b["id"]: b for b in bridges}
    divergence = []
    for s in settlements:
        if not s["bridge"]:
            continue
        for wid, w in warnings.items():
            reach = w["t_min"] + DISSEMINATION_MIN + s["bridge"]["frac"] * s["walk_min"]
            if bridge_by_id[s["bridge"]["id"]]["arrival_min"] < reach and s["engine_slack"][wid] >= 0:
                divergence.append({"settlement": s["id"], "warning": wid})

    # ---------- events (timeline ticks) ----------
    events = [{"t_min": t0, "label": "Flood bursts at source", "kind": "burst"}]
    for wid, w in warnings.items():
        events.append({"t_min": w["t_min"], "label": w["label"], "kind": "warning"})
    for o in rep["observations"]:
        if o.get("use") == "excluded":
            continue
        place = o["place"].split("/")[-1]
        if "first_arrival" in o:
            events.append({"t_min": hhmm_to_min(o["first_arrival"]), "label": f"Wave at {place}", "kind": "impact"})
        if "second_wave" in o:
            events.append({"t_min": hhmm_to_min(o["second_wave"]), "label": f"Second wave at {place}", "kind": "impact"})
    events.sort(key=lambda e: e["t_min"])

    # ---------- time range ----------
    t_first = min([t0] + [w["t_min"] for w in warnings.values()])
    t_last = max([t0 + float(arr_lo[-1])] + [e["t_min"] for e in events] + [s["arrival_min"] for s in settlements])
    time_range = [int(np.floor((t_first - 15) / 5) * 5), int(min(np.ceil((t_last + 20) / 10) * 10, 24 * 60))]

    # ---------- flood path polyline ----------
    path = []
    idx = list(range(0, len(S.path), 5)) + ([len(S.path) - 1] if (len(S.path) - 1) % 5 else [])
    for i in idx:
        x, y = T.xy(*np.unravel_index(int(S.path[i]), T.shape))
        path.append([round(x, 1), round(y, 1), round(float(S.km_path[i]), 3)])

    # ---------- cameras ----------
    def cam(cid, label, x, y, dist, az=200.0, polar=38.0):      # fairly top-down: deep gorges hide the river at low angles
        r, c = T.rc(x, y)
        r, c = min(max(r, 0), ny - 1), min(max(c, 0), nx - 1)
        return {"id": cid, "label": label, "x": round(x, 1), "y": round(y, 1), "z": round(float(dem[r, c]), 1),
                "dist_m": dist, "az_deg": az, "polar_deg": polar}
    pxy = np.array([[p[0], p[1]] for p in path])
    mid = pxy[len(pxy) // 2]
    cameras = [cam("overview", "Overview", float(mid[0]), float(mid[1]), 70000.0, 190.0, 50.0)]
    sx, sy = TF.transform(rep["source"]["lon"], rep["source"]["lat"])
    cameras.append(cam("source", "Source", sx, sy, 16000.0))
    for o in rep["observations"]:
        if o.get("use") == "calibration":
            ox, oy = TF.transform(o["lon"], o["lat"])
            cameras.append(cam(slug(o["place"].split("/")[-1]), o["place"].split("/")[-1], ox, oy, 11000.0))

    date = re.search(r"\d{4}-\d{2}-\d{2}", rep["event"]).group(0)
    scenario = {
        "schema": SCHEMA, "id": replay_id, "title": rep["event"], "synthetic": False, "crs": "EPSG:32645",
        "grid": {"x_left": x_left, "y_top": y_top, "dx": dx, "nx": int(nx), "ny": int(ny),
                 "dem_min": round(float(dem.min()), 2), "dem_max": round(float(dem.max()), 2)},
        "t_ref": f"{date}T00:00:00+05:45", "time_range_min": time_range, "burst_min": t0,
        "dissemination_min": float(DISSEMINATION_MIN),
        "flood": {"km_step": KM_STEP, "arrival_min": [round(float(v), 3) for v in arr_lo],
                  "height_m": [round(float(v), 3) for v in h_hi], "path": path},
        "warnings": warnings, "default_warning": default_warning,
        "settlements": settlements, "units": units_out, "bridges": bridges, "events": events, "cameras": cameras,
        "layers": ["slack", "arrival", "walk", "hand"], "headline": headline,
        "checks": {"footprint_cells_engine": engine_fp, "footprint_cells_baked": baked_fp,
                   "bridge_divergence": divergence},
        "provenance": {"engine": "engine/ (claude-luis): Valley + Scenario, GRASS r.watershed + r.walk",
                       "replay": f"replay/{replay_id}.json", "machine": platform.machine(),
                       "byteorder": sys.byteorder, "node": platform.node(),
                       "baked_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                       "bake_s": round(time.time() - t_start, 1)},
    }
    with open(f"{out}/scenario.json", "w") as f:
        json.dump(scenario, f, allow_nan=False, ensure_ascii=False, separators=(",", ":"))
    print(f"baked {replay_id}: {nx}x{ny}, {len(settlements)} settlements, {len(bridges)} bridges, "
          f"footprint engine={engine_fp} baked={baked_fp}, bridge divergence={len(divergence)}, "
          f"{scenario['provenance']['bake_s']} s on {platform.machine()} ({sys.byteorder}-endian)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "oct11", sys.argv[2] if len(sys.argv) > 2 else "out/oct11")
