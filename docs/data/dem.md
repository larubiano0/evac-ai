# Elevation (DEM): Copernicus GLO-30

**File:** `data/processed/dem_30m.tif` + `data/processed/dem_30m.json`
**Script:** `scripts/fetch_dem.py`

## What it is

A digital elevation model: a grid where each cell holds the ground height in metres. Copernicus GLO-30 is
the European Space Agency's global DEM, derived from TanDEM-X radar (2011–2015). For this region it is
the most accurate free global DEM, better than SRTM in steep terrain.

## What we use it for

- **Slope** and **height above the river** for each road segment (risk-model features)
- **Tobler walking speed** on trails (`v = 6·exp(-3.5·|tan θ + 0.05|)` km/h)
- **Landslide-dam lake:** fill the valley behind a dam of assumed height, find what floods
- **Outburst path:** follow steepest descent downstream from the dam
- **3D map** base terrain

## Format

| Property | Value |
|---|---|
| Grid | 3784 rows × 5191 columns |
| Cell size | 1 arc-second (≈ 31 m N–S, ≈ 27 m E–W at 28° N) |
| CRS | EPSG:4326 (lon/lat, WGS84) |
| Values | `int16`, metres above the EGM2008 geoid (≈ sea level) |
| Range | 181 m (Trishuli valley floor) to 8,044 m (Manaslu massif) |
| Median | 3,402 m; 5th–95th percentile 620–5,781 m |
| Bounds | see `dem_30m.json` (`west`, `north`, `dx`, `dy`) |
| Size | 24 MB, zlib-compressed GeoTIFF |

Pixel `(row, col)` covers longitude `west + col·dx` to `+dx` and latitude `north − row·dy` to `−dy`.

```python
import json, tifffile
dem = tifffile.imread("data/processed/dem_30m.tif")
m = json.load(open("data/processed/dem_30m.json"))
def elev(lon, lat):
    return dem[int((m["north"] - lat) / m["dy"]), int((lon - m["west"]) / m["dx"])]
```

For slope in metres, convert the cell size: `dy_m = dy · 111_320`, `dx_m = dx · 111_320 · cos(lat)`.

## Caveats

- **It is a surface model, not bare earth.** Values include forest canopy and buildings (a few metres to
  ~20 m in forested valleys). Fine for routing; it adds some error to small-lake volumes.
- **Rounded to whole metres** to fit in git. This is below GLO-30's own vertical accuracy (~2–4 m).
- **Pre-dates the 2026 events.** The August debris flood and the October landslide changed the valley
  floors. A post-event drone DEM (stretch goal) would replace the affected patch.
- Radar shadow on the steepest faces leaves some infilled cells. These are mostly high peaks away from
  roads.

## Source and licence

Copernicus DEM GLO-30, via AWS Open Data: <https://registry.opendata.aws/copernicus-dem/>.
Free to use with attribution: *"Produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus
Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights
reserved."*
