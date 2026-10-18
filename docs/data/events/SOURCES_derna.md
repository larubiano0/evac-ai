# Derna dam-burst flash flood, 10-11 Sep 2023: table sources

VM: `~/work-agent-lcpizani/events/derna/` (`table.npz`, `labels_extra.npz`, `build_report.json`, this file as `SOURCES.md`).
Built by `scripts/damage/events/build_terrain.sh` and `build_event_table.py --event derna` (agent-lcpizani, 2026-10-17).

## Labels
- **Dataset:** UNITAR-UNOSAT, *Flood impact assessment in Derna City, East Province, Libya*, UNOSAT code FL20230912LBY (GDACS 1102204). HDX page: https://data.humdata.org/dataset/flood-impact-assessment-in-derna-city-east-province-libya. File: https://unosat.org/static/unosat_filesystem/3671/FL20230912LBY_SHP.zip. The gdb version (FL20230912LBY_gdb.zip) was also checked for coded domains.
- **Licence:** CC BY-SA (as listed on HDX). Attribution: "UNITAR-UNOSAT, FL20230912LBY".
- **Positives:** `PHR_20230913_AffectedStructure_Derna` has 2,217 points from Pléiades imagery of 13 Sep 2023. Every point is "Building (General / Default)", "Damage", "Damaged Buildings", "Not yet field validated". The HDX description calls these buildings "exposed to rushing floodwaters". 2,180 of them are exact duplicates of the S2_20230912 layer.
- **Analysed area:** `S2_20230912_AnalysisExtent_Derna`, 11.9 km². It is the only analysis extent for Derna city in the package; the PHR layer has no extent of its own. 2,207 of the 2,217 points fall inside it. The 10 outside are dropped so that positives and negatives come from the same area.
- **Negatives:** OSM buildings from an Overpass attic snapshot `[date:"2023-09-20T00:00:00Z"]` (ways with `building=*`, © OpenStreetMap contributors, ODbL).
  - Why this snapshot: pre-event OSM had only 85 building ways here (2023-09-10). Mapping after the event (presumably a humanitarian mapping activation; not checked) raised the count to 3,306 on 09-15, 6,154 on 09-17 and a peak of 9,739 on 2023-09-20. It drifted down afterwards (9,600 on 09-25, 9,627 on 10-01, 9,641 on 11-01, 9,258 today); we did not check why.
  - 7,638 polygons have their centroid inside the extent.
  - A negative is a polygon that contains no UNOSAT point and is farther from every point than the match tolerance.
  - Match tolerance = 9.99 m, the 95th percentile of the distance from each UNOSAT point to its nearest OSM polygon (computed from the data: 1,680 points lie inside a polygon, p50 = 0 m).
  - 1,426 polygons within the tolerance are dropped as ambiguous. That leaves 4,652 negatives; 11 building relations are not used.
- **Mapping:**
  - `y = 1` for each UNOSAT point, with the row at the point and `osm_id = "unosat/<feature index>"`. `labels_extra.npz` stores the OSM way that contains the point, if any.
  - `y = 0` for each negative OSM polygon, with the row at its centroid and `osm_id = "way/<id>"`.
  - **`destroyed_only` is undefined** (UNOSAT has a single class) and is set to 0 for every row; the report says `destroyed_only_defined: false`. Do not use Derna for a destroyed-only model.
- **Cloud:** `S2_20230912_CloudObstruction_Derna` covers 2.79 km² of the extent, yet 399 PHR points lie inside it, so the Pléiades analysis did cover that area. Rows are kept, and `labels_extra.npz:in_s2_cloud` flags them (within 500 m: 240 affected / 161 unaffected).
- **Bridges:** none. `S2_20230912_AffectedInfrastructure_Derna` has 8 points, but their SiteID codes (22, 48, 49) have no domain in the shapefile or gdb, so they cannot be decoded.

## Terrain
- **DEM:** Copernicus GLO-30 DSM tiles N32E021 and N32E022 (attribution as for Ahr).
- **Grid:** bbox 21.9-22.75E, 32.35-32.85N, warped to EPSG:32634 at 30 m; 1881 x 2636 cells. GRASS `r.watershed -s`, threshold 5000.
- **Checks:** D8 downhill fraction 0.990. The source catchment (518,150 cells, about 466 km²) does not touch the grid edge.

## Flood path
- **Source:** OSM way 1207192349 (waterway=dam, name=Abou Mansour, start_date=1976), centre 22.57708E 32.65937N. This is the upper of the two Wadi Derna dams whose failure caused the flood. The southern tip of UNOSAT's `PHR_20230913_FloodExtent_Derna` polygon (32.659N, 22.576E) lies at the same dam.
- **Snapping:** `snap_to_channel(radius=15)` moved the source 538 m to 22.5805E 32.6633N, just downstream of the dam.
- **Cut at the coast:** the path is cut at the cell nearest the lowest downstream end vertex of the OSM Wadi Derna ways (way 1207020859 ends at the coast, 22.65082E 32.76723N). The path end is 19 m from it. The first path cell with DEM <= 0 m is 3 cells further.
- **Result:** 15.45 km. The distance from path cells to the OSM wadi line is p50 12.5 m, p95 46 m, max 224 m.
- **DSM bumps:** the path profile has 9 uphill steps > 5 m. The largest is +21.4 m and +16.7 m on consecutive cells at about 22.6198E 32.7296N, roughly 2.5 km above the city. This looks like a structure in the 2011-2015 DSM, for example a dam or bridge that the flood destroyed, but it is not verified. HAND downstream of such steps is relative to lower channel cells, which is correct, but the profile is not monotone.

## Table (see build_report.json)
- **Rows:** buildings only.
- **Within 2 km:** 577 affected / 1,194 unaffected.
- **Within 500 m:** 567 affected / 637 unaffected.
- **Main limitation:** only 26% of the 2,207 positives are kept. 1,630 positives and 3,458 negatives are "inside grid, not draining to path". Derna city sits on the coastal fan at the wadi mouth: these cells (median 621 m from the D8 channel, median elevation about 12 m) drain straight to the sea along their own D8 routes and never join the wadi path. The real flood spread across the fan, which a single-channel HAND-to-path model cannot represent. The kept rows are the wadi-corridor part of the city; the dropped fan buildings are not modelled.
- **HAND sanity:** affected share is 0.8 at HAND 2-20 m, 0.52 at 20-50 m and 0.12 above 50 m. The median HAND is 10.8 m for affected rows and 58 m for unaffected rows. The step at low HAND is weaker than for Ahr or Nepal. There are 60 positives at HAND > 50 m around 22.635-22.640E 32.757N (DSM elevation about 66 m, about 200 m from the channel, on the gorge edge). Their labels come from UNOSAT unchanged.
- **`ls_500m`** is 0 everywhere.

## Caveats
- **Label quality:** UNOSAT labels are preliminary and not field-validated. The single class means "affected / exposed", not graded damage.
- **Negatives:**
  - We don't know whether the 2023-09-20 OSM buildings were mapped from pre- or post-event imagery. If post-event, buildings washed away entirely may be missing as polygons; positives don't depend on OSM, so this affects only matching.
  - Negatives are "not marked by UNOSAT", not field-verified as undamaged.
- **DEM:** pre-event DSM (buildings included, both dams present).
