"""Audit of prediction mode's "where should I go?" (engine/escape.py): are the destinations really safe ground?
Run on L1CC from a repo copy with a full data/ (incl. data/processed):
    timeout 280 python3 docs/validation/audit_escape.py budhi     ->  docs/validation/audit_escape_budhi.json
    timeout 280 python3 docs/validation/audit_escape.py trishuli  ->  docs/validation/audit_escape_trishuli.json
Start points: Aug 26 = buildings tagged destroyed/damaged (they were really hit); Oct 11 = buildings the planner's
conservative footprint puts at risk. Each query is made at t = 0 (warning at the start of the flood) and t = 30 min.
Independent checks on each destination: freeboard above the preset's flood line (HAND - height), the planner's
conservative rule (HAND > 1.3 x height + 5 m), distance to the nearest REAL destroyed building (Aug 26), whether the
route steps on a blocked river cell, and time margin when the flood comes at the early edge of its band (x0.75).
"""
import csv, json, sys, time
sys.path.insert(0, ".")
import numpy as np
from scipy.spatial import cKDTree
from engine import escape as esc

key = sys.argv[1] if len(sys.argv) > 1 else "budhi"
tag = sys.argv[2] if len(sys.argv) > 2 else ""
OUT = f"docs/validation/audit_escape_{key}{tag}.json"
rng = np.random.default_rng(0)
t = time.time(); S = esc.FloodScenario(key); build_s = time.time() - t
V, T, ctx, F = S.V, S.V.T, S.ctx, S.F
hand = ctx.hand
from scipy import ndimage
# independent "below the flood line" test (planner rule, engine/scenario.py), NOT taken from escape.py
BELOW = (ctx.drain >= 0) & (hand <= F.height(np.nan_to_num(S.km)) * 1.3 + 5.0)


def zone_mask(gr, gc, tau, radius_m=600.0):           # same construction as FloodScenario._zone, returned as cells
    R = int(radius_m / esc.CELL); nr, nc = T.shape
    r0, r1, c0, c1 = max(gr - R, 0), min(gr + R + 1, nr), max(gc - R, 0), min(gc + R + 1, nc)
    ok = (S.p_search[r0:r1, c0:c1] <= tau + 1e-6) & (S.blocked[r0:r1, c0:c1] == 0)
    yy, xx = np.ogrid[r0:r1, c0:c1]; ok &= (yy - gr) ** 2 + (xx - gc) ** 2 <= R * R
    lab, _ = ndimage.label(ok, structure=np.ones((3, 3)))
    m = np.zeros(T.shape, bool); m[r0:r1, c0:c1] = (lab == lab[gr - r0, gc - c0]) & ok
    return m

