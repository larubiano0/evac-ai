# Ahr valley flash flood, 14-15 Jul 2021: table sources

VM: `~/work-agent-lcpizani/events/ahr/` (`table.npz`, `labels_extra.npz`, `build_report.json`, this file as `SOURCES.md`).
Built by `scripts/damage/events/build_terrain.sh` and `build_event_table.py --event ahr` (agent-lcpizani, 2026-10-17).

## Labels
- **Dataset:** Samprogna Mohor, G., Koch, O., Buhrmann, A., Kirschbauer, L., Thieken, A. & Sieg, T. (2025): *Structural building damage mapped with use of remote sensing in the Ahr valley.* 4TU.ResearchData. https://doi.org/10.4121/8f7a21d3-9bb9-4808-ae51-761eb3fba986 (file `SamprognaMohor_etal_Raters123.zip`, md5 138e48ba62452f6e7fd5f65255668be2)
- **Licence:** ODbL 1.0. Polygons are OpenStreetMap geometries (© OpenStreetMap contributors, 2022).
- **Paper:** Samprogna Mohor et al. (2024), *Remote sensing-based mapping of structural building damage in the Ahr valley*, J. Flood Risk Management, e12983, https://doi.org/10.1111/jfr3.12983
- **Content:** 19,507 polygons, EPSG:4326. Grades D0-D6 (Maiwald & Schwarz 2019, https://doi.org/10.1002/dama.201910014), assigned by visual assessment of LVermGeo orthophotos (24-28 Jul 2021) and a GeoFly 3D mesh (22 Jul 2021). Rater 1 graded 19,187 polygons; raters 2 and 3 graded subsets.
- **Mapping used:** `DmgGrd_R1` (the only near-complete rater).
  - `y = 1` if R1 >= D1 (any damage), `y = 0` if R1 = D0.
  - `destroyed_only = 1` if R1 is D5 or D6 (the two highest grades).
  - The 320 polygons with no R1 grade are dropped.
  - R1 counts: D0 11,990 / D1 2,481 / D2 2,666 / D3 1,621 / D4 239 / D5 71 / D6 119.
  - Where rater 2 also graded a building (n = 1,734), R1 and R2 agree on affected yes/no for 95.8% of them.
  - `labels_extra.npz` stores `grade_r1` (0-6) per kept row, so other thresholds (for example D2+ or D3+) can be used without rebuilding.
- **Rows** sit at polygon centroids (computed in EPSG:32632). The dataset has no OSM ids, so `osm_id = "4tu/<feature index in the shapefile>"`.
- **Negatives** are real D0 buildings from the same dataset, inside the districts the raters analysed.

## Terrain
- **DEM:** Copernicus GLO-30 DSM tiles N50E006 and N50E007 from https://copernicus-dem-30m.s3.amazonaws.com/ ("produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved").
- **Grid:** bbox 6.2-7.35E, 50.12-50.68N, warped (bilinear) to EPSG:32632 at 30 m; 1994 x 2786 cells.
- **Drainage:** GRASS `r.watershed -s` (D8, threshold 5000), same recipe as `pipeline/build_valley.sh`, in a private GRASS database under `~/work-agent-lcpizani/events/grassdb`.
- **Checks:**
  - D8 downhill fraction is 0.982 (Nepal Trishuli: 0.997); the valley is gentler and the DSM includes buildings and trees.
  - The source catchment (515,204 cells, about 464 km²) does not touch the grid edge.

## Flood path
- **Source:** OSM node 173885816 (place=village, name=Schuld, 6.88686E 50.44608N). Why Schuld: it is the upstream village on the Ahr named in the task brief as where the worst damage run began (Schuld -> Altenahr -> Bad Neuenahr-Ahrweiler -> Sinzig). The 4TU labels start only around Altenahr (positives begin at river km 16), so moving the source further upstream would only shift `river_km`.
- **Snapping:** `snap_to_channel(radius=15)` moved the source 469 m to 6.893E 50.4447N on the Ahr D8 channel.
- **Cut at the mouth:** the path is cut at the cell nearest the lowest downstream end vertex of the OSM `waterway=river name=Ahr` ways, which is the Rhine confluence at 7.27928E 50.55992N (way 208098220). The path end is 112 m from it. Without the cut, the path would continue down the Rhine to the grid edge.
- **Result:** 54.6 km. The distance from path cells to the OSM Ahr line is p50 56 m, p95 261 m, max 604 m (30 m D8 in a meandering valley). There are 3 uphill steps > 5 m (max 8 m).

## Table (see build_report.json)
- **Rows:** buildings only; there are no bridge labels in the dataset.
- **Within 2 km:** 7,197 affected / 10,614 unaffected.
- **Within 500 m:** 7,014 affected / 4,521 unaffected; 97.5% of all positives fall inside 500 m. 188 rows with `destroyed_only` = 1 lie within 500 m.
- **Dropped:** 1,149 negatives (all D0) don't drain into the cut path (Rhine side below the confluence, or other routes); 227 negatives lie beyond 2 km. No positives were dropped.
- **HAND sanity (within 500 m), affected share by HAND band:**

  | HAND band | Affected share | n |
  |---|---|---|
  | < 2 m | 0.89 | 1,961 |
  | 2-5 m | 0.81 | 4,132 |
  | 5-10 m | 0.49 | 3,585 |
  | 10-20 m | 0.12 | 1,343 |
  | 20-50 m | 0.006 | 492 |
  | > 50 m | 0 | 22 |

  Median HAND is 3.6 m for affected rows and 7.8 m for unaffected rows.
- **`ls_500m`** is 0 everywhere (Nepal-only feature).

## Caveats
- The DEM is a 2011-2015 DSM, so pre-event buildings and trees raise ground elevation (HAND noise of a few metres).
- Labels come from one rater, assigned by visual assessment from aerial imagery. Interior-only damage (D1) may be under-detected.
- Rows only cover districts the 4TU raters analysed. Unaffected buildings outside those districts are not represented.
