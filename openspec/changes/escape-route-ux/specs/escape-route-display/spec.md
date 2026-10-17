## ADDED Requirements

### Requirement: Main route is one continuous line in one colour
The prediction page SHALL draw the main route as a single continuous line in one style: a white line over a dark casing, with an animated direction of travel. That colour SHALL NOT be in the risk palette or the flood-path colour. The route SHALL NOT change colour along its length.

#### Scenario: Route crossing a risky point
- **WHEN** the response path contains points with `unsafe: true`
- **THEN** the route is still drawn as one white, outlined line, with no red or green pieces

#### Scenario: Reduced motion
- **WHEN** the browser reports `prefers-reduced-motion: reduce`
- **THEN** the direction of travel is shown without animation

### Requirement: Destination has one label that matches its zone
The page SHALL mark the destination with one pin and one label:
- "Safe ground" with a green zone when `destination_safe` is true;
- "Best ground you can reach · N% risk" with an amber zone when it is false.

No separate unsafe dot SHALL be drawn at the destination.

#### Scenario: Safe destination
- **WHEN** `destination_safe` is true
- **THEN** the pin reads "Safe ground" and the zone is green

#### Scenario: Best-effort destination
- **WHEN** `destination_safe` is false and the destination's P(destroyed) is 0.15
- **THEN** the pin reads "Best ground you can reach · 15% risk", the zone is amber, and no red dot is drawn at the pin

### Requirement: At most one hazard marker
The page SHALL draw at most one hazard marker, from `hazard`, with a permanent short instruction:
- "Pass before N min" for `race`;
- "May already be flooded (N%)" for `flooded`.

Individual unsafe points SHALL NOT be drawn as dots.

#### Scenario: Race hazard
- **WHEN** `hazard` is `{kind: "race", pass_before_min: 14}`
- **THEN** one ⚠ marker labelled "Pass before 14 min" is drawn at that point

#### Scenario: No hazard
- **WHEN** `hazard` is null
- **THEN** no hazard marker is drawn

### Requirement: Banner leads with the urgency word
The result card banner SHALL start with the urgency word as its largest text: "WALK", "HURRY" or "RUN". It is followed by the walk time to safe ground and the time to spare. RUN SHALL use the danger style.

#### Scenario: RUN answer
- **WHEN** `urgency` is `"run"`
- **THEN** the banner's first line reads "RUN" in the danger style, followed by the walk time

#### Scenario: WALK answer
- **WHEN** `urgency` is `"walk"`
- **THEN** the banner's first line reads "WALK" and shows the time to spare

### Requirement: Backup route is opt-in
The page SHALL NOT draw the backup route by default. When a backup exists, the result card SHALL offer "Show another way (N min)". Turning it on draws the backup as a thin grey dashed line, with no destination or hazard markers.

#### Scenario: Default view
- **WHEN** a route answer with a backup is shown
- **THEN** only the main route is on the map and the card shows the toggle

### Requirement: Camera stays put when the answer is visible
After an answer, the map SHALL only pan or zoom if the route and destination are not fully inside the current view (or the zoom is below 13). Changing the time slider SHALL NOT move the map.

#### Scenario: Repeat click on the same spot
- **WHEN** the user clicks a point, the whole answer is already in view, and the user clicks the same screen position again
- **THEN** the map has not moved, the second query uses the same coordinates, and the same route is shown

#### Scenario: Answer off-screen
- **WHEN** the destination is outside the current view
- **THEN** the map fits the route and destination

### Requirement: Risk overlay recedes while a route is shown
While a route is drawn, the risk overlay opacity SHALL be reduced, and it SHALL be restored when the answer has no route or the scenario reloads.

#### Scenario: Route shown
- **WHEN** a response with `status` `route` is drawn
- **THEN** the overlay opacity is lower than with no route shown

### Requirement: Legend matches the drawing
The legend SHALL describe only what is drawn: your way out, safe ground (green) / best ground (amber), the hazard marker, and the backup when shown. Per-segment colour entries SHALL be removed.

#### Scenario: Legend after change
- **WHEN** the page loads
- **THEN** the legend has no "spot the flood may reach before you" red-line entry
