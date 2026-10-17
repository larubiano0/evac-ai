"""Smoke + sanity test for prediction mode (engine/escape.py) on the VM. Real presets, real terrain.

Checks: scenarios build for both valleys and a moved trigger; every route is contiguous 8-neighbour steps;
route times are increasing; no route point is entered after the flood when its p exceeds the tau used;
confidence equals 1 - max(risk); points outside the zone say so; timing on s390x.
escape-route-ux checks (time-aware addendum): risky points are only passed before the flood; the destination
follows the a/b/c rule, checked against exhaustive searches: (a) closest safe cell walking, (b) closest safe
cell at the running pace when walking can't reach one, (c) lowest-P reachable cell (ties: sooner) when no safe
cell is reachable; the running pace is 2x for the first 5 min only (synthetic grid); can_run=False walks;
destination_safe agrees with the zone's max_risk; the hazard is never the destination; urgency thresholds;
same query twice -> same answer; screenshot + 128-min cases; p50/p95 query time on s390x.
"""
import ctypes, json, os, platform, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from engine import escape as esc

fails = []
# old answers here ended on a 13-20% cell at the edge of the red band (scan of the pre-change engine, t=0)
SCREENSHOT_CASES = [(84.94583, 28.46362), (84.96257, 28.46956), (84.94668, 28.46742), (84.93884, 28.46081)]
# 84.93884, 28.46081 is also the "128-min" case: the least-risky-crossing ladder sent it on a 128 min climb


def full_search(S, res, run, goal_p):
    """Re-run the C search for this answer's start; returns (goal or -1, T, p, start). goal_p < 0 = exhaustive."""
    x, y = S.V.tf.transform(res["path"][0]["lon"], res["path"][0]["lat"])
    r, c = S.V.T.rc(x, y)
    (r0, c0, nr, nc), (dem, trail, blocked, p, A) = S._window(r, c, None)
    lib = esc._search_lib()
    Tm = np.empty(nr * nc, np.float64); prev = np.empty(nr * nc, np.int32)
    start = (r - r0) * nc + (c - c0)
    blocked.flat[start] = 0
    P = esc._ptr
    g = lib.escape_search(nr, nc, P(dem, ctypes.c_float), P(trail, ctypes.c_ubyte), P(blocked, ctypes.c_ubyte),
                          P(p, ctypes.c_float), P(A, ctypes.c_float), start, res["minutes_after_start"], esc.UNSAFE_P,
                          esc.CELL, P(Tm, ctypes.c_double), P(prev, ctypes.c_int), goal_p,
                          esc.RUN_SPEEDUP if run else 1.0, esc.RUN_LIMIT_MIN)
    return g, Tm, p.ravel(), start


