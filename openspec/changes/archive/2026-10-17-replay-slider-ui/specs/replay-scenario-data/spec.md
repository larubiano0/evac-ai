## ADDED Requirements

### Requirement: Versioned scenario contract
The system SHALL describe each replay as `viewer/data/<id>/scenario.json` with `"schema": "evac-ai/scenario@1"`. The file contains:
- `crs` (EPSG:32645), `grid`, `t_ref`, `time_range_min`, `burst_min`, `dissemination_min`
- `flood` (`path`, `km_step`, `arrival_min`, `height_m`)
- `warnings`, `settlements`, `bridges`, `events`, `cameras`, `layers`, `headline`, `provenance`

Coordinates MUST be EPSG:32645 metres. Times MUST be minutes after `t_ref` (midnight NPT on the event day).

#### Scenario: Valid scenario loads
- **WHEN** the UI loads a scenario whose `schema` is `evac-ai/scenario@1` and whose required fields are present
- **THEN** the replay renders without errors

#### Scenario: Unknown schema version is rejected
- **WHEN** the UI loads a scenario with a different `schema` value
- **THEN** the UI shows an error naming the expected and received versions and does not render the replay

### Requirement: Synthetic data is labelled
A scenario MUST carry a boolean `synthetic`. When it is true, the UI SHALL show a persistent "ARTIFICIAL DATA" badge. Scenarios baked from `engine/` set it to false, and the UI SHALL show their `provenance` (engine source, host machine and byte order, bake time).

#### Scenario: Artificial scenario shows badge
- **WHEN** a scenario with `synthetic: true` is loaded
- **THEN** an "ARTIFICIAL DATA" badge is visible in both 2D and 3D views at every slider position

#### Scenario: Engine scenario shows provenance
- **WHEN** a scenario with `synthetic: false` is loaded
- **THEN** no artificial badge is shown, and a provenance line names the engine and the host it was computed on

### Requirement: Little-endian uint16 raster layers
The bake SHALL write the following full-resolution layers as explicit little-endian unsigned 16-bit, row-major, north row first, matching `grid.nx × grid.ny`. The value 65535 means no data.

| Layer | Encoding |
|---|---|
| `dem.u16.bin` | `elevation = value · 0.25 m` |
| `hand.u16.bin` | decimetres |
| `riverkm.u16.bin` | units of 10 m |
| `walk.u16.bin` | walking time to safety in units of 0.1 min |

#### Scenario: Bake on a big-endian host
- **WHEN** the bake runs on s390x (big-endian)
- **THEN** the written files are byte-identical to those produced on a little-endian host from the same inputs

#### Scenario: Round-trip check
- **WHEN** the validator decodes `dem.u16.bin`
- **THEN** the minimum and maximum elevations match the values recorded by the bake from the source raster to within 0.25 m

### Requirement: Layers come from the engine
The bake SHALL compute the layers by importing claude-luis's `engine.scenario.Valley` and `engine.scenario.Scenario` for the replay:
- **HAND and river-km**: drainage-following to the event's flood path. Cells not draining to the path get 65535.
- **Walking time**: from the r.walk time to safety.
- **Flood envelope**: early arrival and conservative height per km.

The bake MUST NOT modify files in `engine/`, `pipeline/` or the VM's `~/evac-ai`. GRASS runs against a private copy of the GRASS database.

#### Scenario: Tributary trigger
- **WHEN** the oct11 replay is baked
- **THEN** cells draining to the Syar Khola below the source and to the Budhi Gandaki below the confluence get finite river-km, and cells draining to the Budhi Gandaki above the confluence get 65535

#### Scenario: Footprint matches engine
- **WHEN** the validator counts cells with finite river-km and `HAND ≤ height(km)`, using the quantized layers and the 0.1 km envelope lookup exactly as the shader does
- **THEN** the count is within 1% of the engine's conservative footprint cell count

### Requirement: Settlements match engine slack
For each settlement the engine reports at risk, the bake SHALL write `pop` (people at risk) and `arrival_min` (earliest arrival). It SHALL also write `walk_min` defined as `arrival_after_burst − min over at-risk buildings of (arrival_b − walk_b)`. Then `arrival − (warn + dissemination + walk_min)` equals the engine's settlement `slack_min` for every warning time. Each settlement SHALL have a `route` following the steepest descent of the walking-time raster from its limiting building to safe ground.

#### Scenario: Slack parity
- **WHEN** the validator recomputes each settlement's slack for every warning in the scenario
- **THEN** each value matches the engine's `slack_min` for that warning to within 0.1 min

### Requirement: People units match the engine
The bake SHALL write `units`: one entry per at-risk building, as `[settlement index, arrival_min (absolute), walk_min, people]`. Arrival and walk come from the engine's building arrays (full precision), and people is 4 per building. The settlement's stranded trekkers are added to its limiting building, the one with the minimum `arrival − walk`.

Each settlement SHALL also carry:
- `route_walk_min`: the engine's longest walk, from the building its route starts at
- `route_len_m` and `route_climb_m`
- `engine[warning]`: `people_without_time`, `status` and `slack_min`

#### Scenario: Units reproduce the headline
- **WHEN** the validator sums people over units with `arrival − (warn + dissemination + walk) < 0` for each warning
- **THEN** the sum equals `headline[warning].people_without_time` exactly, and the sum over all units equals `people_at_risk`

### Requirement: Engine headline carried through
The bake SHALL store the engine's summary for each warning (people at risk, people without time) in `headline`.

#### Scenario: Headline shown
- **WHEN** the user selects a warning
- **THEN** the UI shows the engine's "people without time" for that warning next to the live counters
