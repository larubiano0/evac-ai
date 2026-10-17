# viewer: 2D/3D flood replay

A static Three.js viewer that replays a flood scenario on the real DEM. It has a 2D shaded-relief contour map and a 3D terrain view, a time slider, a slack heat map and settlement states. Everything runs in the browser from a baked bundle in `data/<id>/`. Nothing is computed on a server during the replay.

It lives in its own directory, separate from `web/` (the Leaflet UI, owned by claude-luis). How the two relate is still to be coordinated.

## Run

```bash
cd viewer && python3 -m http.server 8090
# open http://localhost:8090/?scenario=oct11
```

## Bake the data (on the L1CC VM)

The bundle is computed by claude-luis's `engine/` (`Valley`, `Scenario`) on the VM, from his terrain products. The bake only reads `engine/` and `~/evac-ai/data`. It works in `~/work-claude-lucas` with a private copy of the GRASS database.

```bash
viewer/bake/run_on_vm.sh            # bakes oct11 on the VM and copies it into viewer/data/oct11/
python3 viewer/bake/validate.py viewer/data/oct11
```

The data format is described in [`data/SCHEMA.md`](data/SCHEMA.md).

`run_on_vm.sh` reads the VM address and key from `L1CC_HOST` / `L1CC_KEY` (never commit either). It exits non-zero and copies nothing back if the bake fails.

## URL parameters

`?scenario=oct11&t=06:30&warn=official_sms&view=3d&heat=slack&cam=arughat&sel=jagat`

`t` is `HH:MM` NPT. `warn` is a key of `scenario.warnings`. `heat` is `slack|arrival|walk|hand|off`. `cam` is a camera id. `sel` opens a settlement's details. The URL follows what you do (time, warning, view, heat map, selection), so a copied link reopens the same moment. With no parameters the viewer opens at the default warning time, framed on the upper valley.

Keyboard: **Space** plays and pauses; **← →** step one minute (**Shift** for ten); **Esc** closes details. Everything is reachable by Tab, starting with a skip link to the replay controls.

## Tests

```bash
python3 viewer/bake/validate.py viewer/data/oct11   # bundle vs schema; footprint and slack parity with the engine
node viewer/test/state.test.mjs                      # state machine (spec scenarios) + counts vs engine headline
(cd viewer && python3 -m http.server 8090 &) && node viewer/test/ui.cdp.mjs   # headless Chrome: UX, a11y and layouts (390/768/1280/1440)
```

## Libraries & resources

- **IBM Plex Sans / Plex Mono** (SIL OFL), loaded from Google Fonts with system fallbacks.
- **Three.js r165** (MIT): https://threejs.org. Vendored in `vendor/three/` with its LICENSE. Uses the OrbitControls, CSS2DRenderer and Line2 addons.
- **Design inspiration**: [monica-alegre/mountain-3d-viewer](https://github.com/monica-alegre/mountain-3d-viewer) by Monica Alegre, for the minimal controls, thin range sliders and contour/conceptual/realistic modes. That repo has no license, so **no code was copied**; only the visual ideas were reused.
- **Copernicus DEM GLO-30**: © DLR e.V. 2010–2014 and © Airbus Defence and Space GmbH 2014–2018, provided under COPERNICUS by the European Union and ESA.
- **OpenStreetMap** data (settlements, buildings, bridges): © OpenStreetMap contributors, ODbL.
- **Flood envelope, HAND, walking time and slack**: `engine/` by claude-luis (GRASS GIS r.watershed and r.walk).
