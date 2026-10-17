"""Damage-model training tables for past flash floods outside Nepal (leave-one-event-out evaluation).

Same output format as scripts/damage/build_table.py (table_trishuli.npz): X (FEATURES_ALL order, envelope=None),
cols, y, destroyed_only, kind, osm_id (U32), lonlat, max_dist_m. Rows are buildings that drain into the event's
flood path and lie <= --max-dist-m from it (training uses <= 500 m). Features come from engine.terrain.Terrain +
engine.damage_model, exactly as for Nepal. ls_500m is a Nepal-only feature and is 0 here.

Events (all inputs are real published data; see <event>/SOURCES.md on the VM):
  ahr    Ahr valley, Germany, 14-15 Jul 2021. Labels: 4TU.ResearchData doi:10.4121/8f7a21d3-9bb9-4808-ae51-761eb3fba986
         (Samprogna Mohor et al. 2025, ODbL), 19,507 OSM-derived polygons, rater-1 grades D0-D6 (Maiwald & Schwarz
         2019). y = R1 >= D1 (any damage), destroyed_only = R1 in {D5, D6} (the two highest grades); R1 empty -> dropped.
         Source: OSM node 173885816 (place=village Schuld). Path cut at the Ahr mouth (downstream end of the OSM
         waterway=river name=Ahr ways = the Rhine confluence).
  derna  Derna, Libya, 10-11 Sep 2023. Labels: UNOSAT FL20230912LBY (HDX, CC BY-SA). Positives = the 2,217 points of
         PHR_20230913_AffectedStructure_Derna ("exposed to rushing floodwaters", one class: destroyed_only is undefined
         and set to 0). Analysed area = S2_20230912_AnalysisExtent_Derna (the only Derna analysis extent in the package).
         Negatives = OSM buildings (Overpass attic snapshot 2023-09-20) whose centroid lies inside that extent, that
         contain no UNOSAT point and are farther from every UNOSAT point than the 95th percentile of the UNOSAT-point
         -> nearest-OSM-polygon distance (computed from the data). Only rows inside the extent are kept.
         Source: OSM way 1207192349 (waterway=dam, name=Abou Mansour). Path cut at the downstream end of the OSM
         Wadi Derna ways (the coast).
No bridges: neither label set grades bridges (UNOSAT's 8 S2_20230912_AffectedInfrastructure points carry SiteID codes
with no decoding domain in the package), so the tables are buildings only.

Writes <root>/<event>/{table.npz, labels_extra.npz, build_report.json}. Run on the VM:
  python3 -I scripts/damage/events/build_event_table.py --event ahr
Inputs (downloads, read as data) live under <root>/<event>/{labels_dl,osm_dl}; terrain in <root>/<event>/proc
(scripts/damage/events/build_terrain.sh).
"""
import argparse, json, os, platform, sys, time
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--event", required=True, choices=["ahr", "derna"])
ap.add_argument("--root", default=os.path.expanduser("~/work-agent-lcpizani/events"))
ap.add_argument("--repo", default=os.path.expanduser("~/work-agent-lcpizani/repo"))
ap.add_argument("--max-dist-m", type=float, default=2000.0)
a = ap.parse_args()
sys.path.insert(0, a.repo)

import geopandas as gpd
from shapely.geometry import Polygon, LineString, Point
from scipy.spatial import cKDTree
from pyproj import Transformer
from engine.terrain import Terrain
from engine import damage_model as dm

EV = os.path.join(a.root, a.event)
U = os.path.join(EV, "labels_dl")
O = os.path.join(EV, "osm_dl")

EVENTS = {
    "ahr": dict(name="Ahr valley flash flood, Germany, 14-15 Jul 2021", epsg=32632,
                source=(6.88686, 50.44608), source_ref="OSM node 173885816 (place=village, name=Schuld, wikidata Q818785)",
                river=os.path.join(O, "ahr_river.json"), river_ref="OSM ways waterway=river name=Ahr (Overpass 2026-10-17)"),
    "derna": dict(name="Derna dam-burst flash flood, Libya, 10-11 Sep 2023", epsg=32634,
                  source=(22.57708, 32.65937), source_ref="OSM way 1207192349 (waterway=dam, name=Abou Mansour, start_date=1976), centre",
                  river=os.path.join(O, "derna_wadi.json"), river_ref="OSM ways waterway=river/stream name=وادي درنة (Wadi Derna) (Overpass 2026-10-17)"),
}
cfg = EVENTS[a.event]
EPSG = cfg["epsg"]
TF = Transformer.from_crs(4326, EPSG, always_xy=True)
INV = Transformer.from_crs(EPSG, 4326, always_xy=True)


