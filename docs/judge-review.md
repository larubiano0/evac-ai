# Judge's-eye review (Sat Oct 17, ~17:50 ET; freeze Sun 02:00 ET, about 8 h left)

Owner `agent-aayush`. This is an honest score of the project **as it stands now**, against the four judging criteria
(10 points each) and the separate AI Innovation Excellence award. Then a ranked fix list, ordered by score gained per hour.
Validation numbers are in [`validation.md`](validation.md).

## Scores today

| Criterion | Now | Reachable by freeze | Why |
|---|---|---|---|
| 1. Community value, fit with "Real-Time AI for Critical Decisions" | **7** | 8–9 | Real 2026 Nepali floods and real warning timelines. The decision (who to warn first, which bridge not to cross) is concrete. **Minus:** the Nepali text is unreviewed, there's no live trigger feed, and no official or community voice is in the pitch |
| 2. Novelty | **7** | 7–8 | Per-building *slack* (arrival − warning − walk uphill) as the decision quantity. HAND measured against **this flood's** path. r.walk run on a negated DEM. A damage model whose key feature (freeboard) transfers across events. A resident "where should I go?" with a confidence. The components are standard; the combination and the framing are not |
| 3. Technical design, LinuxONE + open-source AI/ML, **with screenshots** | **4–5** | 7–8 | Runs on s390x in a container, CPU only, measured latency, spatial-holdout ML, calibrated probabilities. **Minus:** no screenshots in the repo; the container doesn't include prediction mode or the model; the LinuxONE story is only "it runs"; NNPA isn't shown |
| 4. Execution and pitch | **5** | 8 | Script written, numbers validated today. **Minus:** not recorded; three UIs compete for 3 minutes; the damage model isn't visible in the main planner UI |
| AI Innovation Excellence (separate) | contender | stronger | The damage model is the candidate: trained on one real flood, tested on a part of the river it never saw (AUC 0.97 / 0.82), Platt-calibrated, applied out of event to Oct 11 (146 expected vs. 365 footprint vs. ~62–72 reported). Judges must *see* it in the demo |

## What will impress a judge

- **The headline is real and checkable:** 0 vs. 1,456 people without time (03:30 village relay vs. 06:40 SMS), on a
  flood that happened 6 days ago. For Aug 26, an alert at the 08:37 seismic signal cuts the people without time by ~87 % in the model.
- **Honest validation:**
  - Leave-one-out arrival errors, with the direction of error stated (extrapolation is early, the safe side).
  - 9 of 10 mappable destroyed places flagged, 4 of 6 lost bridges.
  - The two misses explained by root cause (OSM gap, 175 m D8 drift).
  - Footprint validated **cross-side**, not in-sample.
  - The finding that wave speed doesn't transfer between flood types (up to 163 min late), with what we did about it (per-type presets).
- **Speed on L1CC:** 5 s per new scenario, 30 ms cached, 2–5 ms per "where do I go" query.
- **Design for failure:** templates instead of an LLM for life-safety text; one-SMS Nepali alert (62–69 chars, fits Meshtastic); no reporter identities stored.

## What is missing or weak

1. **No screenshots in the repo.** Criterion 3 asks for them explicitly: L1CC instance, running containers, the model running on the VM.
2. **The container is behind `main`.**
   - The `Dockerfile` copies `engine/ api/ web/ replay/ pipeline/` but **not `models/`**, and has **no C compiler**.
     `engine/escape.py` compiles `escape_search.c` with `cc` at first use.
   - So prediction mode and the damage model only run bare-metal (port 8001). A rebuild from `main` keeps the planner
     working, because the escape import is lazy, but `/api/predict/*` would fail inside the container.
3. **The LinuxONE story is thin.** "s390x, big-endian" is a porting hazard we handled, not a reason to choose Z. What's
   missing is a measured reason. See the NNPA test below.
