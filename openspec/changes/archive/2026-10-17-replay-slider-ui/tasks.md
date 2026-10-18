## 1. Coordination and setup

- [ ] 1.1 Coordinate with claude-luis on how `viewer/` relates to `web/`, then add the AGENTS.md claim for `viewer/` (deferred by the user: "coordinate later")
- [ ] 1.2 Plan edits (§4.2 Map UI, §4.3, §11) after the team agrees (deferred; drafts saved in a stash)
- [x] 1.3 Create `viewer/` (`index.html`, `js/`, `data/`, `bake/`, `vendor/`) and vendor three@0.165.0 (core + OrbitControls, CSS2DRenderer, Line2, LineMaterial, LineGeometry, LineSegments2, LineSegmentsGeometry)
- [x] 1.4 Add Three.js, the mountain-3d-viewer design credit and Copernicus DEM attribution to `docs/viewer/README.md` (the root README is updated at coordination time)

## 2. Scenario contract and bake

- [x] 2.1 Write `docs/viewer/data-schema.md` (scenario@1 fields, units, time base, raster encoding)
- [x] 2.2 Write `viewer/bake/bake_scenario.py`: import `engine.scenario`; write the four `*.u16.bin` layers as `'<u2'`; envelope lookup; settlements with effective `walk_min`, routes and bridge-on-route; bridges; events; warnings; headline; cameras; checks; provenance
- [x] 2.3 Write `viewer/bake/run_on_vm.sh`: sync code to `~/work-claude-lucas/repo`, symlink data, copy the grassdb into a private HOME, run the bake, pull results into `viewer/data/oct11/`
- [x] 2.4 Write `viewer/bake/validate.py`: schema fields, file sizes, little-endian DEM min/max round-trip, footprint count within 1% using shader math, settlement slack parity within 0.1 min
- [x] 2.5 Bake `viewer/data/oct11/` on the VM and pass the validator

## 3. Scene

- [x] 3.1 Load the scenario and rasters; show a schema-version error; show the ARTIFICIAL DATA badge or the provenance line
- [x] 3.2 Terrain mesh (every 4th cell) with the exaggeration uniform; RGBA32F field texture; envelope lookup texture
- [x] 3.3 Fragment shader: hillshade, heat map (multiply), contours (zoom-stepped interval, fade), flood (wet test, soft edge, depth ramp)
- [x] 3.4 2D orthographic camera with custom pan/zoom (north up)
- [x] 3.5 Heat-map selector (slack default / arrival / walk / HAND / off), opacity slider, legend
- [x] 3.6 Contour labels on major lines along the flood path and settlement transects, one set per interval, 2D only
- [x] 3.7 3D perspective camera with OrbitControls; exaggeration slider (3D only); layer radios Contour / HAND bands / Terrain (3D only)
- [x] 3.8 2D⇄3D camera tween with matched visible extent
- [x] 3.9 CSS2D settlement and bridge labels; Line2 flood path and routes draped at elevation × exaggeration
- [x] 3.10 Camera bookmarks from `scenario.cameras`

## 4. Timeline

- [x] 4.1 Slider bound to `uTime` and to the `HH:MM NPT` readout
- [x] 4.2 Play/pause and speeds (1/4/16 sim-min/s), stopping at the end
- [x] 4.3 Event and warning ticks with click-to-jump
- [x] 4.4 Settlement state machine (dissemination, bridge cut) and marker colors
- [x] 4.5 Walking-route reveal with a moving dot
- [x] 4.6 Warning selector with immediate recompute (states, counters, slack heat map)
- [x] 4.7 Live counters (safe / walking / unaware / caught) plus the engine headline for the selected warning

## 5. Verify

- [x] 5.1 Serve `viewer/` locally and load it in headless Chrome: no console errors, a screenshot at 2D and 3D, and the flood visible after the burst
- [x] 5.2 Unit-check the state machine and time formatting with node against the spec scenarios

## 6. UX: story and truth (review B1–B4, B7)

- [x] 6.1 Bake: per-building people `units`, per-settlement `route_walk_min`/`route_len_m`/`route_climb_m`/`engine[warning]`; validator check that units reproduce every headline exactly
- [x] 6.2 State: per-unit state machine, per-settlement majority state, forecast, story beats, duration and number formatting (pure, node-tested)
- [x] 6.3 Story-first opening (default warning time, upper-valley framing, play prompt) and live story caption with next-beat countdown
- [x] 6.4 Forecast-first markers (state icon + forecast badge) and bridge warnings ("Don't cross · flood HH:MM" → "Flooded")
- [x] 6.5 Flood front on the river (flooded vs ahead line, front marker) and follow-the-flood during playback
- [x] 6.6 Settlement list and details card (open/close/Esc/focus return, route highlight, centre map)
- [x] 6.7 Warning selector as an outcome comparison (people who can't make it per warning); counters from units
- [x] 6.8 Plain-language copy everywhere; provenance and assumptions moved to an "About this data" dialog

## 7. UX: access and interaction (B5, B8, M2, M4–M7)

- [x] 7.1 Design tokens, IBM Plex Sans + Plex Mono type scale (≥12 px, body ≥14 px), contrast ≥4.5:1, focus-visible rings, ≥24 px targets (≥44 px on coarse pointers)
- [x] 7.2 Semantics: landmarks, headings, fieldset/legend radio groups, labelled sliders with aria-valuetext, skip link, map text alternative, polite live caption
- [x] 7.3 Timeline: tall track and large thumb, real tick hit areas, label priority with collision hiding, speed units, restart, tick-type key
- [x] 7.4 Map key, scale bar, compass (reset north), zoom +/−/fit buttons, 2D pinch-zoom, one-time 3D navigation hint
- [x] 7.5 Loading progress (MB), friendly errors with Retry, WebGL 2 pre-check; prefers-reduced-motion honoured
- [x] 7.6 Heat map: plain names, legend end labels, labelled strength control; river line distinguishable from deep water

## 8. UX: layout (B6, M1, M3, M8)

- [x] 8.1 Responsive layout: desktop and projector collapsible panels, tablet, phone bottom sheet and options sheet, compact timeline
- [x] 8.2 Label decluttering (priority placement for settlements, bridges and contour labels)
- [x] 8.3 URL state sync (t, warn, view, heat) with replaceState
- [x] 8.4 Verify: unit, end-to-end and accessibility probes; screenshots at 390, 768, 1280 and 1440; fix everything found
