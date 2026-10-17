"""Impacted-AREA training tables: one row per 30 m terrain cell, labelled from a published, satellite-derived
flood / debris extent (no labels are produced by us: every y traces to a polygon in a cited product).

Label rule (per cell of the event's terrain grid, using the cell CENTRE):
  y = 1  centre inside the product's observed flood/debris extent (and inside its analysed area)
  y = 0  centre inside the analysed area, outside the extent, and outside every cloud/shadow/not-analysed mask
  none   centre outside the analysed area, or masked -> no row (counted in the report)
Centre-in-polygon is evaluated with rasterio.features.rasterize(all_touched=False) on the Terrain grid itself,
which burns a cell exactly when its centre lies inside the polygon.

Rows: cells that drain into the event's flood path (Terrain.hand_to) and lie <= --max-dist-m (default 2000) from
it; training should use the <= 500 m subset, the same corridor as the building tables. Columns: X in
dm.FEATURES_ALL order, computed by engine.damage_model.features() at the cell centre exactly as for buildings.
The `kind` feature is 2 for cells (0 = building, 1 = bridge); the string column kind = "cell".

Outputs on the VM (<root>/<event>/): area_table.npz, area_labels_extra.npz (secondary products as comparison
labels: -1 = not covered/masked by that product, 0/1 as above), area_build_report.json.
  python3 -I scripts/damage/events/build_area_table.py --event aug26
Sources and licences per event: scripts/damage/events/SOURCES_area_<event>.md.
"""
import argparse, glob, json, os, platform, sys, time
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--event", required=True, choices=["aug26", "oct11", "derna", "ahr"])
ap.add_argument("--root", default=os.path.expanduser("~/work-agent-lcpizani/events"))
ap.add_argument("--repo", default=os.path.expanduser("~/work-agent-lcpizani/repo"))
ap.add_argument("--evac", default="/home/linux1/evac-ai", help="read-only: Nepal terrain grids")
ap.add_argument("--max-dist-m", type=float, default=2000.0)
a = ap.parse_args()
sys.path.insert(0, a.repo)

import geopandas as gpd
from rasterio import features as rfeat
from shapely import make_valid
from shapely.ops import unary_union
from scipy.spatial import cKDTree
from pyproj import Transformer
from engine.terrain import Terrain
from engine import damage_model as dm

EV = os.path.join(a.root, a.event)
KIND_CELL = 2.0


def L(path, layer=None):
    """(file, layer) spec relative to the event dir."""
    return (os.path.join(EV, path), layer)


def one(pattern):
    f = sorted(glob.glob(os.path.join(EV, pattern), recursive=True))
    assert len(f) == 1, (pattern, f)
    return f[0]


# A label set: extent (y = 1), aoi (analysed area), masks (excluded). Secondary sets go to area_labels_extra.npz.
# A set may be a list of parts (one per AOI) whose labels are combined: a cell is 1 if 1 in any part, else 0
# if 0 in any part, else -1.
def cems(dirpat):
    d = os.path.dirname(one(dirpat + "/**/*observedEventA*.shp"))
    g = lambda k: sorted(glob.glob(os.path.join(d, f"*_{k}_*.shp")))
    return {"extent": [(g("observedEventA")[0], None)], "aoi": [(g("areaOfInterestA")[0], None)],
            "masks": [(f, None) for f in g("notAnalysedA")], "dir": os.path.relpath(d, EV)}


