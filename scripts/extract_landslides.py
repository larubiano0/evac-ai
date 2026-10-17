"""Past landslides: USGS inventory of the 2015 Gorkha earthquake (Roback et al.).

Run on a laptop (pyproj); the VM only reads the outputs.

Source: Roback, K., Clark, M.K., West, A.J., et al., 2017, Map data of landslides
triggered by the 25 April 2015 Mw 7.8 Gorkha, Nepal earthquake: USGS data release,
https://doi.org/10.5066/F7DZ06F9 (public domain).

Outputs
  data/raw/landslides/landslides_2015.geojson   polygons in the study bbox, WGS84
                                                (~140 MB, so gitignored)
  data/processed/landslides_2015.csv            one row per landslide: centroid, area m2
"""
import csv
import json

import shapefile
from pyproj import Transformer

from common import PROCESSED, RAW, bbox, download, log

URL = ("https://www.sciencebase.gov/catalog/file/get/582c74fbe4b04d580bd377e8"
       "?f=__disk__47%2F64%2F62%2F476462808bb07b2ea46b6ebe15d2214bbcfc5078")
ZIP = RAW / "landslides" / "Roback_Nepal_final_files.zip"
SHP = RAW / "landslides" / "roback" / "Roback_Nepal_final_files" / "Full20170209.shp"


def main():
    if not SHP.exists():
        import zipfile
        download(URL, ZIP)
        zipfile.ZipFile(ZIP).extractall(RAW / "landslides" / "roback")

    to_wgs = Transformer.from_crs("EPSG:32645", "EPSG:4326", always_xy=True)
    b = bbox()
    feats, rows = [], []
    reader = shapefile.Reader(str(SHP))
    for i, sr in enumerate(reader.iterShapeRecords()):
        pts = sr.shape.points
        lons, lats = to_wgs.transform([p[0] for p in pts], [p[1] for p in pts])
        clon, clat = sum(lons) / len(lons), sum(lats) / len(lats)
        if not (b["west"] <= clon <= b["east"] and b["south"] <= clat <= b["north"]):
            continue
        parts = list(sr.shape.parts) + [len(pts)]
        rings = [[[round(lons[j], 6), round(lats[j], 6)] for j in range(parts[k], parts[k + 1])]
                 for k in range(len(parts) - 1)]
        rec = sr.record.as_dict()
        feats.append({"type": "Feature", "id": f"roback/{i}",
                      "geometry": {"type": "Polygon", "coordinates": rings},
                      "properties": {"area_m2": round(rec["Area"], 1), "trigger": rec["Trigger"]}})
        rows.append((i, round(clon, 6), round(clat, 6), round(rec["Area"], 1), rec["Trigger"]))

    out = RAW / "landslides" / "landslides_2015.geojson"
    out.write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                              separators=(",", ":")))
    log(f"  {out.name}: {len(feats)} polygons, {out.stat().st_size / 1e6:.1f} MB")
    out = PROCESSED / "landslides_2015.csv"
    with open(out, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "lon", "lat", "area_m2", "trigger"])
        w.writerows(rows)
    log(f"  {out.name}: {len(rows)} rows, {out.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
