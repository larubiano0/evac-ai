# Hack2Skill submission: drafted answers

IBM Z Datathon 2026 · team Latinos · title `Latinos_IBM Z Datathon 2026 Project`
⚠️ **The form closes 18/10/2026 12:30 IST = Sun Oct 18, 03:00 ET.** The team plan says 09:00 ET, which is six hours *after* the form closes. 03:00 ET is the real deadline.

Each answer is plain text, ready to paste: copy what's inside the code block. The count in each heading was measured with Python `len()` against the 1,024 limit.
Every number below is copied from a result file in this repo (sources at the end). Don't round or change them without checking the file.

---

## Challenges *(dropdown)*

Pick the theme option: **Real-Time AI for Critical Decisions** (or the closest wording the dropdown offers).

---

## What is the Problem you are trying to solve? *(928 / 1024)*

```
In Nepal's mountain valleys, flash floods hit villages minutes to hours after a blockage upstream bursts, and the river gauges fail first. In the two most recent floods the official warning came late and said too little. On 11 Oct 2026 (Budhi Gandaki, Gorkha) the official SMS went out at 06:40, about 10 minutes after the first wave reached Arughat; villagers had already warned each other by phone at ~03:30. On 26 Aug 2026 (Bhotekoshi-Trishuli) four gauges were destroyed, DHM learned of the flood by phone, and the SMS was generic, Nepali-only and gave no time to impact.

In the first minutes, officials have no answer to the question that matters: who will be hit, when, and who still has time to walk to safe ground? Residents have no answer to "where do I go, right now?" Bridges fail while people are still crossing them. We need a system that turns one early report into a ranked, location-specific warning in seconds.
```

---

## How are you planning to solve the problem? (Brief Overview) *(992 / 1024)*

```
evac-ai ("Time to Safety") turns one upstream observation (a phone report, a gauge going silent, a pin on the map) into a per-settlement action plan in seconds.
1) Trace the flood path downhill on a 30 m Copernicus DEM (D8 flow, height above the river).
2) Arrival time and water height per river km, calibrated on the two real 2026 floods, shown as bands.
3) ML models trained on real damage tags and satellite flood maps give P(destroyed) per building and bridge and P(flooded) per 30 m cell.
4) GRASS r.walk gives the walking time uphill to safe ground, crossing the river only on bridges.
5) Slack = arrival - warning - walk ranks who to warn first.
Outputs: an officials' planner (ranked alerts, one SMS each in English and Nepali, bridges to close, what-if map), a resident "Where should I go?" route (2-5 ms per query) and an offline phone page with one instruction and a countdown.
Stack: Python, FastAPI, GRASS, GDAL, scikit-learn, IBM zDNN, Leaflet, Docker, OpenStreetMap, WorldPop.
```

---

## How does your solution leverage IBM Z / LinuxONE technologies? *(1009 / 1024)*

```
The whole system runs on IBM LinuxONE Community Cloud: one Docker container on an IBM z17 VM (Ubuntu 24.04 s390x, 3 vCPU, 7.8 GB). Terrain, flood model, walking-time model, the ML damage and flood-area models (trained and served on the VM) and the API all run there. No data leaves the machine and there is no external AI service.

We use the z17's Telum on-chip AI accelerator (NNPA) through IBM zDNN. A flood's height is uncertain, so we score every 30 m cell under 100 possible flood heights: 12.7 M predictions. A neural copy of our flood-area model does this in 2.7 s on the accelerator vs 83 s for the tree model on the CPU (31x), with a mean difference of 0.012 in probability. In the app, the planner's "What if the flood is bigger?" map runs 10 M predictions in 2.6 s on the accelerator, while the CPUs keep serving users.

Why LinuxONE: a national warning service needs uptime on the worst day, data kept in-country, and fast answers. Measured on the VM: 5.1 s per new flood scenario, 0.03 s cached.
```

---

## What value does your solution deliver, and who will benefit from it? *(1015 / 1024)*

