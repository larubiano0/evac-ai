"""Download WorldPop 2026 constrained population (100 m) for Nepal and crop it.

Source: WorldPop Global2 R2025A, https://hub.worldpop.org/project/categories?id=3
Licence: CC BY 4.0, "WorldPop (www.worldpop.org), University of Southampton".

Outputs
  data/raw/worldpop/npl_pop_2026_CN_100m_R2025A_v1.tif   whole country (gitignored)
  data/processed/population_100m.tif                    float32 people per cell, 0 = none
  data/processed/population_100m.json                   geotransform + totals
"""
import json
import math

import numpy as np
import tifffile

from common import PROCESSED, RAW, bbox, download, log, write_geotiff

YEAR = 2026
NAME = f"npl_pop_{YEAR}_CN_100m_R2025A_v1.tif"
URL = (f"https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/{YEAR}"
       f"/NPL/v1/100m/constrained/{NAME}")


def main():
    path = download(URL, RAW / "worldpop" / NAME)
    with tifffile.TiffFile(path) as tif:
        page = tif.pages[0]
        arr = page.asarray()
        dx, dy, _ = page.tags["ModelPixelScaleTag"].value
        _, _, _, west, north, _ = page.tags["ModelTiepointTag"].value

    b = bbox()
    r0 = max(0, math.floor((north - b["north"]) / dy))
    r1 = min(arr.shape[0], math.ceil((north - b["south"]) / dy))
    c0 = max(0, math.floor((b["west"] - west) / dx))
    c1 = min(arr.shape[1], math.ceil((b["east"] - west) / dx))
    crop = arr[r0:r1, c0:c1].astype(np.float32)
    crop[~np.isfinite(crop) | (crop < 0)] = 0  # nodata (-99999) -> nobody lives here
    crop_west, crop_north = west + c0 * dx, north - r0 * dy

    out = PROCESSED / "population_100m.tif"
    write_geotiff(out, crop, crop_west, crop_north, dx, dy)
    meta = {
        "crs": "EPSG:4326", "shape": list(crop.shape),
        "west": crop_west, "north": crop_north, "dx": dx, "dy": dy,
        "year": YEAR, "total_people_in_bbox": round(float(crop.sum())),
        "source": URL,
    }
    (PROCESSED / "population_100m.json").write_text(json.dumps(meta, indent=2))
    log(f"  wrote {out.name} {crop.shape} ({out.stat().st_size / 1e6:.1f} MB), "
        f"{meta['total_people_in_bbox']:,} people in bbox")


if __name__ == "__main__":
    main()