def osm_lines(path):
    out = []
    for e in json.load(open(path))["elements"]:
        if e["type"] == "way" and len(e.get("geometry", [])) >= 2:
            x, y = TF.transform([g["lon"] for g in e["geometry"]], [g["lat"] for g in e["geometry"]])
            out.append((e["id"], np.c_[x, y]))
    return out


def load_ahr():
    g = gpd.read_file(os.path.join(U, "SamprognaMohor_etal_Raters123.shp"))
    assert g.crs.to_epsg() == 4326
    cen = g.to_crs(EPSG).geometry.centroid
    lon, lat = INV.transform(cen.x.values, cen.y.values)
    grade = g["DmgGrd_R1"].astype(object).where(g["DmgGrd_R1"].notna(), None).values
    order = {"D0": 0, "D1": 1, "D2": 2, "D3": 3, "D4": 4, "D5": 5, "D6": 6}
    gnum = np.array([order.get(v, -1) if v is not None else -1 for v in grade])
    bad = sorted(set(v for v in grade if v is not None and v not in order))
    assert not bad, f"unexpected R1 grades {bad}"
    keep = gnum >= 0
    # rater agreement (affected yes/no) where rater 2 also graded the building, for the report
    r2 = g["DmgGrd_R2"].astype(str).str.extract(r"D(\d)")[0].astype(float).values
    both = keep & np.isfinite(r2)
    agree = float(((gnum[both] >= 1) == (r2[both] >= 1)).mean()) if both.any() else None
    fid = np.arange(len(g))
    rows = dict(lonlat=np.c_[lon, lat][keep], y=(gnum[keep] >= 1).astype(int), des=(gnum[keep] >= 5).astype(int),
                ids=np.array([f"4tu/{i}" for i in fid[keep]]),
                extra={"grade_r1": gnum[keep].astype(np.int8), "source_fid": fid[keep]})
    info = {"label_file": "SamprognaMohor_etal_Raters123.shp", "polygons": int(len(g)),
            "dropped_r1_ungraded": int((~keep).sum()),
            "r1_grade_counts": {f"D{k}": int((gnum == k).sum()) for k in range(7)},
            "r1_vs_r2_affected_agreement": {"n_both_graded": int(both.sum()), "agreement": agree},
            "mapping": "y = DmgGrd_R1 >= D1; destroyed_only = DmgGrd_R1 in {D5, D6}; R1 empty -> dropped",
            "osm_id_note": "dataset has no OSM ids; osm_id = '4tu/<feature index in the shapefile>'"}
    return rows, info


