# Project Context: Nepal Evacuation Router (IBM Z Datathon 2026, team "Latinos")

Read this before doing any work. It defines the goal, hard constraints, the system spec, the data, and the priorities. When a decision is not covered here, choose whatever ships a working demo on LinuxONE soonest.

---

## 1. Hard constraints (never violate)

- **All code must be written during the event.** Don't import code from earlier projects. Open-source libraries are fine.
- **Record every library, dataset and external resource you use, with a link**, in `README.md` under "Libraries & Resources". It is required for submission.
- **Everything must run on IBM LinuxONE Community Cloud (L1CC):** s390x, **big-endian**, CPU only, no GPU.
  - Watch for byte-order bugs when loading binary model weights or rasters, and check that model outputs make sense on L1CC (not just locally).
  - GDAL, rasterio and geopandas may not install. Fall back to numpy + `tifffile`/Pillow + networkx + plain JSON/GeoJSON.
  - Use IBM's prebuilt ML image when possible: https://github.com/linuxone-community-cloud/jupyter-lab-ml
- **Design pattern: predictive + generative AI.** This matches the mandatory IBM labs. A predictive model scores the risk and a generative model writes the alerts.
- **Scope is clipped to 2–3 districts:** Rasuwa / Nuwakot (labels from the August flood) and Gorkha (the October landslide-dam scenario). Don't expand.
- **Store road and segment states only, never reporter identities.**

## 2. Deliverables (definition of done)

1. A GitHub repo with a README that covers the architecture, how to run it, the list of libraries and resources, and the limitations.
2. A video of 3 minutes or less. It must show the problem, the data behind it, the solution, and **the system running on LinuxONE**, including the instance itself.
3. **Screenshots of the L1CC instance and containers running.** Judges score these as evidence.
4. Optional: an architecture flowchart and a prototype link.
- Submission title: `Latinos_IBM Z Datathon 2026 Project`
- **Internal deadline: submitted by Sun Oct 18, 9:00 AM ET.** The hard close is around 10:00 AM.
- **Feature freeze: Sun 2:00 AM ET.** After that, only bug fixes, the video and the README.

### Judging (10 points each)
1. Value to the community and fit with the theme ("Real-Time AI for Critical Decisions")
2. Novelty
3. Technical design and use of LinuxONE + open-source AI/ML (containers, security, scalability, with screenshots as evidence)
4. Execution and pitch: complete, demoed, within the time limit

**Finishing on time matters most.** A working end-to-end demo is better than unfinished extra features.

---

## 3. What we're building

**One line:** A live map of a Nepali river valley during a disaster. It updates from crowdsourced reports and live river gauges, predicts which roads and bridges will fail, and spreads evacuees across the routes that still work. It also produces plans that work offline.

**The gap it fills:** Nepal's warnings did go out, but people could not coordinate where to go while roads and bridges were failing. If everyone takes the same route, that route fails. The government's "Setu Rapid" portal only maps responders and equipment. We add failure prediction, landslide-lake modeling, fusion of crowd reports and capacity-aware routing.

### Components (in priority order; build the top ones first)

| # | Component | Spec |
|---|---|---|
| P0 | **Map store** | Road/trail/bridge graph from OSM plus a 30 m DEM grid. Each edge stores `state` (open / damaged / blocked / unknown), `confidence`, `evidence[]` and `timestamp`. |
| P0 | **Risk model** | `HistGradientBoostingClassifier` per segment. Features: slope, height above river, bridge or river-crossing flag, distance to past landslides, live rainfall, river level. Present the output as a ranking. |
| P0 | **Router** | networkx. Walking time uses Tobler's function `v = 6*exp(-3.5*abs(tan(θ)+0.05))` km/h. Include footpaths and suspension bridges. Destinations are high ground or shelters (OSM schools and health posts stand in, since there is no official shelter dataset). |
| P0 | **Map UI** | Leaflet in 2D, served from LinuxONE, coloring segments by risk and state. Use deck.gl TerrainLayer (3D) only if there is time. |
| P1 | **Capacity-aware assignment** | Population per village comes from OSM building counts plus WorldPop, adjusted for seasonal trekkers. An edge or shelter costs more as it fills, so neighboring villages can be sent different ways. Baseline for comparison: everyone takes the shortest path. |
| P1 | **Report labeler** | CLIP zero-shot first, a small VLM only if the CPU is fast enough. Labels: bridge washed out / landslide on road / road flooded / road passable. Location comes from EXIF GPS, then a pin, then place names in the text geocoded against OSM. Match a report to segments within a few hundred meters, since people film from across the river. |
| P1 | **Fusion** | Update edge confidence based on how recent the report is, how much we trust the source, and whether reports agree. A confirmed landslide raises the risk of nearby segments with similar terrain. |
| P1 | **Landslide-dam scenario** (centerpiece of the demo) | When a report says the river is blocked: fill the DEM upstream to an assumed dam height to get the lake, flag the upstream homes and roads it floods, and trace the downstream outburst path. Mark bridges and low roads on that path as high risk **before the burst**, then reroute. |
| P1 | **Generative alerts** | SMS text in Nepali and English, written by an LLM (use whatever model the IBM Predictive+Generative lab uses). |
| P2 | **Offline plans** | For each village, a main route plus backups for likely failures ("if the Arughat bridge is out, go X"). Export as a small offline map and printable sheets. |
| P2 | **Recycled-footage check** | Reject reports that reuse old disaster media (perceptual hash against known past media). |
| P3 | Drone DEM intake | Accept a GeoTIFF, align it to the 30 m DEM, swap in that patch and recompute. Stretch goal only. Skip OpenDroneMap (probably not available on s390x). |

