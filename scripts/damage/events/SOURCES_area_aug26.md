# Aug 26 2026 Bhotekoshi–Trishuli debris flood: impacted-area labels

VM: `~/work-agent-lcpizani/events/aug26/` (`area_table.npz`, `area_labels_extra.npz`, `area_build_report.json`; downloads in `*_dl/`).
Builder: `build_area_table.py --event aug26`. Report copy: `reports/area_aug26_build_report.json`.

## Primary labels (`y`)
- **UNITAR-UNOSAT, FL20260826NPL** (GDACS 1104124, GLIDE FF-2026-000162-NPL), "Mudflow/Rockflow Impact Assessment in Rasuwa & Nuwakot Districts". HDX: https://data.humdata.org/dataset/mudflow-rockflow-impact-assessment-in-rasuwa-nuwakot-districts-bagmati-province-nepal-as-o. File: https://unosat.org/static/unosat_filesystem/4259/FL20260826NPL.gdb.zip. It is byte-identical to the gdb under products 4257, 4258 and 4260.
- **Licence:** CC BY-SA (HDX). Attribution: "UNITAR-UNOSAT, FL20260826NPL".
- **Mapped:** `UNOSAT_Multisensor_20260826_20260828_FloodExtent`, one multipolygon of 64.9 km². HDX describes it as "satellite-detected mudflow/rockflow extent derived from Sentinel-2 imagery acquired on 27 August 2026 and PlanetScope imagery acquired on 26 August 2026". It mixes water, mud and rockflow in one class. Resolution: Sentinel-2 10 m, PlanetScope ~3 m. Acquisition times are not in the package. The layer name says 26–28 Aug. Preliminary, not field-validated.
- **Analysed area:** `UNOSAT_Multisensors_20260826_20260828_AnalysisExtent`, 1,246 km² (84.35–85.54E). It covers the whole 2 km corridor on our grid.
- **Masks:** **none published** (no cloud layer in the gdb). Any cloud inside the analysed area therefore counts as "not flooded".
- Extent cells west of 84.73E (down to the Narayani) are outside the Trishuli terrain grid and are not used.

## Comparison labels (`area_labels_extra.npz`; -1 = not covered)
- `y_cems_first` / `y_cems_latest`: **Copernicus EMS Rapid Mapping EMSR927** (© 2026 European Union; HDX lists CC BY; cite "Copernicus Emergency Management Service (© 2026 European Union), EMSR927"). https://mapping.emergency.copernicus.eu/activations/EMSR927 , packages from `https://rapidmapping.emergency.copernicus.eu/backend/EMSR927/<AOI>/<product>/<name>.zip`.
  - Grading products, layer `observedEventA`, class "6-Mass Movement / Landslide", photo-interpretation.
  - Masks: `areaOfInterestA` minus `notAnalysedA`.
  - AOI01 Syapru Besi (3.5 km², WorldView-3 0.3 m, 27 Aug 05:05 UTC); AOI02 Timure (3.0 km², Legion 0.3 m, 27 Aug 05:05 UTC); AOI03 Bidur (21 km², Satellogic 0.8 m 27 Aug 04:22 UTC + BlackSky 1 m 12:09 UTC; monitoring: PeruSat 27 Aug + Resurs-P 28 Aug); AOI05 Phosretar (23.9 km², Pléiades 0.5 m + Pléiades Neo 0.3 m 31 Aug; monitoring: 5 Sep).
  - AOI04 Bharatpur and AOI06 Kyundi were **cancelled for persistent cloud** (no data).
  - "first" = first grading product per AOI. "latest" = monitoring version where it exists.
  - Agreement with UNOSAT ≤ 500 m: 95.6% (41,298 squares covered).
- `in_hot_extent`: **HOT** "Nepal Flood 2026 Flood Extent, Observed 27 August 2026" (31.7 km²), https://production-raw-data-api.s3.amazonaws.com/ISO3/NPL/combined/hot_flood_npl_flood_extent.geojson from HDX `hot_flood_npl` (ODbL). HOT says it was "mapped from drone, Landsat, PlanetScope and Sentinel imagery", but gives no analyst, date per source or analysed area, so it is a positive-only flag. It contains 91% of UNOSAT y=1 and 3.5% of y=0.
- `in_jaxa_alos2_fpm`: **JAXA** Flood Proxy Map, ALOS-2 28 Aug 2026 (automatic SAR analysis) via Sentinel Asia, https://sentinel-asia.org/EO/2026/article20260826NP/JAXA/JAXA_20250828_FPM_ALOS2_Nepal_FLDEXT.zip. Licence not stated. Covers only 13% of UNOSAT y=1, as expected for SAR in steep valleys (radar shadow and layover).

## Terrain / path
`/home/linux1/evac-ai/data/proc_trishuli` (Copernicus GLO-30, EPSG:32645, read-only). Source: Rasuwagadhi (85.383E 28.276N), snapped with radius 15, same as `build_table.py` and `engine/escape.py`. Path 121.2 km.

## Counts
≤ 500 m: 28,458 y=1 / 98,070 y=0. ≤ 2 km: 30,226 / 412,947. 31,445 corridor squares had no label (outside the analysed area). There were no non-finite features.
