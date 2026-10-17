## Context

- **The demo needs a replay of the Oct 11 Budhi Gandaki flood** (plan §9, 0:50–2:10). The source is on the Syar Khola near Chumling/Chhekampar (`replay/oct11.json`). The flood runs down the Syar Khola into the Budhi Gandaki and on to Arughat (river-km 62.5 of a 94.8 km path).
- **claude-luis owns the engine and the existing UI**:
  - `engine/` (`Valley`, `Scenario`): D8 drainage-following HAND to the event channel, an envelope calibrated on the replay (early arrival, conservative height), r.walk time to safety, and per-building and per-settlement slack.
  - `pipeline/`: the terrain inputs.
  - `web/` and `api/`: the Leaflet UI and FastAPI.
- **Terrain on the VM** (`~/evac-ai/data/proc`, read only): `dem_g.tif`, `sdir.tif`, `streams.tif`, `acc.tif`. EPSG:32645, 30 m, 1357 × 2748, top-left (273511.3, 3165145.3).
- **This change is a separate viewer in `viewer/`**, so it doesn't collide with `web/`. Coordination comes later.
- **Inspiration: monica-alegre/mountain-3d-viewer.** It has no license, so it is a visual reference only and no code is copied.
- **Constraints**:
  - The viewer is static and browser-only, with no API calls during replay.
  - The bake runs on L1CC (s390x, big-endian), so byte order must be handled explicitly.
  - Feature freeze is Sun 02:00 ET.

## Goals / Non-Goals

**Goals:**
- Every visual is a pure function of slider time and warning choice, so scrubbing is exact in both directions.
- One scene with two views: a 2D shaded-relief contour map and 3D terrain. Both share the flood, heat map and markers.
- Numbers agree with the engine: the final flood extent equals its footprint, and settlement slack equals its `slack_min`.

**Non-Goals:**
- Hydrodynamics or recession. The water stays at the envelope maximum after the front arrives.
- Changes to `engine/`, `pipeline/`, `web/`, `api/` or the VM's `~/evac-ai`.
- Live triggers (a new source location). That is `api/`'s job.
- Mobile-first layout.

## Decisions

### D1. One Three.js scene, two cameras
- **World axes** are y-up: `X = easting − x_left`, `Z = northing_top − northing` (south = +Z), `Y = elevation × exaggeration`.
- **2D view**:
  - An `OrthographicCamera` looking straight down with north up.
  - Pan and zoom are handled by a small custom handler (drag and wheel). OrbitControls is avoided because orbiting a straight-down camera is degenerate.
  - Exaggeration is fixed at x1.
- **3D view**: a `PerspectiveCamera` with OrbitControls (`maxPolarAngle` 85°).
- **Switching** between the two:
  - 3D→2D: tween the perspective camera over about 1 s to near-straight-down above the target, then swap to the orthographic camera with matching visible height.
  - 2D→3D: the reverse.
  - The visible extent is matched with `halfHeight = d · tan(fov/2)`.

### D2. Terrain mesh on CPU, everything else in one fragment shader
- **Mesh**: a custom `BufferGeometry` sampled every 4th cell (340 × 687 ≈ 233k vertices). `position.y` is the elevation; the vertex shader multiplies it by `uExag`. World x/z are passed to the fragment shader.
- **One `RGBA32F` data texture** at full 30 m resolution:
  - R: DEM (m)
  - G: HAND (m, −1 = none)
  - B: river-km (−1 = none)
  - A: walking time (min, −1 = none)
- **Two 1D `RG32F` lookup textures** hold the engine envelope per 0.1 km: the early arrival (minutes after burst) and the conservative height (m).
- **Sampling** uses `texelFetch` everywhere, with bilinear interpolation done by hand. Float-linear filtering is an optional WebGL extension, so this keeps the viewer working everywhere.

