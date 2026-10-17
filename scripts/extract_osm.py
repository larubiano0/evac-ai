"""Extract study-area layers from the Geofabrik Nepal OSM extract.

Run on a laptop (pyosmium has no s390x wheel); the VM only reads the outputs.

Source: Geofabrik Nepal extract, https://download.geofabrik.de/asia/nepal.html
Licence: ODbL, "(c) OpenStreetMap contributors".

Usage: python extract_osm.py data/raw/osm/nepal-YYMMDD.osm.pbf

Outputs (data/processed/osm/)
  districts.geojson   Gorkha, Rasuwa, Nuwakot boundaries
  roads.geojson       highway=* lines incl. tracks, paths, footways, bridges
  waterways.geojson   rivers and streams
  places.geojson      settlements (place=*)
  shelters.geojson    schools, health facilities, shelters, assembly points
  damage.geojson      anything carrying a damage / destroyed / damaged tag
  buildings.csv       building centroids (lon, lat, osm id, damage flag)
plus data/processed/study_area.json (bbox used by every other script).
"""
import csv
import json
import sys
from pathlib import Path

import osmium
from osmium.geom import GeoJSONFactory

from common import DISTRICTS, PROCESSED, log

OUT = PROCESSED / "osm"
PAD = 0.03  # degrees (~3 km) around the districts so edge routes are not cut

ROAD_TAGS = {"highway", "name", "name:en", "name:ne", "ref", "bridge", "bridge:structure",
             "bridge:name", "tunnel", "ford", "layer", "surface", "smoothness", "tracktype",
             "sac_scale", "trail_visibility", "access", "foot", "motor_vehicle", "width",
             "lanes", "oneway", "seasonal", "man_made", "note"}
WATER_TAGS = {"waterway", "name", "name:en", "name:ne", "intermittent"}
PLACE_TAGS = {"place", "name", "name:en", "name:ne", "population", "is_in", "wikidata"}
SHELTER_TAGS = {"amenity", "healthcare", "emergency", "social_facility", "building", "name",
                "name:en", "name:ne", "capacity", "beds", "isced:level", "operator:type"}
DAMAGE_PREFIXES = ("damage", "damaged", "destroyed", "was:", "flood", "landslide", "hazard")
ROAD_HIGHWAYS = {
    "motorway", "trunk", "primary", "secondary", "tertiary", "unclassified", "residential",
    "living_street", "service", "track", "path", "footway", "bridleway", "steps", "cycleway",
    "pedestrian", "road", "motorway_link", "trunk_link", "primary_link", "secondary_link",
    "tertiary_link",
}
PLACES = {"city", "town", "village", "hamlet", "isolated_dwelling", "locality",
          "neighbourhood", "suburb", "farm"}
SHELTER_AMENITY = {"school", "college", "university", "kindergarten", "hospital", "clinic",
                   "doctors", "health_post", "shelter", "community_centre", "townhall",
                   "place_of_worship", "police"}

geo = GeoJSONFactory()


def damage_tags(tags):
    return {t.k: t.v for t in tags if t.k.startswith(DAMAGE_PREFIXES)}


def props(obj, keep):
    p = {t.k: t.v for t in obj.tags if t.k in keep}
    p.update(damage_tags(obj.tags))
    return p


def feature(kind, osm_id, geometry, properties):
    if isinstance(geometry, str):
        geometry = json.loads(geometry)
    return {"type": "Feature", "id": f"{kind}/{osm_id}", "geometry": geometry,
            "properties": properties}


def ring_centroid(geometry):
    ring = geometry["coordinates"][0][0]
    return [sum(c[0] for c in ring) / len(ring), sum(c[1] for c in ring) / len(ring)]


def find_districts(pbf):
    """Pass 1: assemble admin-boundary areas and keep the three study districts."""
    wanted = {d.lower() for d in DISTRICTS}
    found = {}
    fp = osmium.FileProcessor(pbf).with_areas(osmium.filter.TagFilter(("boundary", "administrative")))
    for obj in fp:
        if not obj.is_area() or obj.tags.get("boundary") != "administrative":
            continue
        names = {obj.tags.get(k, "") for k in ("name", "name:en")}
        hit = next((d for d in wanted
                    if any(n.lower() in (d, f"{d} district") for n in names)), None)
        if hit is None:
            continue
        level = obj.tags.get("admin_level", "99")
        prev = found.get(hit)
        # Prefer the lowest admin level (district over ward/municipality).
        if prev and int(prev["properties"]["admin_level"]) <= int(level):
            continue
        try:
            geom = geo.create_multipolygon(obj)
        except RuntimeError:
            continue
        found[hit] = feature("relation" if not obj.from_way() else "way", obj.orig_id(), geom,
                             {"name": hit.title(), "admin_level": level,
                              "osm_name": obj.tags.get("name")})
    missing = wanted - found.keys()
    if missing:
        raise SystemExit(f"district boundaries not found in extract: {sorted(missing)}")
    return list(found.values())


def bounds_of(features):
    xs, ys = [], []
    for f in features:
        for poly in f["geometry"]["coordinates"]:
            for ring in poly:
                xs += [c[0] for c in ring]
                ys += [c[1] for c in ring]
    return {"south": min(ys) - PAD, "west": min(xs) - PAD,
            "north": max(ys) + PAD, "east": max(xs) + PAD}


