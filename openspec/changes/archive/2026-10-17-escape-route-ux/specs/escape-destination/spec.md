## ADDED Requirements

### Requirement: Destination is the closest safe place
The escape search SHALL choose as its destination the closest cell, by walking time, with P(destroyed) ≤ `UNSAFE_P`. The risk ladder τ SHALL control only which risky cells may be entered after the flood arrives. It SHALL NOT be used to accept a destination above `UNSAFE_P` while any safe cell is reachable at some ladder level. Only when no safe cell is reachable at any level SHALL the destination be the least risky reachable ground (`destination_safe` false).

#### Scenario: Safe ground beyond a risky first cell
- **WHEN** the first cell reachable with P(destroyed) ≤ 0.15 has P(destroyed) 0.15, and a cell with P(destroyed) 0.04 is reachable further on
- **THEN** the destination is the closest reachable cell with P(destroyed) ≤ 0.10 and `destination_safe` is true

#### Scenario: Closest, not safest
- **WHEN** two safe cells are reachable, one at 0.08 and 4 min away and one at 0.00 and 9 min away
- **THEN** the destination is the 0.08 cell 4 min away

#### Scenario: No safe ground reachable
- **WHEN** no cell with P(destroyed) ≤ `UNSAFE_P` is reachable at any ladder level
- **THEN** the destination is the least risky reachable ground and `destination_safe` is false

#### Scenario: Same input, same answer
- **WHEN** the same scenario is queried twice with the same lon, lat and minutes_after_start
- **THEN** both responses have identical `path`, `destination` and `safe_zone`

### Requirement: Urgency says WALK, HURRY or RUN
Every response with a route SHALL include `urgency`, computed from the tightest margin `m` (flood arrival minus your arrival, over risky points on the path and your own spot):
- `"run"` when `m` < `RUN_MIN` (3 min), when the flood reaches a risky point before you do, or when the flood is already at your spot;
- `"hurry"` when `RUN_MIN` ≤ `m` < `HURRY_MIN` (10 min);
- `"walk"` otherwise.

The `headline` SHALL start with RUN, Hurry or Leave now accordingly. `no_route` answers SHALL have urgency `"run"`.

#### Scenario: Plenty of time
- **WHEN** the tightest margin is 25 min
- **THEN** `urgency` is `"walk"` and the headline starts with "Leave now"

#### Scenario: Little time
- **WHEN** the tightest margin is 2 min
- **THEN** `urgency` is `"run"` and the headline starts with "RUN"

#### Scenario: Flood already here
- **WHEN** the flood has already reached your spot
- **THEN** `urgency` is `"run"`

### Requirement: Response states whether the destination is safe
Every route response (`status` `route` or `no_route` with a path) SHALL include `destination_safe`: true when the destination's P(destroyed) ≤ `UNSAFE_P`, false otherwise.

#### Scenario: Safe destination
- **WHEN** the destination's P(destroyed) is 0.04
- **THEN** `destination_safe` is true

#### Scenario: Best-effort destination
- **WHEN** the destination's P(destroyed) is 0.15
- **THEN** `destination_safe` is false

### Requirement: Safe zone agrees with the destination
The `safe_zone` polygon SHALL be built from ground connected to the destination with P(destroyed) ≤ `UNSAFE_P` when `destination_safe` is true, and ≤ the destination's P(destroyed) + 0.01 otherwise. `safe_zone.max_risk` SHALL report the threshold used.

#### Scenario: Safe zone never includes unsafe ground
- **WHEN** `destination_safe` is true
- **THEN** `safe_zone.max_risk` ≤ `UNSAFE_P`

#### Scenario: Least-risky zone is labelled by its threshold
- **WHEN** `destination_safe` is false and the destination's P(destroyed) is 0.15
- **THEN** `safe_zone.max_risk` is 0.16

### Requirement: One hazard per route
Every route response SHALL include `hazard`, which is either null or one path point other than the destination, with `kind`:
- `"flooded"`: the riskiest point with P(destroyed) > `UNSAFE_P` reached at or after flood arrival, when there is one;
- otherwise `"race"`: the point with P(destroyed) > `UNSAFE_P` and the smallest margin (flood arrival − your arrival), with `pass_before_min` = flood arrival − minutes_after_start.

`unsafe_points` SHALL remain in the response.

#### Scenario: Race against the flood
- **WHEN** the path crosses one point with P(destroyed) 0.4 that the flood reaches 14 min from now, and you reach it 9 min from now
- **THEN** `hazard.kind` is `"race"` and `hazard.pass_before_min` is 14

#### Scenario: Clear path
- **WHEN** no point before the destination has P(destroyed) > `UNSAFE_P`
- **THEN** `hazard` is null

### Requirement: Time-aware destination choice (addendum)
The search SHALL only pass a cell with P(destroyed) > `UNSAFE_P` if you reach it before the flood (arrival grid), anywhere on the route. Running pace SHALL be 2 × walking speed for the first 5 minutes of the trip, then walking. The destination SHALL be:
- (a) the closest safe ground reachable walking, if any;
- (b) otherwise the closest safe ground reachable at the running pace, with `urgency` `"run"`;
- (c) otherwise the lowest-P cell reachable before the flood at the running pace (ties: sooner arrival), with `urgency` `"run"` and `destination_safe` false.

With `can_run` false, only the walking pace SHALL be used. When the running pace was used, the response SHALL include `walk_only` and the card SHALL say it assumes you can run for about 5 minutes. This requirement supersedes the risk-ladder wording in "Destination is the closest safe place".

#### Scenario: Walking is enough
- **WHEN** safe ground is reachable walking before the flood along the route
- **THEN** the destination is the closest such ground, `pace` is `"walk"`, and urgency follows the margin

#### Scenario: Only running gets there in time
- **WHEN** no safe ground is reachable walking before the flood, but some is at the running pace
- **THEN** the destination is the closest safe ground at the running pace, `pace` is `"run"`, `urgency` is `"run"`, and `walk_only` holds the walking answer

#### Scenario: No safe ground in time
- **WHEN** no safe ground is reachable before the flood even running
- **THEN** the destination is the lowest-P cell reachable before the flood, `destination_safe` is false and `urgency` is `"run"`

#### Scenario: Running is capped at 5 minutes
- **WHEN** a trip takes 142.6 min walking on flat trail
- **THEN** at the running pace it takes 5 + (142.6 − 10) = 137.6 min

#### Scenario: The 128-minute climb is gone
- **WHEN** the user clicks 84.93884, 28.46081 (Budhi, oct11, t = 0, flood 2 min away)
- **THEN** the answer is never a route that reaches risky cells after the flood; it is the safest ground reachable in time