def check_destination(S, res, label):
    """a/b/c rule against exhaustive searches; destination_safe <=> p_dest <= UNSAFE_P; zone threshold; hazard."""
    if res["status"] != "route":
        return
    d, ok, ch, pace = res["destination"], res["destination_safe"], res["choice"], res["pace"]
    can_run = res.get("can_run", True)
    if ok != (d["p_destroyed"] <= esc.UNSAFE_P + 5e-4):
        fails.append(f"{label}: destination_safe={ok} but p_dest={d['p_destroyed']}")
    if ok != (ch == "closest_safe"):
        fails.append(f"{label}: choice {ch} vs destination_safe {ok}")
    if not can_run and pace != "walk":
        fails.append(f"{label}: can_run=False but pace {pace}")
    for pt in res["path"][1:]:
        a = pt["flood_arrival_min"]
        if pt["p_destroyed"] > esc.UNSAFE_P and a is not None and pt["t_min"] >= a:
            fails.append(f"{label}: risky point passed after the flood (t {pt['t_min']} >= {a})"); break
    z = res.get("safe_zone") or {}
    if ok and z.get("max_risk", 0) > esc.UNSAFE_P + 1e-9:
        fails.append(f"{label}: safe destination but zone max_risk {z.get('max_risk')}")
    if not ok and abs(z.get("max_risk", -1) - round(d["p_destroyed"] + 0.01, 3)) > 1e-9:
        fails.append(f"{label}: best-effort zone max_risk {z.get('max_risk')} != p_dest + 0.01")
    g_walk = full_search(S, res, False, esc.UNSAFE_P)[0]
    if ch == "closest_safe":
        if pace == "run" and g_walk >= 0:
            fails.append(f"{label}: ran although safe ground is reachable walking")
        _, Tm, p, start = full_search(S, res, pace == "run", -1.0)
        safe = (p <= esc.UNSAFE_P) & np.isfinite(Tm)
        safe[start] = False
        if not safe.any() or abs(Tm[safe].min() - d["t_min"]) > 0.01:
            fails.append(f"{label}: destination is not the closest safe cell at pace {pace}")
    else:
        if full_search(S, res, can_run, esc.UNSAFE_P)[0] >= 0:
            fails.append(f"{label}: best-effort destination although safe ground is reachable")
        _, Tm, p, start = full_search(S, res, can_run, -1.0)
        reach = np.isfinite(Tm); reach[start] = False
        pr = np.round(p[reach].astype(float), 3)
        if abs(pr.min() - d["p_destroyed"]) > 1e-3:
            fails.append(f"{label}: (c) destination p {d['p_destroyed']} but safest reachable is {pr.min()}")
        elif abs(Tm[reach][pr == pr.min()].min() - d["t_min"]) > 0.01:
            fails.append(f"{label}: (c) tie not broken by the sooner arrival")
    hz = res.get("hazard")
    if hz is not None:
        if hz["index"] >= len(res["path"]) - 1 or (hz["lon"], hz["lat"]) == (d["lon"], d["lat"]):
            fails.append(f"{label}: hazard is the destination")
        if hz["p_destroyed"] <= esc.UNSAFE_P or hz["kind"] not in ("race", "flooded"):
            fails.append(f"{label}: bad hazard {hz}")
    if res.get("urgency") not in ("walk", "hurry", "run"):
        fails.append(f"{label}: route without urgency")
    if (pace == "run" or not ok) and res.get("urgency") != "run":
        fails.append(f"{label}: running pace / unsafe destination but urgency {res.get('urgency')}")
    if pace == "run" and can_run and not res.get("walk_only"):
        fails.append(f"{label}: running answer without walk_only")


def pace_check():
    """Synthetic flat trail, 1 x 400 cells, no flood: running = half the walking time while elapsed < 5 min,
    walking after (an edge straddling 5 min is split)."""
    n = 400
    dem = np.zeros(n, np.float32); trail = np.ones(n, np.uint8); blocked = np.zeros(n, np.uint8)
    p = np.zeros(n, np.float32); A = np.full(n, np.inf, np.float32)
    lib, P = esc._search_lib(), esc._ptr
    out = {}
    for run in (False, True):
        Tm = np.empty(n, np.float64); prev = np.empty(n, np.int32)
        lib.escape_search(1, n, P(dem, ctypes.c_float), P(trail, ctypes.c_ubyte), P(blocked, ctypes.c_ubyte),
                          P(p, ctypes.c_float), P(A, ctypes.c_float), 0, 100.0, esc.UNSAFE_P, esc.CELL,
                          P(Tm, ctypes.c_double), P(prev, ctypes.c_int), -1.0, 2.0 if run else 1.0, esc.RUN_LIMIT_MIN)
        out[run] = Tm - 100.0
    W = out[False]
    expect = np.where(W / 2 <= esc.RUN_LIMIT_MIN, W / 2, esc.RUN_LIMIT_MIN + (W - 2 * esc.RUN_LIMIT_MIN))
    err = np.abs(out[True] - expect).max()
    print(f"pace check: walk {W[-1]:.1f} min for 12 km, run {out[True][-1]:.1f} min (expected {expect[-1]:.1f}); "
          f"max error {err:.2e} min; 5-min cap saves exactly {W[-1] - out[True][-1]:.2f} min")
    if err > 1e-6:
        fails.append(f"pace check: running pace error {err}")