def main(pbf):
    OUT.mkdir(parents=True, exist_ok=True)
    log("pass 1: district boundaries")
    districts = find_districts(pbf)
    b = bounds_of(districts)
    for d in districts:
        log(f"  {d['properties']['name']}: {d['id']} admin_level={d['properties']['admin_level']}")
    (PROCESSED / "study_area.json").write_text(json.dumps(
        {"districts": [d["properties"]["name"] for d in districts], "pad_deg": PAD, "bbox": b},
        indent=2))
    log(f"  bbox {b}")

    def inside(lon, lat):
        return b["west"] <= lon <= b["east"] and b["south"] <= lat <= b["north"]

    layers = {k: [] for k in ("roads", "waterways", "places", "shelters", "damage")}
    buildings = []

    log("pass 2: features in bbox")
    fp = (osmium.FileProcessor(pbf)
          .with_locations()
          .with_areas()
          .with_filter(osmium.filter.KeyFilter("highway", "waterway", "place", "amenity",
                                               "healthcare", "emergency", "social_facility",
                                               "building", "man_made", "damage",
                                               "damage:event", "destroyed:building",
                                               "damaged:building", "destroyed:highway")))
    for obj in fp:
        tags = obj.tags
        dmg = damage_tags(tags)
        if obj.is_node():
            loc = obj.location
            if not loc.valid() or not inside(loc.lon, loc.lat):
                continue
            point = {"type": "Point", "coordinates": [loc.lon, loc.lat]}
            if tags.get("place") in PLACES:
                layers["places"].append(feature("node", obj.id, point, props(obj, PLACE_TAGS)))
            if (tags.get("amenity") in SHELTER_AMENITY or "healthcare" in tags
                    or tags.get("emergency") == "assembly_point" or "social_facility" in tags):
                layers["shelters"].append(feature("node", obj.id, point, props(obj, SHELTER_TAGS)))
            if dmg:
                layers["damage"].append(feature("node", obj.id, point, dict(t for t in
                                                ((x.k, x.v) for x in tags))))
        elif obj.is_way():
            try:
                lons = [n.lon for n in obj.nodes]
                lats = [n.lat for n in obj.nodes]
            except osmium.InvalidLocationError:
                continue
            if not any(inside(x, y) for x, y in zip(lons, lats)):
                continue
            hw = tags.get("highway")
            is_bridge_area = tags.get("man_made") == "bridge"
            if (hw in ROAD_HIGHWAYS or is_bridge_area) and len(obj.nodes) >= 2:
                f = feature("way", obj.id, geo.create_linestring(obj), props(obj, ROAD_TAGS))
                layers["roads"].append(f)
                if dmg:
                    layers["damage"].append(f)
            elif tags.get("waterway") in {"river", "stream", "canal"} and len(obj.nodes) >= 2:
                layers["waterways"].append(
                    feature("way", obj.id, geo.create_linestring(obj), props(obj, WATER_TAGS)))
            elif dmg and len(obj.nodes) >= 2 and not obj.is_closed():
                # Washed-out roads are often retagged destroyed:highway=* with no highway=*;
                # these are the failure labels, so keep their line geometry.
                layers["damage"].append(feature("way", obj.id, geo.create_linestring(obj),
                                                dict((x.k, x.v) for x in tags)))
        elif obj.is_area():
            try:
                geom = json.loads(geo.create_multipolygon(obj))
            except RuntimeError:  # broken multipolygon in OSM
                continue
            lon, lat = ring_centroid(geom)
            if not inside(lon, lat):
                continue
            kind = "way" if obj.from_way() else "relation"
            point = {"type": "Point", "coordinates": [lon, lat]}
            # Destroyed buildings are retagged destroyed:building=* with no building=*.
            if "building" in tags or "destroyed:building" in tags:
                buildings.append((round(lon, 6), round(lat, 6), f"{kind}/{obj.orig_id()}",
                                  tags.get("building") or tags.get("destroyed:building"),
                                  dmg.get("damage:event", ""),
                                  "destroyed" if any(k.startswith("destroyed") for k in dmg)
                                  else "damaged" if dmg else ""))
            if (tags.get("amenity") in SHELTER_AMENITY or "healthcare" in tags
                    or tags.get("emergency") == "assembly_point" or "social_facility" in tags):
                layers["shelters"].append(feature(kind, obj.orig_id(), point,
                                                  props(obj, SHELTER_TAGS)))
            if tags.get("place") in PLACES:
                layers["places"].append(feature(kind, obj.orig_id(), point,
                                                props(obj, PLACE_TAGS)))
            if dmg:
                layers["damage"].append(feature(kind, obj.orig_id(), point,
                                                dict((x.k, x.v) for x in tags)))

    def write_geojson(name, feats):
        path = OUT / f"{name}.geojson"
        path.write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                   separators=(",", ":"), ensure_ascii=False))
        log(f"  {path.name}: {len(feats)} features, {path.stat().st_size / 1e6:.1f} MB")

    write_geojson("districts", districts)
    for name, feats in layers.items():
        # Dedupe: a damaged road is appended to both roads and damage; areas can repeat.
        seen, uniq = set(), []
        for f in feats:
            if f["id"] not in seen:
                seen.add(f["id"])
                uniq.append(f)
        write_geojson(name, uniq)

    path = OUT / "buildings.csv"
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["lon", "lat", "osm_id", "building", "damage_event", "damage"])
        w.writerows(buildings)
    log(f"  {path.name}: {len(buildings)} rows, {path.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    main(str(Path(sys.argv[1]).resolve()))
