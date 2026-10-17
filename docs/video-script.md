# Video script: "Time to Safety" (3:00 max)

Packet G · owner `agent-aayush` · follows `latinos-ibmz-datathon-plan.md` §9 · **Draft, Sat 14:40 ET**

Spoken narration is about **400 words** (~150 wpm ≈ 2:40), which leaves ~20 s for pauses and UI waits.
Numbers in **[brackets]** are placeholders until packet D (validation) and packet B (damage model) report.
The values next to them are the provisional numbers from the `AGENTS.md` log. **Don't record before they're confirmed.**

Recording: screen capture at 1920×1080. The UI runs through the SSH tunnel at `http://localhost:8000`. Keep a
terminal open on the L1CC VM in a second window. Record the narration separately and lay it over the capture.

---

## 0:00–0:30 · The problem: Oct 11, Budhi Gandaki

**Screen:** title card "October 11, 2026 · Budhi Gandaki, Gorkha" → UI zoomed on the valley, river path drawn, no
footprint yet. Two time stamps fade in on the map: **03:30 Dharche**, **06:40 SMS**.

**Narration:**
> On October 11, a blocked river burst in the Budhi Gandaki valley. At three-thirty in the morning, villagers
> upstream phoned the people below them. The government SMS went out at six-forty, ten minutes after the first
> wave had already hit Arughat. At Arughat, an ambulance driver crossed the bridge while the river was rising.
> When he came back, a span was gone. Nobody died, because people trusted the phone call and ran uphill.

## 0:30–0:50 · The idea

**Screen:** black card, white text, one line at a time.

**Narration:**
> Nobody can forecast these floods. There's no rain. The mountain just falls. But once someone sees it happen,
> you *can* compute who has time to run. That's what we built.

**On screen:** "You can't predict when the mountain falls. You can compute who has time to run."

## 0:50–2:10 · Live on LinuxONE (the demo)

| Time | Screen | Narration |
|---|---|---|
| 0:50 | Terminal on the L1CC VM: `uname -m` → `s390x`, `sudo docker ps` shows `evac-ai` up. Cut to the browser; the header shows the host from `/api/scenario` (`s390x`, big-endian) | "Everything runs in one container on IBM LinuxONE: s390x, big-endian, CPU only." |
| 1:00 | Click **Place trigger**, click the river near the Oct 11 source, burst 03:45, warning 03:30 | "A report comes in: the river has stopped upstream. We drop a pin." |
| 1:08 | Path appears with arrival times. Drag the **wave clock** slider: the front moves downstream | "The engine traces the flood path down the river and gives an arrival-time band for every kilometre, calibrated on what really happened." |
| 1:20 | Footprint fills in | "The footprint comes from height above the river, measured against this flood's path, not a generic flood map." |
| 1:30 | Settlements turn red / amber / green; escape routes as green dashed lines | "For each of [112,515] buildings, GRASS works out the walking time uphill to safe ground, on the same bank. Then slack: arrival, minus warning, minus the walk." |
| 1:45 | Alert list on the left; open the top settlement, show the EN and NE short alerts | "Alerts come out ranked: who gets hit first and who has the least time. The SMS says when, which way to go and which bridge not to cross, in Nepali and English, in one message." |
| 1:55 | Bridges at risk highlighted; hover Dobhan / Machhakhola | "These are the bridges in the flood's path. Several of them are bridges that were really lost." |
| 2:02 | Header badges: `s390x`, `big-endian`, `compute X s` | "A new scenario takes about [4.5] seconds on LinuxONE." |

*(If B is integrated by recording time, add at ~1:35: "A gradient-boosting model trained on 2,759 buildings destroyed on August 26 flags the ones most likely to go." Use the real AUC from packet B; otherwise cut this line.)*

## 2:10–2:35 · Results

**Screen:** the "Who had time to escape?" panel (`/api/compare`), then a results card.

**Narration:**
> We replayed October 11 with the warning at two times. With the villagers' three-thirty relay,
> **[0]** people are left without time. With the official six-forty SMS, **[all ~1,456]** are.
> Predicted arrival times are within **[± X min]** of the reported ones, and the footprint contains **[Y %]**
> of the buildings destroyed on August 26.

**Results card (on screen):** people without time at 03:30 vs. 06:40 · arrival-time error · footprint vs. destroyed buildings · latency on L1CC · *(damage-model AUC if B is done)*.

## 2:35–3:00 · Why IBM Z, limits, next steps

**Screen:** architecture flowchart from the README (mermaid render), then the team card.

**Narration:**
> A warning system has to keep working when everything else is failing, and it holds data about people.
> That's what IBM Z is built for. Our limits: it's not a hydraulic model. It uses a few calibration points
> and assumes four people per building, and the Nepali text still needs review. Next: feed it into cell
> broadcast, take seismic and gauge triggers automatically, and print a plan for every village before the
> next flood.

**End card:** `Latinos_IBM Z Datathon 2026 Project` · github.com/larubiano0/evac-ai · "Map data © OpenStreetMap contributors (ODbL) · Copernicus DEM · WorldPop CC BY 4.0"

---

## Screenshot list (submission requires L1CC instance + running containers)

| # | What | How | Used in |
|---|---|---|---|
| S1 | **L1CC instance page** (dashboard showing the VM, s390x, Ubuntu 24.04) | L1CC web console | Submission, video 0:50 |
| S2 | **Terminal: `uname -a`, `lscpu` (z17 / 3 vCPU), `free -h`** on the VM | SSH session (crop out the IP) | Submission |
| S3 | **`sudo docker ps`** showing container `evac-ai` up, plus `sudo docker images` (evac-ai, 1.15 GB) | `bash scripts/docker_run.sh` output | Submission, video 0:50 |
| S4 | `curl localhost:8000/api/scenario?replay=oct11&warn=06:40` with `host.machine = s390x`, `byteorder = big`, `timing` | VM terminal | Submission, README |
| S5 | UI: full Oct 11 view at the 06:40 warning (footprint, red settlements, alert list) | Browser via tunnel | README, video 2:10 |
| S6 | UI: same at the 03:30 warning (all green/amber) | Browser | README, video 2:10 |
| S7 | UI: one settlement's alerts open (EN + NE short and full) | Browser | Video 1:45 |
| S8 | UI: bridges at risk + escape routes, zoomed on Dobhan/Machhakhola | Browser | Video 1:55 |
| S9 | UI: a new trigger placed by click (POST /api/trigger result) | Browser | Video 1:00 |
| S10 | Damage model report on the VM (AUC, flagged X of Y) | Packet B output | Video 1:35, results card, if B is done |
| S11 | README mermaid flowchart, rendered on GitHub | GitHub | Video 2:35 |

**Before taking any screenshot:** no VM IP, key path or token visible (the repo is public). Crop or blur the SSH prompt.

## Recording checklist (Sun 06:00–08:30 ET)

- [ ] D numbers filled in above; brackets removed
- [ ] Nepali alerts reviewed (packet H, `NE_REVIEWED = True`), or say "draft" on screen
- [ ] Container rebuilt from the frozen `main` (Sun 02:00) and `docker ps` freshly captured
- [ ] Cached scenarios warmed (`scripts/serve_test.sh` or one call per warning time) so the UI doesn't stall on camera
- [ ] Timed run-through ≤ 3:00
- [ ] Upload, then put the link in the Hack2Skill submission by **Sun 09:00 ET**