def load_derna():
    S = os.path.join(U, "x", "FL20230912LBY_SHP")
    ext = gpd.read_file(os.path.join(S, "S2_20230912_AnalysisExtent_Derna.shp")).to_crs(EPSG).geometry.unary_union
    cloud = gpd.read_file(os.path.join(S, "S2_20230912_CloudObstruction_Derna.shp")).to_crs(EPSG).geometry.unary_union
    pts = gpd.read_file(os.path.join(S, "PHR_20230913_AffectedStructure_Derna.shp")).to_crs(EPSG)
    assert set(pts["d_Grouped_"]) == {"Damaged Buildings"}
    snap = "attic_20230920.json"
    polys, ids = [], []
    for e in json.load(open(os.path.join(O, snap)))["elements"]:
        if e["type"] == "way" and len(e.get("geometry", [])) >= 4:
            polys.append(Polygon([(q["lon"], q["lat"]) for q in e["geometry"]])); ids.append(f"way/{e['id']}")
    n_rel = sum(e["type"] == "relation" for e in json.load(open(os.path.join(O, snap)))["elements"])
    b = gpd.GeoDataFrame({"osm_id": ids}, geometry=polys, crs=4326).to_crs(EPSG)
    b["geometry"] = b.geometry.buffer(0)
    b = b[b.geometry.centroid.within(ext)].reset_index(drop=True)
    p_in = pts.geometry.within(ext).values
    P = pts[p_in].reset_index(drop=True)
    # UNOSAT point -> nearest OSM polygon distance (0 if inside) defines the match tolerance (95th percentile)
    nn = gpd.sjoin_nearest(P[["geometry"]], b[["geometry"]], distance_col="dm")
    d_pt = nn.groupby(level=0)["dm"].min().reindex(range(len(P))).values
    tol = float(np.percentile(d_pt, 95))
    inside = gpd.sjoin(P[["geometry"]], b[["geometry"]], predicate="within")
    poly_hit = np.zeros(len(b), bool); poly_hit[inside["index_right"].values] = True
    matched_way = np.full(len(P), "", dtype=object)
    for i, j in zip(inside.index, inside["index_right"]):
        matched_way[i] = b.at[j, "osm_id"]
    nb = gpd.sjoin_nearest(b[["geometry"]], P[["geometry"]], distance_col="dm")
    d_poly = nb.groupby(level=0)["dm"].min().reindex(range(len(b))).values
    neg = (~poly_hit) & (d_poly > tol)
    bc = b.geometry.centroid
    blon, blat = INV.transform(bc.x.values, bc.y.values)
    plon, plat = INV.transform(P.geometry.x.values, P.geometry.y.values)
    nP, nN = len(P), int(neg.sum())
    lonlat = np.vstack([np.c_[plon, plat], np.c_[blon, blat][neg]])
    in_cloud = np.concatenate([P.geometry.within(cloud).values, bc[neg].within(cloud).values])
    fid = np.flatnonzero(p_in)
    rows = dict(lonlat=lonlat, y=np.r_[np.ones(nP, int), np.zeros(nN, int)], des=np.zeros(nP + nN, int),
                ids=np.r_[np.array([f"unosat/{i}" for i in fid]), b["osm_id"].values[neg]].astype(str),
                extra={"in_s2_cloud": in_cloud,
                       "matched_osm_way": np.r_[matched_way.astype(str), b["osm_id"].values[neg]].astype("U32")})
    info = {"label_file": "PHR_20230913_AffectedStructure_Derna.shp", "unosat_points": int(len(pts)),
            "unosat_points_outside_extent_dropped": int((~p_in).sum()),
            "analysis_extent": "S2_20230912_AnalysisExtent_Derna.shp", "analysis_extent_km2": round(ext.area / 1e6, 3),
            "s2_cloud_in_extent_km2": round(ext.intersection(cloud).area / 1e6, 3),
            "osm_snapshot": "Overpass attic [date:\"2023-09-20T00:00:00Z\"], ways building=*", "osm_relations_skipped": n_rel,
            "osm_buildings_in_extent": int(len(b)), "unosat_points_inside_osm_polygon": int(len(inside.index.unique())),
            "match_tolerance_m_p95": round(tol, 2), "osm_polygons_containing_point": int(poly_hit.sum()),
            "osm_dropped_ambiguous_within_tol": int(((~poly_hit) & (d_poly <= tol)).sum()),
            "negatives": nN,
            "mapping": "y = 1 for each UNOSAT PHR affected point (row at the point); y = 0 for OSM buildings in the extent "
                       "with no UNOSAT point inside and > tol from every point; destroyed_only undefined (single class) -> 0",
            "destroyed_only_defined": False}
    return rows, info


