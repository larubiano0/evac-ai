# evac-ai: "Time to Safety" flash-flood warning

**IBM Z Datathon 2026 · team Latinos** · runs on an IBM z17 in LinuxONE Community Cloud · [AI on the Telum on-chip accelerator](docs/linuxone-ai.md) · [Documentation](docs/README.md) · [Sources](docs/sources.md)

> Nepal can't predict when the mountain falls. It can predict who has time to run.

In Nepal's two most recent flash floods the gauges failed first and people did the warning.
On **Oct 11, 2026 (Budhi Gandaki, Gorkha)** a relayed phone warning reached Dharche at about 03:30; the
official SMS went out at 06:40, after the first wave hit Arughat (about 06:30). On **Aug 26, 2026
(Bhotekoshi–Trishuli, Rasuwa/Nuwakot)** four gauges were destroyed, DHM learned of the flood by phone, and the
SMS was generic, Nepali-only and gave no time-to-impact. Background and sources:
[`docs/idea/nepal-disaster-research.md`](docs/idea/nepal-disaster-research.md).

evac-ai turns **one upstream observation** (a report, a gauge going silent, a pin on the map) into a
**per-settlement action plan within seconds**: when the wave arrives, how high it gets, how long it takes to
walk uphill to safe ground, which bridges not to cross, and who has no time left. Those people get warned first.

```
slack = first-wave arrival (early band) − (warning time + 5 min dissemination + walking time to safe ground)
```

A settlement is **red** if any of its at-risk buildings has slack < 0, **amber** if the minimum slack is under
15 min, and **green** otherwise. Alerts are ordered by earliest arrival, then by people at risk.

---

## What exists today