EVENTS = {
    "aug26": dict(
        name="Bhotekoshi-Trishuli glacier/ice-rock avalanche debris flood, Nepal, 26 Aug 2026", epsg=32645,
        proc=os.path.join(a.evac, "data", "proc_trishuli"), source=(85.383, 28.276), snap_radius=15,
        source_ref="Rasuwagadhi border (AGENTS.md; same as scripts/damage/build_table.py)", river=None,
        primary=dict(name="unosat_FL20260826NPL",
                     extent=[(None, "UNOSAT_Multisensor_20260826_20260828_FloodExtent")],
                     aoi=[(None, "UNOSAT_Multisensors_20260826_20260828_AnalysisExtent")], masks=[],
                     gdb="unosat_dl/FL20260826NPL_4259.gdb.zip.x/**/*.gdb"),
        secondary={
            "y_cems_first": ["cems_dl/x/EMSR927_AOI01_GRA_PRODUCT_v1", "cems_dl/x/EMSR927_AOI02_GRA_PRODUCT_v2",
                             "cems_dl/x/EMSR927_AOI03_GRA_PRODUCT_v1", "cems_dl/x/EMSR927_AOI05_GRA_PRODUCT_v3"],
            "y_cems_latest": ["cems_dl/x/EMSR927_AOI01_GRA_PRODUCT_v1", "cems_dl/x/EMSR927_AOI02_GRA_PRODUCT_v2",
                              "cems_dl/x/EMSR927_AOI03_GRA_MONIT01_v1", "cems_dl/x/EMSR927_AOI05_GRA_MONIT01_v2"],
        },
        positive_only={"in_hot_extent": "hot_dl/hot_flood_npl_flood_extent.geojson",
                       "in_jaxa_alos2_fpm": "sentinelasia_dl/jaxa/JAXA_20250828_FPM_ALOS2_Nepal_FLDEXT/2026-00033-WLD_202608280620_FLDEXT.geojson"}),
    "oct11": dict(
        name="Budhi Gandaki landslide/avalanche-dam burst flood, Gorkha, Nepal, 11 Oct 2026", epsg=32645,
        proc=os.path.join(a.evac, "data", "proc"), source=(84.9627, 28.4740), snap_radius=15,
        source_ref="replay/oct11.json source (Syar Khola near Chumling, approximate); radius 15 as engine/escape.py (prediction mode)",
        river=None,
        primary=dict(name="unosat_FL20261011NPL", extent=[("unosat_dl/FL20261011NPL_SHP.zip.x/**/S2_20261011_MudslideExtent.shp", None)],
                     aoi=[("unosat_dl/FL20261011NPL_SHP.zip.x/**/S2_20261011_AnalysisExtent.shp", None)], masks=[]),
        secondary={}, positive_only={}),
    "derna": dict(
        name="Derna dam-burst flash flood, Libya, 10-11 Sep 2023", epsg=32634,
        proc=os.path.join(EV, "proc"), source=(22.57708, 32.65937), snap_radius=15,
        source_ref="OSM way 1207192349 (waterway=dam, Abou Mansour), centre; same as build_event_table.py",
        river="osm_dl/derna_wadi.json",
        primary=dict(name="unosat_FL20230912LBY_S2",
                     extent=[("labels_dl/x/FL20230912LBY_SHP/S2_20230912_FloodExtent_Derna.shp", None)],
                     aoi=[("labels_dl/x/FL20230912LBY_SHP/S2_20230912_AnalysisExtent_Derna.shp", None)],
                     masks=[("labels_dl/x/FL20230912LBY_SHP/S2_20230912_CloudObstruction_Derna.shp", None)]),
        secondary={},
        positive_only={"in_phr_extent": "labels_dl/x/FL20230912LBY_SHP/PHR_20230913_FloodExtent_Derna.shp"}),
    "ahr": dict(
        name="Ahr valley flash flood, Germany, 14-15 Jul 2021", epsg=32632,
        proc=os.path.join(EV, "proc"), source=(6.88686, 50.44608), snap_radius=15,
        source_ref="OSM node 173885816 (place=village Schuld); same as build_event_table.py",
        river="osm_dl/ahr_river.json",
        primary=dict(name="cems_EMSR517_AOI15_GRA_MONIT01_v3", cems="cems_dl/EMSR517_AOI15_GRA_MONIT01_r1_RTP01_v3_vector"),
        secondary={"y_cems_aoi15_first": ["cems_dl/EMSR517_AOI15_GRA_PRODUCT_r1_RTP01_v1_vector"],
                   "y_cems_aoi03_s1": ["cems_dl/EMSR517_AOI03_DEL_PRODUCT_r1_RTP01_v1_vector"]},
        positive_only={}),
}
cfg = EVENTS[a.event]
EPSG = cfg["epsg"]
TF = Transformer.from_crs(4326, EPSG, always_xy=True)
INV = Transformer.from_crs(EPSG, 4326, always_xy=True)