```
Users: Nepal's district disaster offices, NDRRMA and DHM duty officers, who must decide in minutes who to warn first. Beneficiaries: residents, trekkers and hydropower crews in steep valleys with little time to move.

Outcome: from one report, a ranked warning list with time to impact, the people with no time left, bridges not to cross, and a personal route to safe ground that works offline, in English and Nepali.

Tested on the real 2026 floods. 11 Oct: with the villagers' 03:30 phone relay, 0 of ~1,456 people at risk are left without time; with the 06:40 SMS, all of them are. 9 of 10 locatable destroyed places and 4 of 6 lost bridges are flagged. 26 Aug: alerting at the 08:37 seismic signal instead of the 09:15 SMS cuts people without time from ~12,300 to ~1,600 (model estimate).

Value: earlier, targeted warnings; each alert fits one SMS or LoRa mesh packet; built only on free open data, so any valley with a DEM and OpenStreetMap can be added. A research prototype, not an official warning service.
```

---

## Upload your pitch deck in PDF Format *(≤ 5 MB)*

**TODO.** Deck in progress: outline in [`docs/submission/pitch/outline.md`](docs/submission/pitch/outline.md). Export to PDF, check the size is under 5 MB.

## Github Link of your Project *(must be public)*

```
https://github.com/larubiano0/evac-ai
```
Checked Sun 00:41 ET: returns HTTP 200 without signing in (public).

## Video Submission Link *(YouTube/Vimeo, max 3:00)*

**TODO (human).** The silent 1:48 demo is at `docs/submission/video/demo.mp4`, plus the team's 45 s motivation clip. Add narration (script in [`docs/submission/README.md`](docs/submission/README.md)), join the two (≤ 3:00), upload to YouTube as **Unlisted** (not Private, or judges can't open it), and paste the link here.

## Share the link to your pitch deck *(only if the upload fails)*

Optional backup: the PDF on GitHub, `https://github.com/larubiano0/evac-ai/blob/main/docs/submission/pitch/<file>.pdf`, once committed.

## Link to all open-source resources used *(975 / 1024)*

```
Full list with licences: https://github.com/larubiano0/evac-ai#libraries--resources
Data: Copernicus DEM https://registry.opendata.aws/copernicus-dem/ ; OpenStreetMap https://download.geofabrik.de/asia/nepal.html ; OSM flood damage tags https://wiki.openstreetmap.org/wiki/Organised_Editing/Activities/Nepal_Floods_2026 ; WorldPop https://hub.worldpop.org/ ; USGS 2015 landslides https://doi.org/10.5066/F7DZ06F9 ; UNOSAT flood maps https://unosat.org/products ; Copernicus EMS https://mapping.emergency.copernicus.eu/activations/EMSR517 ; Ahr damage https://doi.org/10.4121/8f7a21d3-9bb9-4808-ae51-761eb3fba986 ; DHM https://hydrology.gov.np
Software: GRASS GIS https://grass.osgeo.org ; GDAL https://gdal.org ; FastAPI https://fastapi.tiangolo.com ; scikit-learn https://scikit-learn.org ; NumPy https://numpy.org ; SciPy https://scipy.org ; IBM zDNN https://github.com/IBM/zDNN ; Leaflet https://leafletjs.com ; Three.js https://threejs.org ; Docker https://www.docker.com
```

## Any other document (flowchart / architecture)

```
https://github.com/larubiano0/evac-ai/blob/main/docs/architecture.md
```
Figures: `docs/figures/fig1-core-loop.png` … `fig6-telum-accelerator.png`. Validation write-up: `docs/validation.md`. Accelerator benchmark: `docs/linuxone-ai.md`.

---

## Where every number comes from

| Claim | Source file |
|---|---|
| 0 vs ~1,456 people without time (03:30 vs 06:40), 5.1 s new scenario | `docs/validation/oct11_results.json` (`triggers`, `scenario_new_s`) |
| 9 of 10 places, 4 of 6 bridges | `docs/validation.md`, README "Results so far" |
| ~12,300 vs ~1,600 (Aug 26, 09:15 SMS vs 08:37 seismic) | `docs/validation/aug26_results.json`, README. Flood line rebuilt from damage marks, so in-sample |
| 12.7 M predictions, 2.7 s vs 82.9 s, 31x, MAE 0.012 | `docs/linuxone-ai.md`, `models/surrogate/metrics.json` |
| 10 M in 2.6 s in the app | `docs/linuxone-ai.md` "Live in the app" |
| 2-5 ms per route query, 0.03 s cached | `docs/validation.md` latency section |
| SMS 06:40 after first wave ~06:30; relay ~03:30; 4 gauges destroyed Aug 26 | `nepal-disaster-research.md` §0, §1.1 (with source links) |
| z17 / 9175, 3 vCPU, 7.8 GB | `latinos-ibmz-datathon-plan.md` §1 (VM probe), screenshot S2 |
