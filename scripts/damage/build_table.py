"""Build the Aug 26 training table for the damage model (packet B).

Rows: OSM buildings and bridges that drain into the Bhotekoshi-Trishuli flood path and lie within
--max-dist-m (default 2000; training uses the <= 500 m subset, the 2 km set is for comparison).
Labels (Aug 26 2026 OSM tagging, docs/data/osm_damage_labels.md):
  buildings: damage_event == 2026NepalFlood -> 1 (destroyed or damaged), empty -> 0, other events dropped
  bridges:   destroyed:bridge (event 2026NepalFlood) or a still-mapped bridge tagged with the event -> 1,
             other bridge=* highway ways -> 0 (dropped if within 50 m of a positive: likely a rebuilt crossing)
  bridges are featurised at their crossing point (damage_model.crossing_points), not the midpoint
Writes <out>/table_trishuli.npz and models/damage/build_report.json.

Run on the VM from the repo root:
  python3 scripts/damage/build_table.py --proc /home/linux1/evac-ai/data/proc_trishuli --out ~/work-agent-lcpizani/out
"""
import argparse, csv, json, os, platform, sys, time
import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from engine.terrain import Terrain
from engine import damage_model as dm

EVENT = "2026NepalFlood"
SOURCE = (85.383, 28.276)          # Rasuwagadhi border, as in AGENTS.md
OSM = os.path.join(dm.REPO, "data", "processed", "osm")


