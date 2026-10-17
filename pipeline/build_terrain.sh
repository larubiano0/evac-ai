#!/bin/bash
# Terrain products with off-the-shelf tools. Inputs: GRASS map 'dem'. Outputs in GRASS + data/proc/*.tif
#   acc/dir   : r.watershed flow accumulation / drainage direction
#   streams   : r.stream.extract channels (threshold in cells; 5000 cells * 900 m2 = 4.5 km2 catchment)
#   hand      : SAGA "Vertical Distance to Channel Network" (= Height Above Nearest Drainage)
set -e
G=pipeline/g.sh; P=data/proc; T=${1:-5000}
$G g.region raster=dem --quiet
time $G r.watershed -s elevation=dem accumulation=acc drainage=dir memory=3000 --overwrite --quiet
time $G r.stream.extract elevation=dem accumulation=acc threshold=$T stream_raster=streams stream_vector=streams direction=sdir memory=3000 --overwrite --quiet
$G r.out.gdal -c input=streams output=$P/streams.tif format=GTiff type=Int32 createopt=COMPRESS=DEFLATE --overwrite --quiet
$G r.out.gdal -c input=sdir output=$P/sdir.tif format=GTiff type=Int16 createopt=COMPRESS=DEFLATE --overwrite --quiet
$G r.out.gdal -c input=acc output=$P/acc.tif format=GTiff type=Float32 createopt=COMPRESS=DEFLATE --overwrite --quiet
time saga_cmd -f=q ta_channels 3 -ELEVATION $P/dem_budhi.tif -CHANNELS $P/streams.tif -DISTANCE $P/hand.sdat -BASELEVEL $P/hand_base.sdat
gdal_translate -q -co COMPRESS=DEFLATE $P/hand.sdat $P/hand.tif
gdalinfo -stats $P/hand.tif | grep -E "Size is|STATISTICS_(MIN|MAX|MEAN)"
