"""Smoke + sanity test for prediction mode (engine/escape.py) on the VM. Real presets, real terrain.

Checks: scenarios build for both valleys and a moved trigger; every route is contiguous 8-neighbour steps;
route times are increasing; no route point is entered after the flood when its p exceeds the tau used;
confidence equals 1 - max(risk); points outside the zone say so; timing on s390x.
"""
import json, os, platform, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from engine import escape as esc

fails = []


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
