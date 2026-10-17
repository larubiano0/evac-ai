# Project Context: "Time to Safety" Flash-Flood Warning (IBM Z Datathon 2026, team "Latinos")

Read this before doing any work. It defines the goal, hard constraints, what we build and what we don't, the data, and the priorities. If a decision isn't covered here, pick whatever gets a working demo running on LinuxONE soonest.

**Background:** `nepal-disaster-research.md` covers the last five disasters, the existing apps and communication channels, the state of the art (§7), and the gap analysis. **Don't re-research topics already covered there.** Add to it instead.

---

## 1. Hard constraints (never violate)

- **All code must be written during the event.** Open-source libraries are fine.
- **Log every library, dataset and external resource with a link** in `README.md` under "Libraries & Resources".
- **Everything runs on IBM LinuxONE Community Cloud (L1CC):** s390x, **big-endian**, CPU only.
  - Watch byte order when reading binary rasters or model weights. Check outputs on L1CC, not just on a laptop.
  - **Probed VM facts (Sat 13:10):** Ubuntu 24.04, z/VM, machine type 9175 (z17), **3 vCPU, 7.8 GB RAM + 4 GB swap, 36 GB free disk**, no GPU. **NNPA AI accelerator present.** Vector extensions vx/vxe/vxe2. numpy matmul about 157 GFLOP/s. Passwordless sudo. Outbound internet OK (PyPI, GitHub, Geofabrik, Copernicus DEM S3, BIPAD, DHM, HuggingFace). Only port 22 is listening.
  - **Already installed via apt:** numpy 1.26, scipy 1.11, scikit-learn 1.4, pandas 2.1, Pillow, shapely 2.0, pyproj 3.6, **rasterio 1.3**. **Use system Python** (or a venv with `--system-site-packages`). pip has no s390x wheels for these, so don't `pip install` them. pip wheels are available for networkx, fastapi, uvicorn, tifffile.
  - Available via apt but not installed: gdal-bin, docker.io, podman, cmake. No docker/podman yet. Install `docker.io` when we containerize.
  - Login: `ssh -i ~/.ssh/l1cc_latinos.pem linux1@<VM_IP>` (the IP is in the team chat, not in the repo). Serving the web UI publicly needs a port opened (check the L1CC security group/firewall).
- **Predictive AI is required. Generative AI is optional.** The team decided **templates instead of an LLM** for alerts. Only add an LLM if it adds something templates can't.
- **Scope:** the Budhi Gandaki (Gorkha/Dhading, Oct 11) is the main demo. The Bhotekoshi–Trishuli (Rasuwa/Nuwakot, Aug 26) is the second replay and the source of training labels. Don't expand to other areas.
- **Never store reporter identities.** Store only the observation, its location and its time.

## 2. Deliverables (definition of done)

1. A GitHub repo with a README covering the architecture, how to run it, the libraries and resources used, and the limitations.
2. A video, **3 minutes or less**: the problem, the data behind it, the solution, and the system **running on LinuxONE** (show the instance).
3. **Screenshots of the L1CC instance and the running containers.**
4. Optional: an architecture flowchart and a prototype link.
- Submission title: `Latinos_IBM Z Datathon 2026 Project`
- **Submit by Sun Oct 18, 9:00 AM ET** (hard close around 10:00). **Feature freeze at Sun 2:00 AM ET.**

**Judging** (10 points each): (1) community value and fit with the theme "Real-Time AI for Critical Decisions", (2) novelty, (3) technical design and use of LinuxONE + open-source AI/ML, with screenshots as evidence, (4) execution and pitch. **Finishing on time matters most.**

---

## 3. The problem (verified; details in the research file)

In Nepal's two most recent flash floods, **sensors failed first and people did the warning**:
- **Oct 11, Budhi Gandaki:** an avalanche or landslide blocked the river, which burst and re-blocked several times. A warning relayed by locals reached Dharche at about **03:30**. The first wave hit Arughat at about **06:30**. The official SMS went out at **06:40**. The Arughat gauge (danger level 5 m) peaked at 8.43 m and was then swept away. No deaths were confirmed, because people got phone calls from upstream and ran uphill. At least 6 bridges were lost, and one span of the Arughat bridge failed while people were still crossing.
- **Aug 26, Bhotekoshi–Trishuli:** an ice-rock avalanche. Four gauges were destroyed and **DHM learned about the flood by phone**. The SMS was generic, in Nepali only, and late in places. About 1,454–1,497 people died. A head teacher evacuated 900 students 10 minutes before the flood, after **phone calls from upstream**.
- **No one can forecast these floods in advance.** Google Flood Hub, GloFAS and DHM forecasts are rainfall-driven, and these events had no rain. Debris-flow simulators need inputs that are unknown until after the event and take hours to run.
- **Official warnings don't tell anyone what to do.** They give no time-to-impact, no place to go and no bridge to avoid. DHM also can't legally order evacuations.

