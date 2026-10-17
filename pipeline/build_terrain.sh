#!/bin/bash
# Terrain products with off-the-shelf tools. Inputs: GRASS map 'dem'. Outputs in GRASS + data/proc/*.tif
#   acc/dir   : r.watershed flow accumulation / drainage direction
#   streams   : r.watershed stream segments (threshold in cells; 5000 cells * 900 m2 = 4.5 km2 catchment)
#   hand      : SAGA "Vertical Distance to Channel Network" (= Height Above Nearest Drainage)
set -e
G=pipeline/g.sh; P=data/proc; T=${1:-5000}
$G g.region raster=dem --quiet
# r.stream.extract timed out (>200 s) on this grid; r.watershed's own stream output takes seconds.
time $G r.watershed -s elevation=dem threshold=$T accumulation=acc drainage=dir stream=streams memory=3000 --overwrite --quiet
$G r.mapcalc "sdir = dir" --overwrite --quiet
$G r.out.gdal -c input=streams output=$P/streams.tif format=GTiff type=Int32 createopt=COMPRESS=DEFLATE --overwrite --quiet
$G r.out.gdal -c input=sdir output=$P/sdir.tif format=GTiff type=Int16 createopt=COMPRESS=DEFLATE --overwrite --quiet
$G r.out.gdal -c input=acc output=$P/acc.tif format=GTiff type=Float64 createopt=COMPRESS=DEFLATE --overwrite --quiet
# Export the DEM from GRASS too: SAGA rejects grids whose origins differ by ~1e-9 m (gdalwarp vs GRASS rounding).
$G r.out.gdal -c input=dem output=$P/dem_g.tif format=GTiff type=Float32 createopt=COMPRESS=DEFLATE --overwrite --quiet
# SAGA ignores Int32 GeoTIFF nodata -> every cell became a channel. Pass a Byte mask (1=channel, nodata=0).
$G r.mapcalc "chan = if(isnull(streams), null(), 1)" --overwrite --quiet
$G r.out.gdal -c input=chan output=$P/chan.tif format=GTiff type=Byte nodata=0 createopt=COMPRESS=DEFLATE --overwrite --quiet
time saga_cmd ta_channels 3 -ELEVATION $P/dem_g.tif -CHANNELS $P/chan.tif -DISTANCE $P/hand.sdat -BASELEVEL $P/hand_base.sdat 2>&1 | grep -E "Error|error" || true
gdal_translate -q -a_nodata -99999 -co COMPRESS=DEFLATE $P/hand.sdat $P/hand.tif
gdalinfo -stats $P/hand.tif | grep -E "Size is|STATISTICS_(MIN|MAX|MEAN)"
