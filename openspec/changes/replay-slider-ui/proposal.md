## Why

The pitch depends on one moment: a judge drags a time slider and watches the Oct 11 flood run down the Syar Khola and Budhi Gandaki while settlements turn green (reached safety) or red (caught). The team wants this on real terrain, in a 3D view and a 2D shaded-relief contour map, with a slack heat map. The visual style is inspired by monica-alegre/mountain-3d-viewer: minimal controls, thin range sliders, stepped colors, switchable view modes.

claude-luis owns `web/` (Leaflet UI) and `api/`, so this viewer is built **in a separate directory, `viewer/`**. How the two UIs fit together will be coordinated later.

## What Changes

- **New static app in `viewer/`**: one Three.js scene of the Budhi Gandaki corridor on the real 30 m DEM, viewed as a **2D shaded-relief contour map** or as **3D terrain**, with an animated switch between them.
- **A replay slider** with play/pause, speeds and event ticks (community relay, burst, wave at Jagat, police informed, NDRRMA informed, wave at Arughat, official SMS, second wave). Everything shown is a pure function of the slider time `t`.
- **The flood is drawn in a shader**: a cell is wet when it drains to the flood path and `t ≥ arrival(km)` and `HAND ≤ height(km)`. The values come from claude-luis's calibrated envelope, so the final extent equals the engine's conservative footprint.
- **The slack heat map is the default**, multiply-blended on the relief and recomputed live when the warning time changes.
- **Settlement markers** follow a state machine (unaware → walking → safe | caught), plus walking routes, bridges and live counters.
- **A versioned scenario contract** (`scenario.json` plus little-endian `uint16` rasters), produced by a bake script that **imports claude-luis's `engine/`**. It runs on the L1CC VM in its own work directory, against a copy of the GRASS database, and doesn't modify `engine/`, `pipeline/` or `~/evac-ai`.
- The artificial-scenario generator and the placeholder terrain from the earlier draft are **dropped**: real engine outputs now exist.

## Capabilities

### New Capabilities
- `replay-scenario-data`: the scenario contract (schema, units, time base, raster encoding) and the bake that produces it from `engine/` outputs.
- `replay-scene`: the terrain scene, 2D/3D cameras and switch, the 2D contour map, 3D layer modes, the heat map, the shader flood, labels and markers.
- `replay-timeline`: the replay slider, playback, event ticks, settlement state machine, warning selection and live counters.
- `replay-ux`: the MVP experience layer. It covers:
  - story caption and opening view
  - forecast-first markers and bridge warnings
  - settlement details and list
  - map key, scale bar, compass and zoom controls
  - plain-language copy
  - accessibility (WCAG 2.2 AA)
  - responsive layout (phone, tablet, desktop, projector)
  - loading and error states
  - shareable URL state

### Modified Capabilities
<!-- none: openspec/specs/ is empty -->

## Impact

- **New code**: `viewer/` (static HTML/JS, no build step) and `viewer/bake/` (Python, run on the VM: numpy, rasterio, scipy, pyproj, and `engine/` by import).
- **New dependency**: Three.js 0.165.0, vendored in `viewer/vendor/`. Log it in README "Libraries & Resources" with the mountain-3d-viewer design credit and Copernicus DEM attribution.
- **Depends on claude-luis's** `engine/` API (`Valley`, `Scenario`) and `data/proc` + `data/raw` on the VM, read only.
- **Not touched**: `web/`, `api/`, `engine/`, `pipeline/`, VM `~/evac-ai`. AGENTS.md claim and plan edits are deferred until the team coordinates.