| Piece | File(s) | What it does |
|---|---|---|
| Terrain model | [`engine/terrain.py`](engine/terrain.py) | Loads the GRASS DEM, D8 flow directions, streams and accumulation. Snaps a trigger to the channel, traces the downstream flood path, computes **HAND** (height above nearest drainage, Nobre et al. 2011) against that path by pointer jumping on the D8 graph |
| Flood envelope | [`engine/flood.py`](engine/flood.py) | Not a hydrodynamic model. Two 1-D curves along river km: arrival time and peak height, linearly interpolated between calibration knots from a replay file, with ±25 % time and ±30 % height bands. Height decays exponentially toward a 3 m floor beyond the last knot |
| Time to safety | [`engine/safety.py`](engine/safety.py) | GRASS **r.walk** (Naismith/Langmuir anisotropic walking cost) on the **negated** DEM, with safe cells as the start, so each step has the same climb as the real escape. The flood channel is a barrier except at OSM bridge cells. Traces a walking route to safe ground from `r.walk`'s direction output |
| Scenario runner | [`engine/scenario.py`](engine/scenario.py) | Per OSM building: in the footprint or not, arrival, walk time, slack. Per settlement (buildings within 3 km of an OSM place): people at risk (4 per building, an assumption), people without time, status, alert rank, escape route. Bridges at risk = OSM bridges in the footprint or on the path |
| Template alerts | [`engine/alerts.py`](engine/alerts.py) | No LLM. English and Nepali, short (1 SMS / Meshtastic / cell-broadcast page) and full (plan page). The Nepali text was reviewed by a native Nepali reader on our team (`NE_REVIEWED = True`) |
| Damage model | [`engine/damage_model.py`](engine/damage_model.py), [`models/damage/`](models/damage/) | Gradient-boosted trees (scikit-learn) trained on the buildings tagged destroyed (2,759) or damaged (415) after the Aug 26 flood, 3,093 of them within 500 m of the river: P(destroyed) for every building and bridge near the river. [Write-up](docs/models/damage.md) |
| Flood-area model | [`models/area/`](models/area/) | `area_fb`, trained on UNOSAT satellite flood maps: P(flooded) for every 30 m square near the river. Drives the risk map in prediction mode. [Write-up](docs/models/area.md) |
| Prediction mode | [`engine/escape.py`](engine/escape.py), [`engine/escape_search.c`](engine/escape_search.c), [`web/predict.html`](web/predict.html) | "Where should I go?": from any point and time, the closest safe ground, the walking route (Tobler walking speed on the DEM + OSM trails, river crossed only on bridges), a leave-by time and one instruction (stay / leave / hurry / run / climb) |
| What-if map | [`engine/whatif.py`](engine/whatif.py), [`engine/surrogate.py`](engine/surrogate.py), [`scripts/nnpa/zdnn_mlp.c`](scripts/nnpa/zdnn_mlp.c) | Scores every 30 m square under 100 possible flood heights (±30 %) with a neural copy of `area_fb`, run on the z17 Telum on-chip AI accelerator through IBM zDNN. Shows ground that is safe in this flood but not in a bigger one. [Write-up](docs/linuxone-ai.md) |
| API | [`api/app.py`](api/app.py) | FastAPI. Keeps the valley in memory and caches scenarios. Endpoints below |
| Landing page | [`web/landing.html`](web/landing.html) | `/`: the story in one screen and links to the three views |
| Officials' planner | [`web/index.html`](web/index.html) | `/planner`, Leaflet 2D: trigger comparison ("who had time to escape?"), warning-time box, wave-clock slider, footprint, ranked alert list with EN/NE alerts, bridges at risk, green dashed escape routes, click-to-place new trigger, damage-model colours, what-if map |
| Resident "Go" view | [`web/go.html`](web/go.html), [`web/go-sw.js`](web/go-sw.js) | `/go`: for someone in a panic on a phone. Location from GPS (or `?lat=&lon=&t=` for demos, or a tap), one big instruction (GO UPHILL NOW / HURRY / YOU ARE SAFE HERE), countdown, leave-by time, arrow and route to the safe place, EN/नेपाली. Uses the prediction API read-only. Works offline (below) |
| Replays | [`replay/oct11.json`](replay/oct11.json), [`replay/aug26.json`](replay/aug26.json) | Event timelines: source point, burst time and band, warning triggers, observations (each marked `calibration` or `excluded` with a note and a source), reported damage, source URLs |
| Terrain build | [`pipeline/`](pipeline/) | DEM + OSM download, GRASS `r.watershed` build per valley ([`build_valley.sh`](pipeline/build_valley.sh)), GRASS wrapper [`g.sh`](pipeline/g.sh), `r.walk` direction test |
| Study-area data | [`data/`](docs/data/README.md), [`scripts/`](scripts/) | Committed, clipped layers for Gorkha/Rasuwa/Nuwakot: Copernicus DEM, WorldPop, OSM (incl. Aug 26 damage labels), 2015 landslides, DHM feed snapshot. Fetch/extract scripts |
| 3D replay | [`viewer/`](viewer/) | Static Three.js viewer: a real flood moving down the valley on the real terrain, with a time slider. [Docs](docs/viewer/README.md) |
| Container | [`Dockerfile`](Dockerfile), [`scripts/docker_run.sh`](scripts/docker_run.sh) | One image with everything above, run on L1CC and served on `127.0.0.1:8000` |

**Not built yet:** serving the Aug 26 replay from the planner API (validation runs it on the Trishuli build), live DHM/BIPAD
triggers, and the phone-to-phone mesh relay.

### API

| Endpoint | Returns |
|---|---|
| `GET /api/replays` | Available replays with burst time and triggers |
| `GET /api/scenario?replay=oct11&warn=HH:MM` | `{summary, settlements[], bridges_at_risk[], path, wave_speeds_kmh, timing, host}`. Each settlement has `name, name_ne, lon, lat, buildings_at_risk, people_at_risk, people_without_time, river_km, arrival_early, walk_min_median, walk_min_max, slack_min, status, alert_rank, route, alerts{short_en, short_ne, full_en, full_ne}` |
| `GET /api/compare?replay=oct11` | The summary for each trigger time in the replay (e.g. community relay 03:30 vs. official SMS 06:40) |
| `GET /api/footprint?replay=oct11[&lon=&lat=&burst=]` | Conservative inundation footprint, GeoJSON |
| `POST /api/trigger {lon, lat, burst, warn, replay}` | Full scenario for a new trigger point, reusing the wave-speed/height curves calibrated on `replay` |
| `GET /api/predict/options` | Valleys and flood types available to prediction mode |
| `POST /api/predict/scenario` | Builds (and caches) a prediction scenario: a trigger point + a flood type calibrated on a real flood |
| `GET /api/predict/p.png` | The per-square flood-risk map as a PNG overlay |
| `POST /api/predict/escape` | "Where should I go?" for one point and time: destination, route, leave-by, instruction (2–5 ms) |
| `GET /api/predict/whatif?valley=budhi&n=100`, `/api/predict/whatif.png` | What-if floods: every 30 m square under 100 flood heights (±30 %), run on the Telum on-chip AI accelerator ([docs/linuxone-ai.md](docs/linuxone-ai.md)) |
| `GET /` · `/planner` · `/predict` · `/go` | Landing page · officials' planner · "Where should I go?" · resident Go page (+ `/go-sw.js`, its offline service worker) |

