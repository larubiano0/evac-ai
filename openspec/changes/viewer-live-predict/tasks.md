## 1. Coordination

- [ ] 1.1 Tell agent-aayush (owner of `api/`) about the `/viewer` mount line in the prediction section of `api/app.py`
- [ ] 1.2 Agree with agent-aayush which process serves the demo: prediction mode inside the `evac-ai` container (rebuild from `main`) or the 8001 process. Update docs/deploy.md

## 2. API (additive, prediction section only)

- [ ] 2.1 Add `app.mount("/viewer", StaticFiles(directory=f"{ROOT}/viewer", html=True), name="viewer")` before the `/static` mount
- [ ] 2.2 Deploy to the VM service and check that `curl localhost:8001/viewer/` returns `index.html` and `localhost:8001/viewer/data/oct11/scenario.json` returns 200

## 3. Bake and schema

- [ ] 3.1 `bake_scenario.py`: build `engine.escape.FloodScenario` for the bundle; write `pdestroyed.u16.bin` (P×10000, `'<u2'`, 65535 = NaN) and `predict{valley,preset,trigger}`
- [ ] 3.2 Add `p_destroyed` and `crosses_flood_river` to `bridges[]` (match by OSM id)
- [ ] 3.3 `SCHEMA.md`: document the optional layer and fields (still `@1`)
- [ ] 3.4 `validate.py`: P parity check (≤ 1e-4, NaN mask exact); re-bake `oct11` on the VM and pass

## 4. Viewer: damage layer

- [ ] 4.1 `data.js`: load `pdestroyed.u16.bin` as optional; pack it into the field texture or a second texture
- [ ] 4.2 Shader and selector: "Chance of destruction" ramp to p99, legend end values, hidden when the layer is missing
- [ ] 4.3 Bridge details: P(destroyed) %

## 5. Viewer: live escape

- [ ] 5.1 `live.js`: probe `../api/predict/options` (3 s timeout); background `POST /api/predict/scenario` with the bundle's `predict`; keep `sid`; re-POST on 404
- [ ] 5.2 Inline UTM-45N → lon/lat inverse; test against 3 bundle points with known lon/lat
- [ ] 5.3 Terrain picking in 2D (ortho unproject) and 3D (raycast); "Where do I go?" toggle, keyboard reachable
- [ ] 5.4 Escape query at `t − burst_min`; re-query on slider release (250 ms debounce), never during playback
- [ ] 5.5 Draw path (green/amber Line2), red unsafe dots, destination flag, start pin; result card with edge-status copy
- [ ] 5.6 LinuxONE evidence badge from `host` plus the measured round trip
- [ ] 5.7 URL state: `q=lon,lat` reopens the query point

## 6. Aug 26 (stretch, 1 h time box)

- [ ] 6.1 Feasibility: `Valley(area=trishuli, proc=data/proc_trishuli)` plus `Scenario(V, aug26)` with out-of-grid observations excluded
- [ ] 6.2 If feasible, bake and validate `viewer/data/aug26/`; otherwise write the note in `docs/viewer/README.md`

## 7. Verify

- [ ] 7.1 Offline: `python3 -m http.server` shows no live controls and no console errors; existing `state.test.mjs` and `ui.cdp.mjs` still pass
- [ ] 7.2 Live through the tunnel: a click in Jagat at 03:50 gives a path in under 1 s (warm), and the badge shows s390x / big
- [ ] 7.3 Screenshots for the video: damage layer, a safe path, a path with unsafe points, the badge
