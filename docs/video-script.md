# Video script: "Time to Safety" (3:00 max)

Packet G · owner `agent-aayush` · follows `docs/idea/project-plan.md` §9 · **Draft, Sat 14:40 ET**

Spoken narration is about **400 words** (~150 wpm ≈ 2:40), which leaves ~20 s for pauses and UI waits.
Numbers were checked by packet D (Sat 17:30 ET); sources and caveats are in [`validation.md`](validation.md).

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

## 0:50–2:10 · Live on LinuxONE (the demo: three screens)

The problem and solution parts are already recorded. This is the demo cut. UI via the SSH tunnel: planner
`http://localhost:18000/planner` (landing page at `/`), resident view `http://localhost:18000/predict` (port 8000 container, `evac-ai:pred4`).
Warm the caches first (one load of each page, plus a Trishuli prediction scenario, ~53 s cold).

| Time | Screen | Narration |
|---|---|---|
| 0:50 | VM terminal: `lscpu \| grep -E "Machine type\|Flags"` (9175 = z17, `nnpa` = the Telum AI accelerator), `sudo docker ps` (`evac-ai` up) | "Everything runs in one container on an IBM z17 on LinuxONE Community Cloud." |
| 0:55 | Same terminal: `bench_ensemble.py` output from [linuxone-ai.md](linuxone-ai.md) (100 what-if floods × 126,528 cells: CPU 83 s, Telum accelerator 2.7 s) | "A flood's height is never certain, so we score every spot under a hundred possible floods: 12 million predictions. The z17's on-chip AI accelerator does it in under 3 seconds, 31 times faster than our VM's CPUs." |
| 1:00 | **Planner** (`/`). "Who had time to escape?" card: click 03:30, then 06:40 | "October 11. With the villagers' phone relay at three-thirty, nobody is left without time. With the official SMS at six-forty, all fourteen hundred are." |
| 1:15 | Drag the **wave clock**; settlements turn red as the front passes | "Arrival times and heights come from the real flood, kilometre by kilometre." |
| 1:25 | Open the #1 settlement: EN + NE SMS, walk time, escape route; red bridges | "Alerts come out ranked by who is hit first, in one Nepali SMS: when, which way to climb, which bridge not to cross." |
| 1:35 | **Colour by: Damage model**. Bridge widths change; the badge shows the model's time | "A model trained on 2,759 buildings destroyed on August 26 scores every building and bridge in under a second. It found the bridges that were really lost." |
| 1:45 | **Place trigger**: click upstream on the river; the result appears (~5 s) | "A new report comes in. A new flood, computed on LinuxONE in five seconds." |
| 1:55 | **Resident view** (`/predict`): click a riverside house; route to the green safe zone, leave-by time, WALK/HURRY/RUN | "And for the person standing by the river: where to go, and how long they have." |
| 2:02 | **Go view** (`/go?lat=28.2955&lon=84.9059&t=10`, DevTools phone mode; on a phone it uses GPS): GO UPHILL NOW, 20 min countdown, leave-by, arrow, route. Tap **नेपाली**. DevTools Network → **Offline**, reload: same screen, "Offline: saved route". Tap the green flag: "You reached safe ground" | "In a panic, nobody reads a map. This page finds you, gives one instruction and a countdown, in Nepali too. And when the network drops, it still knows your way out." (~25 s: trim the 1:55 row to compensate) |

## 2:10–2:35 · Results

**Screen:** the "Who had time to escape?" panel (`/api/compare`), then a results card.

**Narration:**
> We replayed October 11 with the warning at two times. With the villagers' three-thirty relay,
> **zero** people are left without time. With the official six-forty SMS, **all fourteen hundred** are.
> It flags nine of the ten destroyed places we can map, and four of six lost bridges.
> On August 26, with the flood line fitted on one half of the river, the footprint holds three quarters or more
> of the destroyed buildings on the other half.

**Results card (on screen):** Oct 11: 0 vs. 1,456 people without time (03:30 relay vs. 06:40 SMS) · 9 of 10 reported places, 4 of 6 lost bridges · Aug 26 footprint: 75–83 % of destroyed buildings (cross-validated) · damage model AUC 0.97 · arrival error 0–38 min held out · 5 s per new scenario on L1CC.

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
| S1 | **L1CC instance page** (dashboard showing the z17 VM) | L1CC web console | Submission, video 0:50 |
| S2 | **Terminal: `uname -a`, `lscpu` (z17 / 3 vCPU), `free -h`** on the VM | SSH session (crop out the IP) | Submission |
| S3 | **`sudo docker ps`** showing container `evac-ai` up, plus `sudo docker images` (evac-ai, 1.15 GB) | `bash scripts/docker_run.sh` output | Submission, video 0:50 |
| S4 | `curl localhost:8000/api/scenario?replay=oct11&warn=06:40` with `timing` | VM terminal | Submission, README |
| S5 | UI: full Oct 11 view at the 06:40 warning (footprint, red settlements, alert list) | Browser via tunnel | README, video 2:10 |
| S6 | UI: same at the 03:30 warning (all green/amber) | Browser | README, video 2:10 |
| S7 | UI: one settlement's alerts open (EN + NE short and full) | Browser | Video 1:45 |
| S8 | UI: bridges at risk + escape routes, zoomed on Dobhan/Machhakhola | Browser | Video 1:55 |
| S9 | UI: a new trigger placed by click (POST /api/trigger result) | Browser | Video 1:00 |
| S10 | Damage model report on the VM (AUC, flagged X of Y) | Packet B output | Video 1:35, results card, if B is done |
| S11 | README mermaid flowchart, rendered on GitHub | GitHub | Video 2:35 |

**Before taking any screenshot:** no VM IP, key path or token visible (the repo is public). Crop or blur the SSH prompt.

## Recording checklist (Sun 06:00–08:30 ET)

- [x] D numbers filled in above; brackets removed (Sat 17:30, `docs/validation.md`)
- [ ] Nepali alerts reviewed (packet H, `NE_REVIEWED = True`), or say "draft" on screen
- [ ] Container rebuilt from the frozen `main` (Sun 02:00) and `docker ps` freshly captured
- [ ] Cached scenarios warmed (`scripts/serve_test.sh` or one call per warning time) so the UI doesn't stall on camera
- [ ] Timed run-through ≤ 3:00
- [ ] Upload, then put the link in the Hack2Skill submission by **Sun 09:00 ET**
