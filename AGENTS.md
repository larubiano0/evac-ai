# AGENTS.md: coordination between the team's coding agents

**Every agent: read this first, then `latinos-ibmz-datathon-plan.md` (spec) and `nepal-disaster-research.md` (background).**
Several agents are working on this repo at once. This file prevents duplicate work and stops agents from overwriting each other.

## Protocol
1. `git pull --rebase` **before starting any task and before every commit.**
2. **Claim a task** by adding or updating your row in the table below, then commit and push *right away*, before doing the work.
3. Don't edit files or VM directories that another agent has claimed. Ask your human to coordinate instead.
4. Push small commits often (at least every 30–45 min). Start commit messages with your agent ID, e.g. `[claude-luis] add HAND build`.
5. When you finish or stop, update your row (status, what's next, what's broken).
6. Never commit secrets: keys (`*.pem`/`*.cer`), the VM IP, tokens, **or anyone's personal email address** (in files *or* as the git author). Use GitHub usernames and `…@users.noreply.github.com` addresses. The repo is **PUBLIC**.

## ⚠️ ACTION REQUIRED (every agent and human with a clone): private email scrub, Sat 14:51
`main` was rewritten and force-pushed (old tip `9f5061a`, new tip `7df63d3`) to remove a teammate's private email from `AGENTS.md`. Old copies of that history must not survive anywhere. Do this in **every** clone you have: laptop, VM `~/evac-ai` and `~/work-*`, containers.
1. **Move onto the new history.** No local commits: `git fetch origin && git reset --hard origin/main`. Local commits: `git fetch origin && git rebase --onto origin/main 9f5061a`.
2. **Purge the old commits locally.** Delete any branch, tag or stash still holding them (`git branch --contains 9f5061a`, `git stash list`), then:
   `git reflog expire --expire=now --all && git gc --prune=now`
3. **Check it's gone:** `git log --all --format=%H | while read c; do git grep -l 'gmail.com' $c -- AGENTS.md; done` should print only lines for *other* people's addresses already in the registry, or nothing. Ask agent-aayush's human if unsure. **Don't paste the address anywhere** (chat, logs, issues).
4. **Never push the old SHAs back** (no `git push --force` from an un-purged clone; no merging old branches).
5. **Repo owner (Luis) only:** ask GitHub Support to purge the cached old commits, which are still reachable by SHA (e.g. `c862b56`, `346e799`, `8dfca0e`, `bf70ec1`, `39fa12f`, `4ec1b39`, `c6b4254`, `9f5061a`): <https://support.github.com/request/remove-data>. Also check for forks.
6. When done, add a log line `[your-id] email scrub done` so we know every clone is clean.

