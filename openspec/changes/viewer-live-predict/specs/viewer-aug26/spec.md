## ADDED Requirements

### Requirement: Aug 26 replay bundle (stretch)
If the engine can produce settlements for the Trishuli valley, the bake SHALL produce `viewer/data/aug26/` from `data/proc_trishuli` and `replay/aug26.json`. Observations outside the terrain grid (Kali Khola, Devghat) SHALL be excluded from calibration, and the exclusion SHALL be listed in `provenance`.

#### Scenario: Bundle validates
- **WHEN** `validate.py viewer/data/aug26` runs
- **THEN** it passes the same checks as `oct11` (schema, little-endian round-trip, footprint within 1 %, slack parity within 0.1 min)

#### Scenario: Switch replays
- **WHEN** the user opens `?scenario=aug26`
- **THEN** the Bhotekoshi–Trishuli corridor loads, with its warning ticks (seismic 08:37, DHM 09:00, SMS 09:15)

#### Scenario: Not feasible
- **WHEN** the engine cannot produce Trishuli settlements within the 1 h time box
- **THEN** no `aug26` bundle is shipped, and `viewer/README.md` states that only Oct 11 is available and why