def mid(coords):
    return coords[len(coords) // 2]


def load_buildings(bbox):
    w, s, e, n = bbox
    ll, lab, des, ids, dropped = [], [], [], [], 0
    with open(os.path.join(OSM, "buildings.csv")) as f:
        for r in csv.DictReader(f):
            lon, lat = float(r["lon"]), float(r["lat"])
            if not (w <= lon <= e and s <= lat <= n):
                continue
            ev = r["damage_event"]
            if ev == EVENT:
                lab.append(1); des.append(int(r["damage"] == "destroyed"))
            elif ev == "":
                lab.append(0); des.append(0)
            else:
                dropped += 1
                continue
            ll.append((lon, lat)); ids.append(r["osm_id"])
    return np.array(ll), np.array(lab), np.array(des), np.array(ids), dropped


def load_bridges(bbox):
    w, s, e, n = bbox
    inb = lambda p: w <= p[0] <= e and s <= p[1] <= n
    pos, neg = [], []
    for f in json.load(open(os.path.join(OSM, "damage.geojson")))["features"]:
        p, g = f["properties"], f["geometry"]
        if p.get("damage:event") != EVENT:
            continue
        is_bridge = "destroyed:bridge" in p or (p.get("bridge") not in (None, "no")
                                                and ("highway" in p or "destroyed:highway" in p))
        if not is_bridge:
            continue
        if g["type"] not in ("LineString", "Point"):
            continue
        line = g["coordinates"] if g["type"] == "LineString" else [g["coordinates"]]
        pt = mid(line)
        if inb(pt):
            pos.append((pt[0], pt[1], f.get("id") or p.get("id", ""), line))
    for f in json.load(open(os.path.join(OSM, "roads.geojson")))["features"]:
        p, g = f["properties"], f["geometry"]
        if p.get("bridge") in (None, "no") or "highway" not in p or g["type"] != "LineString":
            continue
        pt = mid(g["coordinates"])
        if not inb(pt):
            continue
        row = (pt[0], pt[1], f.get("id") or p.get("id", ""), g["coordinates"])
        (pos if p.get("damage:event") == EVENT else neg).append(row)
    return pos, neg


def dedupe(rows, r_m):
    """Keep the first of any rows closer than r_m (rows: list of (lon, lat, id, line); by midpoint)."""
    if not rows:
        return rows, 0
    x, y = dm.TF.transform([r[0] for r in rows], [r[1] for r in rows])
    tree, keep, gone = cKDTree(np.c_[x, y]), [], set()
    for i in range(len(rows)):
        if i in gone:
            continue
        keep.append(rows[i])
        gone.update(j for j in tree.query_ball_point((x[i], y[i]), r_m) if j != i)
    return keep, len(rows) - len(keep)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--proc", default="/home/linux1/evac-ai/data/proc_trishuli")
    ap.add_argument("--out", default=os.path.expanduser("~/work-agent-lcpizani/out"))
    ap.add_argument("--max-dist-m", type=float, default=2000.0)
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    t0 = time.time()

    T = Terrain(a.proc)
    r, c = T.snap_to_channel(*T.rc(*dm.TF.transform(*SOURCE)), radius=15)
    path = T.downstream_path(r, c)
    ctx = dm.PathContext(T, path)
    inv = dm.Transformer.from_crs(32645, 4326, always_xy=True)
    corners = [inv.transform(*T.xy(rr, cc)) for rr, cc in [(0, 0), (0, T.shape[1] - 1), (T.shape[0] - 1, 0),
                                                           (T.shape[0] - 1, T.shape[1] - 1)]]
    bbox = (min(p[0] for p in corners), min(p[1] for p in corners), max(p[0] for p in corners), max(p[1] for p in corners))
    t_ctx = time.time() - t0

    b_ll, b_y, b_des, b_id, b_dropped_event = load_buildings(bbox)
    br_pos, br_neg = load_bridges(bbox)
    br_pos, dup_pos = dedupe(br_pos, 20.0)
    br_neg, dup_neg = dedupe(br_neg, 20.0)
    if br_pos and br_neg:
        px, py = dm.TF.transform([q[0] for q in br_pos], [q[1] for q in br_pos])
        nx, ny = dm.TF.transform([q[0] for q in br_neg], [q[1] for q in br_neg])
        d, _ = cKDTree(np.c_[px, py]).query(np.c_[nx, ny])
        near_pos = int((d < 50).sum())
        br_neg = [q for q, dd in zip(br_neg, d) if dd >= 50]
    else:
        near_pos = 0
    br = br_pos + br_neg
    br_xing = dm.crossing_points(ctx, [q[3] for q in br]) if br else np.empty((0, 2))   # score bridges where they cross
    ll = np.vstack([b_ll, br_xing.reshape(-1, 2)])
    y = np.concatenate([b_y, np.ones(len(br_pos), int), np.zeros(len(br_neg), int)])
    des = np.concatenate([b_des, np.ones(len(br_pos), int), np.zeros(len(br_neg), int)])
    kind = np.array(["building"] * len(b_ll) + ["bridge"] * len(br))
    ids = np.concatenate([b_id, np.array([str(q[2]) for q in br])])

    t1 = time.time()
    X, names, ok, extra = dm.features(ctx, ll, kind, envelope=None, max_dist_m=a.max_dist_m)
    t_feat = time.time() - t1
    keep = ok
    np.savez_compressed(os.path.join(a.out, "table_trishuli.npz"), X=X[keep], cols=np.array(names),
                        y=y[keep], destroyed_only=des[keep], kind=kind[keep], osm_id=ids[keep].astype("U32"),
                        lonlat=ll[keep], max_dist_m=a.max_dist_m)

    def counts(m):
        return {f"{k}_{lab}": int(((kind == k) & (y == lab) & m).sum()) for k in ("building", "bridge") for lab in (0, 1)}
    d = extra["dist_channel_m"]
    pos_km = extra["river_km"][keep & (y == 1)]
    report = {
        "event": "Aug 26 2026 Bhotekoshi-Trishuli", "proc": a.proc, "path_km": float(ctx.km_path[-1]),
        "path_cells": int(len(path)), "grid_bbox_lonlat": bbox, "max_dist_m": a.max_dist_m,
        "candidates": counts(np.ones(len(y), bool)),
        "kept_le_max_dist": counts(keep),
        "kept_le_500m": counts(keep & (d <= 500)),
        "dropped": {
            "buildings_other_damage_event": b_dropped_event,
            "bridges_duplicate_within_20m": {"positive": dup_pos, "negative": dup_neg},
            "bridge_negatives_within_50m_of_positive": near_pos,
            "outside_grid": counts(~extra["inside_grid"]),
            "inside_grid_not_draining_to_path": counts(extra["inside_grid"] & ~extra["drains_to_path"]),
            "beyond_max_dist": counts(extra["drains_to_path"] & (d > a.max_dist_m)),
            "nonfinite_features": counts(extra["drains_to_path"] & (d <= a.max_dist_m) & ~ok),
        },
        "positives_river_km": {"min": float(np.min(pos_km)), "median": float(np.median(pos_km)),
                               "max": float(np.max(pos_km))} if len(pos_km) else None,
        "positives_destroyed_only_le_500m": int((keep & (d <= 500) & (des == 1)).sum()),
        "features": names, "arch": platform.machine(),
        "timing_s": {"path_context": round(t_ctx, 2), "features": round(t_feat, 2), "total": round(time.time() - t0, 2)},
    }
    os.makedirs(dm.MODEL_DIR, exist_ok=True)
    json.dump(report, open(os.path.join(dm.MODEL_DIR, "build_report.json"), "w"), indent=2)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