### D3. Wet test and soft edges
- **Per texel**: `wet = km ≥ 0 && hand ≤ H(km) && tRel ≥ A(km)`, where `tRel = t − burst_min`.
- **Smooth edges**: per texel, the margin `H(km) − hand` is clamped to ±4 m, and set to −4 before the wave arrives. The 4 neighbouring margins are blended bilinearly and passed through `smoothstep(−0.3, 0.3)`. Edges then follow the HAND surface at sub-cell resolution. A first version blended binary wet flags, which left visible 30 m stair-steps.
- **Depth color**: `H − hand`, blended bilinearly, ramps from light to deep blue over 0–20 m. Water alpha is 0.65.
- At the end of the range, the wet set equals the engine's `flood` mask. The only differences come from quantization (hand to 0.1 m, km to 10 m, envelope lookup at 0.1 km), and the bake checks the cell count to within 1%.

### D4. Layers come from the engine, not recomputed
- `viewer/bake/bake_scenario.py` imports `engine.scenario.Valley` and `Scenario`, the same entry points `api/` uses, with the same extra trekkers (`{"Jagat": 100}`). It reads:
  - `S.hand`, `S.km`, `S.tts` and `S.flood`
  - `S.F` (the envelope), `S.t0`, `S.path`, `S.km_path`
  - `S.settlements(warn)`, `S.buildings(warn)`, `S.summary(warn)` and `S.bridges_at_risk()`
