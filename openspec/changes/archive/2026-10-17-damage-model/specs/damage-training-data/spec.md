## ADDED Requirements

### Requirement: Rows are buildings and bridges in the flood corridor
The training table SHALL contain one row per OSM building and per bridge whose location drains into the Aug 26 flood path (`Terrain.hand_to(path)` gives `drain_idx >= 0`) and lies within 500 m (straight line) of a path cell. Each row SHALL carry a `kind` value (`building` or `bridge`) and the OSM id.

#### Scenario: Building near the main river is included
- **WHEN** a building centroid drains into the Bhotekoshi–Trishuli path and is 120 m from the nearest path cell
- **THEN** it appears in the table with `kind = building`

#### Scenario: Building outside the corridor is excluded
- **WHEN** a building is 900 m from the path, or its cell drains into a channel that is not on the path
- **THEN** it does not appear in the 500 m table

#### Scenario: Wider table for comparison
- **WHEN** the table is built with `max_dist_m = 2000`
- **THEN** it contains every row of the 500 m table plus the rows between 500 m and 2 km

### Requirement: Labels come from Aug 26 OSM damage tags
A building row SHALL be labelled 1 when its `damage_event` is `2026NepalFlood` (`destroyed` or `damaged`), and 0 when `damage_event` is empty. Buildings tagged with any other event SHALL be excluded. A bridge row SHALL be labelled 1 when it is a `destroyed:bridge` feature with `damage:event=2026NepalFlood`, and 0 when it is a `bridge=*` way in `roads.geojson`. The table SHALL also store a `destroyed_only` label for the sensitivity check.

#### Scenario: Damaged building counts as affected
- **WHEN** a building has `damage_event = 2026NepalFlood` and `damage = damaged`
- **THEN** its label is 1 and its `destroyed_only` label is 0

#### Scenario: 2015 earthquake damage is excluded
- **WHEN** a building has `damage_event = nepal_earthquake_2015`
- **THEN** it is not in the table

### Requirement: Terrain features are computed per row
Each row SHALL have the features `hand`, `river_km`, `dist_channel_m`, `slope_deg`, `valley_width_m`, `channel_slope`, `bend_curv`, `outside_bend`, `log_acc`, `ls_500m` and `kind`, computed from the engine's `Terrain` for the event's path and from `data/processed/landslides_2015.csv`. The table SHALL NOT include building footprint size, absolute elevation, or coordinates as features.

#### Scenario: Feature vector is complete
- **WHEN** the table is built for the Trishuli path
- **THEN** every row has a finite value for each listed feature, or the row is dropped and counted in a build report

#### Scenario: River km increases downstream
- **WHEN** two rows drain into path cells A and B, with B downstream of A
- **THEN** `river_km` of the B row is greater than that of the A row

### Requirement: Freeboard feature for v2
When a flood envelope is supplied, each row SHALL also have `freeboard = hand − envelope.height(river_km)`. Because `replay/aug26.json` has no usable height knot inside the Trishuli grid, the Aug 26 envelope SHALL be reconstructed from damage marks: the 90th percentile of affected-building HAND per 5 km river-km bin (≥ 30 positives), loaded into `engine.flood.FloodEnvelope`. In the spatial holdout, the knots SHALL be fitted on the training side only. The knots SHALL be saved to `models/damage/aug26_damage_envelope.json`.

#### Scenario: Building above the flood line
- **WHEN** a row has `hand = 40` and the envelope height at its river km is 25 m
- **THEN** its `freeboard` is 15

#### Scenario: No envelope supplied
- **WHEN** features are built without an envelope
- **THEN** the table has no `freeboard` column and v1 can still be trained

### Requirement: Build report
Building the table SHALL write a report with row counts by kind and label, rows dropped and why, and the river-km range of the positives.

#### Scenario: Report after build
- **WHEN** the table build finishes
- **THEN** a JSON report exists with counts per (kind, label) and dropped-row counts