**The gap we fill:** turning *an upstream observation* into *an action plan for each settlement, within seconds*. That means when the flood will arrive, how high it will be, where the nearest safe ground is, which bridges to avoid, and who can't make it in time, so they get warned first.

**Pitch lines:** "On October 11, the villagers' warning beat the government's by three hours. We built the system that makes that warning official, instant and specific." / "Nepal can't predict when the mountain falls. It can predict who has time to run."

## 4. What we build

### 4.1 Core loop (the demo)

```
TRIGGER ──> FLOOD PATH ──> ARRIVAL TIME + HEIGHT ──> TIME TO SAFETY ──> SLACK ──> ALERTS
(report /    (river         (per river km;            (walk uphill,      (arrival −   (per settlement,
 gauge drop /  network       HAND-based height)        Tobler, bridges     warning −    ranked by urgency,
 seismic)      downstream)                             only if needed)     walk)        multilingual)
```

**Optimize for lives saved:** the number of people whose **slack ≥ 0**, where `slack = flood arrival − (warning delay + walking time to safety)`. Every ranking and alert follows from this.

### 4.2 Components, in priority order

| # | Component | Spec |
|---|---|---|
| **P0** | **Trigger intake** | Takes three kinds of input: (a) a structured or free-text report ("river stopped at Chhekampar", "loud roar, landslide blocking the Syar Khola"), (b) a falling-gauge anomaly, (c) a manual pin. The output is an event: `{location on the river, time, type, confidence}`. |
| **P0** | **Flood path + arrival time** | Trace the river network downstream of the trigger (OSM waterways). Arrival time = river distance ÷ wave speed, **calibrated on the Oct 11 and Aug 26 timelines** (roughly 20–40 km/h; see research §7.4). Show the result as a band (earliest/latest), not a single number. |
| **P0** | **Flood height + safe ground** | HAND raster (DEM elevation minus the elevation of the nearest river cell). The flood-height envelope decreases downstream and is calibrated on observed heights (Salleri 20–25 m, Arughat 8.43 m, Timure >20 m, Devghat 6.57 m). Safe means HAND > height + margin. |
| **P0** | **Time to safety** | Run Dijkstra on the DEM grid with a Tobler walking cost, starting from every building or settlement and ending at the nearest safe cell, **on the same bank**. Crossing at a bridge is allowed only if the bridge is reached before the flood. This is a reimplementation of the USGS PEAT method. |
| **P0** | **Slack + ranking** | Population per settlement comes from OSM building counts × household size, plus trekker counts at checkpoints where known. Compute slack for each settlement and label it **red** (can't make it), **amber** (<15 min margin) or **green**. Output an alert order: earliest arrival first, weighted by population at risk. |
| **P0** | **Map UI** | Leaflet in 2D. Shows the river path with arrival times, the inundation footprint, settlements colored by slack, the safe ground and the walking routes. A replay slider. |
| **P1** | **Template alerts (no LLM)** | Fixed templates in Nepali and English, filled with computed values: arrival time, direction, which bridge to avoid. Our Nepali-reading teammate checks the Nepali text. There are two lengths: a short trigger of 200 bytes or less (SMS / cell broadcast / Meshtastic), and a full plan page. |
| **P1** | **Report intake form** | A structured form: pick a place from the OSM gazetteer, pick an observation type (river stopped / roar / blockage seen / flood seen), and a time. **No LLM.** |
| **P1** | **Cross-event arrival/height model** | Fit wave speed and height decay against distance from the source (plus slope and valley width) across several events (research §8: Oct 11, Aug 26, Chamoli 2021, Sikkim 2023, Melamchi 2021). Validate leave-one-event-out. This is the main predictive ML (HistGradientBoosting or a simple regression). |
| **P2** | **Predictive damage model** | Gradient boosting that predicts the probability a building is destroyed. Features: HAND, distance to the river, river bend curvature, valley width, distance from the source. **Trained on the Aug 26 OSM damage tags with a spatial holdout.** Used to validate and correct the height envelope. This is our main predictive ML. |
| **P1** | **Bridge bottleneck check** | Only for settlements whose safe ground is across a bridge: people × seconds per person crossing vs. slack. Flag when the crossing takes longer than the slack. Also "**don't cross**" warnings for bridges in the flood's path. |
| **P2** | **Gauge-drop detector** | Flags a sharp fall in water level with no rain as a likely upstream blockage. Built on BIPAD/DHM river history. Starts as a rule; becomes a model if history is available. |
| **P2** | **Warning-delay comparison** | Re-run the same event with the trigger at the community report time (03:30) and at the actual SMS time (06:40). Report how many more people get slack ≥ 0. **This is our headline number.** |
| **P3** | Secondary lake risk | Lake volume and the area upstream it would flood, behind a long-lived blockage (the days-long case, like the Aug 28 barrier lake in Tibet). Only if all of the above is done. |

### 4.3 Explicitly NOT building (already exists, or isn't needed)

- Rainfall/riverine flood forecasting (Google Flood Hub, GloFAS, DHM), weather alerts (the Nepal Weather app), the hazard dashboard and incident database (BIPAD), rescue and relief requests (Setu Rapid), alert delivery infrastructure (1155 SMS, future cell broadcast). **We only produce content that could be fed to them.**
- Full hydrodynamic or debris-flow simulation (r.avaflow, HEC-RAS): too slow, inputs unknown live, probably won't install on s390x.
- A general crowd-congestion optimizer or agent-based simulation: there's no documented congestion. We only check the bridge bottleneck.
- 3D rendering, drone DEM import, image classification of crowd photos (CLIP), detection of recycled footage, social-media scraping.

### 4.4 Architecture

```
OSM (rivers, bridges, buildings, paths) ─┐
DEM 30 m → HAND raster (precomputed) ────┼─> Precompute per valley: river graph w/ distances,
                                          │    HAND, Tobler cost grid, settlements + population
BIPAD/DHM river feed ─> gauge-drop rule ─┐│
Text report ─> LLM parser ───────────────┼┴─> Event ─> path/arrival/height ─> time-to-safety (Dijkstra)
Manual pin ──────────────────────────────┘                         │
                                     Damage GBM (calibrates height)┤
                                                                   └─> slack per settlement ─> ranking
                                                                        ─> LLM alert text ─> Leaflet UI / JSON API
```
Containers on one L1CC instance: `api` (FastAPI, holds the precomputed grids in memory) and `web` (static Leaflet). No LLM container. Measure the **latency from trigger to alerts** (target: under 10 s per valley).

### 4.5 Stack
Python, numpy, scipy (`scipy.sparse.csgraph.dijkstra` on the grid), networkx (river graph), scikit-learn (HistGradientBoosting), FastAPI, tifffile/Pillow, Leaflet. No LLM.

---

## 5. Data

| Data | Use | Status |
|---|---|---|
| Copernicus GLO-30 / SRTM DEM | HAND, slope, Tobler cost | Not downloaded. Clip to the Budhi Gandaki and Bhotekoshi–Trishuli corridors |
| OSM: waterways, bridges, buildings, paths, places | River graph, bridges, population, gazetteer | Not downloaded. Overpass or the Geofabrik Nepal extract. **Check building coverage in upper Gorkha** |
| OSM Aug 2026 damage tags (`damage:event=2026NepalFlood`, `destroyed:building=yes`) | Labels for the damage model | Found, unverified. Check counts |
| **BIPAD API** `bipadportal.gov.np/api/v1/{river,rain,incident,alert}` | Gauge history (gauge-drop rule), geotagged incidents | **Verified public, no key.** Query filters seem to be ignored, so test pagination and station filtering. Find out how far back history goes |
| DHM live feed: Socket.IO `https://hydrology.gov.np/gss/socket.io` (Engine.IO v3; emit `client_request` with `river_test`/`rainfall_watch`/`river_discharge`) | Live gauge panel, live gauge-drop check | Verified Oct 15. DHM's own history endpoint returns 403 |
| **Event timelines** (research §1.1, §1.3) | Calibrating wave speed and height, scripting the replay | **Done.** Need to turn them into `replay/oct11.json` and `replay/aug26.json` with coordinates |
| Trekker counts (MCAP checkpoints: about 98 entered on Oct 10; 100+ in Jagat, 17 in Lokpa, 40 in Chhekampar) | Population at risk | From news. Hard-code for the replay |
| WorldPop | Fallback population | Optional |
| OpenAerialMap before/after imagery | Video visuals only | Optional |

## 6. Evaluation (numbers for the video)

1. **Arrival-time error:** predicted vs. observed arrival at each timestamped point (Oct 11: Paiyu/Jagat, Soti, Arughat; Aug 26: Betrawati, Trishuli, Malekhu, Devghat). Use leave-one-event-out calibration.
2. **Footprint:** the share of destroyed buildings (Aug OSM tags) inside the predicted inundation footprint, and the share of footprint buildings left undamaged.
3. **Damage GBM:** AUC on a spatial holdout.
4. **Headline:** people with slack ≥ 0 when the trigger is the community report vs. the official SMS time, for both replays.
5. **Latency** on LinuxONE, from trigger to ranked alerts.

## 7. Known risks

| Risk | Mitigation |
|---|---|
| s390x install or byte-order problems | Test numpy/scipy/sklearn and the DEM read on L1CC first |
| Height envelope too crude | Present a band, calibrate on the observed heights, validate with the damage labels, and state the limits plainly |
| OSM buildings sparse in upper Gorkha | Fall back to settlement points × estimated household counts |
| Scope creep | Follow the priority order in §4.2. Everything in §4.3 stays out |

## 8. Milestones (ET; it's Sat 12:15 now)

| By | Done |
|---|---|
| Sat 14:00 | L1CC set up, installs tested, repo created. DEM + OSM pulled for the Budhi Gandaki. Replay JSON for Oct 11 |
| Sat 18:00 | HAND raster, river graph with distances, arrival-time function calibrated on Oct 11. Tobler/Dijkstra time to safety. First slack map |
| Sat 22:00 | Leaflet UI with replay slider. FastAPI on L1CC. Templated LLM alerts. Bridge check |
| Sun 02:00 | Aug 26 corridor + damage GBM, report parser, comparison of the two trigger times, latency + screenshots. **FREEZE** |
| Sun 08:30 | Video recorded, README written, flowchart done |
| Sun 09:00 | **Submitted** |

## 9. Video structure (3:00 or less)
- 0:00–0:30: Oct 11. The villagers' warning at 03:30, the government SMS at 06:40, the bridge failing under the ambulance.
- 0:30–0:50: "You can't predict when the mountain falls. You can compute who has time to run."
- 0:50–2:10: Live on LinuxONE. A report comes in → path and arrival times → inundation → slack map (red/amber/green) → alert ranking → Nepali/English alerts → bridge warning.
- 2:10–2:35: Results: arrival-time error, footprint vs. damage, people saved by the earlier trigger, latency.
- 2:35–3:00: Why IBM Z (reliability for critical infrastructure, privacy), limits, next steps (cell broadcast integration, seismic triggers, Kathmandu 10 Action Points).

## 10. Key links
- L1CC registration (code `SSF2026`): https://linuxone.cloud.marist.edu/#/register?flag=VM · Setup: https://ibm.biz/BdPcL8 · https://community.ibm.com/zsystems/l1cc/faststart/
- Submission + IBM labs: https://hack2skill.com/event/datathon-2026
- BIPAD API: https://bipadportal.gov.np/api/v1/ · DHM: https://hydrology.gov.np
- USGS PEAT method: https://www.usgs.gov/software/pedestrian-evacuation-analyst-tool
- OSM Nepal Floods 2026: https://wiki.openstreetmap.org/wiki/Organised_Editing/Activities/Nepal_Floods_2026
- LinuxONE lessons from past teams: https://community.ibm.com/community/user/blogs/akshata-pandit/2025/04/24/our-experience-using-ibm-linuxone-from-datathon-pa

---

## 11. Decision log
- Pivoted from "3D map + crowd routing" to "time to safety": real lead time came from upstream human observation, and no congestion has been documented (research §0, §7.5).
- The landslide-dam lake model was moved to P3: the Oct 11 blockage lasted minutes to hours, not days.
- **Audience = residents directly** (decided). Consequence: plans are **precomputed per settlement and distributed ahead of time** (offline page / printout). During the event, the **trigger message is tiny** (≤200 bytes), so it fits SMS, cell broadcast, or LoRa mesh (Meshtastic) payloads. We do **not** build mesh networking. We only make our output compatible with it.
- Team: 4 people, with Claude writing most of the code. Roles stay flexible.
- No LLM: templates do the job. One teammate reads Nepali and checks the template text.
- Calibration expanded beyond the two 2026 events (research §8). Earthquakes count only as triggers of landslide dams, not as a hazard we model.
- SSH key for L1CC is at `~/.ssh/l1cc_latinos.pem` (RSA 2048). VM reachable as `linux1`. **Never commit the key or the IP.**

## 12. Status log (agents: update as you work)
<!-- One line per entry: time — component — change — next. -->
- Sat 12:15 — context — plan rewritten after research — start L1CC setup + data pull
- Sat 13:10 — L1CC — probe run: z17, 3 vCPU / 7.8 GB, NNPA, the scientific Python stack is preinstalled — next: data pull for the Budhi Gandaki