### Architecture
```
DHM Socket.IO feed ─┐
OSM graph ──────────┤
DEM 30 m ───────────┼─> Map store ─┬─> Risk model (GBM)            [predictive]
Crowd reports ──────┘              ├─> Report labeler (CLIP)       [predictive]
                                   ├─> Dam lake + outburst path    [terrain]
                                   ├─> Capacity-aware router (networkx)
                                   └─> Alert/plan writer (LLM)     [generative]
                                   └─> Web UI (Leaflet), served from LinuxONE
```
Every service runs as a container on one shared L1CC instance. **Measure the end-to-end latency** from a new report arriving to updated plans for every village.

### Stack
Python, numpy, pandas, networkx, scikit-learn, FastAPI or Flask, tifffile/Pillow, Leaflet, `python-socketio` 4.x, CLIP (via torch).

---

## 4. Data

| Data | Status | Notes |
|---|---|---|
| Live river levels (188 stations) | **Verified** | See the DHM feed details below |
| Live rainfall | Visible on the site, not pulled yet | Same feed, `rainfall_watch` event |
| Historical gauge readings | **Unavailable** | `/gss/api/observation?series_id=` returns 403 (needs an API key). Don't plan around it. |
| Roads, trails, bridges, buildings, schools, health posts | Not downloaded | OSM via Overpass, the Geofabrik Nepal extract or HOT/HDX. **Check rural trail coverage in Gorkha and Rasuwa early.** |
| August flood damage labels | Found, unconfirmed | OSM tags `damage:event=2026NepalFlood`, `destroyed:building=yes`, `damaged:building=yes` (Rasuwa, Nuwakot). **First confirm whether any roads carry these tags.** If only buildings do, label roads by the destroyed buildings next to them. |
| Elevation | Not downloaded | Copernicus GLO-30 or SRTM 30 m |
| Past landslides | Not downloaded | NASA Global Landslide Catalog (sparse) |
| Population | Not downloaded | WorldPop |
| Images to evaluate the labeler | Not downloaded | CrisisMMD |
| Before/after imagery | Public | OpenAerialMap (imagery.hotosm.org), Vantor imagery, CC BY-NC. Use for video visuals only. |
| Ground truth for road closures | News | NDRRMA closures reported by Himalayan Times and Kantipur. Geocode a few by hand. |
| Live social feeds | **Unavailable** | Platform APIs are closed. Demo by replaying hand-collected public posts and **label it as a replay.** |

### DHM live feed (verified Oct 15)
- Endpoint: Socket.IO at `https://hydrology.gov.np/gss/socket.io`, Engine.IO v3 (Socket.IO v2 protocol). Use `python-socketio` 4.x or `socket.io-client` 2.x.
- On connect, emit `client_request` with `"river_test"`, `"rainfall_watch"` and `"river_discharge"`. The server answers with events of the same names.
- Fields in each `river_test` station: `name, id, stationIndex, basin, district, latitude, longitude, series_id, waterLevel{datetime,value}, status, warning_level, danger_level, steady (STEADY|RISING|FALLING), elevation, tags`
- Updates every 10–15 minutes.
- Relevant stations: Trishuli at Galchi, Trishuli River at Bhorle, Trishuli River at Kali Khola, Trishuli Khola at Dhunche, Bhote Koshi at Bahrabise, Narayani at Devghat, Seti Gandaki at Damauli.

