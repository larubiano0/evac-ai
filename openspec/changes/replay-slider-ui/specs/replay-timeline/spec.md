## ADDED Requirements

### Requirement: Replay slider
The UI SHALL provide a full-width time slider spanning `scenario.time_range_min`, with a readout of the current time in Nepal time (`HH:MM NPT`). Moving the slider SHALL update the flood, markers, routes and counters in the same frame.

#### Scenario: Scrub updates everything
- **WHEN** the user drags the slider from 03:00 to 06:30
- **THEN** the readout shows 06:30 NPT, and the flood, settlement states and counters reflect t = 06:30 without a perceptible lag

### Requirement: Playback
The UI SHALL provide play/pause and at least three speeds. Each speed is expressed as simulated minutes per real second (default options 1, 4 and 16). Playback SHALL stop at the end of the time range.

#### Scenario: Play to end
- **WHEN** the user presses play at 16 sim-min/s
- **THEN** the slider advances continuously and pauses at `time_range_min[1]`

### Requirement: Event ticks
The slider SHALL show a tick and a short label for each `scenario.events` entry and for each warning time. Clicking a tick SHALL set the slider time to that event.

#### Scenario: Jump to official SMS
- **WHEN** the user clicks the "Official SMS" tick
- **THEN** the slider moves to `warnings.official.t_min`

### Requirement: Settlement state machine
State SHALL be evaluated per *people unit*: one per at-risk building, with the engine's 4 people per building, plus stranded trekkers attached to the settlement's limiting building. Each unit's state is a pure function of `t`, the selected warning time `warn_t`, `dissemination_min`, and the unit's own `arrival_min` and `walk_min`. Let `go = warn_t + dissemination_min` (when people start moving) and `done = go + walk_min`. The unit is:
- **caught** if `arrival_min < done` and `t ≥ arrival_min`
- otherwise **unaware** if `t < go`
- otherwise **walking** if `t < done`
- otherwise **safe**

A settlement marker shows the state holding the most people; ties go to the more severe state. Bridge timing is not part of the state machine, because the engine does not model it (the bake found 0 divergent cases). Bridges are shown as warnings instead (replay-ux).

#### Scenario: Reaches safety
- **WHEN** warn_t = 03:30, dissemination = 5, walk_min = 10 and arrival = 05:10
- **THEN** the settlement is unaware before 03:35, walking from 03:35 to 03:45, and safe from 03:45 onward

#### Scenario: Caught
- **WHEN** warn_t = 06:40, dissemination = 5, walk_min = 10 and arrival = 06:30
- **THEN** the settlement is unaware before 06:30, becomes caught at 06:30, and stays caught for all later t

### Requirement: Walking routes animate
The route is the engine's escape route from the settlement's longest-walk building, with walking time `route_walk_min`. Between `go` and `go + route_walk_min`, the route SHALL be drawn up to the fraction `(t − go) / route_walk_min` of its length, with a moving dot at the head. Once complete, the full route stays drawn.

#### Scenario: Halfway
- **WHEN** t is halfway between go and go + route_walk_min
- **THEN** half of the route is drawn and the dot sits at its midpoint

### Requirement: Warning scenario selection
The UI SHALL let the user choose among the entries in `scenario.warnings`. For oct11 these are the four replay triggers: community relay 03:30, police informed 05:30, NDRRMA informed 06:20 and official SMS 06:40. Changing the choice SHALL recompute all settlement states and counters immediately, at the current t.

#### Scenario: Compare warnings
- **WHEN** the user switches from "community relay" (03:30) to "official SMS" (06:40) at t = 08:00
- **THEN** the "safe" counter decreases and the "caught" counter increases, without moving the slider

### Requirement: Live counters
The UI SHALL show the people in each state at the current t, summed over people units: safe, on the move, not warned yet, and caught.

#### Scenario: Counters sum to total
- **WHEN** the slider is at any time t
- **THEN** the counters sum to the total population of all settlements in the scenario

#### Scenario: End of replay equals engine
- **WHEN** the slider is at the end of the range
- **THEN** for every warning, the caught counter equals `headline[warning].people_without_time`
