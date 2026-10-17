#!/bin/bash
# Empirical check: does r.walk's cost at X mean "time to walk FROM start TO X" (uphill costly) or the reverse?
set -e
G=pipeline/g.sh
read AE AN < <(echo "84.8116 28.0384" | gdaltransform -s_srs EPSG:4326 -t_srs EPSG:32645 | awk '{print int($1), int($2)}')
BE=$((AE+900)); BN=$AN
$G g.region raster=dem n=$((AN+1500)) s=$((AN-1500)) e=$((AE+1500)) w=$((AE-1500)) --quiet
$G r.mapcalc "fr0 = 0" --overwrite --quiet
echo "A(valley) elev: $($G r.what map=dem coordinates=$AE,$AN | cut -d'|' -f4)   B(900 m east) elev: $($G r.what map=dem coordinates=$BE,$BN | cut -d'|' -f4)"
$G r.walk elevation=dem friction=fr0 output=cA start_coordinates=$AE,$AN --overwrite --quiet
$G r.walk elevation=dem friction=fr0 output=cB start_coordinates=$BE,$BN --overwrite --quiet
echo "cost at B when start=A : $($G r.what map=cA coordinates=$BE,$BN | cut -d'|' -f4) s"
echo "cost at A when start=B : $($G r.what map=cB coordinates=$AE,$AN | cut -d'|' -f4) s"
$G g.region raster=dem --quiet
# Fix: negated DEM + start at destination should reproduce the uphill A->B time.
$G g.region raster=dem n=$((AN+1500)) s=$((AN-1500)) e=$((AE+1500)) w=$((AE-1500)) --quiet
$G r.mapcalc "negdem = -dem" --overwrite --quiet
$G r.walk elevation=negdem friction=fr0 output=cBn start_coordinates=$BE,$BN --overwrite --quiet
echo "NEGATED DEM, start=B, cost at A : $($G r.what map=cBn coordinates=$AE,$AN | cut -d'|' -f4) s  (should equal start=A cost at B)"
$G g.region raster=dem --quiet
