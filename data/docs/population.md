# Population: WorldPop 2026 (100 m, constrained)

**File:** `data/processed/population_100m.tif` + `data/processed/population_100m.json`
**Script:** `scripts/fetch_worldpop.py`

## What it is

An estimate of how many people live in each 100 m × 100 m cell. WorldPop spreads census and survey
totals across the map using satellite-detected buildings, roads, night lights and land cover.
"Constrained" means people are only placed in cells that contain buildings, which suits scattered hill
villages much better than the unconstrained version. The release used here (Global2, R2025A) gives a
2026 projection.

## What we use it for

- **People per village:** sum the cells nearest each `place=*` point, or within its catchment
- **Demand in the evacuation router:** how many people each village sends along its route
- **Shelter load:** compared against shelter capacity (or a stand-in, such as school size)

## Format

| Property | Value |
|---|---|
| Grid | 1262 rows × 1731 columns |
| Cell size | 3 arc-seconds (≈ 90 m) |
| CRS | EPSG:4326 |
| Values | `float32` people per cell; `0` = no one (WorldPop nodata was set to 0) |
| Populated cells | 458,193 of 2,184,522 (21 %) |
| Densest cell | 583 people |
| Total in bbox | ≈ 1.96 million |
| Size | 1.7 MB |

Read it the same way as the DEM (see [dem.md](dem.md)), using `population_100m.json` for the bounds.

## Caveats

- **The bbox total is not the three-district total.** The rectangular study area takes in the northern
  edge of the Kathmandu valley. Gorkha, Nuwakot and Rasuwa together hold roughly 0.55 million people.
  Always clip to `osm/districts.geojson` or to village catchments before summing.
- **Modelled, not counted.** Per-cell values carry wide error; per-village sums are more reliable.
- **Residents only.** Trekkers and seasonal workers are not included. The Manaslu circuit (Budhi
  Gandaki) and Langtang (Rasuwa) carry thousands of trekkers in October–November, so add a seasonal
  adjustment on top for those corridors.
- **Pre-disaster.** People displaced in August–October 2026 are still counted at home.

## Source and licence

WorldPop (www.worldpop.org), School of Geography and Environmental Science, University of Southampton.
Global2 R2025A, `npl_pop_2026_CN_100m_R2025A_v1.tif`:
<https://hub.worldpop.org/>. Licence: CC BY 4.0.