- **Isolation on the VM**: everything runs in `~/work-claude-lucas/repo` (a copy of this repo's code).
  - `data/raw` is a symlink to `~/evac-ai/data/raw`.
  - `data/proc/*.tif` are symlinks to Luis's files. `data/proc/work` is a real local directory.
  - GRASS (r.walk) writes maps into the grassdb. `pipeline/g.sh` resolves it relative to the repo (`<repo>/data/grassdb`, changed by claude-luis in 6b8b834), so the repo copy gets a private *copy* of the grassdb (34 MB), refreshed on every bake. Luis's mapset is never written. `HOME` also points to a private directory.

### D5. Raster encoding: little-endian `uint16` binary
- Browsers decode PNG through canvas at 8 bits per channel, so 16-bit PNGs silently lose precision. The layers are binary files instead:

| File | Encoding | No data |
|---|---|---|
| `dem.u16.bin` | value × 0.25 m | 65535 |
| `hand.u16.bin` | decimetres; negative HAND is clamped to 0 | 65535 = doesn't drain to the path |
| `riverkm.u16.bin` | units of 10 m | 65535 |
| `walk.u16.bin` | units of 0.1 min, capped at 65534 | 65535 |

- The arrays are row-major with the north row first.
- **They are always written with explicit `'<u2'`.** The bake runs on s390x, and native byte order there would corrupt every value.
- Each file is about 7.5 MB, for about 30 MB in total.
- The viewer decodes the files into the RGBA32F texture with a `DataView` read in little-endian, so it doesn't depend on the browser's byte order.

### D6. Scenario contract: `viewer/data/<id>/scenario.json`, schema `evac-ai/scenario@1`
- **Times** are minutes after `t_ref` (midnight NPT). The UI displays them as `HH:MM NPT`.
- **Settlement fields**:
  - `arrival_min` is absolute (`burst_min` + the earliest building arrival).
  - `walk_min` is the effective value from D8.
  - `engine_slack` maps each warning id to the engine's `slack_min`, and the validator uses it for the parity check.
- **The full field list is in `viewer/data/SCHEMA.md`**:
  - `grid`: `x_left`, `y_top`, `dx`, `nx`, `ny`, `dem_min`, `dem_max`
  - `flood`: `km_step`, `arrival_min` (relative to burst), `height_m`, `path` as `[[x, y, km], …]`
  - `warnings`, `settlements`, `bridges`, `events`, `cameras`, `layers`, `headline`, `checks`, `provenance`

### D7. Slack heat map follows the engine's definition
- **Per cell**: `slack = A(km) − (warnRel + dissemination + walk)`. It is shown only on footprint cells (`hand ≤ H(km)`), because the engine only scores buildings inside the footprint.
- **It is recomputed live** from uniforms when the warning changes.
- **The other heat fields**:
  - Arrival: footprint cells only.
  - Walking time: all cells with data.
  - HAND: cells draining to the path, clamped to 0–100 m.

### D8. Settlement walk time is defined so slack matches the engine exactly
- The engine's settlement slack is `min over at-risk buildings of (arr_b − walk_b) − warn − 5`. Define:
  - `K = min_b(arr_b − walk_b)`
  - `arrival_e = min_b arr_b`
  - `walk_min = arrival_e − K`
- Then `arrival_e − (warn + 5 + walk_min) = slack_min` for every warning, and the state machine's "caught" holds exactly when `slack_min < 0`.
- **Route**: the engine's own escape route (`settlements()[i].route`), traced along r.walk movement directions from the settlement's longest-walk building (claude-luis, "Packet R"). This keeps the routes identical to `web/`. As a fallback for engines without routes, use steepest descent on the time surface from the limiting building.
- **Bridge on route**: an OSM bridge-at-risk within 45 m of a route vertex. Its position along the route sets when the settlement reaches it.

### D9. Look and feel (reference-inspired, reimplemented)
- **Controls** are stacked top-right: small-caps labels, light Roboto, a 1px black range track and a 12px hollow thumb.
- **The timeline** is a full-width bottom bar with ticks for events and warnings, a play button, speeds 1/4/16 sim-min/s, and the `HH:MM NPT` readout.
- **Colors**:
  - Markers: unaware grey `#8a8f98`, walking amber `#f2a541`, safe green `#2e9e44`, caught red `#d7263d`.
  - Heat palettes avoid those hues. Slack is diverging, purple `#762a83` (negative) to near-white to teal `#018571` (positive), clamped to ±60 min. Arrival, walking time and HAND use cividis, a sequential blue→yellow scale.

### D10. No build step; Three.js is vendored
- `viewer/index.html` has an importmap pointing at `viewer/vendor/three/`:
  - `three.module.js` (r165 is self-contained)
  - the addons `OrbitControls`, `CSS2DRenderer`, `Line2`, `LineMaterial`, `LineGeometry`, `LineSegments2` and `LineSegmentsGeometry`
- It is served with `python3 -m http.server` from `viewer/`.

### D11. The 2D view is a shaded-relief contour map
- **Draw order** in the fragment shader:
  ```
  base     = mix(0.70, 1.00, hillshade)               // NW light, az 315°, alt 45°
  color    = base * mix(1, heat, uHeatOpacity·cover)   // MULTIPLY blend
  color   *= 1 − line · (major ? 0.55 : 0.30) · fade   // contours above the heat map
  color    = mix(color, water(depth), 0.65 · wet)      // flood above the contours
  ```
- **Why multiply, not alpha blending:** it keeps the relief visible through the color, so the valley floor and slopes stay readable.
- **Why the hillshade is low-contrast:** the steep walls' shadows would otherwise hide the heat colors.
- **Contour lines**: `f = e/interval`. The line strength is `1 − smoothstep(0.5, 1.5, dist/fwidth(f))`, which gives about 1 px lines. Major lines are every 5th. *Minor* lines fade between `fwidth(f)` 0.3 and 0.7 (closer together than about 2–3 px). Major lines never fade, so steep walls keep their structure; an earlier version faded every line, which left blotchy 30 m patches.
- **Interval by metres-per-pixel**: 20 m if mpp ≤ 3, 100 m if mpp ≤ 15, otherwise 500 m. These were tightened after screenshots showed 20 m lines too dense on Himalayan walls.
- **Flood and footprint edges**: the per-cell margin `height(km) − HAND` (clamped to ±4 m, −4 before arrival) is interpolated bilinearly and thresholded at 0. That gives smooth sub-cell edges instead of 30 m stair-steps. The cell-level wet set is unchanged.
- **Labels**: CSS2D labels on major contours, where they cross the flood path and E–W transects through each settlement (±1.5 km). There is one label set per interval level, and labels show only in 2D.
- **3D layer radios**:
  - Contour: same as 2D.
  - HAND bands: stepped HAND colors under the contours.
  - Terrain: full-contrast hillshade, no contours.

### D12. Default heat map = slack
- Slack is selected on load whenever the bundle has the walking-time layer; otherwise arrival is the default.
- The legend sits under the controls: a bar with tick labels and units.

## Risks / Trade-offs

- **The engine API changes under us** (claude-luis is actively editing) → the bake pins what it reads to the attributes above and fails loudly if any are missing. Re-run the bake after engine updates.
- **The GRASS copy goes stale** → it is copied fresh on each bake run (34 MB, a few seconds).
- **Byte-order corruption on s390x** → explicit `'<u2'` writes, and the validator checks DEM min/max against the values the bake recorded.
- **Walking times are 1–3 min**, so routes are about 100 m long and invisible at corridor zoom → camera bookmarks zoom to settlements. In practice slack is driven by arrival − warning, which is the story anyway.
- **Our whole-settlement state counts differ from the engine's per-building "people without time"** → show the engine headline next to the live counters, labelled.
- **Shader contours look jagged at 20 m on a 30 m DEM** → bilinear sampling and fwidth anti-aliasing. If needed, raise the minimum interval to 50 m.
- **Download size (about 30 MB)** → fine on localhost and an SSH tunnel. Gzip later if served publicly.

## Migration Plan

This is a new directory, so there is no migration. Baked data in `viewer/data/oct11/` is regenerated by the bake. Whether to commit the roughly 30 MB of binaries is decided at coordination time.

## Open Questions

- How the viewer relates to `web/` (merge, link, or replace) once the team coordinates.
- Satellite drape (Sentinel-2 cloudless, CC BY-NC-SA): worth adding for the video?

## UX decisions (MVP review, after the first build)

### D14. Forecast first, outcome second
A warning tool is judged by what it tells people *before* the water arrives. So:
- From the selected warning time, each marker shows the engine's forecast for that warning as a badge, next to its current-state icon.
- Bridges switch to "Don't cross · flood HH:MM" when the warning is issued, not when they flood.
- The outcome (caught / safe) still plays out over time, so the replay stays honest.

### D15. People units instead of whole settlements
The first build gave each settlement one state, which disagreed with the engine's per-building count (for example 764 vs 1,340). The bake now ships one unit per at-risk building, plus trekkers on the limiting building, so the counters are exact at every t and equal the engine headline at the end. Settlement markers show the state holding the most people.

### D16. Story caption as the narrative spine
Story beats are built from the scenario: warnings, the burst, the flood reaching each settlement (its earliest arrival), and observed impacts. The caption shows the latest beat and the next one with a countdown. It is also the polite live region, so screen-reader users hear the story without per-frame noise.

### D17. Typography and tokens
- **Type**: IBM Plex Sans for the UI and IBM Plex Mono for clock and numbers. IBM's own face suits an IBM Z project, has tabular figures, and is very legible at small sizes. It replaces single-family Roboto.
- **Tokens**: colours are CSS custom properties. The state colours stay (grey / amber / green / red), but every state also has its own icon (dot / arrow / check / cross). The forecast badge is a triangle with "!".

### D18. Layout
- **Desktop and projector**: a story panel on the left, map options on the right (both collapsible), map controls bottom-right, a scale bar bottom-left, and the caption top-centre.
- **Under 760 px**: the story panel is a bottom sheet (collapsed to one line of outcome), map options open from a "Layers" button, and the timeline drops tick labels (the caption carries them).
