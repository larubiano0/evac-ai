# Flood damage labels: OSM `damage:event=2026NepalFlood`

**File:** `data/processed/osm/damage.geojson` (plus the `damage_event` / `damage` columns of `buildings.csv`)
**Script:** `scripts/extract_osm.py`

## What it is

After the 26 August 2026 debris flood, HOT and OSM volunteers traced damage from post-event Vantor
satellite imagery (35–72 cm/pixel) and tagged it in OpenStreetMap following the OSM
[Nepal Floods 2026](https://wiki.openstreetmap.org/wiki/Organised_Editing/Activities/Nepal_Floods_2026)
guidelines. **These are our only ground-truth labels for which roads and bridges failed.** The risk
model is trained and evaluated on them.

## How the tagging works (important when reading the data)

OSM uses *lifecycle prefixes*. A road that was washed away is not left as `highway=primary`. The mapper
**renames the key**, so it becomes `destroyed:highway=primary` and there is no `highway` tag at all.
The same goes for `destroyed:building`, `destroyed:bridge`, and so on. Partly damaged features keep their
normal tag and get `damaged:building=yes` or similar. Every feature from this event also carries
`damage:event=2026NepalFlood`.

As a result, a naive `highway=*` filter **misses the destroyed roads**. That is why destroyed roads appear
only in `damage.geojson`, not in `roads.geojson`.

## Contents

10,833 features in total: 380 LineStrings (roads, bridges, channels) and 10,453 Points (areas reduced
to centroids, plus nodes).

By event: `2026NepalFlood` 4,005 · `nepal_earthquake_2015` 6,573 · untagged event 245 ·
Kyirong (Tibet) debris flows 10.

### 2026 flood: roads and bridges (the training labels)

| Tag | Line features |
|---|---|
| `destroyed:highway=*` | 238 (298 features carry the tag in total) |
| `destroyed:bridge=*` | 58 lines (63 in total) |
| still `highway=*`, tagged with the event | 18, e.g. the Devighat–Tadi bridge (check each one: damaged, or the rebuilt replacement?) |
| `destroyed:waterway`, `destroyed:tunnel`, `destroyed:barrier` | 11 |

That gives about **314 road or bridge segments that failed in August**. The positive class is small
next to 57,000 road ways. Present results as a ranking ("flagged X of the Y segments that failed"),
not as accuracy.

### 2026 flood: other tags

`destroyed:building` 2,759 · `damaged:building` 415 · `destroyed:natural` 50 · `destroyed:landuse` 28 ·
`destroyed:tourism` 24 · `destroyed:amenity` 23 · `destroyed:power` 13 · `destroyed:man_made` 7.
Optional detail tags: `damage:type` (`flood` 170, `landslide` 127) and `damage:date` (`2026-08-26`, 177).

### Where

All 2026 flood labels lie within 27.80–28.34° N, 84.89–85.49° E: the Trishuli / Bhote Koshi corridor
through Rasuwa and Nuwakot. **There are no labels in Gorkha** (the October Budhi Gandaki event),
which suits the plan: train on the Trishuli corridor and run the October scenario on Gorkha.

## How to use it

```python
import json
feats = json.load(open("data/processed/osm/damage.geojson"))["features"]
failed_roads = [f for f in feats
                if f["properties"].get("damage:event") == "2026NepalFlood"
                and f["geometry"]["type"] == "LineString"
                and any(k in f["properties"] for k in
                        ("destroyed:highway", "destroyed:bridge", "highway"))]
```

To label graph edges, snap each failed line onto `roads.geojson` edges, either by shared OSM node
positions or by buffer overlap of about 20 m. A destroyed way usually lies where its former `highway`
way was, and the surviving neighbour segments still join it.

For the **spatial holdout**, split the corridor north–south (for example Rasuwa above Dhunche versus
Nuwakot below Betrawati) so train and test segments are not neighbours.

## Caveats

- **Mapped from imagery, not on the ground.** Cloud cover, narrow gorges and tree cover hide damage.
  Missing labels are not proof a road survived.
- **One event, volunteer effort.** Coverage is densest where mappers worked first.
- `nepal_earthquake_2015` labels are a different hazard; keep them out of the flood training set (or
  use them as a separate feature).

## Licence

© OpenStreetMap contributors, ODbL 1.0. Imagery credit for the underlying tracing: Vantor via
OpenAerialMap, CC BY-NC.