`/api/scenario` also carries the damage model's output as additional keys: `p_destroyed_mean`, `expected_destroyed` and
`n_scored` per settlement, `p_destroyed` per bridge, and a `damage_model` block.

---

## Architecture

Big picture below; every component, file and port is in [`docs/architecture.md`](docs/architecture.md).

```mermaid
flowchart TB
  SEE["Someone sees a flood start<br/>(phone call from upstream, river gauge, seismic signal)<br/><i>'the river burst here, at 03:45'</i>"]

  subgraph Z["IBM LinuxONE (L1CC, z17) · one Docker container · nothing leaves the machine"]
    direction TB
    P1["1 · Flood path<br/>follow the river downhill from that point"]
    P2["2 · When and how high<br/>arrival time + water height for every river km,<br/>calibrated on two real 2026 Nepal floods"]
    P3["3 · AI: what gets hit<br/>P(destroyed) for every building and bridge,<br/>P(flooded) for every 30 m square of ground"]
    P4["4 · Time to run<br/>walking time uphill to safe ground,<br/>crossing the river only on bridges"]
    P5["5 · Slack = arrival − warning − walk<br/>red: no time · amber: under 15 min · green"]
    P1 --> P2 --> P3 --> P4 --> P5
  end

  SEE --> P1
  P5 --> OFF["<b>Officials</b> · planner (/planner)<br/>who to warn first · SMS text in Nepali + English<br/>bridges to close · who had time under each warning"]
  P5 --> RES["<b>Residents</b> · 'Where should I go?' (/predict)<br/>tap where you are → route to safe ground,<br/>leave-by time, how sure we are"]
  P5 --> REP["<b>Story / training</b> · 3D replay (viewer/)<br/>watch a real flood move down the valley"]
```

Everything runs in one container on one L1CC VM (Ubuntu 24.04, z17, 3 vCPU, 7.8 GB RAM). There is no LLM.
One service on one port (8000) serves the landing page (`/`) and three screens: the officials' planner (`/planner`), the residents' "Where should I go?" (`/predict`) and the phone view (`/go`), plus every `/api/...` endpoint. The 3D replay (`viewer/`) is a separate static page, not part of the container. The scientific stack (numpy, scipy, rasterio, pyproj, shapely, scikit-learn) comes from Ubuntu's
apt packages.

---

## How to run

### The demo, on L1CC (container)

```bash
# on the VM, from the repo root (~/evac-ai)
bash scripts/docker_run.sh
```

The script runs the `evac-ai:latest` image as the owner of `data/` (GRASS refuses a mapset owned by another
uid) with `HOME=/tmp`, waits for the API, runs one Oct 11 scenario and prints `docker ps`. Port 8000 is closed
externally, so open it through an SSH tunnel from your laptop:

```bash
ssh -L 8000:localhost:8000 linux1@<VM_IP>
```

Then browse to <http://localhost:8000>. The VM IP and key are shared in the team chat, never in this repo.

The image is built from [`Dockerfile`](Dockerfile) (`sudo docker build -t evac-ai:latest .` on the VM, ~91 s). Ubuntu 24.04 s390x, with the scientific stack and GRASS from apt. `data/` is mounted at runtime. The image includes `models/` and compiles `escape_search.c` and the zDNN bridge (`scripts/nnpa/zdnn_mlp.c`), so the planner, prediction mode and the what-if map all run in the container.

### Interactive 3D flood replay (runs locally)

The separate [Three.js viewer](viewer/) replays the Oct 11 flood over the real terrain, with 2D/3D views, a time slider, settlement states and a time-to-safety heat map. Its precomputed replay data is committed in [`viewer/data/oct11/`](viewer/data/oct11/), so anyone can try it without a VM login or a data build:

```bash
cd viewer
python3 -m http.server 8090 --bind 127.0.0.1
```

