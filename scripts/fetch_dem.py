"""Download Copernicus GLO-30 DEM tiles and crop a mosaic to the study area.

Source: Copernicus DEM GLO-30 on AWS Open Data (no account needed).
  https://registry.opendata.aws/copernicus-dem/
Licence: free use with attribution, "produced using Copernicus WorldDEM-30
(c) DLR e.V. 2010-2014 and (c) Airbus Defence and Space GmbH 2014-2018
provided under COPERNICUS by the European Union and ESA".

Outputs
  data/raw/dem/*.tif               full 1x1 degree tiles (gitignored)
  data/processed/dem_30m.tif       cropped int16 GeoTIFF (metres), EPSG:4326
  data/processed/dem_30m.json      geotransform + shape, for numpy-only readers
"""
import json
import math

import numpy as np
import tifffile

from common import PROCESSED, RAW, bbox, download, log, write_geotiff

BASE = "https://copernicus-dem-30m.s3.amazonaws.com"


def tile_name(lat, lon):
    ns = "N" if lat >= 0 else "S"
    ew = "E" if lon >= 0 else "W"
    return f"Copernicus_DSM_COG_10_{ns}{abs(lat):02d}_00_{ew}{abs(lon):03d}_00_DEM"


def read_tile(path):
    """Return (array, west, north, dx, dy) using the GeoTIFF tiepoint/scale tags."""
    with tifffile.TiffFile(path) as tif:
        page = tif.pages[0]
        arr = page.asarray().astype(np.float32)
        sx, sy, _ = page.tags["ModelPixelScaleTag"].value
        _, _, _, west, north, _ = page.tags["ModelTiepointTag"].value
    return arr, west, north, sx, sy


def main():
    b = bbox()
    tiles = []
    for lat in range(math.floor(b["south"]), math.floor(b["north"]) + 1):
        for lon in range(math.floor(b["west"]), math.floor(b["east"]) + 1):
            name = tile_name(lat, lon)
            path = download(f"{BASE}/{name}/{name}.tif", RAW / "dem" / f"{name}.tif")
            if path is None:
                log(f"  no tile {name} (ocean/void)")
                continue
            tiles.append(read_tile(path))

    # All GLO-30 tiles at these latitudes share one 1-arcsecond grid.
    dx, dy = tiles[0][3], tiles[0][4]
    west = min(t[1] for t in tiles)
    north = max(t[2] for t in tiles)
    east = max(t[1] + t[0].shape[1] * dx for t in tiles)
    south = min(t[2] - t[0].shape[0] * dy for t in tiles)
    mosaic = np.full((round((north - south) / dy), round((east - west) / dx)), np.nan, np.float32)
    for arr, tw, tn, _, _ in tiles:
        r0, c0 = round((north - tn) / dy), round((tw - west) / dx)
        mosaic[r0:r0 + arr.shape[0], c0:c0 + arr.shape[1]] = arr

    r0 = max(0, math.floor((north - b["north"]) / dy))
    r1 = min(mosaic.shape[0], math.ceil((north - b["south"]) / dy))
    c0 = max(0, math.floor((b["west"] - west) / dx))
    c1 = min(mosaic.shape[1], math.ceil((b["east"] - west) / dx))
    # int16 metres: halves the file so it fits in git; 1 m steps are below GLO-30 accuracy.
    crop = np.round(mosaic[r0:r1, c0:c1]).astype(np.int16)
    crop_west, crop_north = west + c0 * dx, north - r0 * dy

    PROCESSED.mkdir(parents=True, exist_ok=True)
    out = PROCESSED / "dem_30m.tif"
    write_geotiff(out, crop, crop_west, crop_north, dx, dy)
    meta = {
        "crs": "EPSG:4326",
        "shape": list(crop.shape),
        "west": crop_west, "north": crop_north, "dx": dx, "dy": dy,
        "note": "pixel (r, c) covers lon west+c*dx..+dx, lat north-r*dy..-dy; metres above EGM2008",
        "min_m": int(crop.min()), "max_m": int(crop.max()),
        "source": "Copernicus DEM GLO-30, https://registry.opendata.aws/copernicus-dem/",
    }
    (PROCESSED / "dem_30m.json").write_text(json.dumps(meta, indent=2))
    log(f"  wrote {out.name} {crop.shape} ({out.stat().st_size / 1e6:.1f} MB), "
        f"elev {meta['min_m']:.0f}-{meta['max_m']:.0f} m")


if __name__ == "__main__":
    main()
