# Past landslides: 2015 Gorkha earthquake inventory (USGS)

**File:** `data/processed/landslides_2015.csv` (committed)
`data/raw/landslides/landslides_2015.geojson` (polygons, 138 MB, gitignored; re-create with the script)
**Script:** `scripts/extract_landslides.py`

## What it is

Every landslide visible in high-resolution satellite imagery (WorldView, GeoEye) after the
M7.8 Gorkha earthquake of 25 April 2015, mapped by hand by Roback et al. The earthquake's epicentre was
in Gorkha district, and most of the slope failures were in exactly the three districts we cover.

The plan originally named the NASA Global Landslide Catalog. We switched: the NASA export is a 2016
snapshot with only a handful of points in this area, and its download link is now broken. This
inventory has 16,810 mapped landslides inside our study area.

## What we use it for

- **Risk-model feature:** distance from each road segment to the nearest past landslide, and
  landslide density within, say, 500 m
- **Similar-terrain propagation:** slopes that failed in 2015 show which terrain classes fail
- **Map layer:** past-landslide heat for context in the demo

## Format

One row per landslide:

| Column | Type | Meaning |
|---|---|---|
| `id` | int | Row index in the source shapefile (`Full20170209.shp`); joins to the polygon file |
| `lon`, `lat` | float | Polygon vertex centroid, WGS84 |
| `area_m2` | float | Mapped area in m², from the source |
| `trigger` | str | `4/25 mainshock` (16,801) or `5/12 aftershock` (9) |

Size distribution: median 1,235 m², 5th–95th percentile 133–14,076 m², largest 1.72 km².

The polygon GeoJSON has the same `id`, with `area_m2` and `trigger` as properties.

## Caveats

- **Earthquake-triggered, not rain-triggered.** The 2026 events were monsoon and glacial. Steep,
  weak slopes fail under both triggers, so this is a strong proxy, not the same population. Say so in
  the video.
- **Absence does not mean safe.** Mapping extent and cloud or shadow cover varied
  (`MappingExtent20170209.shp` and `ObscuredAreas20170209.shp` in the raw folder). Areas with no
  landslides may simply not have been mapped.
- **The centroid is a vertex average**, not the area centroid. Fine at the scale of road segments.
- Eleven years of regrowth and new failures since 2015 are not reflected.

## Source and licence

Roback, K., Clark, M.K., West, A.J., Zekkos, D., Li, G., Gallen, S.F., Champlain, D., and Godt, J.W.,
2017, *Map data of landslides triggered by the 25 April 2015 Mw 7.8 Gorkha, Nepal earthquake*:
U.S. Geological Survey data release, <https://doi.org/10.5066/F7DZ06F9>.
Paper: Roback et al. 2018, *Geomorphology* 301, 121–138. USGS data, public domain.
