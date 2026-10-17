# OpenStreetMap layers

**Files:** `data/processed/osm/*.geojson`, `data/processed/osm/buildings.csv`, `data/processed/study_area.json`
**Script:** `scripts/extract_osm.py` (laptop only: pyosmium has no s390x wheel)
**Source snapshot:** Geofabrik Nepal extract, 16 Oct 2026 (`nepal-261016.osm.pbf`)

## What it is

OpenStreetMap is the volunteer-built map of the world. In Nepal it is the most complete public source
for village roads, foot trails and suspension bridges, much of it mapped by Kathmandu Living Labs and
the Humanitarian OpenStreetMap Team (HOT) after the 2015 earthquake. HOT also mapped the 2026 flood
damage from post-event imagery. That work is covered separately in [osm_damage_labels.md](osm_damage_labels.md).

We pulled from the Geofabrik country extract rather than the Overpass API. Overpass was overloaded on
event day, and the extract is a fixed snapshot, so results are reproducible.

## Study area

`study_area.json` holds the bounding box of the Gorkha, Rasuwa and Nuwakot district boundaries
(OSM relations 4588150, 4583252, 4583250) plus a 0.03° (~3 km) pad:
**27.73–28.78° N, 84.39–85.83° E**. Every other script, including the DEM and population crops,
reads this file.

The box is a rectangle, so it includes parts of Dhading, Lamjung, Sindhupalchok, the northern
Kathmandu valley, and a strip of Tibet (Kyirong). That is useful for evacuation routes that leave the
districts. Clip to `districts.geojson` when you need district totals.

All coordinates are WGS84 lon/lat. Each feature `id` is `way/<osm id>`, `node/<osm id>` or
`relation/<osm id>`, so you can look it up at `https://www.openstreetmap.org/<id>`.

## Layers

### `districts.geojson`: 3 MultiPolygons, 0.2 MB
Properties: `name` (Gorkha / Rasuwa / Nuwakot), `admin_level` (6), `osm_name`.

### `roads.geojson`: 57,009 LineStrings, 45 MB
**This is the network graph's raw material.** Every `highway=*` way, plus `man_made=bridge` outlines.

| `highway` | Count | Meaning here |
|---|---|---|
| `path` | 28,399 | Foot trails: most of the network, and how most people move |
| `unclassified` | 8,255 | Minor rural roads, often dirt |
| `track` | 7,939 | Farm / jeep tracks, seasonal |
| `residential` | 7,247 | Village and town streets |
| `footway`, `steps` | 1,859 | Paved paths, stone stairways |
| `service` | 1,600 | Access roads |
| `tertiary` / `secondary` / `primary` / `trunk` | 844 / 354 / 96 / 234 | Highways (Prithvi, Pasang Lhamu, etc.) |

Kept tags: `highway`, `name`, `name:en`, `name:ne`, `ref`, `bridge`, `bridge:structure`, `bridge:name`,
`tunnel`, `ford`, `layer`, `surface`, `smoothness`, `tracktype`, `sac_scale` (hiking difficulty, 333
ways), `trail_visibility`, `access`, `foot`, `motor_vehicle`, `width`, `lanes`, `oneway`, `seasonal`,
`man_made`, `note`, plus any damage tags.

**Bridges:** 1,318 ways have `bridge=*` (1,315 `yes`). Only 92 are tagged as suspension bridges
(`bridge=suspension` or `bridge:structure=suspension`); many more exist in reality. Treat
`bridge=yes` on a `path` over a river as a likely suspension bridge.

Ways are full OSM ways, not split at junctions. When building the graph, split each line at nodes
shared with other ways.

### `waterways.geojson`: 4,927 LineStrings, 5 MB
`waterway` = `stream` (4,468), `river` (360), `canal` (99). Properties: `waterway`, `name`, `name:en`,
`name:ne`, `intermittent`. Includes Budhi Gandaki, Trishuli, Bhote Koshi, Ankhu Khola, Daraudi Khola.
Name spellings vary ("Ankhu Khola" / "Ankhu Khloa" / "Ankhu River"), so match fuzzily.

Used for: river-crossing flags, distance and height above the river (with the DEM), and seeding the
landslide-dam lake.

### `places.geojson`: 2,452 Points, 0.4 MB
Settlements: `village` 1,064, `hamlet` 892, `locality` 178, `suburb` 132, `neighbourhood` 79,
`isolated_dwelling` 73, `town` 21, `farm` 12, `city` 1. 1,160 have a `name`. Only 9 have a
`population` tag, so take population from WorldPop instead (see [population.md](population.md)).

These are the **origins** for evacuation, and the names used to geocode text reports
("bridge at Arughat is gone").

### `shelters.geojson`: 4,270 Points, 0.9 MB
Candidate **destinations**. No official shelter dataset is public, so these are stand-ins:
`school` 2,704, `place_of_worship` 739, `clinic` 141, `hospital` 125, `community_centre` 83,
`shelter` 82, `college` 78, `police` 70, `pharmacy` 64, `kindergarten` 53, and others.
Area features (school compounds, etc.) are reduced to a centroid point.
**None have a `capacity` tag**, so estimate capacity from type or footprint.

Note that `amenity=shelter` in OSM is usually a trail-side rest hut, not a disaster shelter.

### `buildings.csv`: 625,045 rows, 26 MB
One row per building footprint (centroid only, to keep the file small).

| Column | Meaning |
|---|---|
| `lon`, `lat` | Centroid |
| `osm_id` | `way/…` or `relation/…` |
| `building` | Building type (`yes`, `house`, …); for destroyed ones, the value of `destroyed:building` |
| `damage_event` | `2026NepalFlood`, `nepal_earthquake_2015`, … or empty |
| `damage` | `destroyed`, `damaged`, or empty |

Damage counts: 2,759 destroyed and 346 damaged in the 2026 flood; 200 damaged in 2015; 142 others.
Used for: population disaggregation, flood-exposure counts ("the lake would reach N houses"), and
evaluation.

### `damage.geojson`: 10,833 features, 2.5 MB
Everything with a `damage*`, `damaged*` or `destroyed*` tag, with **all** its OSM tags. See
[osm_damage_labels.md](osm_damage_labels.md).

## Caveats

- **Trail coverage is uneven.** Areas mapped heavily after 2015 (Gorkha, Rasuwa, Nuwakot) are good;
  remote high valleys are thinner. A missing trail is not proof there is no trail.
- **A snapshot from 16 Oct 2026.** Roads destroyed on 11 Oct (Budhi Gandaki) may not be mapped yet.
  The scenario replay injects those as crowd reports, which is the point of the system.
- Volunteer data: tag usage varies by mapper.

## Licence

© OpenStreetMap contributors, Open Database License (ODbL) 1.0, <https://www.openstreetmap.org/copyright>.
Attribution is required on the map UI and in the submission.