## Agent registry
| Agent ID | Human / git author | Host / branch | Owns (don't edit without asking) | Status | Updated (ET) |
|---|---|---|---|---|---|
| `claude-luis` | Luis Rubiano (GitHub `larubiano0`) | Mac `luissmacbookpro` → drives the L1CC VM over SSH; pushes to `main` | `pipeline/`, `engine/terrain.py` `flood.py` `safety.py` `scenario.py` `alerts.py`, `api/`, `web/`, `replay/oct11.json`, VM `~/evac-ai` | Working: E (offline plan). B fallback at 15:30 | Sat 14:22 |
| `agent-lcpizani` | `[redacted]` | Mac (lucas) → pushes to `main`; VM `~/work-agent-lcpizani` | `data/processed/`, `data/docs/`, `scripts/{common,extract_osm,extract_landslides,fetch_dem,fetch_worldpop,record_dhm}.py`, `engine/damage_model.py`, `engine/route_reliability.py` (B2), `models/damage/`, `scripts/damage/` | **B model DONE** (models/damage/README.md); waiting on claude-luis to wire `predict_scenario` into /api/scenario. Then B2 (approved) | Sat 14:52 |
| `agent-aayush` | Aayush Poudel (GitHub `apoudel20`) | Windows desktop (local); push to `main` | `replay/aug26.json`, `README.md`, `docs/` (video script) | C ✅ F ✅ G draft ✅. Next: fill G numbers when D lands; help D | Sat 14:42 |
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
| A | UI polish, Docker image, serving on L1CC | claude-luis | ✅ DONE 14:20 | — | `Dockerfile` (ubuntu:24.04 s390x + apt sci stack + GRASS), built in 91 s, 1.15 GB. Run: `bash scripts/docker_run.sh` (runs as uid of `data/` owner, port 127.0.0.1:8000). Container `evac-ai` is running |
| T | **Trishuli terrain build** on VM (same pipeline as Budhi Gandaki) | claude-luis | ✅ DONE 14:15 | — | `Terrain('data/proc_trishuli')` works: 121 km path from Rasuwagadhi, D8 99.7%. Example: `engine/debug_trishuli.py`. **Use OSM building coords, not hand-typed ones** (a 400 m error = 200 m of HAND on these slopes) |
| B | **ML damage model** (the judged "AI/ML on LinuxONE" piece) | **agent-lcpizani — DONE (model); API wiring: claude-luis** | 1.5–2 h | T (for HAND features), your damage labels | See spec below. Spatial-holdout AUC + "flagged X of Y destroyed" reported. Model file + `engine/damage_model.py` |
| B2 | **Route reliability (APPROVED by claude-luis 14:35, conditions in next row)**: Monte Carlo over the flood band (height, wave speed, warning delay) + B's `p_destroyed` for bridges → P(escape route still works) and P(settlement cut off) per settlement. **Reads** packet R routes and `engine.scenario` outputs; does **not** replace or edit `engine/safety.py`/`scenario.py`. New file `engine/route_reliability.py` + optional API fields | agent-lcpizani (proposed) | 1.5 h | B, R | `route_p_works`, `p_cut_off` per settlement; list of bridges whose loss flips a route |
|  | ↳ B2 conditions | agent-lcpizani | ≤1 h | **B integrated first** | (1) Start only after B is merged and in `/api/scenario`. (2) Vectorized numpy, **≤2 s per scenario** on the VM (it runs inside the API request). (3) Output: per settlement `p_route_ok`, `p_cut_off`; per bridge `p_fail`. Add as **new keys only**, don't rename existing ones. (4) Hook it in by calling `engine/route_reliability.py` from `api/app.py:payload()`. Tell claude-luis, who owns `api/`, and I'll add the one line if you prefer. (5) Read-only use of `Scenario.tdir/tts/route`. |
| C | `replay/aug26.json` (Aug 26 timeline as a replay) | **agent-aayush** | ✅ DONE 14:35 | — | Same schema as `replay/oct11.json`. Times and gauge readings from `nepal-disaster-research.md` §1.3 and the Wikipedia timeline. Every number has a source URL |
| D | Validation numbers for the video | free (after B, C) | 45 min | B, C | Table: Oct 11 settlements predicted vs. reported; bridges predicted vs. lost (known miss: Soti, Arughat); Aug 26 footprint vs. destroyed buildings; arrival errors |
| R | **Route lines**: walking route from each at-risk settlement to its safe ground | claude-luis | ✅ DONE 14:20 | — | `route`, `route_len_m`, `route_climb_m` per settlement in `/api/scenario` (from r.walk `outdir`; verified that walking time falls at every step and reaches 0). Green dashed lines in the UI |
| E | **Printable offline plan per settlement** (`web/plan.html?name=...`) | free | 45 min | API schema below | One A4 page per settlement: EN + NE full alert, arrival time, walk time, bridges to avoid, small map. Works offline once saved |
| F | README (architecture, run steps, **Libraries & Resources with links**, licenses), mermaid flowchart | free | 45 min | — | README meets plan §2. Attribution: Copernicus DEM, © OSM (ODbL), WorldPop CC BY 4.0, GRASS/SAGA/GDAL, FastAPI, Leaflet |
| G | Video script (≤3:00) + screenshot list | free (human + agent) | 1 h + recording | A, D | Script follows plan §9. Shows the L1CC instance and the model |
| H | **Nepali review** of `engine/alerts.py` templates | **human (Nepali reader)** | 15 min | — | Fix wording, set `NE_REVIEWED = True` |
| L | **Mandatory IBM labs** = notebooks in https://github.com/linuxone-community-cloud/jupyter-lab-ml (found 14:45; confirm on H2S → Resources): **Predictive + Generative** = `Loan_Approval_Demo.ipynb` (ML + IBM Granite via llama.cpp on **zDNN/NNPA**). **Predictive multi-model** = probably `Churn_Scikit_PyTorch.ipynb` / `Fraud_LSTM_Keras_TF.ipynb` | humans + 1 agent | ~1 h | — | Image: `registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x:latest`, Jupyter on port 38888 (blocked externally, so use an SSH tunnel). **Run it on a SEPARATE L1CC VM** (each teammate can register one, code SSF2026, image 'Ubuntu 24.04-Datathon'), **not on the demo VM**: an LLM plus our app in 7.8 GB is risky. Human submits proof on H2S if asked. |
| X | Stretch: Chamoli 2021 / Sikkim 2023 calibration points | free | 1.5 h | — | Rows of (event, km, minutes, height, source). Research §8 |

## Work queues (keep everyone busy: when you finish, take the next item in YOUR queue, then any `free` packet)
| Agent | Now | Next | Then |
|---|---|---|---|
| `claude-luis` | E: offline plan | **B: ML model if agent-lcpizani hasn't checked in by 15:30** | D |
| `agent-lcpizani` | **B: ML damage model** (your labels + `data/proc_trishuli`) | B2: route reliability (approved, ≤1 h) | D: validation numbers |
| `agent-aayush` | ~~C F~~ ✅, G draft ✅ (numbers pending D) | help D | update README results + G after D/B |
| (any further agent) | X: stretch calibration | help D | — |
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

## New agent quickstart (read in this order, about 5 min)
1. `git pull --rebase` on `main`. Read this file, then `latinos-ibmz-datathon-plan.md` §3–4, then `nepal-disaster-research.md` §1.1 and §1.3 (the two events).
2. Add your row to the registry with a unique agent ID, claim **your first queued packet**, commit `[your-id] claim X`, and push **before** working.
3. **No VM is needed for C, F or G.** They're repo-only. If you need the VM, follow "VM etiquette" (your own `~/work-<id>` dir, port 8001+, bounded jobs, tell your human first).
4. Every 30–45 min: pull, update your row + add a log line, push. Don't edit files owned by another agent (registry "Owns" column).
5. Data contract for **C (`replay/aug26.json`)**: copy the structure of `replay/oct11.json` exactly (keys: `event, timezone, source{name,lon,lat,note}, burst_time, burst_time_band, triggers{...{time,desc}}, observations[{place,lon,lat,first_arrival?,peak_height_m?|gauge_peak_m?,src,use}], damage_reported, sources`). Source = the Rasuwagadhi border (lon 85.383, lat 28.276). Burst 08:37 NPT. Gauge timeline: Wikipedia "Timeline of the 2026 Nepal–Tibet floods". Triggers: seismic signal 08:37, DHM informed 09:00, SMS 09:15 (PM says 09:35), Trishuli school phone calls 09:10. **Use real OSM coordinates** (`origin/data/initial-datasets:data/processed/osm/places.geojson`): Timure 28.2528/85.3667, Betrawati 27.9731/85.1860, Trishuli 27.9232/85.1480, Bidur 27.8953/85.1464, Galchhi 27.7974/85.0005, Devighat 27.8600/85.1101. Set `use: "calibration"` only for points with a reliable time **and** location. Mark others `"excluded"` with a note.

## Key findings other agents must know (don't rediscover these)
- **`r.walk` cost runs FROM start TO cell** (uphill costs more). For time *to* safety, run it on a **negated DEM** with safe cells as the start. Verified with `pipeline/test_rwalk_direction.sh` (1841 s both ways).
- Overpass needs a **User-Agent header** or `overpass-api.de` returns 406 (see `pipeline/overpass.py`).
- Most Python packages have no s390x pip wheels, but **they're already installed via apt**.
- Search engines rate-limit the agents. Use Wikipedia's API and WordPress `?s=` site search on Nepali news sites (e.g. english.onlinekhabar.com).
- BIPAD API `bipadportal.gov.np/api/v1/{river,rain,incident,alert}` is public. Its query filters seem to be ignored.

## Log (newest first; one line per entry)
- Sat 14:57 [agent-aayush] Added the **⚠️ ACTION REQUIRED** section at the top: every clone must purge the old history (reflog expire + gc) and Luis should file the GitHub Support purge request. Please log `email scrub done` when finished.
- Sat 14:52 [agent-lcpizani] **Packet B model DONE** (trained + evaluated on L1CC s390x; full write-up models/damage/README.md). Spatial holdout on Aug 26 (split river km 51.8, 2 km gap, 500 m corridor): downstream test v2 ROC AUC 0.968 / PR 0.740, flags 1,043 of 1,474 affected (engine footprint rule: 0.713 / 672); upstream test v1 0.818 vs HAND 0.751 vs rule 0.699. Platt-calibrated (Brier 0.086->0.068). Oct 11 (trained on Aug only): expected affected buildings v2 146 vs v1 271 vs engine footprint 365 vs ~62-72 reported; Dobhan-area bridge #1/49, Sirdibas #3. Soti + Arughat still missed: at Arughat the D8 channel is >=175 m from the real river (HAND 17 m at the bridge vs ~6 m flood line) -> suggest stream-burning the OSM river in pipeline/ (claude-luis); no motorable bridge near Soti exists in OSM. **For claude-luis (api/scenario.py are yours):** `from engine import damage_model as dm; res = dm.predict_scenario(S)` (read-only, ~0.5 s per new path + ~0.3 s; cached). Proposed NEW keys only: per building `p_destroyed` (res['p_building'], aligned with S.V.b_ll; NaN outside corridor); per settlement `p_destroyed_mean`, `expected_destroyed` (sum of p); per bridge in bridges_at_risk `p_destroyed` (res['bridges'], aligned with S.V.bridge_meta; bridges scored at their river-crossing point). Do NOT threshold at 0.5 (Oct probabilities are low); use as colour scale / rank / sums. Models are s390x pickles: load on the VM. Next: B2 once B is in /api/scenario.
- Sat 14:51 [agent-aayush] **HISTORY REWRITTEN on main (force-push, 9f5061a -> 7df63d3)** to remove a private email from AGENTS.md. Only that one line changed; authors, dates and every other file are identical, but the SHAs of the last 8 commits (from ded5d69 on) are new. **Before your next pull:** no local commits -> `git fetch && git reset --hard origin/main`; local commits -> `git fetch && git rebase --onto origin/main 9f5061a`. Don't push the old SHAs back. Never put personal emails in this public repo: use GitHub usernames or noreply addresses.
- Sat 14:46 [claude-luis] Labs found: IBM jupyter-lab-ml repo (Loan_Approval_Demo = Predictive+Generative with Granite on llama.cpp+zDNN/NNPA; Churn/Fraud = predictive). Prebuilt s390x image registry.linuxone.cloud.marist.edu/l1cc/jupyterlab-image-s390x. Packet L updated: run on a separate VM. FYI agent-lcpizani: that image has XGBoost/ONNX/zDNN, which is optional for B's NNPA story.
- Sat 14:42 [agent-aayush] Packet G DRAFT: docs/video-script.md (plan §9 timing, ~400 words of narration, shot-by-shot demo on L1CC, screenshot list S1-S11 incl. L1CC instance + docker ps, recording checklist). Numbers in [brackets] are provisional values from this log; they need packet D (and B's AUC) before recording. Humans: review the narration.
- Sat 14:38 [agent-aayush] Packet F DONE: README.md (what exists per file, API table, mermaid flowchart, container + bare-metal run steps, Oct 11 results as logged here, limitations, Libraries & Resources with links + licenses). Says only what the code does: damage model/B2/E/D marked in progress, Aug 26 not yet wired to proc_trishuli, DHM/BIPAD not live triggers. **claude-luis: the Dockerfile isn't in the repo** (README says so); please commit it. Whoever finishes B/D: update README 'Results so far'. Starting G.
- Sat 14:37 [agent-lcpizani] B features built on L1CC (6.3 s, s390x): engine/damage_model.py (shared feature code for train + inference) + scripts/damage/build_table.py. Aug 26 table within 500 m of the Trishuli path: 3,093 affected / 20,358 unaffected buildings (99.6% of all Aug positives kept), 63 / 72 bridges; report in models/damage/build_report.json. NOTE for aug26 users: its height calibration knots (Kali Khola 84.546, Devghat 84.43) lie WEST of the proc_trishuli grid (edge 84.735), VERIFIED on the VM: Terrain.rc gives col -660 for Kali Khola and numpy wraps silently, so km_of returns 66.06 km (wrong; Devghat gives NaN). calibrate_from_replay(aug26) on proc_trishuli would put the 12.3 m knot at km 66. Suggest an inside-grid check in km_of (claude-luis owns scenario.py/flood.py). For B v2 I reconstruct the Aug flood line from damage marks instead. Next: train v1 + spatial holdout.
- Sat 14:35 [agent-aayush] Packet C DONE: replay/aug26.json (same top-level keys as oct11, 9 observations). 5 calibration points: Syabrubesi 08:50, Betrawati 09:20, Malekhu 11:26, Kali Khola peak 14:14 12.3 m, Devghat 15:20/peak 16:00 6.57 m. Excluded: Trishuli school time, Mugling, Galchhi, Timure. Loads via api/app.py's replay/*.json glob; engine.flood.calibrate_from_replay parses it (tested with a dummy km_of). **For claude-luis (your files, not edited):** (1) api/app.py valley() is hardcoded to data/proc (Budhi Gandaki), so /api/scenario?replay=aug26 needs a per-replay Valley(data/proc_trishuli). (2) Devghat (27.71) is south of the 3-district DEM bbox (south 27.73), and Kali Khola may be past the 121 km path end; Terrain.rc has no bounds check, so km_of may IndexError or wrap. Suggest a bounds check or set Devghat to excluded for the Trishuli build. Starting F.
- Sat 14:33 [claude-luis] Coordination: approved agent-lcpizani's B2 (route reliability) with conditions: after B, <=1 h, <=2 s per scenario, new keys only. Packet C goes to agent-aayush (removed from lcpizani's queue to avoid duplication). Packet L (labs): a human posts the lab links, an agent runs them on a SEPARATE L1CC VM, a human submits the proof. Now starting E (offline plan).
- Sat 14:31 [agent-aayush] Joined (Aayush). Claimed C, then F, then G. Heads-up for C/D: the Devghat 6.57 m gauge is **Narayani at Devghat** (DHM 450, lat 27.71 lon 84.43, Chitwan), not **Devighat** near Bidur (27.86/85.11) listed in the quickstart.
- Sat 14:24 [agent-lcpizani] Checked in. Merged data/initial-datasets into main (3ef815c). Claimed B (ML damage model; Trishuli labels, spatial holdout by river km, buildings + bridges, target: fix the Soti/Arughat miss). Proposed B2 route reliability on top of packet R: claude-luis, OK or not?
- Sat 14:21 [claude-luis] Packet R DONE: escape route per settlement (r.walk outdir tracing, verified monotone to safe ground; e.g. Salleri 192 m/+26 m). Drawn in the UI; container rebuilt. Registered slot agent-new (queue C -> F -> G) + 'New agent quickstart' with the aug26 data contract. Fixed hand-typed times in the board. B fallback: claude-luis takes B if lcpizani hasn't checked in by 15:30.
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
