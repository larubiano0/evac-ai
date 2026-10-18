# Oct 11 2026 Budhi Gandaki landslide/avalanche-dam burst flood: impacted-area labels

VM: `~/work-agent-lcpizani/events/oct11/`. Builder: `build_area_table.py --event oct11`. Report: `reports/area_oct11_build_report.json`.

## Primary labels (`y`)
- **UNITAR-UNOSAT, FL20261011NPL**, "Satellite detected mudflow as of 11 October 2026 in Gorkha District, Gandaki Province, Nepal" (HDX posted 2026-10-16). HDX: https://data.humdata.org/dataset/satellite-detected-mudflow-as-of-11-october-2026-in-gorkha-district-gandaki-province-nepal. File: https://unosat.org/static/unosat_filesystem/4267/FL20261011NPL_SHP.zip (gdb: .../4267/FL20261011NPL.gdb.zip).
- **Licence:** CC BY-SA. Attribution: "UNITAR-UNOSAT, FL20261011NPL".
- **Mapped:** `S2_20261011_MudslideExtent`, 18.2 km², class "Flood Water/Mudslide", status "New Water / Water Increase", confidence "To be evaluated", not field-validated. Sentinel-2 (10 m), 11 Oct 2026. The acquisition time is not in the package. The burst was ~03:45 NPT, and the flood reached Arughat 06:30–07:50.
- **Analysed area:** `S2_20261011_AnalysisExtent`, 473 km² (84.72–84.99E, 27.92–28.52N).
- **Masks:** **none published.**

## Comparison label
- `in_mbrsc_s2_extent`: **MBRSC** (Mohammed Bin Rashid Space Centre) via Sentinel Asia, "Flooded Areas in Gorkha District, Nepal As Observed by Sentinel-2 images on 11 October 2026" (published 2026-10-14). https://sentinel-asia.org/EO/2026/article20261010NP.html, file https://sentinel-asia.org/EO/2026/article20261010NP/MBRSC/20261010-Nepal-Flood-Landslide-Other-00664.zip. We use only `gridcode == 1` polygons (4.2 km²); the single `gridcode 0` polygon is treated as background. There is no analysed area and no licence stated, so it is positive-only. It covers 23.5% of UNOSAT y=1, which looks like open water only, without the mud.

## Terrain / path
`/home/linux1/evac-ai/data/proc` (Budhi Gandaki, GLO-30, EPSG:32645, read-only). Source: `replay/oct11.json` (84.9627E 28.4740N, approximate), snapped with radius 15 as `engine/escape.py` does. Snap offset 484 m. Path 94.4 km.

## Counts
≤ 500 m: 12,258 / 75,396. ≤ 2 km: 14,792 / 309,027. 56,253 corridor squares had no label (outside the analysed area). Of the flood path itself: 2,240 squares in the extent, 156 outside, 306 outside the analysed area.