def unit_checks():
    """Urgency thresholds and hazard choice on hand-made answers (no terrain needed)."""
    U = esc.FloodScenario._urgency
    you = {"flood_already_here": False}
    route = lambda m, unsafe=False, here=False, pace="walk", ok=True: {
        "status": "route", "you": {"flood_already_here": here}, "pace": pace, "destination_safe": ok,
        "min_margin_before_flood_min": m,
                                                 "path": [{"unsafe": unsafe}, {"unsafe": False}]}
    cases = [(route(25), "walk"), (route(None), "walk"), (route(10), "walk"), (route(9.9), "hurry"),
             (route(3), "hurry"), (route(2), "run"), (route(-1), "run"), (route(30, unsafe=True), "run"),
             (route(30, here=True), "run"), (route(30, pace="run"), "run"), (route(None, ok=False), "run"), ({"status": "no_route", "you": you}, "run"),
             ({"status": "safe_here", "you": you}, None), ({"status": "outside_impact_zone", "you": you}, None)]
    for o, want in cases:
        if U(o) != want:
            fails.append(f"urgency {o.get('status')} m={o.get('min_margin_before_flood_min')}: {U(o)} != {want}")
    pt = lambda p, t, a: {"lon": 0, "lat": 0, "p_destroyed": p, "t_min": t, "flood_arrival_min": a}
    H = esc.FloodScenario._hazard
    # spec: one point p 0.4, flood there 14 min from now, you reach it 9 min from now -> race, pass before 14
    h = H([pt(0.05, 100, 200), pt(0.4, 109, 114), pt(0.02, 112, None)], [False, False, False], 100)
    if not h or h["kind"] != "race" or h["pass_before_min"] != 14 or h["index"] != 1:
        fails.append(f"hazard race: {h}")
    h = H([pt(0.05, 0, 9), pt(0.03, 1, None)], [False, False], 0)
    if h is not None:
        fails.append(f"hazard on a clear path: {h}")
    h = H([pt(0.3, 0, 50), pt(0.6, 5, 4), pt(0.4, 6, 5), pt(0.5, 9, None)], [False, True, True, False], 0)
    if not h or h["kind"] != "flooded" or h["index"] != 1:
        fails.append(f"hazard flooded (riskiest after the flood, never the 0.5 destination): {h}")
    print("unit checks (urgency, hazard):", "ok" if not fails else fails)


def check_route(S, res, label):
    if res["status"] != "route":
        return
    pts = res["path"]
    xy = np.array([S.V.tf.transform(p["lon"], p["lat"]) for p in pts])
    steps = np.hypot(*np.diff(xy, axis=0).T) if len(xy) > 1 else np.array([])
    if len(steps) and steps.max() > 30 * 1.5:
        fails.append(f"{label}: non-contiguous step {steps.max():.0f} m")
    t = [p["t_min"] for p in pts]
    if any(b < a for a, b in zip(t, t[1:])):
        fails.append(f"{label}: time not increasing")
    tau = res["risk_ladder_tau"]
    for p in pts[1:]:
        a = p["flood_arrival_min"]
        if a is not None and p["t_min"] >= a and p["p_destroyed"] > tau + 1e-6:
            fails.append(f"{label}: entered risky cell after the flood (p={p['p_destroyed']}, tau={tau})")
    if abs(res["confidence"] - (1 - max(p["risk"] for p in pts))) > 1e-3:
        fails.append(f"{label}: confidence mismatch")
    if res["safe"] != (len(res["unsafe_points"]) == 0):
        fails.append(f"{label}: safe flag inconsistent")


def show(S, name, lon, lat, t):
    t0 = time.time(); res = S.escape(lon, lat, t); dt = time.time() - t0
    check_route(S, res, name)
    check_destination(S, res, f"{name} t={t}")
    y = res.get("you", {})
    print(f"  {name:28s} t={t:5.0f} -> {res['status']:20s} tier={res.get('tier')} p_here={y.get('p_destroyed')} "
          f"flood_in={res.get('minutes_until_flood_here')} ({dt:.2f} s)\n      {res.get('headline')} | {res.get('message', '')}")
    if not res.get("headline") or not res.get("message"):
        fails.append(f"{name} t={t}: no headline/message")
    if res.get("tier") in ("will_hit", "likely") and res.get("walk_min") is None and "No way out" not in res.get("headline", ""):
        fails.append(f"{name} t={t}: at risk but no route")
    if res["status"] == "route" and not res.get("safe_zone"):
        fails.append(f"{name} t={t}: route without safe zone")
    if res.get("backup"):
        print(f"  {'':28s}            backup: {res['backup']['message'][:120]}")
    return res


