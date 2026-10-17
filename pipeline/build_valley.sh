#!/bin/bash
# Build terrain products for one valley.  usage: pipeline/build_valley.sh <area> <west> <south> <east> <north>
# Outputs: data/proc_<area>/{dem_g,sdir,streams,acc}.tif  (budhi keeps data/proc for backward compatibility)
set -e
A=$1; W=$2; S=$3; E=$4; N=$5
P=data/proc_$A; [ "$A" = budhi ] && P=data/proc
mkdir -p $P data/grassdb
gdalbuildvrt -q -overwrite data/raw/dem/mosaic.vrt data/raw/dem/*.tif
gdalwarp -q -overwrite -te $W $S $E $N -te_srs EPSG:4326 -t_srs EPSG:32645 -tr 30 30 -r bilinear \
  -co COMPRESS=DEFLATE -co TILED=YES data/raw/dem/mosaic.vrt $P/dem_utm.tif
[ -d data/grassdb/$A ] || grass -c EPSG:32645 -e data/grassdb/$A >/dev/null 2>&1
export AREA=$A; G=pipeline/g.sh
$G r.in.gdal -o input=$P/dem_utm.tif output=dem --overwrite --quiet
$G g.region raster=dem --quiet
$G r.watershed -s elevation=dem threshold=5000 accumulation=acc drainage=dir stream=streams memory=3000 --overwrite --quiet
for m in "dem dem_g Float32" "dir sdir Int16" "streams streams Int32" "acc acc Float64"; do set -- $m
  $G r.out.gdal -c input=$1 output=$P/$2.tif format=GTiff type=$3 createopt=COMPRESS=DEFLATE --overwrite --quiet; done
gdalinfo $P/dem_g.tif | grep "Size is"