# ---- start points + damage truth ----
dmg_xy = None
if key == "trishuli":
    pts, dxy = [], []
    with open("data/processed/osm/buildings.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r["damage_event"] in ("2026NepalFlood", "8·26吉隆口岸泥石流") and r["damage"] in ("destroyed", "damaged"):
                lo, la = float(r["lon"]), float(r["lat"])
                dxy.append(V.tf.transform(lo, la)); pts.append((lo, la))
    dmg_xy = np.array(dxy); dmg_tree = cKDTree(dmg_xy)
    DMG = np.zeros(T.shape, np.int32)
    for xx_, yy_ in dmg_xy:
        r_, c_ = T.rc(xx_, yy_)
        if 0 <= r_ < T.shape[0] and 0 <= c_ < T.shape[1]:
            DMG[r_, c_] += 1
    starts = [pts[i] for i in rng.choice(len(pts), 150, replace=False)]
else:
    b = json.load(open("data/raw/osm_budhi_buildings.json"))["elements"]
    ll = np.array([(e["center"]["lon"], e["center"]["lat"]) for e in b if "center" in e])
    x, y = V.tf.transform(ll[:, 0], ll[:, 1])
    rc = np.array([T.rc(a, c) for a, c in zip(x, y)])
    ok = (rc[:, 0] >= 0) & (rc[:, 0] < T.shape[0]) & (rc[:, 1] >= 0) & (rc[:, 1] < T.shape[1])
    ll, rc = ll[ok], rc[ok]
    km = S.km[rc[:, 0], rc[:, 1]]; h = hand[rc[:, 0], rc[:, 1]]
    inside = np.isfinite(km) & (h <= F.height(np.nan_to_num(km)) * 1.3)          # planner's conservative footprint
    cand = np.flatnonzero(inside)
    starts = [tuple(ll[i]) for i in rng.choice(cand, min(150, len(cand)), replace=False)]

EARLY = not getattr(esc, "_EARLY_EDGE", False) and "x0.75" not in open(esc.__file__).read()   # fixed code already uses it
rows = []
for (lo, la) in starts:
    for t0 in (0.0, 30.0):
        o = S.escape(lo, la, t0)
        row = {"lon": lo, "lat": la, "t0": t0, "status": o["status"], "tier": o.get("tier"),
               "p_here": o["you"]["p_destroyed"] if "you" in o else None}
        d = o.get("destination")
        if d:
            gr, gc = T.rc(*V.tf.transform(d["lon"], d["lat"]))
            k = S.km[gr, gc]; hd = float(hand[gr, gc])
            hgt = float(F.height(k)) if np.isfinite(k) else float("nan")
            row.update({"dest_p": d["p_destroyed"], "dest_hand_m": round(hd, 1), "dest_km": None if not np.isfinite(k) else round(float(k), 1),
                        "dest_freeboard_m": None if not np.isfinite(k) else round(hd - hgt, 1),
                        "dest_planner_safe": bool(not np.isfinite(k) or hd > 1.3 * hgt + 5.0),
                        "dest_dist_channel_m": round(float(ctx.dist[gr, gc])),
                        "walk_min": o.get("walk_min"), "climb_m": o.get("climb_m"), "safe_flag": o.get("safe")})
            # route checks: blocked cells (river strip without bridge), early-edge time margin
            path = o.get("path") or []
            blocked, margin_early = 0, []
            for p in path[1:]:
                r, c = T.rc(*V.tf.transform(p["lon"], p["lat"]))
                blocked += int(S.blocked[r, c])
                a = S.A[r, c]
                if np.isfinite(a) and p["p_destroyed"] > esc.UNSAFE_P:
                    margin_early.append((0.75 * float(a) if EARLY else float(a)) - p["t_min"])
            row["route_blocked_cells"] = blocked
            row["min_margin_mid"] = o.get("min_margin_before_flood_min")
            row["min_margin_early"] = None if not margin_early else round(min(margin_early), 1)
            if dmg_xy is not None:
                dd, _ = dmg_tree.query(V.tf.transform(d["lon"], d["lat"]))
                row["dest_dist_to_real_damage_m"] = round(float(dd))
            z = o.get("safe_zone")
            if z:
                zm = zone_mask(gr, gc, z["max_risk"])
                row.update({"zone_max_risk": z["max_risk"], "zone_cells": int(zm.sum()),
                            "zone_share_below_line": round(float(BELOW[zm].mean()), 3) if zm.any() else None})
                if dmg_xy is not None:
                    row["zone_real_damaged_buildings"] = int(DMG[zm].sum())
        rows.append(row)


def share(pred, rs):
    rs = [r for r in rs if r.get("dest_p") is not None]
    return round(sum(map(pred, rs)) / max(len(rs), 1), 3), len(rs)


R = [r for r in rows if r.get("dest_p") is not None]
summ = {"valley": key, "preset": S.preset_key, "scenario_build_s": round(build_s, 1), "queries": len(rows),
        "status_counts": {s: sum(r["status"] == s for r in rows) for s in sorted({r["status"] for r in rows})},
        "with_destination": len(R),
        "dest_p_median": float(np.median([r["dest_p"] for r in R])) if R else None,
        "dest_freeboard_m_quantiles": None if not R else
            [float(np.nanpercentile([r["dest_freeboard_m"] if r["dest_freeboard_m"] is not None else np.nan for r in R], q)) for q in (5, 25, 50)],
        "dest_negative_freeboard": share(lambda r: r["dest_freeboard_m"] is not None and r["dest_freeboard_m"] < 0, R),
        "dest_fails_planner_rule": share(lambda r: not r["dest_planner_safe"], R),
        "called_SAFE_but_fails_planner_rule": share(lambda r: bool(r["safe_flag"]) and not r["dest_planner_safe"], R),
        "zone_drawn": share(lambda r: r.get("zone_max_risk") is not None, R),
        "zone_risk_above_10pct": share(lambda r: r.get("zone_max_risk") is not None and r["zone_max_risk"] > esc.UNSAFE_P, R),
        "zone_mostly_below_line": share(lambda r: (r.get("zone_share_below_line") or 0) > 0.5, R),
        "dest_outside_500m_corridor": share(lambda r: r["dest_dist_channel_m"] > 500, R),
        "route_steps_on_blocked_cell": share(lambda r: r["route_blocked_cells"] > 0, R),
        "routes_ok_mid_but_late_at_early_edge": share(lambda r: r["min_margin_mid"] is not None and r["min_margin_mid"] >= 0
                                                       and r["min_margin_early"] is not None and r["min_margin_early"] < 0, R)}
if dmg_xy is not None:
    summ["dest_within_30m_of_real_damage"] = share(lambda r: r["dest_dist_to_real_damage_m"] <= 30, R)
    summ["dest_within_60m_of_real_damage"] = share(lambda r: r["dest_dist_to_real_damage_m"] <= 60, R)
    summ["zone_contains_real_damage"] = share(lambda r: (r.get("zone_real_damaged_buildings") or 0) > 0, R)
    summ["zone_contains_5plus_real_damage"] = share(lambda r: (r.get("zone_real_damaged_buildings") or 0) >= 5, R)
json.dump({"summary": summ, "rows": rows}, open(OUT, "w"), indent=1)
print(json.dumps(summ, indent=1))