def main():
    print("arch", platform.machine())
    unit_checks()
    pace_check()
    t0 = time.time(); S = esc.FloodScenario("budhi"); print(f"budhi/oct11 scenario {time.time() - t0:.1f} s:",
                                                            json.dumps({k: v for k, v in S.describe().items()
                                                                        if k in ('path_km', 'cells_scored', 'cells_p_gt_unsafe', 'runtime_s')}))
    print("  bridges crossing the flood river:", sum(b["crosses_flood_river"] for b in S.bridge_info), "of", len(S.bridge_info))
    pts = {"Jagat/Salleri (replay obs)": (84.8959, 28.3514), "Soti (replay obs)": (84.8547, 28.1353),
           "Arughat (replay obs)": (84.8089, 28.0416)}
    for name, (lo, la) in pts.items():
        for t in (0, 30, 120, 200):
            show(S, name, lo, la, t)
    # a hillside point ~1.5 km from the river above Arughat (outside the zone)
    show(S, "hillside E of Arughat", 84.83, 28.045, 0)
    # 3.2 screenshot case (upper Budhi near the 2160 m contour) + the 128-min case (last one)
    def line(res):
        d = res["destination"]
        return (f"{res['choice']}/{res['pace']}: destination ({d['lon']}, {d['lat']}) p={d['p_destroyed']} "
                f"safe={res['destination_safe']} {res['walk_min']} min, {res['distance_m']} m, +{res['climb_m']} m, "
                f"urgency {res['urgency']}, hazard {res['hazard'] and res['hazard']['kind']}")
    print("screenshot + 128-min cases (oct11, t=0):")
    for lo, la in SCREENSHOT_CASES:
        res = show(S, f"2160m {lo},{la}", lo, la, 0)
        if res["status"] == "route":
            print("      -> " + line(res))
            w = res.get("walk_only") or S.escape(lo, la, 0, can_run=False)
            check_destination(S, w, f"2160m {lo},{la} can't run")
            print("      -> can't run: " + (line(w) if w["status"] == "route" else w["status"]))
    # determinism + random at-risk points: invariants, a/b/c counts and s390x query timing
    rng = np.random.default_rng(1)
    cells = np.argwhere(np.isfinite(S.p) & (S.p > esc.UNSAFE_P))
    cells = cells[rng.permutation(len(cells))[:120]]
    times, n_route, kinds = [], 0, {}
    for i, (r, c) in enumerate(cells):
        lo, la = esc.V_inv(S, r, c)
        t = float((0, 30, 90)[i % 3])
        t0 = time.perf_counter(); res = S.escape(lo, la, t); times.append(time.perf_counter() - t0)
        check_route(S, res, f"random {i}"); check_destination(S, res, f"random {i}")
        if res.get("walk_only"):
            check_route(S, res["walk_only"], f"random {i} can't run")
            check_destination(S, res["walk_only"], f"random {i} can't run")
        if res["status"] == "route":
            n_route += 1
            k = {("closest_safe", "walk"): "a", ("closest_safe", "run"): "b"}.get((res["choice"], res["pace"]), "c")
            kinds[k] = kinds.get(k, 0) + 1
        else:
            kinds[res["status"]] = kinds.get(res["status"], 0) + 1
        if i < 10:
            again = S.escape(lo, la, t)
            if any(json.dumps(res.get(k)) != json.dumps(again.get(k)) for k in ("path", "destination", "safe_zone")):
                fails.append(f"random {i}: same query, different answer")
    print(f"random at-risk points: {len(cells)} queries, {n_route} routes; a/b/c and other answers: {kinds}")
    for k in ("a", "b", "c"):
        if not kinds.get(k):
            print(f"  NOTE: no case ({k}) among the random points")
    ms = np.array(times) * 1000
    print(f"escape() p50 {np.percentile(ms, 50):.1f} ms, p95 {np.percentile(ms, 95):.1f} ms, max {ms.max():.1f} ms")
    if np.percentile(ms, 95) >= 50:
        fails.append(f"escape p95 {np.percentile(ms, 95):.1f} ms >= 50 ms")
    # moved trigger: start the same flood type further downstream (Soti)
    t0 = time.time(); S2 = esc.FloodScenario("budhi", (84.8547, 28.1353), "oct11")
    print(f"budhi moved trigger (Soti) {time.time() - t0:.1f} s, path {S2.describe(short=True)['path_km']} km")
    show(S2, "Arughat, trigger at Soti", 84.8089, 28.0416, 10)
    # Trishuli with the Aug 26 preset
    t0 = time.time(); S3 = esc.FloodScenario("trishuli"); print(f"trishuli/aug26 scenario {time.time() - t0:.1f} s")
    for name, (lo, la) in {"Betrawati": (85.186, 27.9731), "Trishuli bazaar": (85.148, 27.9232)}.items():
        for t in (0, 40):
            show(S3, name, lo, la, t)
    png, bounds = S.p_png(); print("p_png bytes", len(png), "bounds", bounds)
    print("FAILS:", fails or "none")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