Open <http://localhost:8090/?scenario=oct11&view=3d>. This is a visual replay of the scenario output, not a live hydrodynamic simulation. See the [viewer guide](docs/viewer/README.md) for controls and data provenance.

### Bare metal, on L1CC

```bash
# system scientific stack from apt (no s390x pip wheels); FastAPI/Uvicorn from pip
sudo apt install grass gdal-bin python3-numpy python3-scipy python3-rasterio python3-pyproj python3-shapely
python3 -m venv --system-site-packages ~/venv && ~/venv/bin/pip install fastapi uvicorn -r requirements.txt

# 1. Inputs for the Budhi Gandaki (raw data is gitignored)
(cd pipeline && bash fetch_dem.sh && python3 fetch_osm.py budhi)   # Copernicus tiles + Overpass → data/raw/
# 2. Terrain build: data/proc/{dem_g,sdir,streams,acc}.tif + GRASS location data/grassdb/budhi
bash pipeline/build_valley.sh budhi <west> <south> <east> <north>
# 3. Checks
python3 engine/test_terrain.py && python3 engine/test_scenario.py && python3 engine/test_route.py
# 4. Serve (bounded test window, default 20 min) and smoke-test
bash scripts/serve_test.sh
bash scripts/api_smoke.sh
```

`build_valley.sh` works for any valley. The Trishuli build lives in `data/proc_trishuli` (check it with
`python3 engine/test_trishuli.py`). Run everything from the repo root with system `python3` or `~/venv/bin/python`.

### Re-creating the committed study-area data (laptop)

See [`docs/data/README.md`](docs/data/README.md). The OSM extract, landslide inventory and WorldPop crop need packages
without s390x wheels (`requirements-extract.txt`), so they run on a laptop and the outputs are committed.

---

### Offline + mesh
`/go` registers a service worker that caches the page, Leaflet, the flood overlay and the map tiles around you and your
route; the last answer is kept on the phone. With the network gone (try DevTools → Offline) the page still opens, shows
your route and counts down, and the arrow follows your GPS. **Mesh relay is not built:** our SMS alerts already fit one
Meshtastic/LoRa packet (≤161 bytes), so a phone-to-phone relay is the next step, not a feature today.

## Results so far (validated on L1CC, details in [`docs/validation.md`](docs/validation.md))

Two real 2026 floods, five timed observations and one set of volunteer damage tags, so read these as case studies.

- **Headline, Oct 11:** with the community relay (03:30), **0** of ~1,456 people at risk are left without time. With the
  official SMS (06:40), **all ~1,456** are (20 of 20 settlements red). With the police notification (05:30), 1,340 are.
  This matches the reports: no confirmed deaths, because people got calls from upstream and ran uphill.
- **Headline, Aug 26:** with the 09:15 SMS, ~12,300 of ~20,900 people in the footprint had no time (27 of 44 settlements
  red). An alert at the 08:37 seismic signal cuts that to ~1,600 in the model. The flood line is reconstructed from
  damage marks, so this is in-sample.
- **Settlements (Oct 11):** **9 of the 10** reported destroyed/inundated places we can locate are flagged, all red at
  06:40 (miss: Soti). 11 more are flagged but not on the reported list. Philim (reported safe) has 1 flagged building.
- **Bridges (Oct 11):** **4 of 6** reported losses are matched. The **Soti and Arughat** misses have known causes: the
  Soti bridge isn't in OSM, and at Arughat the 30 m D8 channel drifts ≥175 m from the real river.
- **Footprint (Aug 26):** with the flood line fitted on one half of the river, the footprint holds **83 % / 75 %** of
  destroyed buildings on the other half, and 21 % / 49 % of footprint buildings carry no damage tag.
- **Damage model** (spatial holdout on Aug 26): ROC AUC **0.968** downstream (v2) and **0.818**
  upstream (v1), vs. 0.713 / 0.699 for the footprint rule. Oct 11 expected damaged buildings: 146, vs. 365 in the
  footprint and ~62–72 reported.
- **Flood-area model** (`area_fb`; test version trained on the Aug 26 satellite map only, scored on the unseen Oct 11 map; the
  shipped model is then retrained on both floods): ROC AUC **0.937**
  vs 0.932 for the damage model applied per square (a tie within the confidence interval), but much better probabilities:
  Brier **0.057** vs 0.090. That is why it draws the risk map ([docs/models/area.md](docs/models/area.md)).
