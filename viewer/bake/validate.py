"""Validate a viewer bundle against viewer/data/SCHEMA.md.
usage: python3 viewer/bake/validate.py viewer/data/oct11
Exit code 0 only if every check passes.
"""
import json, os, sys
import numpy as np

SCHEMA = "evac-ai/scenario@1"
NODATA = 65535
SCALE = {"dem": 0.25, "hand": 0.1, "riverkm": 0.01, "walk": 0.1}
REQUIRED = ["schema", "id", "title", "synthetic", "crs", "grid", "t_ref", "time_range_min", "burst_min",
            "dissemination_min", "flood", "warnings", "default_warning", "settlements", "bridges", "events",
            "cameras", "layers", "headline", "checks", "provenance"]


def _no_nan(c):
    raise ValueError(f"non-JSON constant {c} in scenario.json")


def lookup(arr, km, step):
    f = np.clip(km / step, 0, len(arr) - 1)
    i0 = np.floor(f).astype(int); i1 = np.minimum(i0 + 1, len(arr) - 1)
    return arr[i0] + (arr[i1] - arr[i0]) * (f - i0)


def main(d):
    fails = []
    def check(ok, msg):
        print(("ok    " if ok else "FAIL  ") + msg)
        if not ok:
            fails.append(msg)

    s = json.load(open(f"{d}/scenario.json"), parse_constant=_no_nan)
    check(s.get("schema") == SCHEMA, f"schema is {SCHEMA}")
    missing = [k for k in REQUIRED if k not in s]
    check(not missing, f"required fields present {missing or ''}")
    if missing:
        return fails
    g = s["grid"]; shape = (g["ny"], g["nx"])

    L = {}
    for name in SCALE:
        p = f"{d}/{name}.u16.bin"
        size = os.path.getsize(p) if os.path.exists(p) else -1
        check(size == g["nx"] * g["ny"] * 2, f"{name}.u16.bin has nx*ny*2 = {g['nx'] * g['ny'] * 2} bytes (got {size})")
        if size == g["nx"] * g["ny"] * 2:
            L[name] = np.fromfile(p, dtype="<u2").reshape(shape)
    if len(L) < 4:
        return fails

    dem = L["dem"]
    check(not (dem == NODATA).any(), "dem has no no-data cells")
    dmin, dmax = dem.min() * SCALE["dem"], dem.max() * SCALE["dem"]
    check(abs(dmin - g["dem_min"]) <= 0.25 and abs(dmax - g["dem_max"]) <= 0.25,
          f"little-endian DEM round-trip: decoded {dmin:.2f}..{dmax:.2f} m vs source {g['dem_min']}..{g['dem_max']} m")

    hand_ok, km_ok = L["hand"] != NODATA, L["riverkm"] != NODATA
    check(np.array_equal(hand_ok, km_ok), "hand and riverkm share the same no-data mask")

    F = s["flood"]
    arr, hgt = np.array(F["arrival_min"]), np.array(F["height_m"])
    check(len(arr) == len(hgt) > 1, "flood.arrival_min and flood.height_m have equal length > 1")
    check(bool(np.all(np.diff(arr) >= 0)), "flood arrival does not decrease downstream")
    kmax = L["riverkm"][km_ok].max() * SCALE["riverkm"]
    check(kmax <= (len(arr) - 1) * F["km_step"] + 1e-9, f"lookup covers max river-km {kmax:.2f}")

    ok = hand_ok & km_ok
    fp = int(np.sum(L["hand"][ok] * SCALE["hand"] <= lookup(hgt, L["riverkm"][ok] * SCALE["riverkm"], F["km_step"])))
    c = s["checks"]
    check(fp == c["footprint_cells_baked"], f"footprint recomputed ({fp}) == bake's count ({c['footprint_cells_baked']})")
    rel = abs(fp - c["footprint_cells_engine"]) / max(c["footprint_cells_engine"], 1)
    check(rel <= 0.01, f"footprint within 1% of engine: {fp} vs {c['footprint_cells_engine']} ({rel:.3%})")

    W = s["warnings"]
    check(s["default_warning"] in W, "default_warning is one of warnings")
    check(set(s["headline"]) == set(W), "headline has one entry per warning")
    t0, t1 = s["time_range_min"]
    check(t0 <= min([s["burst_min"]] + [w["t_min"] for w in W.values()]) and t1 > s["burst_min"],
          f"time range {t0}..{t1} covers burst and warnings")
    check([e["t_min"] for e in s["events"]] == sorted(e["t_min"] for e in s["events"]), "events sorted by time")

    bridge_ids = {b["id"] for b in s["bridges"]}
    worst = 0.0
    for st in s["settlements"]:
        for wid, w in W.items():
            mine = st["arrival_min"] - (w["t_min"] + s["dissemination_min"] + st["walk_min"])
            worst = max(worst, abs(mine - st["engine_slack"][wid]))
        if st["bridge"]:
            check(st["bridge"]["id"] in bridge_ids, f"{st['id']}: route bridge {st['bridge']['id']} is listed")
        check(len(st["route"]) >= 1, f"{st['id']}: route has at least one vertex")
    check(worst <= 0.1, f"settlement slack parity with engine, max |diff| = {worst:.4f} min over "
                        f"{len(s['settlements'])} settlements x {len(W)} warnings")
    check(set(s["layers"]) <= {"slack", "arrival", "walk", "hand"}, "layers are known heat fields")

    # people units reproduce the engine headline exactly, for every warning
    U = s.get("units", [])
    check(len(U) > 0 and all(0 <= u[0] < len(s["settlements"]) for u in U), f"{len(U)} people units reference settlements")
    total = sum(u[3] for u in U)
    for wid, w in W.items():
        h = s["headline"][wid]
        short = sum(u[3] for u in U if u[1] - (w["t_min"] + s["dissemination_min"] + u[2]) < 0)
        check(short == h["people_without_time"] and total == h["people_at_risk"],
              f"{wid}: units give {short:g} without time of {total:g} (engine {h['people_without_time']:g} of {h['people_at_risk']:g})")
        per = {}
        for u in U:
            if u[1] - (w["t_min"] + s["dissemination_min"] + u[2]) < 0:
                per[u[0]] = per.get(u[0], 0) + u[3]
        bad = [st["id"] for i, st in enumerate(s["settlements"]) if per.get(i, 0) != st["engine"][wid]["people_without_time"]]
        check(not bad, f"{wid}: per-settlement people without time match the engine {bad or ''}")
    for i, st in enumerate(s["settlements"]):
        if abs(sum(u[3] for u in U if u[0] == i) - st["pop"]) > 1e-9:
            check(False, f"{st['id']}: units sum to pop")
    return fails


if __name__ == "__main__":
    f = main(sys.argv[1] if len(sys.argv) > 1 else "viewer/data/oct11")
    print(f"\n{'PASS' if not f else f'{len(f)} FAILED'}")
    sys.exit(1 if f else 0)
