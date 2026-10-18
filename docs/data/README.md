# Data

This page describes the repo's [`data/`](../../data/) folder (paths below are relative to it).

Study area: Gorkha, Rasuwa and Nuwakot districts, plus a ~3 km pad
(bbox in [processed/study_area.json](../../data/processed/study_area.json)). All layers are WGS84 / EPSG:4326.

- `processed/`: clipped, ready to use. **Committed**, so the app runs on the VM with no downloads.
- `replay/`: recorded live feeds for the demo replay. **Committed.**
- `raw/`: full downloads. **Gitignored.** Re-create them with the scripts below.

## Layers

Each dataset has a full write-up in this folder: what it is, schema, how we use it, caveats. Satellite flood extents and the other events used for training are in [events/](events/).


| File | What | Source | Licence |
|---|---|---|---|
| `processed/dem_30m.tif` (+ `.json`) | Elevation, int16 metres, 1 arc-second (~30 m). [docs](dem.md) | [Copernicus GLO-30](https://registry.opendata.aws/copernicus-dem/) | Copernicus DEM licence, attribution |
| `processed/population_100m.tif` (+ `.json`) | People per 100 m cell, 2026 projection, constrained. [docs](population.md) | [WorldPop Global2 R2025A](https://hub.worldpop.org/) | CC BY 4.0 |
| `processed/landslides_2015.csv` | 16,810 landslides from the 2015 Gorkha earthquake: centroid, area. [docs](landslides_2015.md) | [Roback et al. 2017, USGS](https://doi.org/10.5066/F7DZ06F9) | Public domain |
| `processed/osm/districts.geojson` | District boundaries. [docs](osm.md) | [OpenStreetMap](https://www.openstreetmap.org/copyright) via [Geofabrik](https://download.geofabrik.de/asia/nepal.html) | ODbL |
| `processed/osm/roads.geojson` | All `highway=*` incl. tracks, paths, footways, bridges | OSM | ODbL |
| `processed/osm/waterways.geojson` | Rivers and streams | OSM | ODbL |
| `processed/osm/places.geojson` | Settlements (`place=*`) | OSM | ODbL |
| `processed/osm/shelters.geojson` | Schools, health facilities, shelters (stand-ins for official shelters) | OSM | ODbL |
| `processed/osm/damage.geojson` | Anything with a `damage*` / `destroyed*` tag: ~314 failed road/bridge segments from Aug 2026. [docs](osm_damage_labels.md) | OSM | ODbL |
| `processed/osm/buildings.csv` | Building centroids + damage flag | OSM | ODbL |
| `replay/dhm/*.json` | Snapshots of DHM river level, rainfall, discharge. [docs](dhm_feed.md) | [hydrology.gov.np](https://hydrology.gov.np) | Public site |

## Reading the rasters without GDAL (works on s390x)

```python
import json, tifffile
dem = tifffile.imread("data/processed/dem_30m.tif")          # (rows, cols) int16
meta = json.load(open("data/processed/dem_30m.json"))
row = int((meta["north"] - lat) / meta["dy"])
col = int((lon - meta["west"]) / meta["dx"])
```

tifffile handles byte order, so the same file reads correctly on big-endian LinuxONE.

## Re-creating everything

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-extract.txt
cd scripts
mkdir -p ../data/raw/osm
curl -L -o ../data/raw/osm/nepal-latest.osm.pbf https://download.geofabrik.de/asia/nepal-latest.osm.pbf
../.venv/bin/python extract_osm.py ../data/raw/osm/nepal-latest.osm.pbf   # ~8 min; writes study_area.json
../.venv/bin/python fetch_dem.py           # crops to the bbox from study_area.json
../.venv/bin/python fetch_worldpop.py
../.venv/bin/python extract_landslides.py
../.venv/bin/python record_dhm.py          # one snapshot; on the VM use --loop 900
```

On the VM, only `requirements.txt` is needed (`record_dhm.py` and the app).
Overpass API was overloaded on event day, so the OSM layers come from the Geofabrik extract.
