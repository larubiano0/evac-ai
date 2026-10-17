#!/bin/bash
# Copernicus GLO-30 DEM tiles (public AWS bucket, no key). Licence: Copernicus DEM, free with attribution.
set -e
mkdir -p ../data/raw/dem && cd ../data/raw/dem
for t in N27_00_E084_00 N27_00_E085_00 N28_00_E084_00 N28_00_E085_00; do
  f=Copernicus_DSM_COG_10_${t}_DEM.tif
  [ -s "$f" ] || curl -sf -o "$f" "https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_${t}_DEM/$f"
  echo "$f $(stat -c %s $f)"
done
