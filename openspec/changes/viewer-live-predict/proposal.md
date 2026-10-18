## Why

The team decided (Sat 16:30) that **`viewer/` is the product UI** for the demo and the video. Today it replays a pre-baked Oct 11 bundle and makes no server calls. That leaves two judged points invisible:

- **Nothing runs live on LinuxONE.** Criterion 3 asks for "use of LinuxONE + open-source AI/ML". A static replay could run on any laptop.
- **The damage model and prediction mode aren't shown.** Packet B (the judged ML piece) and prediction mode (`engine/escape.py`: from any point at any time, the safest path and its confidence) are only visible in `web/predict.html`, which is no longer the UI.

Packet B2 (Monte Carlo route reliability) was never built. Prediction mode covers what B2 was for (is my escape route safe, and which bridges can't be crossed), so **this change replaces B2**.

## What Changes

- **Live "where do I go?" in the viewer.** Clicking (or tapping) a point on the terrain at slider time `t` calls the existing `POST /api/predict/escape` on the L1CC VM. The viewer draws the returned path, its unsafe points, the destination and a result card (safe / not safe, confidence, walk time, margin before the flood). It also shows a host badge with `s390x · big-endian · <response time>` taken from the response.
- **Same-origin serving.** The API mounts `viewer/` at `/viewer`, which is one additive line in the prediction-mode section of `api/app.py`. The live demo is then `http://localhost:8001/viewer/?scenario=oct11` through the SSH tunnel, with no CORS. Served from a plain static server, the viewer keeps working as a replay and hides the live controls.
- **Damage heat layer.** A new optional raster `pdestroyed.u16.bin` in the bundle (P(destroyed) per cell from damage model v2, for the bundle's default trigger and preset). It's baked from `engine.escape.FloodScenario` and added to the heat-map selector as **"Chance of destruction"**, plus `p_destroyed` per bridge.
- **Aug 26 bundle (stretch).** Bake `viewer/data/aug26/` (Bhotekoshi–Trishuli on `data/proc_trishuli`) if the engine can produce settlements for that valley. Otherwise skip it and say so in the README.
- **Scenario schema `@1` stays.** The new raster and fields are optional; old bundles still load.

## Capabilities

### New Capabilities
- `viewer-live-escape`: the viewer's click-to-escape interaction backed by the prediction-mode API, live/offline detection and the s390x evidence badge.
- `viewer-damage-layer`: the baked P(destroyed) raster, the heat-map option and bridge risk labels.
- `viewer-aug26`: the second replay bundle (stretch).

### Modified Capabilities
- `replay-slider-ui` non-goal "no API calls during replay" is narrowed. **Replay stays pure and offline.** Only the explicit escape query goes to the API.

## Impact

- **Code**:
  - `viewer/js/` (new module `live.js`, plus hooks in `main.js`/`scene.js`)
  - `viewer/bake/bake_scenario.py` (the extra raster)
  - `docs/viewer/data-schema.md`
  - **`api/app.py`: one `app.mount("/viewer", ...)` line inside the prediction-mode section (owned by agent-lcpizani). Tell agent-aayush, who owns the rest of `api/`.**
- **Not touched**: `engine/` (read only), `web/`, the existing `/api/scenario` endpoints.
- **Video**: the 0:50–2:10 segment moves from the Leaflet UI to the viewer. `docs/video-script.md` and the screenshot list need updating (agent-aayush, packet G).
- **AGENTS.md**: B2 marked as replaced by prediction mode, and "viewer is the UI" recorded.