4. **The ML isn't in the planner.** `p_destroyed` isn't in `/api/scenario` or on the Leaflet map yet (agent-aayush's queue). Only prediction mode uses the model.
5. **Nepali alerts are unreviewed** (`NE_REVIEWED = False`). In a pitch about Nepal, "draft Nepali" undercuts criterion 1.
6. **Three UIs** (planner `web/index.html`, resident `web/predict.html`, 3D `viewer/`). That's good material, but without a plan it's a confusing demo. The beats are below.

## NNPA / Snap ML: verified on the demo VM today

> **Superseded (Sat 21:11):** this was true for tree models only. A dense neural stand-in now runs on the
> accelerator in the live app: 100 what-if floods (10 M predictions) in 2.6 s, 31× faster than the CPU path in our
> benchmark. See [linuxone-ai.md](linuxone-ai.md).

- The z17 guest exposes the **`nnpa`** CPU flag.
- **Snap ML 1.17.2** installs from a binary s390x wheel in seconds (`pip install snapml` in a `--system-site-packages` venv).
- Without zDNN it warns "Falling back to CPU-only mode". `libzdnn0` is in Ubuntu's apt repo. Extracted without sudo
  (`apt-get download libzdnn0 && dpkg -x`, `SNAPML_ZDNN_LIB=...`), `zdnn_is_nnpa_installed()` returns **True**, and
  Snap ML loads its `_zdnn` build.
- **Measured on a toy problem** the size of our training table (23.6k rows, 10 features, 300 trees of depth 4):
  - Snap ML fits in 0.33 s, about the same as sklearn HGB's 0.4 s.
  - Plain CPU prediction: **0.05 s**. The zDNN path (after `optimize_trees()`): **0.44 s** per 23.6k rows, and 4.3 s for 472k rows.
- **So NNPA is reachable, but it does not speed up a model this small.** We didn't check whether a warm-up call or batch
  size changes this, and didn't retrain our real model in Snap ML.
- **Recommendation:** don't make NNPA the headline. One honest line works: "we tested the Telum accelerator through
  Snap ML and zDNN. For a 300-tree model, the CPU path is faster, so we serve on CPU." The optional IBM labs show NNPA with
  Granite (see below). Spend the hours on items 1–5 below.

## Predictive vs. generative: should we add a Granite Q&A?

**No, not on the demo VM.**
- A grounded Granite Q&A for officials ("why is Dobhan red?") would need llama.cpp plus a 2–3 B model in ~2–3 GB of
  RAM. That's on a 7.8 GB VM shared with a second server on :8001 and r.walk jobs that peak at ~1.7 GB.
- It's also a new failure mode in a life-safety demo, and the team already decided on templates for alerts.
- Generative AI is **optional** for this datathon, and the IBM labs are **optional too** (an organizer confirmed Sat
  that they are not mandatory). If someone wants Granite in the story, the **Loan_Approval_Demo** lab (Granite on
  llama.cpp with zDNN) on a *separate* VM is a source of inspiration and a screenshot. It isn't a requirement.

If the top 6 items are done with time to spare, a separate VM could run a Granite "explain this settlement's status"
page that quotes only `/api/scenario` fields. It must be clearly labelled advisory and kept out of the alert text.

## Which UI for which beat of the video

| Beat | UI | Why |
|---|---|---|
| 0:00–0:30 problem | **`viewer/` 3D replay** of Oct 11, time slider moving the wave down the gorge | The best visual hook; shows terrain and scale in 10 s |
| 0:50 "runs on LinuxONE" | VM terminal: `uname -m`, `lscpu` (machine type 9175, `nnpa` flag), `docker ps` | Evidence for criterion 3 |
| 1:00–1:55 the decision | **Planner `web/index.html`**: drop the trigger, footprint, slack colours, ranked EN/NE alerts, bridges, 03:30 vs. 06:40 compare | Criterion 1: "Real-Time AI for Critical Decisions" is the official's view |
| 1:55–2:10 the resident | **`web/predict.html`**: one click, "where should I go?", route + confidence + leave-by time | Shows the ML (P(destroyed) overlay) and the community end of the system in 15 s |
| 2:10–2:35 results | Static results card from `validation.md` | Numbers judges can check |

Add header links between the three pages so the cut feels like one product (~15 min).

## Ranked priority list (score gained ÷ hours, ~8 h to freeze)

| # | Fix | Hours | Criterion | Who |
|---|---|---|---|---|
| 1 | **Nepali review** of `engine/alerts.py`, set `NE_REVIEWED = True` | 0.25 | 1, 4 | Aayush or another Nepali reader |
| 2 | **Screenshots + a "Running on LinuxONE" README section** (S1–S11 in `video-script.md`, into `docs/screenshots/`; no IP, key path or email visible). Put the security posture in words: API bound to 127.0.0.1, SSH tunnel only, only port 22 open, non-root container, no reporter identities, data stays on the VM | 0.75 | 3 | human (L1CC console) + agent-aayush |
| 3 | **Rebuild the container from `main` with prediction mode**: `COPY models/`, add `gcc` (or build `escape_search.so` in the image, `EVAC_BUILD_DIR`), serve both UIs from one container. Test on port 8002 first, then swap; recapture `docker ps` | 1 | 3 | agent-aayush (Dockerfile) + agent-lcpizani (escape/DEPLOY.md) |
| 4 | **Show the damage model in the planner**: `p_destroyed` per building / settlement / bridge in `/api/scenario` (new keys only) + colour scale on the map; one video line with AUC 0.97 | 1.25 | AI award, 3, 4 | agent-aayush |
| 5 | **Freeze the video plan** using the beats above; timed dry run ≤ 3:00; warm the caches | 0.5 before freeze (+ recording Sun 06:00–08:30) | 4 | humans |
| 6 | **A measured LinuxONE throughput story**: precompute a plan for every trigger km × warning time for the Budhi Gandaki (~95 scenarios × 5 s ≈ 8 min, bounded, at night). Gives "an offline plan for every village before the next flood". Plus one honest NNPA line | 1.5 | 2, 3 | agent-aayush |
| 7 | Header links between the three UIs | 0.25 | 4 | agent-aayush / lcpizani |
| 8 | Packet X: arrival points from Chamoli 2021 / Sikkim 2023 to test cross-event wave speeds (km + time only, no terrain build) | 1.5 | 2 (evidence) | free |
| 9 | Aug 26 in the planner API (the OSM conversion now exists in `docs/validation/run_aug26.py`). About +1.5 GB of RAM for a second valley on the shared VM | 1 | 4 | agent-aayush; only if 1–8 are done |
| 10 | *Optional:* IBM labs (organizer confirmed Sat they are **not mandatory**). Only as inspiration or a screenshot for the NNPA/Granite story, on a separate VM ([`ibm-labs.md`](ibm-labs.md)) | 1–1.5 | 3 (minor) | anyone with spare time |
| — | **Don't before freeze:** stream-burn the OSM river into the DEM (the Arughat fix; `pipeline/`, rebuilds all terrain), a Granite Q&A on the demo VM, retraining on Snap ML | | | |

**Top 5 = about 3.75 h** (Nepali review, screenshots + LinuxONE section, container rebuild, `p_destroyed` in the planner, video plan), which leaves room for #6–7 before 02:00. The IBM labs are optional (organizer, Sat) and sit at the bottom.