def resolve(spec, gdb=None):
    f, layer = spec
    if f is None:
        f = one(gdb)
    elif not os.path.isabs(f):
        f = one(f)
    return f, layer


def read_union(specs, gdb=None):
    if not specs:
        return None, 0, []
    geoms, n, files = [], 0, []
    for s in specs:
        f, layer = resolve(s, gdb)
        g = gpd.read_file(f, layer=layer) if layer else gpd.read_file(f)
        g = g[g.geometry.notna()].to_crs(EPSG)
        n += len(g)
        files.append(os.path.relpath(f, EV) + (f":{layer}" if layer else ""))
        geoms.append(unary_union([make_valid(x) for x in g.geometry]))
    return unary_union(geoms), n, files


def burn(geom, T):
    if geom is None or geom.is_empty:
        return np.zeros(T.shape, bool)
    return rfeat.rasterize([(geom, 1)], out_shape=T.shape, transform=T.transform, fill=0,
                           all_touched=False, dtype="uint8").astype(bool)


def label_set(parts, T, gdb=None):
    """parts: list of dicts with extent/aoi/masks -> per-cell label grid (-1/0/1) + info."""
    lab = np.full(T.shape, -1, np.int8)
    info = []
    for p in parts:
        ext, n_e, f_e = read_union(p["extent"], gdb)
        aoi, n_a, f_a = read_union(p["aoi"], gdb)
        msk, n_m, f_m = read_union(p["masks"], gdb)
        E, A, M = burn(ext, T), burn(aoi, T), burn(msk, T)
        valid = A & ~M
        part = np.where(valid, E.astype(np.int8), -1)
        lab = np.where(part == 1, 1, np.where((part == 0) & (lab != 1), 0, lab)).astype(np.int8)
        info.append({"files": {"extent": f_e, "aoi": f_a, "masks": f_m}, "extent_features": n_e,
                     "extent_km2": round(ext.area / 1e6, 3), "aoi_km2": round(aoi.area / 1e6, 3),
                     "mask_km2": round(msk.area / 1e6, 3) if msk is not None else 0.0,
                     "extent_outside_aoi_km2": round(ext.difference(aoi).area / 1e6, 3),
                     "grid_cells": {"extent": int(E.sum()), "aoi": int(A.sum()), "masked_in_aoi": int((A & M).sum()),
                                    "extent_outside_aoi_or_masked": int((E & ~valid).sum())}})
    return lab, info


def cems_parts(dirs):
    return [cems(d) for d in dirs]


def osm_lines(path):
    out = []
    for e in json.load(open(path))["elements"]:
        if e["type"] == "way" and len(e.get("geometry", [])) >= 2:
            x, y = TF.transform([g["lon"] for g in e["geometry"]], [g["lat"] for g in e["geometry"]])
            out.append(np.c_[x, y])
    return out


def flood_path(T):
    """Same path as the building tables: D8 path from the snapped source; Ahr/Derna cut at the OSM river mouth."""
    sx, sy = TF.transform(*cfg["source"])
    r, c = T.snap_to_channel(*T.rc(sx, sy), radius=cfg["snap_radius"])
    full = T.downstream_path(r, c)
    info = {"source_lonlat": cfg["source"], "source_ref": cfg["source_ref"],
            "snap_offset_m": round(float(np.hypot(*np.subtract(T.xy(r, c), (sx, sy)))), 1)}
    if not cfg["river"]:
        return full, info
    lines = osm_lines(os.path.join(EV, cfg["river"]))
    starts = {tuple(np.round(l[0], 1)) for l in lines}
    terms = [l[-1] for l in lines if tuple(np.round(l[-1], 1)) not in starts]
    inside = lambda p: 0 <= T.rc(*p)[0] < T.shape[0] and 0 <= T.rc(*p)[1] < T.shape[1]
    mouth = terms[int(np.argmin([T.dem[T.rc(*p)] if inside(p) else np.inf for p in terms]))]
    pxy = np.array([T.xy(*divmod(int(i), T.shape[1])) for i in full])
    k = int(np.argmin(np.hypot(pxy[:, 0] - mouth[0], pxy[:, 1] - mouth[1])))
    info.update({"cut_at_osm_river_mouth": [round(v, 5) for v in INV.transform(*mouth)], "path_cut_index": k})
    return full[:k + 1], info


