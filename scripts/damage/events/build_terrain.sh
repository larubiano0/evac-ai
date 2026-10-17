#!/bin/bash
# Terrain products for one past-event valley, same recipe as pipeline/build_valley.sh (GRASS r.watershed -s, D8,
# threshold 5000 cells) but in the event's own UTM zone and in a private GRASS database.
# usage: build_terrain.sh <event_dir> <epsg> <west> <south> <east> <north>
#   <event_dir>/dem_dl/*.tif   Copernicus GLO-30 tiles (input)
#   <event_dir>/proc/{dem_g,sdir,streams,acc}.tif  (output, loadable with engine.terrain.Terrain)
set -e
EV=$1; EPSG=$2; W=$3; S=$4; E=$5; N=$6
DB=$HOME/work-agent-lcpizani/events/grassdb
LOC=$(basename "$EV")_$EPSG
P=$EV/proc; mkdir -p "$P" "$DB"
gdalbuildvrt -q -overwrite "$EV/dem_mosaic.vrt" "$EV"/dem_dl/*.tif
gdalwarp -q -overwrite -te $W $S $E $N -te_srs EPSG:4326 -t_srs EPSG:$EPSG -tr 30 30 -r bilinear \
  -co COMPRESS=DEFLATE -co TILED=YES "$EV/dem_mosaic.vrt" "$P/dem_utm.tif"
[ -d "$DB/$LOC" ] || grass -c EPSG:$EPSG -e "$DB/$LOC" >/dev/null 2>&1
G() { grass "$DB/$LOC/PERMANENT" --exec "$@" 2> >(grep -vE "SyntaxWarning|fmt$" >&2); }
G r.in.gdal -o input="$P/dem_utm.tif" output=dem --overwrite --quiet
G g.region raster=dem --quiet
G r.watershed -s elevation=dem threshold=5000 accumulation=acc drainage=dir stream=streams memory=2000 --overwrite --quiet
for m in "dem dem_g Float32" "dir sdir Int16" "streams streams Int32" "acc acc Float64"; do set -- $m
  G r.out.gdal -c input=$1 output="$P/$2.tif" format=GTiff type=$3 createopt=COMPRESS=DEFLATE --overwrite --quiet; done
gdalinfo "$P/dem_g.tif" | grep "Size is"
