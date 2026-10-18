# Deploy

How to run evac-ai, either **on a LinuxONE (s390x) VM** or **on your own laptop**. Both use the same code and the same
[`Dockerfile`](../Dockerfile).

## What gets deployed

One container, one port (8000). Everything is served by the FastAPI app (`uvicorn api.app:app`):

| Route | What it is |
| --- | --- |
| `/` | Landing page |
| `/planner` | Officials' planner: replay a flood, move the warning time, see who still makes it |
| `/predict` | "Where should I go?": drop a pin, get the nearest safe ground and a walking route |
| `/go` | Phone view: GPS, one instruction, countdown, works offline |
| `/viewer/` | Three.js 2D/3D replay of a pre-baked bundle in `viewer/data/<replay>/` (e.g. `/viewer/?scenario=oct11&view=3d`) |
| `/api/...` | Every API endpoint |

```
browser ──> :8000  Docker container (uvicorn api.app:app) ──> GRASS r.walk on data/grassdb
                    ├─ serves web/ pages and viewer/ (static)
                    └─ mounts data/  (proc/ raw/ grassdb/, ~350 MB, not in git)
```

The terrain products (`data/proc`, `data/raw`, `data/grassdb`) are built by the `pipeline/` scripts (see
"Bare metal" in the [main README](../README.md#bare-metal-on-l1cc)) and are not in git. The 3D replay needs none of
them: its data is committed in `viewer/data/`.

## Prerequisites

| Need | For | Notes |
| --- | --- | --- |
| A checkout of this repo | both | |
| Docker | both | Laptop: Docker Desktop, started. VM: installed, used with `sudo` |
| Terrain data in `data/` | planner, predict, go | Build it once with `pipeline/` |
| SSH access to the VM | VM run | User and address of your own VM |

## A. Run on a LinuxONE VM

1. Copy the code onto the VM (or `git clone` it there) and build the terrain data in `data/` once.

2. Build the image (s390x; about 90 s, 1.15 GB):

   ```bash
   sudo docker build -t evac-ai:latest .
   ```

3. Start the container. It runs as the owner of `data/` (GRASS refuses a mapset owned by another uid), listens on
   `127.0.0.1:8000` only, and prints a smoke check:

   ```bash
   bash scripts/docker_run.sh
   ```

4. Open it from your laptop through an SSH tunnel (port 8000 is not exposed publicly):

   ```bash
   ssh -fN -L 8000:127.0.0.1:8000 <user>@<VM_IP>
   open http://localhost:8000
   ```

   Close the tunnel with `pkill -f "8000:127.0.0.1:8000"`.

## B. Run on your laptop

Tested on an Apple Silicon Mac (arm64). The Dockerfile's base is `ubuntu:24.04`, which is multi-arch, so the same
recipe builds natively.

1. Put the terrain data (`proc/`, `raw/`, `grassdb/`) in a folder **next to** the repo, e.g. `../evac-ai-data`, so it
   can't be committed by accident.

2. Build (Docker Desktop must be running):

   ```bash
   docker build -t evac-ai-local .
   ```

3. Run with your local code mounted, so edits are live: `web/` and `viewer/` changes show on refresh, and `api/` or
   `engine/` changes restart uvicorn on their own.

   ```bash
   docker run -d --name evac-ai-local -p 127.0.0.1:8000:8000 \
     -v "$PWD/engine:/app/engine" -v "$PWD/api:/app/api" -v "$PWD/web:/app/web" -v "$PWD/viewer:/app/viewer" \
     -v "$PWD/replay:/app/replay" -v "$PWD/pipeline:/app/pipeline" \
     -v "$(cd ../evac-ai-data && pwd):/app/data" \
     evac-ai-local /opt/venv/bin/uvicorn api.app:app --host 0.0.0.0 --port 8000 \
       --reload --reload-dir api --reload-dir engine
   open http://localhost:8000
   ```

### Only the 3D replay, no data and no Docker

The replay bundle is committed, so you can serve the repo root on the same port and open the same URL:

```bash
python3 -m http.server 8000 --bind 127.0.0.1    # from the repo root
open "http://localhost:8000/viewer/?scenario=oct11&view=3d"
```

To re-bake a bundle after the engine or terrain changes, see [`viewer/bake/`](../viewer/bake/) and
[viewer/README.md](viewer/README.md).

## Check that it works

```bash
curl -s -o /dev/null -w "UI %{http_code}\n" localhost:8000/
curl -s -o /dev/null -w "viewer %{http_code}\n" localhost:8000/viewer/
curl -s localhost:8000/api/replays
curl -s "localhost:8000/api/scenario?replay=oct11&warn=03:30" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary'])"
```

Expected for Oct 11 with the 03:30 warning: `settlements_at_risk: 20`, `people_at_risk: 1456.0`,
`people_without_time: 0.0`. With `warn=06:40` (the official SMS), `people_without_time` should be about 1,456. A first
(uncached) scenario takes about 5 s; repeats take under 0.1 s.

Without Docker, `scripts/api_smoke.sh` and `scripts/serve_test.sh` run the API directly for quick checks.

## Stop, restart, update

| Task | Laptop | VM |
| --- | --- | --- |
| Stop | `docker stop evac-ai-local` | `sudo docker rm -f evac-ai` |
| Start again | `docker start evac-ai-local` | `bash scripts/docker_run.sh` |
| Logs | `docker logs -f evac-ai-local` | `sudo docker logs -f evac-ai` |
| After a `git pull` | Nothing for code (it's mounted). Rebuild only if the Dockerfile changed | Rebuild (A.2), then restart (A.3) |

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Cannot connect to the Docker daemon` | Start Docker Desktop (`open -a Docker`) and wait about 20 s |
| `port is already allocated` on 8000 | An SSH tunnel, a `http.server` or another container holds it: `lsof -iTCP:8000 -sTCP:LISTEN` |
| `GRASS r.walk failed` / mapset owned by another user | Run the container as the owner of `data/` (`docker_run.sh` does this). On a laptop, delete stale locks: `find ../evac-ai-data/grassdb -name .gislock -delete` |
| Page loads but scenarios 500 | `docker logs` for the traceback; usually a missing file under `data/proc` or `data/raw` |
| `/viewer` shows a blank page | Use the trailing slash, `/viewer/`, so its relative `js/` and `data/` paths resolve |
| Tunnel page stops responding | The tunnel died; reopen it (A.4) |
