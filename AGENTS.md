# AGENTS.md: coordination between the team's coding agents

**Every agent: read this first, then `latinos-ibmz-datathon-plan.md` (spec) and `nepal-disaster-research.md` (background).**
Several agents are working on this repo at once. This file prevents duplicate work and stops agents from overwriting each other.

## Protocol
1. `git pull --rebase` **before starting any task and before every commit.**
2. **Claim a task** by adding or updating your row in the table below, then commit and push *right away*, before doing the work.
3. Don't edit files or VM directories that another agent has claimed. Ask your human to coordinate instead.
4. Push small commits often (at least every 30–45 min). Start commit messages with your agent ID, e.g. `[claude-luis] add HAND build`.
5. When you finish or stop, update your row (status, what's next, what's broken).
6. Never commit secrets: keys (`*.pem`/`*.cer`), the VM IP, tokens. The repo is **PUBLIC**.

## Agent registry
| Agent ID | Human / git author | Host / branch | Owns (don't edit without asking) | Status | Updated (ET) |
|---|---|---|---|---|---|
| `claude-luis` | Luis Rubiano (GitHub `larubiano0`) | Mac `luissmacbookpro` → drives the L1CC VM over SSH; pushes to `main` | `pipeline/`, `engine/terrain.py` `flood.py` `safety.py` `scenario.py` `alerts.py`, `api/`, `web/`, `replay/oct11.json`, VM `~/evac-ai` | Working: R (route lines) | Sat 14:55 |
| `agent-lcpizani` | `[redacted]` | branch `data/initial-datasets` (last push 11:44) | `data/processed/`, `data/docs/`, `scripts/{common,extract_osm,extract_landslides,fetch_dem,fetch_worldpop,record_dhm}.py` | **Please read this file, then take packet B** | — |
| _(teammate 3)_ | | | | add yourself, then take packet C, E or F | |
| _(teammate 4)_ | | | | add yourself, then take packet C, E or F | |

### ⚠️ For `agent-lcpizani`: your branch vs. `main`
- `main` **changed direction at 13:11**. The project is now **"Time to Safety"**: trigger → flood path → arrival time and height → walking time uphill to safe ground → slack per settlement → template alerts. See `latinos-ibmz-datathon-plan.md` §3–4. The road-segment risk model in the old plan is **replaced** by packet B below.
- Your datasets are **very useful and not duplicated**: the damage labels (2,759 destroyed and 415 damaged buildings from Aug 26), WorldPop, the 2015 landslides and the DHM recorder. `main` has its own OSM/DEM pull only for the Budhi Gandaki (VM `~/evac-ai/data/raw`, not in git).
- **Merging into `main`:** a test merge conflicts **only in `.gitignore`** (keep both sides' lines). Please merge your branch into `main` yourself (`git merge origin/main` on your branch, fix `.gitignore`, then merge into `main`). Files are ≤45 MB each, which is fine for GitHub.

## Timeline (ET): freeze **Sun 02:00**, submit **Sun 09:00**
| By | Milestone |
|---|---|
| Sat 16:00 | Packets A, C done. B has features built |
| Sat 19:00 | B trained + evaluated, integrated into the API. E, F drafts |
| Sat 22:00 | D validation numbers. Docker image on L1CC. Everything on `main` |
| Sun 01:00 | Screenshots, video script frozen, README final |
| Sun 02:00 | **FREEZE.** Only bug fixes and recording after this |
| Sun 08:30 | Video recorded and uploaded |
| Sun 09:00 | **Submitted** on Hack2Skill |

## Work packets (claim by putting your agent ID in Owner, then commit and push before starting)
| ID | Packet | Owner | Est. | Depends on | Done when |
|---|---|---|---|---|---|
| A | UI polish, Docker image, serving on L1CC | claude-luis | ✅ DONE 14:55 | — | `Dockerfile` (ubuntu:24.04 s390x + apt sci stack + GRASS), built in 91 s, 1.15 GB. Run: `bash scripts/docker_run.sh` (runs as uid of `data/` owner, port 127.0.0.1:8000). Container `evac-ai` is running |
| T | **Trishuli terrain build** on VM (same pipeline as Budhi Gandaki) | claude-luis | ✅ DONE 14:35 | — | `Terrain('data/proc_trishuli')` works: 121 km path from Rasuwagadhi, D8 99.7%. Example: `engine/debug_trishuli.py`. **Use OSM building coords, not hand-typed ones** (a 400 m error = 200 m of HAND on these slopes) |
| B | **ML damage model** (the judged "AI/ML on LinuxONE" piece) | **agent-lcpizani (proposed)** | 1.5–2 h | T (for HAND features), your damage labels | See spec below. Spatial-holdout AUC + "flagged X of Y destroyed" reported. Model file + `engine/damage_model.py` |
| C | `replay/aug26.json` (Aug 26 timeline as a replay) | free | 45 min | — | Same schema as `replay/oct11.json`. Times and gauge readings from `nepal-disaster-research.md` §1.3 and the Wikipedia timeline. Every number has a source URL |
| D | Validation numbers for the video | free (after B, C) | 45 min | B, C | Table: Oct 11 settlements predicted vs. reported; bridges predicted vs. lost (known miss: Soti, Arughat); Aug 26 footprint vs. destroyed buildings; arrival errors |
| R | **Route lines**: walking route from each at-risk settlement to its safe ground (r.walk `outdir` + `r.path`), shown on the map and in packet E | claude-luis | 45 min | — | Route polyline per settlement in `/api/scenario` (`route` field). Drawn in the UI |
| E | **Printable offline plan per settlement** (`web/plan.html?name=...`) | free | 45 min | API schema below | One A4 page per settlement: EN + NE full alert, arrival time, walk time, bridges to avoid, small map. Works offline once saved |
| F | README (architecture, run steps, **Libraries & Resources with links**, licenses), mermaid flowchart | free | 45 min | — | README meets plan §2. Attribution: Copernicus DEM, © OSM (ODbL), WorldPop CC BY 4.0, GRASS/SAGA/GDAL, FastAPI, Leaflet |
| G | Video script (≤3:00) + screenshot list | free (human + agent) | 1 h + recording | A, D | Script follows plan §9. Shows the L1CC instance and the model |
| H | **Nepali review** of `engine/alerts.py` templates | **human (Nepali reader)** | 15 min | — | Fix wording, set `NE_REVIEWED = True` |
| L | **Mandatory IBM labs** (both): Predictive Hybrid multi-model + Predictive + Generative | **humans, ASAP** | ? | — | Completed on the Hack2Skill dashboard (scoring prerequisite) |
| X | Stretch: Chamoli 2021 / Sikkim 2023 calibration points | free | 1.5 h | — | Rows of (event, km, minutes, height, source). Research §8 |

## Work queues (keep everyone busy: when you finish, take the next item in YOUR queue, then any `free` packet)
| Agent | Now | Next | Then |
|---|---|---|---|
| `claude-luis` | R: route lines | E: offline plan (if no one has taken it) | F, then D |
| `agent-lcpizani` | **B: ML damage model** (your labels + `data/proc_trishuli`) | C: `replay/aug26.json` | D: validation numbers |
| teammate 3 agent | C or F | E | G: video script |
| teammate 4 agent | F or E | G | X: stretch calibration |
| humans | **L: mandatory labs** (everyone, now) | H: Nepali review | G: record video (Sun 06:00–08:30) |

**Routing ownership:** routing (walking time to safety, route lines, bridge "don't cross") belongs to `claude-luis` in `engine/safety.py` / `engine/scenario.py`. `agent-lcpizani` should **not** build a separate router. The old-plan "capacity-aware router" is dropped, since there's no documented congestion (research §7.5).

**Running packet B on the VM:** `cd ~/work-agent-lcpizani` (your own dir). Import the engine from `~/evac-ai` with `sys.path.insert(0, '/home/linux1/evac-ai')`. Load `Terrain('/home/linux1/evac-ai/data/proc_trishuli')`. Snap the source at the Rasuwagadhi border (lon 85.383, lat 28.276, `radius=15`), then `downstream_path` and `hand_to(path)`. Read-only use of `~/evac-ai/data` is fine.

### Packet B spec: building damage model
- **Labels:** Aug 26 OSM buildings. Positive = `destroyed:building` (+ optionally `damaged:building`). Negative = other buildings in the same corridor, within ~2 km of the river.
- **Features per building** (from `engine.terrain` on the Trishuli build + OSM): HAND relative to the flood path, river km from the source, distance to channel, local slope, valley width (cross-section), flow accumulation, channel curvature / outside of bend, building size, distance to the nearest 2015 landslide.
- **Model:** `sklearn.ensemble.HistGradientBoostingClassifier` (installed via apt on the VM, trains in seconds). **Spatial holdout:** split by river km (e.g. train upstream ≤ X km, test below), not randomly.
- **Report:** AUC, precision/recall at the top-k, "flagged X of Y destroyed buildings", feature importances.
- **Integrate:** `engine/damage_model.py` with `features(scenario) -> array` and `predict(scenario) -> prob per building`. The API adds `p_destroyed` per building and a settlement mean. Train on Trishuli, apply to Budhi Gandaki Oct 11.
- **LinuxONE angle:** train and run inference on the VM (s390x). Optional: try IBM Snap ML / zDNN on the **NNPA** accelerator (present on our VM). Only if it installs in <10 min.

### Interfaces (stable, don't break without telling the others)
- `GET /api/scenario?replay=oct11&warn=HH:MM` → `{summary, settlements[], bridges_at_risk[], path (GeoJSON line with stations[]), timing, host}`. Each settlement has `name, name_ne, lon, lat, buildings_at_risk, people_at_risk, people_without_time, river_km, arrival_early, walk_min_median, walk_min_max, slack_min, status, alert_rank, alerts{short_en, short_ne, full_en, full_ne}`.
- `GET /api/compare?replay=oct11` · `GET /api/footprint` (GeoJSON) · `POST /api/trigger {lon, lat, burst, warn, replay}`.
- `engine.scenario.Valley(proc, raw)` / `Scenario(V, replay_dict, ...)`. Run everything **from the repo root on the VM** with system `python3` or `~/venv/bin/python`.

### VM etiquette (one shared 3-CPU / 7.8 GB machine)
- Own working dir per agent: `~/work-<agent-id>`. Don't touch `~/evac-ai` (`claude-luis` rsyncs into it).
- Ports: `8000` = claude-luis. Others use 8001–8003. Port 8000 is **blocked externally**, so all access goes through an SSH tunnel (`ssh -L 8001:localhost:8001 ...`).
- Jobs must be short and bounded (`timeout`), with no unattended long runs. Tell your human before anything over ~5 min.

## Key findings other agents must know (don't rediscover these)
- **`r.walk` cost runs FROM start TO cell** (uphill costs more). For time *to* safety, run it on a **negated DEM** with safe cells as the start. Verified with `pipeline/test_rwalk_direction.sh` (1841 s both ways).
- Overpass needs a **User-Agent header** or `overpass-api.de` returns 406 (see `pipeline/overpass.py`).
- Most Python packages have no s390x pip wheels, but **they're already installed via apt**.
- Search engines rate-limit the agents. Use Wikipedia's API and WordPress `?s=` site search on Nepali news sites (e.g. english.onlinekhabar.com).
- BIPAD API `bipadportal.gov.np/api/v1/{river,rain,incident,alert}` is public. Its query filters seem to be ignored.

## Log (newest first; one line per entry)
- Sat 14:19 [claude-luis] Packet A DONE: Docker on L1CC. Dockerfile + scripts/docker_run.sh; image builds in 91 s (1.15 GB, s390x). Container evac-ai serves the UI on 127.0.0.1:8000 (SSH tunnel), results identical to bare metal. Gotcha: run the container with --user <uid of data/> -e HOME=/tmp, or GRASS says 'MAPSET permission denied'. g.sh now finds grassdb relative to the repo. Starting R (route lines).
- Sat 14:16 [claude-luis] Packet T DONE: data/proc_trishuli built (2663x2730, 10 s), 121 km Bhotekoshi-Trishuli path, D8 99.7%. Added per-agent WORK QUEUES to AGENTS.md. Routing stays with claude-luis (added packet R: route lines). agent-lcpizani -> B (ML), then C, then D. pipeline/build_valley.sh works for any valley.
- Sat 14:13 [claude-luis] COORDINATION: found agent-lcpizani's branch data/initial-datasets (Aug 26 damage labels, WorldPop, 3-district DEM). Rewrote AGENTS.md: registry, timeline, work packets A-X with estimates, Packet B (ML damage model) proposed for agent-lcpizani, API interfaces, VM etiquette. UI fixes (fit to valley, visible footprint, legend).
- Sat 14:03 [claude-luis] web/index.html written (Leaflet: trigger comparison, ranked alert list with EN/NE alerts, footprint, bridges at risk, wave-clock slider, click-to-place new trigger). NOT yet tested in a browser. scripts/api_smoke.sh added.
- Sat 14:02 [claude-luis] API works ON L1CC (s390x, big-endian): api/app.py with /api/scenario, /compare, /footprint, POST /trigger; 4.5 s per new scenario, 0.05 s cached. engine/alerts.py: EN short ~100 chars, NE short 62-69 chars (1 UCS-2 SMS, <=161 B, Meshtastic OK); Nepali is a DRAFT, needs review. Bridges at risk match the reported lost Dobhan/Machhakhola/Sirdibas bridges but MISS Soti + Arughat (lower-valley height too low; known gap). Port 8000 is blocked externally, so we use an SSH tunnel. Next: web/index.html (Leaflet).
- Sat 13:59 [claude-luis] engine/scenario.py: per-building slack for 112,515 OSM buildings, 20 settlements at risk (~1,456 people, assuming 4 per building), 4.5 s per scenario. HEADLINE: 03:30 village relay = 0 people without time (matches no confirmed deaths); 06:40 official SMS = all 1,456 without time. Fixed r.walk gaps in the barrier strip (nearest-cell fill). Next: FastAPI + Leaflet UI (claiming api/ and web/).
- Sat 13:57 [claude-luis] Oct 11 end-to-end WORKS on VM: calibrate -> footprint (11.3 km2, conservative) -> r.walk time-to-safety in 3.9 s. Walk to safe ground is only 1-3 min (Jagat/Salleri/Soti), so warning lead time is what matters. Added replay/oct11.json, engine/flood.py, engine/safety.py, engine/test_oct11.py. Next: per-building analysis + settlements + slack per trigger (03:30 relay vs 06:40 SMS).
- Sat 13:55 [claude-luis] engine/terrain.py works: D8 99.7% downhill, Oct 11 path 94.8 km (Arughat at km 62.5). HAND at known places is plausible (Salleri 17 m, Jagat 23, Soti 14, Philim 150), 0.2 s per event. Caveat: Oct 11 timestamps conflict (Soti 07:30 after Arughat 06:30), so the first wave is calibrated on Jagat ~04:00 and Arughat 06:30 (~17 km/h). Next: engine/flood.py + time-to-safety with r.walk.
- Sat 13:54 [claude-luis] Terrain: r.watershed streams OK (align with OSM Budhi Gandaki: median 30 m). SAGA HAND gave ~0 m everywhere (Philim terrace = 0), so I dropped it. Implementing standard HAND (Nobre 2011) in engine/terrain.py: follow the r.watershed D8 directions to the event's flood channel.
- Sat 13:51 [claude-luis] Claimed engine/ (flood path, arrival, height, time-to-safety) in addition to pipeline/. Now: streams via r.watershed stream= output (r.stream.extract too slow).
- Sat 14:00 [claude-luis] `r.stream.extract` on the full 3.7M-cell grid timed out after 200 s. Next: cut the region to the river corridor, or use `r.watershed` stream output instead.
- Sat 13:55 [claude-luis] `r.watershed` OK, `r.walk` direction verified, DEM clipped to UTM45N 30 m (1357×2748, 335–7148 m).
- Sat 13:40 [claude-luis] OSM pulled: 114,910 buildings, 517 places, waterways, highways, bridges. DEM tiles N27–28 E084–085.
- Sat 13:10 [claude-luis] L1CC probe done; plan rewritten; research pushed.
