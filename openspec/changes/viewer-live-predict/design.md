## Context

- **`viewer/`** (change `replay-slider-ui`) is a static Three.js app. It reads `viewer/data/<id>/scenario.json` and `*.u16.bin` layers, and every visual is a pure function of slider time and warning choice.
- **Prediction mode** (commit 620a3ef) already exists in `api/app.py` and `engine/escape.py`:
  - `GET /api/predict/options` returns the valleys, presets and rules.
  - `POST /api/predict/scenario {valley, lon?, lat?, preset?}` returns `{sid, stations, bridges[{id,name,lon,lat,crosses_flood_river,p_destroyed,flood_arrival_min}], runtime_s, host}`. It takes 2–11 s the first time and is cached (at most 4 entries) after that.
  - `POST /api/predict/escape {sid, lon, lat, minutes_after_start}` returns:
    - `{safe, confidence, walk_min, distance_m, climb_m, destination, min_margin_before_flood_min, unsafe_points[], path[], message, host}`
    - `status` values for edge cases: `outside_terrain`, `outside_impact_zone`, `safe_here`
    - takes under 0.1 s on s390x
  - The service runs on the VM at `127.0.0.1:8001` from `~/work-agent-lcpizani/repo`, reached through an SSH tunnel.
- **Time to freeze**: about 9 h (Sun 02:00 ET). The design favours the smallest change that makes the judged points visible.

## Goals / Non-Goals

**Goals**
- One click on the terrain gives an answer computed live on s390x, drawn in the viewer, in under 1 s once the scenario is warm.
- The damage model is visible as a layer, without the API.
- The replay keeps working with no server (file server or offline save).

**Non-Goals**
- Moving the trigger point inside the viewer. The flood rasters are baked per trigger; a new trigger needs a re-bake. That stays in `web/` / the API.
- Monte Carlo route reliability (old B2). This change replaces it.
- Changing `engine/escape.py` behaviour or the existing `/api/scenario` endpoints.

## Decisions

### D1. Same origin: the API serves the viewer
- Add `app.mount("/viewer", StaticFiles(directory=f"{ROOT}/viewer", html=True), name="viewer")` in the prediction-mode section of `api/app.py`. It must come before the catch-all `/static` mount, and it's additive.
- *Alternative rejected:* CORS on the API plus a separate `http.server` on 8090. It means two tunnels on camera and one more thing that can break.
- **Live detection**: on load, the viewer does `GET ../api/predict/options` (relative to `/viewer/`) with a 3 s timeout. Success turns live mode on. Failure keeps it off, with a quiet note in "About this data".

### D2. Scenario id is derived from the bundle
- The bundle gains `predict: {valley, preset, trigger:{lon,lat}}` in `scenario.json`, written by the bake from `FloodScenario.describe(short=True)`.
- When live mode turns on, the viewer POSTs `/api/predict/scenario` with those values **once, in the background**, and keeps the `sid`. Until it returns, clicks show "Preparing live model on LinuxONE…". A 404 on escape (expired cache) triggers one silent re-POST and a retry.
- **Why:** the escape path then uses the same flood as the replay on screen, so the API and the picture can't disagree.

### D3. Interaction
- **Activation**: a toggle labelled "Where do I go?" (keyboard reachable). While it's on, a click or tap on the terrain sets the query point. Picking uses a raycast against the terrain mesh in 3D and the ortho unprojection in 2D, then UTM → lon/lat. pyproj isn't in the browser, so this needs a small inline UTM-45N inverse, checked against three known points from the bundle.
- **Query time**: `minutes_after_start = t − burst_min` at the current slider time. Moving the slider while a point is set re-queries on release, debounced to 250 ms, never during playback.
- **Drawing**:
  - the path as a Line2 draped like the routes, green if `safe`, amber otherwise
  - `unsafe_points` as red dots
  - the destination as a flag
  - the start as a pin
- **Result card** (re-uses the settlement details card component): the `message` in plain words, confidence %, walk min, climb m, and the margin before the flood. Edge statuses get their own one-line copy.
- **Evidence badge**: `Computed live on IBM LinuxONE · s390x · big-endian · 0.07 s`, from `host` and the measured round trip.

### D4. Damage layer is baked, not fetched
- The bake instantiates `engine.escape.FloodScenario(valley, trigger, preset)` for the bundle and writes `pdestroyed.u16.bin`: P × 10000, with 65535 meaning outside the corridor (NaN).
- It also writes `p_destroyed` and `crosses_flood_river` on each bridge, matched by OSM id where it exists in `bridges[]`.
- **Heat option `damage`**: a sequential ramp from 0 to the bundle's 99th percentile. The legend shows real end values; never threshold at 0.5 (packet B: October probabilities are low).
- *Why bake:* `/api/predict/p.png` is an 8-bit PNG with lossy colour, and the replay must stay pure and offline (D1 of `replay-slider-ui`).

### D5. Aug 26 is gated
- Bake `aug26` only if `engine.scenario.Valley` can load the Trishuli OSM layers and `Scenario(V, aug26)` returns settlements.
- Known blockers (AGENTS.md log 14:35 and 14:37): `km_of` has no bounds check, and Kali Khola and Devghat lie outside the grid. Bake with those observations excluded and say so in the bundle `provenance`.
- If it isn't feasible in 1 h, drop it and note that in `docs/viewer/README.md`.

## Risks / Trade-offs

- **The first scenario POST takes 2–11 s** on a shared 3-CPU VM. *Mitigation:* warm it in the background on load, and warm it again before recording.
- **The API cache holds 4 scenarios.** *Mitigation:* D2's re-POST on 404.
- **The API runs from `~/work-agent-lcpizani/repo` on port 8001, not in the `evac-ai` container on 8000.** For the video, `docker ps` should show the service actually used. *Mitigation:* either run prediction mode in the container (rebuild with the current `main`, now that the Dockerfile is committed) or show the 8001 process in the terminal shot. Decide with agent-aayush (packet A/G).
- **Ownership**: `api/` belongs to agent-aayush except the prediction section. The mount line goes in that section, and agent-aayush is told before pushing.
