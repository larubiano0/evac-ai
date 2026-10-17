## ADDED Requirements

### Requirement: Household profile with a pace class
The system SHALL store, per household, a home location, a pace class (`normal`, `slow`, `needs_help`), a `can_run` flag, an optional contact and a language (EN or NE). The household pace class SHALL be the slowest member's.

#### Scenario: Create a profile
- **WHEN** a resident submits home location, pace class `slow`, `can_run = false`, phone and language NE, with consent given
- **THEN** the profile is stored with exactly those fields and an id is returned

#### Scenario: Slowest member sets the pace
- **WHEN** a household lists one `normal` adult and one `needs_help` member
- **THEN** the stored household pace class is `needs_help`

### Requirement: Consent and data minimisation
The system SHALL NOT store a profile without explicit consent. It SHALL NOT store medical details, ages or names of household members beyond one contact name. It SHALL let the resident delete the profile at any time.

#### Scenario: No consent
- **WHEN** a profile is submitted without the consent flag
- **THEN** nothing is stored and the request is rejected with a reason

#### Scenario: Delete
- **WHEN** a resident deletes their profile
- **THEN** the profile and any computed leave-by times for it are removed, and it no longer appears on any responder list

### Requirement: Pace classes map to fixed speed factors
Each pace class SHALL map to a documented walking-speed factor applied to the Tobler walking time (`normal` 1.0, `slow` a documented factor < 1.0). `needs_help` SHALL be treated as unable to evacuate alone. Running (2× for the first ~5 minutes) SHALL apply only when `can_run` is true.

#### Scenario: Slow pace takes longer
- **WHEN** the same home and scenario are evaluated at `normal` and at `slow`
- **THEN** the `slow` walk time is longer by the documented factor and its leave-by time is earlier

#### Scenario: Cannot run
- **WHEN** `can_run` is false
- **THEN** no running pace is used anywhere on the route