- **"Where should I go?" safety audit** (300 random points per valley): no point below the planner's flood line is ever called
  safe (0 % on both floods). Destinations called safe that the UNOSAT satellite map shows flooded: Oct 11 **0 of 227**,
  Aug 26 **7 of 238** ([docs/validation/escape_satellite_check.md](docs/validation/escape_satellite_check.md)).
- **Telum on-chip AI accelerator:** 100 what-if floods over 126,528 squares (12.7 M predictions) in **2.7 s**, vs 83 s for
  the tree model on the VM's 3 CPUs (**31×**), mean difference 0.012 in probability. Live in the planner: 10 M predictions in 2.6 s.
- **Arrival times (leave-one-out):** **0–38 min** off between observations, and 71–119 min **early** (the safe side)
  when extrapolating past the last gauge. Oct 11 has only two timed points, so its LOO is weak. The Oct 11 wave speed
  does **not** transfer to Aug 26 (up to 163 min late), so each flood type needs its own calibration.
- **Latency on L1CC:**
  - New scenario: **5.1 s** (r.walk 4.7 s; Aug 26 grid: 10.8 s).
  - Cached response with all alerts: **0.03 s**.
  - Prediction mode "where should I go?" query: **2–5 ms**.
- The short Nepali alert is 62–69 characters, so it fits one UCS-2 SMS (≤161 bytes) and a Meshtastic payload. It was reviewed by a native
  Nepali reader on the team (`NE_REVIEWED = True`).

---

## Limitations

- **Not a hydrodynamic or debris-flow model.** Arrival and height are interpolated curves along river km,
  calibrated on a handful of reported times and gauge readings. That's why we show bands, not single numbers.
- **Few calibration points, and some are weak.** Oct 11 uses 2 points (Jagat area 04:00 and 20–25 m; Arughat 06:30 and 8.43 m),
  and its timestamps conflict (Soti 07:30 after Arughat 06:30, so Soti is excluded). Aug 26 has 3 arrival points inside the Trishuli grid and **no height point** (Kali Khola and Devghat lie west of the grid), so its flood line is reconstructed from damage marks. Several are upper bounds
  (a gauge going silent) or peak times rather than first arrivals. The Devghat arrival time has no inline source.
- **Gauge stage is not height above the DEM channel.** Gauge peaks are converted with an assumed ~2.4 m normal stage.
- **Population is an assumption:** 4 people per OSM building, plus hard-coded trekker counts (100 in Jagat on Oct 11).
  Buildings more than 3 km from a named OSM place are not assigned to a settlement. Upper-Gorkha OSM coverage is uneven.
- **Fixed assumptions:** 5 min from warning to people moving, 5 m safety margin above the conservative height, 15 min amber threshold.
- **Walking only, no congestion.** The planner uses `r.walk` walking cost on a 30 m DEM with no trail network; prediction mode adds OSM trails. The cells r.walk can't reach are
  filled by straight-line walking at 1 m/s from the nearest reached cell.
- **The planner API serves the Budhi Gandaki valley only.** `/api/scenario?replay=aug26` returns 501 rather than running on the wrong grid.
  The Aug 26 numbers come from `docs/validation/run_aug26.py` on `data/proc_trishuli`. Prediction mode (`/api/predict/*`) has both valleys.
- **New triggers reuse the curves calibrated on a replay.** A different valley or failure type can behave very differently.
- **Nepali alert text was reviewed by one teammate**, not by DHM or NDRRMA. The DHM live feed and BIPAD are recorded or probed, but **not yet used as live triggers**.
- **This is a research prototype, not an official warning service.** DHM can't legally order evacuations, and neither can this.

---

## Libraries & Resources

All code was written during the event. Everything below is third-party.

### Data

