# Ahr valley flash flood, 14–15 Jul 2021: impacted-area labels

VM: `~/work-agent-lcpizani/events/ahr/` (terrain `proc/` from `build_terrain.sh`, see `SOURCES_ahr.md`). Report: `reports/area_ahr_build_report.json`.

## Primary labels (`y`)
- **Copernicus EMS Rapid Mapping EMSR517** "Flood in Western Germany", AOI15 **Bad Neuenahr-Ahrweiler**, Grading **Monitoring 1, version 3**. https://mapping.emergency.copernicus.eu/activations/EMSR517 , file https://cems-mapping-website.s3.eu-west-1.amazonaws.com/static/activations/EMSR517/EMSR517_AOI15_GRA_MONIT01_r1_RTP01_v3_vector.zip.
- **Licence:** Copernicus EMS data are free and open with attribution: "Copernicus Emergency Management Service (© 2021 European Union), EMSR517" (see https://emergency.copernicus.eu/mapping/ems/cite-copernicus-ems-mapping-portal).
- **Mapped:** `observedEventA`, 173 polygons, 10.8 km², class "5-Flood / Riverine flood", photo-interpretation. Notation: 91 polygons "Flood trace", 82 "Flooded area". 82% of y=1 squares are flood traces, i.e. mud and debris left behind, not standing water. Images: aerial photos 0.12 m (16 Jul 2021) and Pléiades 0.5 m (20 Jul 2021), i.e. 1–5 days after the peak on the night of 14–15 Jul.
- **Analysed area:** `areaOfInterestA`, 120.2 km². **Masks:** no `notAnalysedA` layer.

## Comparison labels
- `y_cems_aoi15_first`: the first AOI15 grading product (v1, Pléiades 18 Jul, AOI 60 km²). Agreement 93.1%.
- `y_cems_aoi03_s1`: AOI03 **Honningen** delineation (Sentinel-1 SAR 15 Jul 05:50 UTC, semi-automatic, AOI 209 km²). Agreement 78.8%: radar finds little in the narrow valley (1,015 of 9,701 y=1 squares).
- `ahr_flood_trace` / `ahr_flooded_area`: the primary polygons split by notation.
- Not used: AOI08 Euskirchen (a different river: Erft/Steinbach), AOI01/04/05/06 (outside the Ahr corridor or other rivers).

## Terrain / path
Source Schuld (OSM node 173885816), radius 15, cut at the Ahr mouth, the same as `build_event_table.py`. Path 54.6 km.

## Counts
≤ 500 m: 10,680 / 36,131. ≤ 2 km: 11,210 / 93,399.