def main():
    t0 = time.time()
    T = Terrain(os.path.join(EV, "proc"))
    assert T.crs.to_epsg() == EPSG, T.crs
    down_frac, moved_frac = T.check_directions()
    sx, sy = TF.transform(*cfg["source"])
    r, c = T.snap_to_channel(*T.rc(sx, sy), radius=15)
    snap_m = float(np.hypot(*(np.subtract(T.xy(r, c), (sx, sy)))))
    full = T.downstream_path(r, c)
    # catchment of the source: does it touch the grid edge (=> truncated upstream area / log_acc)?
    _, drain_src = T.hand_to(np.array([r * T.shape[1] + c]))
    up = drain_src >= 0
    edge = bool(up[0].any() or up[-1].any() or up[:, 0].any() or up[:, -1].any())

    # cut the path at the river mouth: downstream terminal vertex (lowest DEM) of the OSM river ways
    lines = osm_lines(cfg["river"])
    starts = {tuple(np.round(l[0], 1)) for _, l in lines}
    terms = [l[-1] for _, l in lines if tuple(np.round(l[-1], 1)) not in starts]
    z = [T.dem[T.rc(*p)] if 0 <= T.rc(*p)[0] < T.shape[0] and 0 <= T.rc(*p)[1] < T.shape[1] else np.inf for p in terms]
    mouth = terms[int(np.argmin(z))]
    pxy = np.array([T.xy(*divmod(int(i), T.shape[1])) for i in full])
    dm_mouth = np.hypot(pxy[:, 0] - mouth[0], pxy[:, 1] - mouth[1])
    k = int(np.argmin(dm_mouth))
    path = full[:k + 1]
    sea = np.flatnonzero(T.dem.flat[full] <= 0)
    # path vs OSM river: distance of each path cell to the nearest OSM river vertex (densified to 10 m)
    dens = []
    for _, l in lines:
        for j in range(len(l) - 1):
            n = max(int(np.hypot(*(l[j + 1] - l[j])) / 10), 1)
            dens.append(l[j] + np.linspace(0, 1, n, endpoint=False)[:, None] * (l[j + 1] - l[j]))
    dens = np.vstack(dens + [l[-1:] for _, l in lines])
    d_riv, _ = cKDTree(dens).query(pxy[:k + 1])
    ctx = dm.PathContext(T, path)
    zp = T.dem.flat[path]
    rise = np.diff(zp)
    up_i = np.flatnonzero(rise > 5)
    climbs = [{"path_index": int(i), "km": round(float(ctx.km_path[i]), 2), "rise_m": round(float(rise[i]), 1),
               "lonlat": [round(v, 5) for v in INV.transform(*pxy[i])]} for i in up_i[np.argsort(-rise[up_i])][:8]]
    mlon, mlat = INV.transform(*mouth)
    slon, slat = INV.transform(*T.xy(r, c))
    path_ll = [INV.transform(*pxy[i]) for i in range(0, k + 1, max(1, (k + 1) // 12))] + [INV.transform(*pxy[k])]
    terrain = {"grid_shape": list(T.shape), "crs": f"EPSG:{EPSG}", "d8_downhill_fraction": round(down_frac, 4),
               "moved_fraction": round(moved_frac, 4), "source_lonlat": cfg["source"], "source_ref": cfg["source_ref"],
               "snapped_source_lonlat": [round(slon, 5), round(slat, 5)], "snap_offset_m": round(snap_m, 1),
               "source_acc_cells": float(T.acc[r, c]), "source_catchment_touches_grid_edge": edge,
               "full_d8_path_km": round(float(np.sum(np.hypot(*np.diff(pxy, axis=0).T))) / 1000, 2),
               "mouth_lonlat": [round(mlon, 5), round(mlat, 5)], "mouth_ref": cfg["river_ref"] + ": lowest downstream terminal vertex",
               "path_cut_index": k, "path_end_to_mouth_m": round(float(dm_mouth[k]), 1),
               "first_path_cell_dem_le_0_index": int(sea[0]) if len(sea) else None,
               "path_km": round(float(ctx.km_path[-1]), 2), "path_cells": int(len(path)),
               "path_to_osm_river_m": {q: round(float(np.percentile(d_riv, p)), 1) for q, p in
                                       [("p50", 50), ("p90", 90), ("p95", 95), ("max", 100)]},
               "path_dem_start_end_m": [round(float(zp[0]), 1), round(float(zp[-1]), 1)],
               "path_uphill_steps": {"n_rise_gt_1m": int((rise > 1).sum()), "n_rise_gt_5m": int((rise > 5).sum()),
                                     "total_rise_m": round(float(rise[rise > 0].sum()), 1), "largest": climbs},
               "path_lonlat_samples":[[round(x, 5), round(y, 5)] for x, y in path_ll]}
    t_ctx = time.time() - t0

    rows, info = (load_ahr if a.event == "ahr" else load_derna)()
    ll, y, des, ids = rows["lonlat"], rows["y"], rows["des"], rows["ids"]
    kind = np.array(["building"] * len(y))
    t1 = time.time()
    X, names, ok, extra = dm.features(ctx, ll, kind, envelope=None, max_dist_m=a.max_dist_m)
    t_feat = time.time() - t1
    keep = ok
    np.savez_compressed(os.path.join(EV, "table.npz"), X=X[keep], cols=np.array(names), y=y[keep],
                        destroyed_only=des[keep], kind=kind[keep], osm_id=ids[keep].astype("U32"),
                        lonlat=ll[keep], max_dist_m=a.max_dist_m)
    np.savez_compressed(os.path.join(EV, "labels_extra.npz"), osm_id=ids[keep].astype("U32"),
                        **{k2: v[keep] for k2, v in rows["extra"].items()})

    def counts(m):
        return {f"{kk}_{lab}": int(((kind == kk) & (y == lab) & m).sum()) for kk in ("building", "bridge") for lab in (0, 1)}
    d = extra["dist_channel_m"]
    pos_km = extra["river_km"][keep & (y == 1)]
    hi = names.index("hand")
    H = X[:, hi]
    m5 = keep & (d <= 500)
    bands = [(-np.inf, 2), (2, 5), (5, 10), (10, 20), (20, 50), (50, np.inf)]
    hand_bands = []
    for lo, hb in bands:
        m = m5 & (H >= lo) & (H < hb)
        hand_bands.append({"hand_m": f"[{lo},{hb})", "n": int(m.sum()), "affected": int((y[m] == 1).sum()),
                           "share_affected": round(float(y[m].mean()), 3) if m.any() else None})
    dist_bands = []
    for lo, hb in [(0, 50), (50, 100), (100, 200), (200, 500), (500, 1000), (1000, 2000.01)]:
        m = keep & (d >= lo) & (d < hb)
        dist_bands.append({"dist_m": f"[{lo},{hb})", "n": int(m.sum()), "affected": int((y[m] == 1).sum()),
                           "share_affected": round(float(y[m].mean()), 3) if m.any() else None})
    pos_all = int((y == 1).sum())
    report = {
        "event": cfg["name"], "proc": os.path.join(EV, "proc"), "path_km": float(ctx.km_path[-1]),
        "path_cells": int(len(path)), "max_dist_m": a.max_dist_m, "terrain": terrain, "labels": info,
        "candidates": counts(np.ones(len(y), bool)),
        "kept_le_max_dist": counts(keep),
        "kept_le_500m": counts(keep & (d <= 500)),
        "positives_kept_fraction_le_500m": round(float((m5 & (y == 1)).sum() / max(pos_all, 1)), 4),
        "dropped": {
            "outside_grid": counts(~extra["inside_grid"]),
            "inside_grid_not_draining_to_path": counts(extra["inside_grid"] & ~extra["drains_to_path"]),
            "beyond_max_dist": counts(extra["drains_to_path"] & (d > a.max_dist_m)),
            "nonfinite_features": counts(extra["drains_to_path"] & (d <= a.max_dist_m) & ~ok),
        },
        "positives_river_km": {"min": float(np.min(pos_km)), "median": float(np.median(pos_km)),
                               "max": float(np.max(pos_km))} if len(pos_km) else None,
        "positives_destroyed_only_le_500m": int((m5 & (des == 1)).sum()),
        "sanity_hand_bands_le_500m": hand_bands, "sanity_dist_bands": dist_bands,
        "hand_median_le_500m": {"affected": float(np.median(H[m5 & (y == 1)])) if (m5 & (y == 1)).any() else None,
                                "unaffected": float(np.median(H[m5 & (y == 0)])) if (m5 & (y == 0)).any() else None},
        "extra_flags_kept_le_500m": {k2: {"affected": int(v[m5 & (y == 1)].sum()), "unaffected": int(v[m5 & (y == 0)].sum())}
                                     for k2, v in rows["extra"].items() if v.dtype == bool},
        "bridges": "none: no bridge labels in this event's label set",
        "ls_500m_note": "Nepal-only feature (2015 Gorkha landslides); 0 for this event",
        "ls_500m_max": float(np.nanmax(X[keep][:, names.index("ls_500m")])) if keep.any() else None,
        "features": names, "arch": platform.machine(),
        "timing_s": {"path_context": round(t_ctx, 2), "features": round(t_feat, 2), "total": round(time.time() - t0, 2)},
    }
    json.dump(report, open(os.path.join(EV, "build_report.json"), "w"), indent=2, ensure_ascii=False)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
