# Submission process log

What was checked and done to get evac-ai ready for the Hack2Skill form, in order. Written by `agent-lcpizani-submit` for Lucas, Sun Oct 18 2026 (times ET).

**Deadline: the form closes 18/10/2026 12:30 IST = Sun 03:00 ET.** `AGENTS.md` and the plan say 09:00 ET; that is after the form closes.

## Steps

| # | Time | Step | Result |
|---|---|---|---|
| 1 | 00:36 | `git pull --rebase`, read `AGENTS.md` | main at e16800b (demo video committed) |
| 2 | 00:38 | Claimed the task in `AGENTS.md` (registry row + log line), pushed | e25a169 |
| 3 | 00:39 | Secrets scan of the tracked tree (249 files) | clean, see §1 |
| 4 | 00:40 | Scan of the full public history for the VM IP and personal emails | 1 finding (author metadata), see §1 |
| 5 | 00:40 | Code-level check of `api/app.py`, `Dockerfile`, `scripts/docker_run.sh` | no blocking issue, see §2 |
| 6 | 00:41 | Data provenance + numbers check | all data public; README credits incomplete, see §3 |
| 7 | 00:41 | Drafted every form field in [`submissions.md`](../../submissions.md), checked lengths ≤ 1,024 chars, opened all 20 links (HTTP 200) | done |
| 8 | 00:45 | Pitch deck outline: [`pitch/outline.md`](pitch/outline.md) | waiting for Lucas's direction |

## 1. Secrets and personal data

How: `git grep` over the tracked tree for key and token formats (AWS, OpenAI/Anthropic, GitHub, Slack, Google, Hugging Face, PEM headers), `api_key/password/secret/token = "..."` assignments, IPv4 addresses and email addresses; `git log --remotes -p` for the VM IP and the team's known personal domains; secret-looking file names (`*.pem`, `*.key`, `.env`, `id_rsa`).

- **Tracked files: clean.** No keys, tokens, passwords, private keys, VM IP or personal email in any file. `.gitignore` excludes `*.pem`, `*.cer`, `*.key`, `.env`.
- **History content: clean.** No IP or personal email in any diff on any public branch.
- **⚠️ One finding, history metadata:** commit `620a3ef` ("Prediction mode: …", on `main` and all public branches, 61 commits below the tip) has Lucas's personal Gmail as author and committer. This breaks `AGENTS.md` rule 6. Two more such commits (`f913fdd`, `75f1cbb`) exist only on the **local** branch `data/initial-datasets`, not on GitHub.
  - Fixing it means rewriting `main` and force-pushing, which every teammate must then resync (as on Sat 15:10). **Not done; Lucas to decide.** With ~2 h to the deadline, the low-risk option is to leave it and rewrite after judging.
- Local only, never committed: `.venv/`, `.impeccable/`, `__pycache__/`, `data/raw/`, `.claude/worktrees/` (all ignored).

## 2. Code and deployment

- **Inputs are whitelisted.** Replay, valley and preset names are checked against known keys (404/501 otherwise); coordinates are typed floats (pydantic). No shell calls or user-controlled file paths in the API.
- **Not exposed to the internet.** The container publishes `127.0.0.1:8000` only and is reached over an SSH tunnel. It runs as the uid of `data/`, not root.
- **Minor, demo-acceptable:** `POST /api/trigger` caches every new coordinate with no size limit (`CACHE` in `api/app.py`), so many distinct requests would grow memory. Only matters if the port were ever made public.
- `models/*.joblib` are pickles loaded at start-up. They are our own files, so this is fine; never load models from untrusted sources.

## 3. Data: public sources and accuracy

**Every dataset is public** and documented with a source link and licence: `data/README.md` + `data/docs/` (DEM, OSM, WorldPop, landslides, DHM), `scripts/damage/events/SOURCES_*.md` and `DATASETS_flood_extent.md` (satellite flood extents, Ahr damage), and the `sources` list in each `replay/*.json` (every observation has a `src`, and weak ones are marked `excluded`).

**Numbers spot-checked against the result files:** 0 vs 1,456 people without time and 5.1 s per scenario (`docs/validation/oct11_results.json`), surrogate MAE 0.012 and 131 s training (`models/surrogate/metrics.json`), damage-model ROC AUC 0.968 / PR 0.740 (`models/damage/README.md`), event times (`nepal-disaster-research.md` §1.1). All match what the form drafts say.

**Gaps (README is owned by agent-aayush; not edited, waiting for OK):**
1. **README "Libraries & Resources" is missing resources that the code uses**, which the plan's hard rule requires:
   - Satellite flood extents that train the production `area_fb` model: UNOSAT FL20260826NPL and FL20261011NPL, Copernicus EMS EMSR517 (Ahr) and EMSR927, HOT flood extent via HDX, UNOSAT Derna FL20230912LBY.
   - Ahr building damage labels (Samprogna Mohor et al., 4TU.ResearchData, doi:10.4121/8f7a21d3-…).
   - IBM zDNN / libzdnn (Telum accelerator), IBM Snap ML (benchmark only), joblib, geopandas, Pillow, websocket-client, Three.js (vendored in `viewer/vendor/three`), IBM Plex fonts (Google Fonts).
2. **README is out of date in three places:** says the Nepali text is an unreviewed draft (`NE_REVIEWED = True` since Sat 18:55); says `models/` isn't in the container (the `Dockerfile` copies it now); lists the damage model and `p_destroyed` as "in progress" (done).
3. **Two different AUCs.** 0.968 is the *building* damage model v2 on the Aug 26 downstream holdout. The per-cell map uses `area_fb`, AUC 0.937 on unseen Oct 11. Use the right one on each slide.
4. **No `LICENSE` file.** The repo is public but has no licence, so legally nobody may reuse it. Adding one (e.g. MIT) is a team decision.
5. The Aug 26 "~12,300 → ~1,600" figure is in-sample (the flood line is rebuilt from the same damage marks). Say "model estimate".

## 4. Repo tidiness

Fine for judging. The repo root has planning notes that aren't part of the product (`interview-skill.md`, `bridge-failure-monte-carlo.md`, `latinos-ibmz-datathon-plan.md`, `nepal-disaster-research.md`). The README links the last two, so keep them; the first two could move to `plans/`. `docs/validation/` keeps every audit run (`audit_escape_*_{orig,main,fixed,…}.json`), which is noisy but documents the history. Nothing was moved or deleted.

## Still to do (humans)

- [ ] Video: narrate, join with the motivation clip (≤ 3:00), upload to YouTube **Unlisted**, paste the link.
- [ ] Pitch deck PDF ≤ 5 MB.
- [ ] S1 screenshot (L1CC console, IP cropped), optional.
- [ ] Decide: history rewrite for `620a3ef`, README fixes, `LICENSE`.
- [ ] Paste `submissions.md` into the form and submit **before 03:00 ET**.
