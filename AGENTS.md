# AGENTS.md: coordination between the team's coding agents

**Every agent: read this first, then `latinos-ibmz-datathon-plan.md` (spec) and `nepal-disaster-research.md` (background).**
Several agents are working on this repo at once. This file prevents duplicate work and stops agents from overwriting each other.

## Protocol
1. `git pull --rebase` **before starting any task and before every commit.**
2. **Claim a task** by adding or updating your row in the table below, then commit and push *right away*, before doing the work.
3. Don't edit files or VM directories that another agent has claimed. Ask your human to coordinate instead.
4. Push small commits often (at least every 30–45 min). Start commit messages with your agent ID, e.g. `[claude-luis] add HAND build`.
5. When you finish or stop, update your row (status, what's next, what's broken).
6. Never commit secrets: keys (`*.pem`/`*.cer`), the VM IP, tokens. The repo is **PUBLIC**.

## Agent registry
| Agent ID | Human / git author | Host | Working on (claimed) | Status | Updated (ET) |
|---|---|---|---|---|---|
| `claude-luis` | Luis Rubiano (GitHub `larubiano0`) | `luissmacbookpro` (Mac) → drives the L1CC VM over SSH | **Data + terrain + flood engine**: `pipeline/`, `engine/`, VM dirs `~/evac-ai/data/{raw,proc,grassdb}` | In progress: streams + HAND | Sat 14:05 |
| _(next agent: add yourself)_ | | | | | |

## Shared L1CC VM (one machine for the whole team)
- Login as user `linux1` with the team key (path is local to each machine, never in the repo). The IP is in the team chat.
- Specs: z17, 3 vCPU, 7.8 GB RAM, NNPA. The scientific Python stack, **GRASS 8.3, SAGA 9.3 and GDAL 3.8** are installed via apt. **Use system `python3`; don't `pip install` numpy/scipy/sklearn.**
- `~/evac-ai` on the VM is a working copy that `claude-luis` updates with **rsync** (not git), so don't `git pull` there or edit it. Use your own directory, e.g. `~/work-<agent-id>`.
- **There are only 3 CPUs and 7.8 GB of RAM.** Don't start heavy jobs without telling your human, and keep jobs short (minutes, not hours).

## Task board (from the plan, §4.2)
| Task | Owner | State |
|---|---|---|
| OSM + DEM download (Budhi Gandaki) | claude-luis | ✅ done |
| Streams + HAND (GRASS/SAGA) | claude-luis | 🔄 in progress (`r.stream.extract` too slow, see log) |
| Walking time to safety (`r.walk`, negated-DEM trick) | claude-luis | ✅ method verified, ⏳ not yet run |
| Flood path, arrival, height envelope + Oct 11 calibration | claude-luis | ⏳ next |
| Replay JSON `replay/oct11.json` | free | ⏳ |
| Cross-event calibration table (Chamoli 2021, Sikkim 2023, Melamchi 2021; research §8) | free | ⏳ needs numbers pulled from papers |
| Slack + ranking + bridge check | free | ⏳ |
| Alert templates (Nepali/English, ≤200-byte trigger + full plan) | free | ⏳ the Nepali reader reviews them |
| FastAPI + Leaflet UI | free | ⏳ |
| Bridge failure Monte Carlo (`bridge-failure-monte-carlo.md`) | ? (whoever wrote it, please claim it) | 📝 design only |
| Docker on L1CC, README, libraries list | free | ⏳ |

## Key findings other agents must know (don't rediscover these)
- **`r.walk` cost runs FROM start TO cell** (uphill costs more). For time *to* safety, run it on a **negated DEM** with safe cells as the start. Verified with `pipeline/test_rwalk_direction.sh` (1841 s both ways).
- Overpass needs a **User-Agent header** or `overpass-api.de` returns 406 (see `pipeline/overpass.py`).
- Most Python packages have no s390x pip wheels, but **they're already installed via apt**.
- Search engines rate-limit the agents. Use Wikipedia's API and WordPress `?s=` site search on Nepali news sites (e.g. english.onlinekhabar.com).
- BIPAD API `bipadportal.gov.np/api/v1/{river,rain,incident,alert}` is public. Its query filters seem to be ignored.

## Log (newest first; one line per entry)
- Sat 13:54 [claude-luis] Terrain: r.watershed streams OK (align with OSM Budhi Gandaki: median 30 m). SAGA HAND gave ~0 m everywhere (Philim terrace = 0), so I dropped it. Implementing standard HAND (Nobre 2011) in engine/terrain.py: follow the r.watershed D8 directions to the event's flood channel.
- Sat 13:51 [claude-luis] Claimed engine/ (flood path, arrival, height, time-to-safety) in addition to pipeline/. Now: streams via r.watershed stream= output (r.stream.extract too slow).
- Sat 14:00 [claude-luis] `r.stream.extract` on the full 3.7M-cell grid timed out after 200 s. Next: cut the region to the river corridor, or use `r.watershed` stream output instead.
- Sat 13:55 [claude-luis] `r.watershed` OK, `r.walk` direction verified, DEM clipped to UTM45N 30 m (1357×2748, 335–7148 m).
- Sat 13:40 [claude-luis] OSM pulled: 114,910 buildings, 517 places, waterways, highways, bridges. DEM tiles N27–28 E084–085.
- Sat 13:10 [claude-luis] L1CC probe done; plan rewritten; research pushed.
