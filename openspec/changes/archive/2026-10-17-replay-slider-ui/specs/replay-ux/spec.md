## ADDED Requirements

### Requirement: Story-first opening
On load without URL parameters, the viewer SHALL:
- open at the default warning's issue time,
- frame the upper valley, where the first hour of the flood happens,
- show a story caption, and
- prompt the user to press play (button highlight plus "Press ▶ or Space").

The prompt SHALL disappear after the first play.

#### Scenario: First load
- **WHEN** the page loads with no parameters
- **THEN** the clock shows the default warning time, the caption describes the current moment and the next one, and the play button is highlighted

### Requirement: Story caption
The map SHALL show a caption with:
- the latest story beat at or before `t`: a warning, the burst, the flood reaching a settlement, or an observed impact
- the next beat, with a countdown

The caption SHALL be a polite live region that only changes when the beat changes.

#### Scenario: Caption follows time
- **WHEN** t moves past the time the flood reaches Jagat
- **THEN** the caption reads that the flood has reached Jagat and names the next beat with its countdown in minutes

### Requirement: Forecast-first settlement markers
From the selected warning's issue time onwards, each settlement marker SHALL show the engine's forecast for that warning ("everyone can make it", "under 15 min to spare", or "some people can't make it"), before the flood arrives. Each marker SHALL also show the current state of most of its people.

Every state and forecast SHALL use a distinct shape or icon as well as a colour. Colour is never the only cue.

#### Scenario: Forecast before arrival
- **WHEN** the warning is the official SMS (06:40) and t = 06:41
- **THEN** a settlement the flood reaches at 07:00 already shows the "some people can't make it" badge

#### Scenario: Not colour alone
- **WHEN** the map is viewed in greyscale
- **THEN** safe, on the move, not warned, caught, and the forecast badge are still distinguishable by icon shape

### Requirement: Bridge warnings ahead of the flood
From the selected warning time until the flood reaches a bridge, an at-risk bridge SHALL show "Don't cross" with the time the flood arrives. After that it SHALL show "Flooded". Before the warning it SHALL show a neutral bridge icon.

#### Scenario: Countdown on a bridge
- **WHEN** the warning has been issued and the flood reaches bridge B at 06:12, and t = 05:50
- **THEN** bridge B shows "Don't cross · flood 06:12"

### Requirement: Settlement details
Clicking or tapping a settlement marker, or choosing it in the settlement list, SHALL:
- open a details card with:
  - English and Nepali names
  - people at risk
  - when the flood arrives
  - the walk to safety (minutes, distance, climb)
  - time to spare or minutes short, and how many people can't make it, for the selected warning
  - current state
- highlight its escape route
- centre the map on it

The card SHALL close with a close button or Esc and return focus to where it came from.

#### Scenario: Open from the list
- **WHEN** the user activates "Jagat" in the settlement list with the keyboard
- **THEN** the card opens with focus on its heading, the map centres on Jagat, and Esc closes it and returns focus to the list item

### Requirement: One consistent people count
All people counts SHALL come from the engine's per-building numbers. The live counters (safe, on the move, not warned yet, caught) SHALL add up to the people at risk at every `t`. At the end of the replay, "caught" SHALL equal the engine's "people without time" for the selected warning. The warning selector SHALL show that number for every warning.

#### Scenario: Counters match the engine
- **WHEN** the replay reaches its end with the police-informed warning selected
- **THEN** the caught counter equals the engine headline for that warning (1,340 for oct11)

### Requirement: Map furniture
The map SHALL have:
- a key explaining markers, forecast badge, bridges, flood depth, the river line and the flood front
- a scale bar
- a compass that shows north, and in 3D resets the view to north-up when activated
- zoom in, zoom out and fit buttons
- pinch-zoom on touch screens in 2D

#### Scenario: Reset north
- **WHEN** the 3D view has been rotated and the user activates the compass
- **THEN** the camera turns so north is up

### Requirement: Plain language
Visible UI copy SHALL avoid engineering terms: "slack" becomes "time to spare", "HAND" becomes "height above river", and "footprint" is not used. Technical provenance and assumptions SHALL live in an "About this data" dialog.

#### Scenario: No jargon on the main screen
- **WHEN** the page is loaded
- **THEN** the words "slack", "HAND", "footprint", "dissemination" and "engine" do not appear outside the About dialog

### Requirement: Accessibility
The viewer SHALL meet WCAG 2.2 AA for its HTML UI. That means:
- text at least 12 px (body at least 14 px) and contrast at least 4.5:1
- visible focus indicators on every control
- labelled controls, grouped radio sets with legends, and headings and landmarks
- `aria-valuetext` on the time slider
- a text alternative for the map
- targets at least 24×24 px (at least 44×44 px on touch screens)
- full keyboard operation, with a skip link
- `prefers-reduced-motion` honoured: camera moves become instant and pulsing stops

#### Scenario: Keyboard only
- **WHEN** a keyboard user tabs through the page
- **THEN** every control shows a visible focus ring and every settlement's details can be opened without a pointer

### Requirement: Responsive layout
The viewer SHALL be usable at 390×844 (phone), 768×1024 (tablet), 1280×720 (projector) and 1440×900 without overlapping panels or clipped text.
- On phones: the story panel becomes a collapsible bottom sheet, map options open from a button, and the timeline is compact.
- On larger screens: panels can be collapsed.

#### Scenario: Phone
- **WHEN** the page is shown at 390×844
- **THEN** the map, caption, compact timeline and a collapsed story sheet are visible without overlap, and the clock is not clipped

### Requirement: Loading and failure states
While loading, the viewer SHALL show progress in megabytes. Load failures SHALL show a plain explanation and a Retry button. If WebGL 2 is unavailable, it SHALL say so before downloading data.

#### Scenario: Missing data
- **WHEN** a raster file returns HTTP 404
- **THEN** the viewer shows which file failed and a Retry button

### Requirement: Shareable state
The URL SHALL track `t`, `warn`, `view` and `heat` (debounced, without adding history entries), so a copied link reopens the same moment.

#### Scenario: Copy link
- **WHEN** the user pauses at 05:12 with the police warning in 3D and reloads the page
- **THEN** the viewer reopens at 05:12 with the police warning in 3D