### Facts behind the problem (verified; use in the README and video)
- **Aug 26, 2026:** A glacial collapse caused a debris flood down the Bhotekoshi and Trishuli rivers. Over 1,400 people died. The Devghat gauge peaked at 6.57 m, under its 7.3 m warning level, because the levels are calibrated for monsoon floods. Upstream stations were destroyed before they could send alerts. Nepal had no backup communications and no satellite internet.
- **Sept:** Floods blocked the Pasang Lhamu Highway (at Simtar) and the Prithvi Highway (at Krishna Bhir).
- **Oct 11, 2026:** A landslide dammed the Budhi Gandaki in Gorkha, then burst. It destroyed bridges, including the highway bridge between Gorkha and Dhading. Evacuations were ordered for Sirdibas, Khorlabesi and Arughat. This happened three days after the Manaslu trek was declared safe. **DHM has no live gauge on the Budhi Gandaki.**
- Pitch lines: "On October 11, Nepal sent the warning. Then the bridges went." / "Disaster is 3D."

---

## 5. Evaluation (produce these numbers)

1. **Risk model:** train and test on separate stretches of the Trishuli/Bhotekoshi corridor (spatial holdout). Report: "flagged X of the Y segments that failed in August."
2. **Routing:** compare against the shortest-path baseline on load at the busiest bridge and time to clear each village.
3. **Labeler:** accuracy on a CrisisMMD sample.
4. **Scenario replay (Oct 11, Budhi Gandaki):** scripted reports arrive → the dam is detected → downstream bridges turn red → routes change before the burst. Include one recycled old video and show that it gets rejected.
5. **Latency:** time from a new report to updated plans, measured on LinuxONE.

## 6. Known risks

| Risk | Mitigation |
|---|---|
| Wrong outputs on s390x (byte order) | Load and run one model on L1CC in the first hour |
| Geo libraries fail to install | numpy/tifffile/networkx fallback |
| Too few labels (one event, volunteer tags) | Present results as a ranking and state the limits plainly |
| Scope creep | Follow the priority order in §3. Freeze features at 2 AM. |

## 7. Milestones (ET, Sat Oct 17 → Sun Oct 18)

| By | Done |
|---|---|
| Sat 11:00 | L1CC instance shared, installs tested (networkx, sklearn, torch, tifffile, rasterio), both IBM labs run, repo created |
| Sat 13:00 | OSM + DEM pulled for 3 districts, DHM client working, damage tags checked, graph built with features per segment |
| Sat 17:00 | Risk model trained and evaluated, router v1, labeler v1, UI v1 showing risk |
| Sat 22:00 | Capacity-aware routing, Tobler timing, dam lake + outburst path, fusion, offline export, SMS generation |
| Sun 02:00 | Replay script, recycled-footage check, latency measured, LinuxONE screenshots. **FREEZE** |
| Sun 08:30 | Video recorded, README finished, flowchart made |
| Sun 09:00 | **Submitted** |

## 8. Video structure (≤3:00)
- 0:00–0:25: The problem (Oct 11, Devghat 6.57 m vs the 7.3 m warning level)
- 0:25–0:50: The solution and the architecture
- 0:50–2:10: Live demo on LinuxONE: feed → risk → report → dam → lake → red bridges → routes split → SMS → offline sheet
- 2:10–2:35: Results (§5)
- 2:35–3:00: Why IBM Z (uptime for critical infrastructure, reporter privacy), limits, next steps (drone LiDAR, mesh networking)

## 9. Technical links
- L1CC registration (event code `SSF2026`): https://linuxone.cloud.marist.edu/#/register?flag=VM · Setup guide: https://ibm.biz/BdPcL8 · Fast start: https://community.ibm.com/zsystems/l1cc/faststart/
- Jupyter ML image: https://github.com/linuxone-community-cloud/jupyter-lab-ml
- Submission: https://hack2skill.com/event/datathon-2026 (the IBM labs are under Resources)
- DHM: https://hydrology.gov.np
- OSM Nepal Floods 2026: https://wiki.openstreetmap.org/wiki/Organised_Editing/Activities/Nepal_Floods_2026 · HOT: https://www.hotosm.org/en/news/mapping-the-nepal-floods/
- Background on the warning failure: https://nepalitimes.com/nepal-disaster-was-a-warning-to-fix-its-early-warning-system
- Lessons from past teams on LinuxONE: https://community.ibm.com/community/user/blogs/akshata-pandit/2025/04/24/our-experience-using-ibm-linuxone-from-datathon-pa · https://community.ibm.com/community/user/blogs/christopher-eliot-hall/2024/04/10/ibm-z-datathon

---

## 10. Status log (agents: update this as you work)
<!-- One line per entry: date/time — component — what changed — what's next. Keep it short. -->
- _empty_
