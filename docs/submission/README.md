# Submission kit (IBM Z Datathon 2026, team Latinos)

Title: `Latinos_IBM Z Datathon 2026 Project` · submit on Hack2Skill by **Sun Oct 18, 09:00 ET** (freeze 02:00 ET).

## Deliverables (plan §2) and where each one is

| # | Deliverable | Status | Where |
|---|---|---|---|
| 1 | GitHub repo with README: architecture, run steps, libraries & resources, limitations | ready | [`README.md`](../../README.md) |
| 2 | Video ≤ 3:00 | **45 s motivation (recorded) + 1:48 demo below; humans: add narration + face overlay** | [`video/`](video/) |
| 3 | Screenshots of the L1CC instance and the running containers | terminal + app done; **L1CC web console (S1) needs a human** (we don't sign in for you) | [`screenshots/`](screenshots/) |
| 4 | Architecture flowchart (optional) | ready | [`../architecture.html`](../architecture.html), PNGs in [`../figures/`](../figures/) |
| 4 | Prototype link (optional) | the app runs behind an SSH tunnel only (no public port); link the repo + video instead | — |

Judging (10 points each): community value / "Real-Time AI for Critical Decisions", novelty, **technical design and use
of LinuxONE + open-source AI/ML with screenshots as evidence**, execution and pitch.

## Interactive 3D replay — separate judge demo

The repo includes a [2D/3D Three.js flood replay](../../viewer/) of the Oct 11 Budhi Gandaki scenario. It shows the flood advancing over the real terrain, settlement status, walking-time/slack layers and the difference between warning times. The replay data is [committed with the viewer](../../viewer/data/oct11/): judges can run it on a laptop without the VM, credentials or a terrain build.

```bash
cd viewer
python3 -m http.server 8090 --bind 127.0.0.1
```

Open <http://localhost:8090/?scenario=oct11&view=3d>. Use the time slider or Space to play; switch between 2D and 3D in the viewer. This is a visual replay of scenario output computed from the terrain and observed flood timing, not a live hydrodynamic simulation. [Viewer guide and controls](../viewer/README.md).

**Submission note:** the committed 1:48 [demo video](video/demo.mp4) does not show this separate viewer. Include the viewer link and these run steps in the written submission, or capture a short viewer clip if the final video is still being edited.

## Screenshots

All are 1920×1080 stills from the demo recording, taken from the running app on the L1CC VM.

| File | Shows | Judging point |
|---|---|---|
| `S0-landing.jpg` | Landing page at `/`: headline, 0 vs 1,456 people without time, 2.6 s on the accelerator | 1, 4 |
| `S2-l1cc-terminal-z17-docker.jpg` | `lscpu` (s390x, machine type 9175 = z17, 3 CPUs), `nnpa` flag, `docker ps` with `evac-ai:nnpa4` healthy on :8000, 03:30 vs 06:40 results, what-if run with `"backend": "nnpa"` | 3 (LinuxONE evidence) |
| `S6-planner-0330-warning.jpg` / `S5-planner-0640-warning.jpg` | Who had time to escape: 0 vs 1,456 people without time | 1, 4 |
| `S8-planner-damage-model.jpg` | AI damage model colours + "N buildings scored on LinuxONE in X s" | 3 |
| `S8b-planner-whatif-telum.jpg` | What-if map: purple = safe now, floods if bigger; 10 M predictions in 2.58 s on the Telum accelerator | 2, 3 |
| `S7-planner-alerts-en-ne.jpg` | Ranked alerts, one SMS each in English and Nepali | 1 |
| `S9-predict-route.jpg` | Resident "Where should I go?": route to safe ground, leave-by | 1, 2 |
| `S10`–`S13` `go-*.jpg` | Go page: instruction + countdown, Nepali, offline, reached safe ground | 1, 2 |

**Still needed from a human:** S1, the L1CC web console page showing our VM (crop out the IP), and optionally a
screenshot of your own SSH terminal running `sudo docker ps` if you prefer that to S2.

## Demo video (`video/`)

- `record_demo.py` records the whole platform with headless Chrome over the SSH tunnel and builds
  `video/out/demo.mp4` (1920×1080, 30 fps, **no audio**, 108 s). Re-run any time:
  `BASE=http://localhost:18000 python docs/submission/video/record_demo.py` (or pass segment names:
  `landing terminal planner whatif predict go architecture`). `out/` is git-ignored; the current cut is committed as `video/demo.mp4`.
- Blue chips at the top of the screen name each beat, so the video reads without sound.
- The phone segment leaves the right third of the frame empty: a good place for the face overlay.
- Honest-edit notes: the terminal segment replays a real SSH session on the VM captured Sat ~21:13 ET (outputs
  verbatim, `term.html`); in the planner, ~10 s of waiting for the new flood's footprint to load is cut (the app's own
  "computed in N s" label is real); landing and what-if were recorded on the live :8000 (`evac-ai:nnpa4`), the other
  web segments on a test container built from main an hour earlier (same pages, before the what-if card existed).

