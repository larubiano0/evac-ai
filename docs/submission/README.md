# Submission kit (IBM Z Datathon 2026, team Latinos)

Title: `Latinos_IBM Z Datathon 2026 Project` · submit on Hack2Skill by **Sun Oct 18, 09:00 ET** (freeze 02:00 ET).

## Deliverables (plan §2) and where each one is

| # | Deliverable | Status | Where |
|---|---|---|---|
| 1 | GitHub repo with README: architecture, run steps, libraries & resources, limitations | ready | [`README.md`](../../README.md) |
| 2 | Video ≤ 3:00 | **45 s motivation (recorded) + 1:31 demo below; humans: add narration + face overlay** | [`video/`](video/) |
| 3 | Screenshots of the L1CC instance and the running containers | terminal + app done; **L1CC web console (S1) needs a human** (we don't sign in for you) | [`screenshots/`](screenshots/) |
| 4 | Architecture flowchart (optional) | ready | [`../architecture.html`](../architecture.html), PNGs in [`../figures/`](../figures/) |
| 4 | Prototype link (optional) | the app runs behind an SSH tunnel only (no public port); link the repo + video instead | — |

Judging (10 points each): community value / "Real-Time AI for Critical Decisions", novelty, **technical design and use
of LinuxONE + open-source AI/ML with screenshots as evidence**, execution and pitch.

## Screenshots

All are 1920×1080 stills from the demo recording, taken from the running app on the L1CC VM.

| File | Shows | Judging point |
|---|---|---|
| `S2-l1cc-terminal-z17-docker.jpg` | `lscpu` (s390x, machine type 9175 = z17, 3 CPUs), `nnpa` flag, `docker ps` with `evac-ai` healthy on :8000, live API results for 03:30 vs 06:40 | 3 (LinuxONE evidence) |
| `S6-planner-0330-warning.jpg` / `S5-planner-0640-warning.jpg` | Who had time to escape: 0 vs 1,456 people without time | 1, 4 |
| `S8-planner-damage-model.jpg` | AI damage model colours + "N buildings scored on LinuxONE in X s" | 3 |
| `S7-planner-alerts-en-ne.jpg` | Ranked alerts, one SMS each in English and Nepali | 1 |
| `S9-predict-route.jpg` | Resident "Where should I go?": route to safe ground, leave-by | 1, 2 |
| `S10`–`S13` `go-*.jpg` | Go page: instruction + countdown, Nepali, offline, reached safe ground | 1, 2 |

**Still needed from a human:** S1, the L1CC web console page showing our VM (crop out the IP), and optionally a
screenshot of your own SSH terminal running `sudo docker ps` if you prefer that to S2.

## Demo video (`video/`)

- `record_demo.py` records the whole platform with headless Chrome over the SSH tunnel and builds
  `video/out/demo.mp4` (1920×1080, 30 fps, **no audio**, 90.7 s). Re-run any time:
  `BASE=http://localhost:18000 python docs/submission/video/record_demo.py` (or pass segment names:
  `terminal planner predict go architecture`). `out/` is git-ignored; upload the mp4, don't commit it.
- Blue chips at the top of the screen name each beat, so the video reads without sound.
- The phone segment leaves the right third of the frame empty: a good place for the face overlay.
- Honest-edit notes: the terminal segment replays a real SSH session on the VM captured Sat ~20:45 ET (outputs
  verbatim, `term.html`); in the planner, ~10 s of waiting for the new flood's footprint to load is cut (the app's own
  "computed in N s" label is real); the web segments were recorded against a test container built from the same
  `main` as the demo.

### Shot list and narration (≈ 1:31; read at a calm pace, ~150 words)

| Time | On screen | Say (suggested) |
|---|---|---|
| 0:00 | Terminal on the LinuxONE VM: z17 (9175), `nnpa`, `docker ps`, two `curl` results | "This all runs in one container on an IBM z17 in LinuxONE Community Cloud. Same flood, two warning times: with the villagers' 3:30 phone relay, nobody is left without time; with the 6:40 SMS, all 1,456 people are." |
| 0:16 | Planner: click 03:30 then 06:40; zoom to the upper valley; drag the wave clock | "This is the officials' planner. The first wave moves down the river, kilometre by kilometre, calibrated on the real October 11 flood." |
| 0:30 | Damage model colours | "An AI model trained on 2,759 buildings destroyed on August 26 scores every building and bridge, on LinuxONE, in about a second." |
| 0:36 | Place trigger upstream → new flood computed | "A new report comes in: the river burst here. A new flood, computed in seconds." |
| 0:42 | #1 settlement: ranked alert, English + Nepali SMS | "Alerts come out ranked by who is hit first. One SMS each, English and Nepali: when, which way to climb, which bridge not to cross." |
| 0:49 | Where should I go? Tap a riverside house, then move time forward | "For a resident: tap where you are. Closest safe ground, the route, how long you have. Twenty minutes later, the answer changes to hurry." |
| 1:04 | Go page on a phone: GO UPHILL NOW, countdown, arrow; Nepali | "In a panic nobody reads a map. This page finds you, gives one instruction and a countdown, in Nepali too." |
| 1:11 | Network off, page still works; reach the green flag → safe | "When the network drops, it still knows your way out." |
| 1:22 | Architecture figures: container on LinuxONE; Telum accelerator chart | "One container, open-source tools, models trained on real floods. And the z17's on-chip AI accelerator runs our neural network eighteen times faster than its CPU." |

## Before recording or submitting

- [ ] Warm the demo: load `/`, `/predict`, `/go` once and a Trishuli prediction scenario (~53 s cold).
- [ ] S1 screenshot from the L1CC console (IP cropped).
- [ ] Narrate + overlay the face cam on `demo.mp4`; join with the 45 s motivation part; total ≤ 3:00.
- [ ] No VM IP, key or personal email anywhere in the repo (it is public).
- [ ] Submit on Hack2Skill with the title above, the repo link and the video link.