| Resource | Use | License / terms |
|---|---|---|
| [Copernicus DEM GLO-30](https://registry.opendata.aws/copernicus-dem/) (AWS Open Data) | Elevation, D8 flow, HAND, walking cost | Free with attribution: "produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA" |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) via [Overpass API](https://overpass-api.de/) and the [Geofabrik Nepal extract](https://download.geofabrik.de/asia/nepal.html) | Buildings, places (EN + NE names), bridges, waterways, roads | **© OpenStreetMap contributors**, [ODbL 1.0](https://opendatacommons.org/licenses/odbl/) |
| [OSM Nepal Floods 2026 mapping](https://wiki.openstreetmap.org/wiki/Organised_Editing/Activities/Nepal_Floods_2026) | Aug 26 `destroyed:building` / `damaged:building` labels | © OpenStreetMap contributors, ODbL. Imagery for that tracing: Vantor via OpenAerialMap, CC BY-NC |
| [WorldPop Global2 R2025A](https://hub.worldpop.org/) | Population, 100 m, 2026 constrained | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/), "WorldPop (www.worldpop.org), University of Southampton" |
| [USGS 2015 Gorkha landslide inventory](https://doi.org/10.5066/F7DZ06F9) (Roback et al. 2017) | Past-landslide feature | Public domain (US Government work) |
| [DHM, Government of Nepal](https://hydrology.gov.np) | Gauge locations and warning/danger levels, live-feed snapshots (`scripts/record_dhm.py`) | Public website, no stated license; attribution to DHM |
| [BIPAD Portal API](https://bipadportal.gov.np/api/v1/) | Probed for river, rain, incident and alert data (not yet used by the app) | Public API, Government of Nepal (NDRRMA) |
| Event reports: [Wikipedia timeline of the 2026 Nepal–Tibet floods](https://en.wikipedia.org/wiki/Timeline_of_the_2026_Nepal%E2%80%93Tibet_floods), [2026 Budhi Gandaki flood](https://en.wikipedia.org/wiki/2026_Budhi_Gandaki_flood), NDRRMA/BWSN SitReps, Kathmandu Post, Onlinekhabar, Mongabay, ICIMOD | Replay timelines and calibration points (each URL is in the `sources` of the replay file) | Cited as sources; Wikipedia text is CC BY-SA 4.0 |
| [UNOSAT](https://unosat.org/products) FL20260826NPL, FL20261011NPL (via [HDX](https://data.humdata.org/dataset/2026-nepal-flash-flood)), FL20230912LBY (Derna) | Satellite flood/debris extents: training labels for the flood-area model (`area_fb`), Derna as a test flood | CC BY-SA (HDX), "UNITAR-UNOSAT" |
| [Copernicus EMS EMSR517](https://mapping.emergency.copernicus.eu/activations/EMSR517) (Ahr 2021) | Test flood for the flood-area model | Free with attribution, "© 2021 European Union, EMSR517" |
| [Ahr building damage, Samprogna Mohor et al. 2025](https://doi.org/10.4121/8f7a21d3-9bb9-4808-ae51-761eb3fba986) (4TU.ResearchData) | Extra damage labels for the leave-one-flood-out test of the damage model | ODbL 1.0 |
| [Sentinel Asia](https://sentinel-asia.org/) (JAXA ALOS-2, MBRSC Sentinel-2), [HOT flood extent](https://data.humdata.org/dataset/hot_flood_npl) | Cross-checks of the UNOSAT maps only | Per provider; see [docs/data/events/](docs/data/events/) |
| Map tiles: [OpenStreetMap](https://www.openstreetmap.org/copyright), [OpenTopoMap](https://opentopomap.org/about), [Esri World Imagery](https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9) | UI basemaps | OSM: ODbL / © OSM contributors. OpenTopoMap: CC BY-SA. Esri: Esri terms of use, attribution |

### Software

| Library / tool | Use | License |
|---|---|---|
| [GRASS GIS](https://grass.osgeo.org/) (`r.watershed`, `r.walk`, `r.mapcalc`) | D8 flow and streams, walking time to safety | GPL-2.0-or-later |
| [SAGA GIS](https://saga-gis.sourceforge.io/) | Tried for HAND in `pipeline/build_terrain.sh`, then replaced by our own HAND | GPL-2.0 (tools) / LGPL (API) |
| [GDAL](https://gdal.org/) (`gdalwarp`, `gdalbuildvrt`, `gdal_translate`) | DEM mosaic, reprojection to UTM 45N | MIT |
| [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) | API server | MIT / BSD-3-Clause |
| [Leaflet 1.9.4](https://leafletjs.com/) | Map UI | BSD-2-Clause |
| [NumPy](https://numpy.org/), [SciPy](https://scipy.org/) | Arrays, KD-tree, distance transform | BSD-3-Clause |
| [rasterio](https://rasterio.readthedocs.io/), [pyproj](https://pyproj4.github.io/pyproj/), [Shapely](https://shapely.readthedocs.io/) | Raster I/O, coordinate transforms, footprint polygons | BSD-3-Clause / MIT / BSD-3-Clause |
| [scikit-learn](https://scikit-learn.org/), [joblib](https://joblib.readthedocs.io/) | Building damage model and flood-area model (HistGradientBoosting), model files | BSD-3-Clause |
| [IBM zDNN](https://github.com/IBM/zDNN) (`libzdnn`, Ubuntu apt) | Runs the neural what-if model on the z17 Telum on-chip AI accelerator ([docs/linuxone-ai.md](docs/linuxone-ai.md)) | Apache-2.0 |
| [IBM Snap ML](https://pypi.org/project/snapml/) | Benchmark only (`scripts/nnpa/`), not used by the app | IBM, see PyPI |
| [geopandas](https://geopandas.org/), [Pillow](https://python-pillow.org/) | Satellite flood-extent tables (laptop); PNG overlays | BSD-3-Clause / MIT-CMU |
| [Three.js r165](https://threejs.org/) | 3D replay viewer (`viewer/`, vendored with its licence) | MIT |
| [IBM Plex](https://github.com/IBM/plex) via Google Fonts | UI typeface | SIL OFL 1.1 |
| [websocket-client](https://github.com/websocket-client/websocket-client), headless [Chrome](https://www.google.com/chrome/), [FFmpeg](https://ffmpeg.org/) | Recording the demo video (`docs/submission/video/record_demo.py`) | Apache-2.0 / Chrome terms / LGPL-2.1+ |
| [tifffile](https://github.com/cgohlke/tifffile), [imagecodecs](https://github.com/cgohlke/imagecodecs) | Byte-order-safe GeoTIFF reads; WorldPop decode | BSD-3-Clause |
| [requests](https://requests.readthedocs.io/), [python-socketio](https://github.com/miguelgrinberg/python-socketio) 4.x | Data fetch; DHM Socket.IO feed recorder | Apache-2.0 / MIT |
| [pyosmium](https://osmcode.org/pyosmium/), [pyshp](https://github.com/GeospatialPython/pyshp) | OSM extract, landslide shapefile (laptop only) | BSD-2-Clause / MIT |
| [Docker](https://www.docker.com/) (`docker.io`), [Ubuntu 24.04 s390x](https://ubuntu.com/download/server/s390x) | Container on L1CC | Apache-2.0 / various free licenses |
| [IBM LinuxONE Community Cloud](https://linuxone.cloud.marist.edu/) | Host (s390x, z17) | Free community-cloud terms |

### Methods we reimplemented

- HAND: Nobre, A.D. et al. (2011), *Height Above the Nearest Drainage, a hydrologically relevant new terrain model*, Journal of Hydrology 404.
- Time to safety on foot after the [USGS Pedestrian Evacuation Analyst (PEAT)](https://www.usgs.gov/software/pedestrian-evacuation-analyst-tool) approach, using GRASS `r.walk`.

---

## Repository layout

```
api/        FastAPI app
engine/     terrain, flood envelope, time to safety, scenario, alerts (+ test_*.py, run on the VM)
web/        Leaflet UI
replay/     event timelines (oct11, aug26)
pipeline/   DEM/OSM fetch and GRASS terrain build per valley
scripts/    study-area data fetch/extract, DHM recorder, serve/smoke/docker scripts
data/       committed study-area layers (raw/ is gitignored; proc*/ and grassdb/ are built on the VM, not committed)
models/     trained model files (damage, area, surrogate)
viewer/     Three.js 3D replay
docs/       all documentation: idea, research, architecture, data and sources, models, validation, deployment, submission
```

**Documentation index:** [`docs/README.md`](docs/README.md) (from the idea to the sources). Full source list: [`docs/sources.md`](docs/sources.md).

**Team agents and teammates:** start with [`AGENTS.md`](AGENTS.md) (who's doing what, plus the task board), then
[`docs/idea/project-plan.md`](docs/idea/project-plan.md) (spec) and
[`docs/idea/nepal-disaster-research.md`](docs/idea/nepal-disaster-research.md) (background).