def bands(v, y, edges, key):
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (v >= lo) & (v < hi)
        out.append({key: f"[{lo},{hi})", "n": int(m.sum()), "affected": int(y[m].sum()),
                    "share_affected": round(float(y[m].mean()), 3) if m.any() else None})
    return out


def main():
    t0 = time.time()
    T = Terrain(cfg["proc"])
    assert T.crs.to_epsg() == EPSG, T.crs
    down_frac, _ = T.check_directions()
    path, pinfo = flood_path(T)
    ctx = dm.PathContext(T, path)
    t_ctx = time.time() - t0

    P = cfg["primary"]
    if "cems" in P:
        lab, linfo = label_set(cems_parts([P["cems"]]), T)
    else:
        lab, linfo = label_set([P], T, P.get("gdb"))
    sec = {k: label_set(cems_parts(v), T) for k, v in cfg["secondary"].items()}
    pos_only = {}
    for k, f in cfg["positive_only"].items():
        g, n, files = read_union([(f, None)])
        pos_only[k] = (burn(g, T), {"file": files[0], "features": n, "km2": round(g.area / 1e6, 3)})

    drain = ctx.drain.ravel()
    dist = ctx.dist.ravel()
    labf = lab.ravel()
    drains = drain >= 0
    corr = drains & (dist <= a.max_dist_m)
    cand = np.flatnonzero(corr)
    rr, cc = np.divmod(cand, T.shape[1])
    xs, ys = T.transform * (cc + 0.5, rr + 0.5)
    lon, lat = INV.transform(np.asarray(xs), np.asarray(ys))
    ll = np.c_[lon, lat]
    t1 = time.time()
    X, names, ok, extra = dm.features(ctx, ll, [KIND_CELL] * len(cand), envelope=None, max_dist_m=a.max_dist_m)
    t_feat = time.time() - t1
    yl = labf[cand]
    keep = ok & (yl >= 0)
    idx = cand[keep]
    y = yl[keep].astype(np.int8)
    ids = np.array([f"cell/{i}" for i in idx], dtype="U32")
    np.savez_compressed(os.path.join(EV, "area_table.npz"), X=X[keep], cols=np.array(names), y=y,
                        kind=np.array(["cell"] * len(idx)), event=a.event, cell_id=ids, osm_id=ids,
                        flat_index=idx, lonlat=ll[keep], max_dist_m=a.max_dist_m, label_source=P["name"])
    ex = {k: v[0].ravel()[idx] for k, v in sec.items()}
    ex.update({k: v[0].ravel()[idx] for k, v in pos_only.items()})
    if a.event == "ahr":                      # CEMS notation: flood trace vs flooded area, primary product
        d = cems(P["cems"])
        g = gpd.read_file(d["extent"][0][0]).to_crs(EPSG)
        for note in ("Flood trace", "Flooded area"):
            sub = g[g["notation"] == note]
            ex["ahr_" + note.lower().replace(" ", "_")] = burn(unary_union([make_valid(x) for x in sub.geometry]), T).ravel()[idx]
    np.savez_compressed(os.path.join(EV, "area_labels_extra.npz"), cell_id=ids, **ex)

    # ---- report ----
    Xk, dk = X[keep], dist[idx]
    H = Xk[:, names.index("hand")]
    m5 = dk <= 500
    labelled_grid = labf >= 0
    pos_grid = labf == 1
    path_lab = labf[path]
    d_pos = dist[pos_grid & drains]

    def cnt(m):
        return {"y1": int((y[m] == 1).sum()), "y0": int((y[m] == 0).sum())}

    ex_rep = {}
    for k, v in ex.items():
        v5 = v[m5]
        if v.dtype == bool:
            ex_rep[k] = {"positive_cells_le_500m": int(v5.sum()),
                         "share_of_primary_y1_inside": round(float(v5[y[m5] == 1].mean()), 3) if (y[m5] == 1).any() else None,
                         "share_of_primary_y0_inside": round(float(v5[y[m5] == 0].mean()), 3) if (y[m5] == 0).any() else None}
        else:
            both = v5 >= 0
            ex_rep[k] = {"cells_le_500m_covered": int(both.sum()),
                         "confusion_primary_vs_this": {f"primary{p}_this{s}": int(((y[m5] == p) & (v5 == s)).sum())
                                                       for p in (0, 1) for s in (0, 1)},
                         "agreement": round(float((y[m5][both] == v5[both]).mean()), 3) if both.any() else None}
    pk = Xk[:, names.index("river_km")]
    report = {
        "event": cfg["name"], "label_source": P["name"], "proc": cfg["proc"], "arch": platform.machine(),
        "label_rule": "y=1 cell centre in extent (inside AOI); y=0 centre in AOI, outside extent, not masked; else no row",
        "terrain": {"grid_shape": list(T.shape), "crs": f"EPSG:{EPSG}", "d8_downhill_fraction": round(down_frac, 4),
                    **pinfo, "path_cells": int(len(path)), "path_km": round(float(ctx.km_path[-1]), 2)},
        "primary_label_parts": linfo,
        "secondary_label_parts": {k: v[1] for k, v in sec.items()},
        "positive_only_layers": {k: v[1] for k, v in pos_only.items()},
        "rows_le_500m": cnt(m5), "rows_le_2km": cnt(np.ones(len(y), bool)),
        "rows_by_dist_km": {f"<= {d} m": cnt(dk <= d) for d in (250, 500, 1000, 2000)},
        "corridor_cells_le_max_dist": int(corr.sum()),
        "dropped_corridor_cells": {
            "outside_aoi_or_masked": int((corr & ~labelled_grid).sum()),
            "nonfinite_features": int((~ok & (yl >= 0)).sum())},
        "extent_cells_accounting": {
            "labelled_y1_cells_on_grid": int(pos_grid.sum()),
            "kept_le_500m": int(m5[y == 1].sum()), "kept_le_max_dist": int((y == 1).sum()),
            "not_draining_to_path": int((pos_grid & ~drains).sum()),
            "draining_but_beyond_max_dist": int((pos_grid & drains & (dist > a.max_dist_m)).sum()),
            "positives_dist_to_path_m": {q: round(float(np.percentile(d_pos, p)), 1) for q, p in
                                         [("p50", 50), ("p90", 90), ("p99", 99), ("max", 100)]} if len(d_pos) else None},
        "path_cells_labelled": {"y1": int((path_lab == 1).sum()), "y0": int((path_lab == 0).sum()),
                                "unlabelled": int((path_lab < 0).sum()),
                                "note": "share of the D8 flood path itself inside the mapped extent (channel mapped or not)"},
        "labelled_river_km_le_500m": {"min": round(float(pk[m5].min()), 2), "max": round(float(pk[m5].max()), 2)} if m5.any() else None,
        "sanity_hand_bands_le_500m": bands(H[m5], y[m5], [-np.inf, 2, 5, 10, 20, 50, np.inf], "hand_m"),
        "sanity_dist_bands": bands(dk, y, [0, 30, 60, 100, 200, 500, 1000, 2000.01], "dist_m"),
        "hand_median_le_500m": {"y1": float(np.median(H[m5 & (y == 1)])) if (m5 & (y == 1)).any() else None,
                                "y0": float(np.median(H[m5 & (y == 0)])) if (m5 & (y == 0)).any() else None},
        "secondary_vs_primary_le_500m": ex_rep,
        "kind_feature": "2 = cell (0 building, 1 bridge)", "features": names,
        "ls_500m_note": "Nepal-only feature; 0 outside Nepal",
        "timing_s": {"path_context": round(t_ctx, 2), "features": round(t_feat, 2), "total": round(time.time() - t0, 2)},
    }
    json.dump(report, open(os.path.join(EV, "area_build_report.json"), "w"), indent=2, ensure_ascii=False)
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