### Shot list and narration (≈ 1:48; read at a calm pace, ~200 words)

| Time | On screen | Say (suggested) |
|---|---|---|
| 0:00 | Landing page: headline, 0 vs 1,456, 2.6 s; scrolls to the three doors | "Time to Safety: flash-flood warning for Nepal's mountain valleys, for officials, for residents, and for a phone in a panic." |
| 0:05 | Terminal on the LinuxONE VM: z17 (9175), `nnpa`, `docker ps`, 03:30 vs 06:40, what-if on `nnpa` | "It all runs in one container on an IBM z17. Same flood, two warning times: the villagers' 3:30 relay leaves nobody without time; the 6:40 SMS leaves all 1,456." |
| 0:22 | Planner: 03:30 then 06:40; zoom; drag the wave clock | "This is the officials' planner. The first wave moves down the river, calibrated on the real October 11 flood." |
| 0:36 | Damage model colours | "An AI model trained on 2,759 buildings destroyed on August 26 scores every building and bridge in about a second." |
| 0:42 | Place trigger upstream → new flood computed | "A new report comes in: the river burst here. A new flood, computed in seconds." |
| 0:48 | #1 settlement: ranked alert, English + Nepali SMS | "Alerts are ranked by who is hit first. One SMS each, English and Nepali." |
| 0:55 | What-if map: purple fringe, card "0.91 km² … 2.58 s on the Telum accelerator" | "A flood's height is never certain, so we score every spot under a hundred possible floods: 12 million predictions. The z17's on-chip AI accelerator does it in under 3 seconds, 31 times faster than our VM's CPUs." |
| 1:06 | Where should I go? Tap a riverside house, then move time forward | "For a resident: tap where you are. Closest safe ground, the route, how long you have." |
| 1:21 | Go page on a phone: GO UPHILL NOW, countdown, arrow; Nepali | "In a panic nobody reads a map. This page finds you, gives one instruction and a countdown, in Nepali too." |
| 1:28 | Network off, page still works; reach the green flag → safe | "When the network drops, it still knows your way out." |
| 1:39 | Architecture figures: container on LinuxONE; Telum chart | "One container, open-source tools, models trained on real floods, on IBM LinuxONE." |

(12 M and 31× are the Trishuli benchmark in `docs/linuxone-ai.md`; the card on screen shows Budhi, 10 M in 2.6 s. Both are real.)

## Before recording or submitting

- [ ] Warm the demo: load `/`, `/predict`, `/go` once and a Trishuli prediction scenario (~53 s cold).
- [ ] S1 screenshot from the L1CC console (IP cropped).
- [ ] Narrate + overlay the face cam on `demo.mp4`; join with the 45 s motivation part; total ≤ 3:00.
- [ ] No VM IP, key or personal email anywhere in the repo (it is public).
- [ ] Submit on Hack2Skill with the title above, the repo link and the video link.
