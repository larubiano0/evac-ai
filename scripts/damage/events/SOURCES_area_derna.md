# Derna dam-burst flood, 10–11 Sep 2023: impacted-area labels

VM: `~/work-agent-lcpizani/events/derna/` (package already used for the building table, see `SOURCES_derna.md`). Report: `reports/area_derna_build_report.json`.

## Primary labels (`y`)
- **UNITAR-UNOSAT, FL20230912LBY** (GDACS 1102204), https://data.humdata.org/dataset/flood-impact-assessment-in-derna-city-east-province-libya , file https://unosat.org/static/unosat_filesystem/3671/FL20230912LBY_SHP.zip. **Licence:** CC BY-SA.
- **Mapped:** `S2_20230912_FloodExtent_Derna`, 3.15 km², Sentinel-2 10 m, 12 Sep 2023 (~1.5 days after the night of 10–11 Sep).
- **Analysed area:** `S2_20230912_AnalysisExtent_Derna` (11.9 km², the city only).
- **Mask:** `S2_20230912_CloudObstruction_Derna`, which covers 2.8 km² of that area. 556 extent squares under the mask were dropped.

## Comparison label
- `in_phr_extent`: `PHR_20230913_FloodExtent_Derna` (Pléiades, 13 Sep). It has no analysis extent of its own, so it is positive-only. It contains 100% of S2 y=1.

## Terrain / path
Source: Abou Mansour dam (OSM way 1207192349), radius 15, cut at the coast, the same as `build_event_table.py`. Path 15.5 km.

## Counts and caveat
≤ 500 m: 669 / 800. 2,273 extent squares **do not drain into the single D8 path**: the city sits on a fan where the flood spread sideways, but D8 sends each square straight to the sea. Only the wadi corridor is labelled. That is a small table, used for testing only.
