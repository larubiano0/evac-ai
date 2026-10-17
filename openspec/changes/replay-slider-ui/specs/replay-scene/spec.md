## ADDED Requirements

### Requirement: Terrain from real DEM
The scene SHALL render the Budhi Gandaki corridor terrain from the baked Copernicus 30 m DEM, georeferenced in EPSG:32645 metres, with the origin at the grid's lower-left corner.

#### Scenario: Terrain loads
- **WHEN** the page opens with a valid scenario bundle
- **THEN** the corridor terrain is visible, and the Arughat and Chhekampar labels sit on their real positions

### Requirement: 2D and 3D views of one scene
The UI SHALL offer a 2D/3D view control:
- **2D**: an orthographic top-down camera with pan/zoom only and exaggeration fixed at x1.
- **3D**: a perspective camera with orbit controls.

Switching SHALL animate the camera over about 1 s and SHALL keep the flood, markers and slider time unchanged.

#### Scenario: Switch preserves state
- **WHEN** the user switches from 3D to 2D at slider time 06:12
- **THEN** the camera animates to top-down, rotation is disabled, and the flood extent and settlement colors are identical to before the switch

### Requirement: Vertical exaggeration in 3D
In 3D view, the UI SHALL provide an exaggeration slider from x1 to x5 that scales terrain heights without rebuilding geometry.

#### Scenario: Exaggeration hidden in 2D
- **WHEN** the view is 2D
- **THEN** the exaggeration control is hidden or disabled, and heights render at x1

### Requirement: Shader flood is a pure function of time
The terrain SHALL show a cell as wet if and only if:
- its river-km is finite,
- `t ≥ burst + arrival(km)` (the engine's early arrival), and
- `HAND ≤ height(km)` (the engine's conservative height).

HAND and river-km are sampled at full 30 m resolution. Water color SHALL deepen with depth `height − HAND`. The water stays at the envelope maximum after arrival; recession is not modelled. At the end of the time range, the wet area SHALL equal the engine's conservative footprint.

#### Scenario: Before the burst
- **WHEN** slider time is earlier than `burst_min`
- **THEN** no cell is wet

#### Scenario: Scrub back is exact
- **WHEN** the user scrubs forward to 07:00 and then back to 05:00
- **THEN** the flood extent at 05:00 is identical to the extent shown when 05:00 was first reached

#### Scenario: Off-path cells stay dry
- **WHEN** the slider is at the end of the time range
- **THEN** cells with river-km 65535 (for example, the Budhi Gandaki above the confluence) are not wet

### Requirement: 2D view is a shaded-relief contour map
In 2D, the terrain SHALL be drawn as a shaded-relief contour map:
- **Base**: a light, low-contrast greyscale hillshade from the full-resolution DEM, with light from the NW (azimuth 315°, altitude 45°). Its brightness range SHALL be limited (about 0.7–1.0) so overlaid colors stay readable.
- **Contours**: drawn over the hillshade from the full-resolution DEM in the shader. Major lines SHALL be every 5th interval, drawn heavier, and labelled with elevation in metres.
- **Interval**: SHALL adapt to zoom (default steps 500 / 100 / 20 m) so lines never merge into solid fill on steep valley walls. Lines SHALL stay about 1 px wide at every zoom.
- **Draw order, bottom to top**: hillshade → heat map (when on) → contours → flood → flood path, routes, bridges and settlement markers.

#### Scenario: 2D shows shaded relief with contours
- **WHEN** the user switches to 2D with the heat map off
- **THEN** the terrain appears as a light grey shaded relief with contour lines, with the flood and markers on top

#### Scenario: Interval adapts to zoom
- **WHEN** the user zooms from the full corridor into Arughat
- **THEN** the contour interval steps down (for example 500 m → 100 m → 20 m), and adjacent lines stay visually separate on the valley walls

#### Scenario: Flood reads against contours
- **WHEN** the flood covers the valley floor in 2D
- **THEN** the water fill is drawn over the contour lines, and the contours stay faintly visible through the water

### Requirement: Heat map overlay on the relief
The UI SHALL offer a heat-map overlay over the terrain in 2D and 3D, with a selector listing the fields available in the scenario bundle, plus "off". The heat map SHALL be **multiply-blended** onto the hillshade so the relief stays visible through the colors. It SHALL have an opacity control and a legend with units. Its palette SHALL be a sequential scale that doesn't reuse the settlement state hues (red/amber/green), so markers stay distinct. Cells with no data (65535) SHALL be left uncolored.

Candidate fields, used when present in the bundle:
- **Flood arrival time**: minutes after the burst, from river-km and `arrival_min`. Footprint cells only.
- **Walking time to safety**: minutes, from claude-luis's r.walk raster. All cells with data.
- **Slack**: arrival − (warning + dissemination + walk), recomputed live when the warning changes. Footprint cells only, matching the engine, which only scores buildings inside the footprint.
- **HAND**: metres above the drainage. Cells that drain to the flood path.

**Slack is the default heat map** in both 2D and 3D whenever the bundle has a walking-time raster. If it doesn't, the default falls back to flood arrival time.

#### Scenario: Default is slack
- **WHEN** the page opens with a bundle that has `walk.u16.bin`
- **THEN** the slack heat map is on, using the selected warning scenario, and its legend reads "Slack (min)" with the colors diverging at 0

#### Scenario: Relief shows through the heat map
- **WHEN** the arrival-time heat map is on at full opacity
- **THEN** ridges and valley walls are still visible as light/dark shading inside the colored area, and contour lines are drawn above it

#### Scenario: Slack heat map follows the warning toggle
- **WHEN** the slack heat map is on and the user switches the warning from "community" to "official"
- **THEN** the heat map colors update immediately, without moving the slider

#### Scenario: Missing field
- **WHEN** the bundle has no `walk.u16.bin`
- **THEN** "Walking time to safety" does not appear in the selector

### Requirement: 3D layer modes
In 3D, the UI SHALL offer layer radios:
- **Contour**: the same contour lines as 2D, draped on the terrain.
- **HAND bands**: stepped colors by HAND band, with contours.
- **Terrain**: shaded relief.

The flood overlay SHALL be visible in every layer mode.

#### Scenario: HAND bands
- **WHEN** the user selects HAND bands in 3D
- **THEN** the terrain is colored in fixed HAND steps that stay the same at every zoom level

#### Scenario: Layer radios hidden in 2D
- **WHEN** the view is 2D
- **THEN** the layer radios are hidden or disabled, and the contour map is shown

### Requirement: Labels, routes and bridges
The scene SHALL draw:
- settlement and bridge labels as screen-space HTML that stays readable in both views
- the flood path as a line
- walking routes as lines draped on the terrain
- bridges as markers

#### Scenario: Labels readable in 2D and 3D
- **WHEN** the view switches between 2D and 3D
- **THEN** labels keep a constant screen size and stay attached to their positions

### Requirement: Camera bookmarks
The UI SHALL list `scenario.cameras` as bookmarks. Selecting one SHALL animate the 3D camera to the stored pose.

#### Scenario: Jump to Arughat
- **WHEN** the user selects the "Arughat" bookmark in 3D
- **THEN** the camera animates to the Arughat pose within about 1 s
