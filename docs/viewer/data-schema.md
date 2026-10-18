# Scenario bundle: `evac-ai/scenario@1`

A bundle is a directory `viewer/data/<id>/` containing `scenario.json` and four raster layers.

## Conventions

- **Coordinates**: EPSG:32645 (UTM 45N) metres.
- **Times**: minutes after `t_ref`, which is midnight NPT (UTC+05:45) on the event day. `HH:MM NPT = t_ref + t`.
- **Rasters**: `grid.nx × grid.ny` values of **little-endian uint16**, row-major, **north row first**. Cell `(row r, col c)` has its centre at `x = x_left + (c + 0.5)·dx` and `y = y_top − (r + 0.5)·dx`. **65535 = no data.**

| File | Value | Meaning of 65535 |
|---|---|---|
| `dem.u16.bin` | elevation = v × 0.25 m | no data |
| `hand.u16.bin` | HAND to the flood path = v × 0.1 m (negative clamped to 0) | cell does not drain to the flood path |
| `riverkm.u16.bin` | river-km of the path cell it drains to = v × 0.01 km | cell does not drain to the flood path |
| `walk.u16.bin` | walking time to safe ground = v × 0.1 min (capped at 65534) | no data |

## `scenario.json`

| Field | Type | Meaning |
|---|---|---|
| `schema` | `"evac-ai/scenario@1"` | the viewer refuses anything else |
| `id`, `title` | string | |
| `synthetic` | bool | true → the viewer shows an ARTIFICIAL DATA badge |
| `crs` | `"EPSG:32645"` | |
| `grid` | object | `x_left`, `y_top`, `dx`, `nx`, `ny`, `dem_min`, `dem_max` (m, from the source raster, for the round-trip check) |
| `t_ref` | ISO string | midnight NPT, e.g. `"2026-10-11T00:00:00+05:45"` |
| `time_range_min` | `[start, end]` | slider range |
| `burst_min` | number | flood starts at the source |
| `dissemination_min` | number | minutes from the warning being issued to people starting to move |
| `flood.km_step` | number | spacing of the lookup arrays (km) |
| `flood.arrival_min` | number[] | early first-wave arrival, **minutes after `burst_min`**, at `i·km_step` |
| `flood.height_m` | number[] | conservative flood height above the channel (m) at `i·km_step` |
| `flood.path` | `[x, y, km][]` | flood channel polyline, downstream order |
| `warnings` | `{id: {label, desc, t_min}}` | selectable warning times |
| `default_warning` | string | id of the warning selected on load |
| `settlements[]` | object | see below |
| `units` | `[settlement index, arrival_min, walk_min, people][]` | one *people unit* per at-risk building (engine: 4 people per building; stranded trekkers added to the settlement's limiting building). Arrival and walk at full precision. Counters and the state machine run on these |
| `bridges[]` | object | `id`, `label`, `x`, `y`, `river_km`, `arrival_min` (absolute) |
| `events[]` | object | `t_min`, `label`, `kind` (`warning`, `burst`, `impact`); timeline ticks |
| `cameras[]` | object | `id`, `label`, `x`, `y`, `z` (target elevation m), `dist_m`, `az_deg` (camera direction from target, clockwise from north), `polar_deg` (from vertical) |
| `layers` | string[] | heat fields available: `slack`, `arrival`, `walk`, `hand` |
| `headline` | `{warning_id: {people_at_risk, people_without_time, settlements_at_risk, red, amber}}` | engine summary per warning |
| `checks` | object | `footprint_cells_engine`, `footprint_cells_baked` |
| `provenance` | object | `engine`, `machine`, `byteorder`, `node`, `baked_at`, `bake_s` |

### Settlement

| Field | Meaning |
|---|---|
| `id`, `name`, `name_ne` | |
| `x`, `y` | OSM place node |
| `pop` | people at risk (engine: at-risk buildings × 4, plus stranded trekkers) |
| `river_km` | median river-km of its at-risk buildings |
| `arrival_min` | absolute time of the earliest first-wave arrival at its at-risk buildings |
| `walk_min` | effective walking time: `arrival_after_burst − min over buildings of (arrival_b − walk_b)` |
| `engine_slack` | `{warning_id: slack_min}` from the engine; the parity check requires `arrival_min − (warn + dissemination_min + walk_min) == engine_slack[w]` |
| `route` | `[x, y][]` escape route to safe ground: the engine's r.walk route (from the settlement's longest-walk building); for older engines, steepest descent of the walking time from the limiting building |
| `bridge` | `null` or `{id, frac}`: an at-risk bridge on the route, and the fraction of the route at which it is crossed |
| `buildings` | number of at-risk buildings |
| `route_walk_min`, `route_len_m`, `route_climb_m` | the engine's escape route: walking time from its start building (the settlement's longest walk), length, climb |
| `engine` | `{warning_id: {people_without_time, status, slack_min}}` straight from the engine; the forecast badge uses it |

## State machine (viewer)

Evaluated per people unit `[i, arrival, walk, people]`. Let `go = warn + dissemination_min` and `done = go + walk`:

- if `arrival < done` and `t ≥ arrival` → **caught**
- otherwise: `t < go` → **unaware**; `t < done` → **walking**; else → **safe**

At the end of the replay the people caught equal `headline[warning].people_without_time` exactly (checked by `validate.py`).
A settlement marker shows the state holding the most people (ties → the more severe state), and from the warning time a
forecast badge from `engine[warning]`: some people can't make it (`people_without_time > 0`), under 15 min to spare, or fine.
Bridges are not part of the state machine (the engine does not model bridge timing); they show *Don't cross* from the
warning until the flood arrives, then *Flooded*.
