## ADDED Requirements

### Requirement: Personal leave-by time
For an active flood scenario, the system SHALL compute for each profile in the flood's reach the latest departure time from home that still passes every cell of the route to the closest reachable safe ground (P ≤ UNSAFE_P) before the flood arrives at that cell, at the profile's pace. The leave-by time SHALL be that latest departure minus 10 minutes.

#### Scenario: Plenty of time
- **WHEN** the flood reaches a `normal` household's route in 60 min and the walk takes 15 min
- **THEN** the latest departure is 45 min from now and the leave-by time is 35 min from now

#### Scenario: Recomputed on update
- **WHEN** the scenario's arrival estimate changes
- **THEN** every affected profile's leave-by time is recomputed and a changed time is re-sent

### Requirement: Alert at the leave-by time
The system SHALL send each profile one alert at its leave-by time, in the profile's language. The alert states the leave-by clock time, the direction or route summary, the distance and the safe-ground destination. If the leave-by time has already passed when it is computed, the system SHALL send the alert immediately, worded "leave now" (and "RUN" when only running gets there in time).

#### Scenario: Leave-by time in the future
- **WHEN** the leave-by time is 09:12 and the current time is 08:50
- **THEN** no alert goes out before 09:12, and at 09:12 the alert "leave by 09:12" is sent

#### Scenario: Already late
- **WHEN** the leave-by time is earlier than now
- **THEN** a "leave now" alert is sent immediately

### Requirement: Responders' "cannot make it" list
The system SHALL produce, per scenario, a list for responders of: every `needs_help` household in the flood's reach, and every household whose route cannot reach safe ground before the flood even when leaving now at its pace. Each entry has contact name, location, pace class and minutes until the flood reaches the home. Only authorised responders and the household's nominated neighbours SHALL see it.

#### Scenario: Needs help
- **WHEN** a `needs_help` household lies in the flood's reach
- **THEN** it appears on the responder list with minutes until the flood

#### Scenario: Too late at walking pace
- **WHEN** a `slow` household's closest safe ground cannot be reached before the flood even leaving now
- **THEN** it appears on the responder list, and the household still receives a "leave now" alert with the best reachable ground

### Requirement: Honest about short warning times
When the flood is predicted to reach a profile's route in less time than walk time + 10 minutes, the alert SHALL NOT promise a buffer. It SHALL say how many minutes remain.

#### Scenario: Near the source
- **WHEN** the flood reaches the route 4 min from now and the walk takes 6 min
- **THEN** the alert says leave now, gives the 4 minutes, and the household is on the responder list
