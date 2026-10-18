# Deploy runbook

How to bring up evac-ai from scratch, either **on the L1CC VM** (the LinuxONE deploy the judges see) or **on your own laptop with no VM at all**. Both use the same code and the same Docker image recipe.

## What gets deployed

| App | What it is | Port | Needs |
| --- | --- | --- | --- |
| Leaflet UI + API (`web/`, `api/`, `engine/`) | FastAPI computes scenarios (flood path, GRASS `r.walk` time to safety, alerts) and serves the map UI at `/` | 8000 | Python + GRASS + terrain data, packaged as the `evac-ai` Docker image |
| 3D/2D viewer (`viewer/`) | Three.js replay of a pre-baked bundle in `viewer/data/<replay>/` | 8090 | Any static file server |

```
browser ──> :8000  Docker container (uvicorn api.app:app) ──> GRASS r.walk on data/grassdb
                    └─ mounts data/  (proc/ raw/ grassdb/, ~350 MB, NOT in git)
browser ──> :8090  python3 -m http.server in viewer/   (static, no server-side compute)
```

The terrain products (`data/proc`, `data/raw`, `data/grassdb`) are built on the VM by the `pipeline/` scripts and are not in git. A laptop run needs one copy of them; after that the VM is not used.

## Prerequisites

| Need | For | Notes |
| --- | --- | --- |
| Checkout of `main` | both | `git pull --rebase` before every run |
| Team SSH key (`.pem`) | VM run, and the one-time data copy | Ask a teammate for the file. Never commit it |
| VM address | same | SSH user `linux1`. Written here as `<VM_IP>`; get it from the team chat (this repo is public) |
| Docker | both | Laptop: Docker Desktop, started. VM: installed, used with `sudo` |
| Python 3 | viewer | Only for `python3 -m http.server` |
| `Dockerfile` | both | **Not in git yet.** It is untracked at `~/evac-ai/Dockerfile` on the VM; copy it with `scp` (below) until someone commits it |

Set these once per shell so the commands paste as-is:

```bash
export KEY=~/Downloads/latinos.pem     # path to the team key
export VM=linux1@<VM_IP>
```

## A. Run on the L1CC VM

`~/evac-ai` on the VM is owned by `claude-luis` (see `AGENTS.md`). Coordinate before rebuilding or restarting the container there.

1. Get the code onto the VM. `~/evac-ai` is synced from a laptop rather than pulled from git, so push your checkout's code dirs:

   ```bash
   rsync -az -e "ssh -i $KEY" --exclude __pycache__ api engine pipeline replay web scripts "$VM:evac-ai/"
   ```

2. Build the image (s390x; about 90 s, 1.15 GB):

   ```bash
   ssh -i $KEY $VM 'cd ~/evac-ai && sudo docker build -t evac-ai:latest .'
   ```

3. Start the container. It runs as the owner of `data/` (GRASS refuses a mapset owned by another uid), listens on `127.0.0.1:8000` only, and the script prints a smoke check:

   ```bash
   ssh -i $KEY $VM 'cd ~/evac-ai && bash scripts/docker_run.sh'
   ```

4. Open it from your laptop. Port 8000 is blocked from outside, so use an SSH tunnel:

   ```bash
   ssh -i $KEY -fN -L 8000:127.0.0.1:8000 $VM
   open http://localhost:8000
   ```

   Close the tunnel with `pkill -f "8000:127.0.0.1:8000"`.

What you see in the browser is the VM's copy of the code. Local edits show up only after step 1 (and a container restart for `api/` or `engine/` changes).

## B. Run on your laptop (no VM)

Tested on an Apple Silicon Mac (arm64). The Dockerfile's base is `ubuntu:24.04`, which is multi-arch, so the same recipe builds natively.

1. **Copy the data once** into a folder next to the repo, not inside it (`data/proc` and `data/grassdb` are not gitignored, so a copy inside the repo could get committed):

   ```bash
   DATA=../evac-ai-vmdata
   mkdir -p $DATA
   rsync -az -e "ssh -i $KEY" $VM:evac-ai/data/{proc,raw,grassdb} $DATA/
   ```

   This is a snapshot. Re-run it when the terrain is rebuilt on the VM.

2. **Get the Dockerfile** (until it is committed):

   ```bash
   scp -i $KEY "$VM:evac-ai/Dockerfile" /tmp/evac-ai.Dockerfile
   ```

3. **Build** (Docker Desktop must be running):

   ```bash
   docker build -t evac-ai-local -f /tmp/evac-ai.Dockerfile .
   ```

4. **Run with your local code mounted**, so edits are live: `web/` changes show on refresh, and `api/` or `engine/` changes restart uvicorn on their own.

   ```bash
   docker run -d --name evac-ai-local -p 127.0.0.1:8000:8000 \
     -v "$PWD/engine:/app/engine" -v "$PWD/api:/app/api" -v "$PWD/web:/app/web" \
     -v "$PWD/replay:/app/replay" -v "$PWD/pipeline:/app/pipeline" \
     -v "$(cd ../evac-ai-vmdata && pwd):/app/data" \
     evac-ai-local /opt/venv/bin/uvicorn api.app:app --host 0.0.0.0 --port 8000 \
       --reload --reload-dir api --reload-dir engine
   open http://localhost:8000
   ```

   If an SSH tunnel to the VM is still holding port 8000, close it first (`pkill -f "8000:127.0.0.1:8000"`).

## C. The 3D/2D viewer

Serve it (works the same on the laptop or the VM):

```bash
cd viewer && python3 -m http.server 8090 --bind 127.0.0.1
open "http://localhost:8090/?scenario=oct11"
```

It only reads `viewer/data/<replay>/`. To re-bake a bundle after the engine or terrain changes (runs on the VM, writes only `~/work-claude-lucas` there):

```bash
L1CC_KEY=$KEY L1CC_HOST=$VM viewer/bake/run_on_vm.sh oct11
python3 viewer/bake/validate.py viewer/data/oct11
```

## Check that it works

```bash
curl -s -o /dev/null -w "UI %{http_code}\n" localhost:8000/
curl -s localhost:8000/api/replays
curl -s "localhost:8000/api/scenario?replay=oct11&warn=03:30" | python3 -c "import json,sys; print(json.load(sys.stdin)['summary'])"
```

Expected for Oct 11 with the 03:30 warning: `settlements_at_risk: 20`, `people_at_risk: 1456.0`, `people_without_time: 0.0`. With `warn=06:40` (the official SMS), `people_without_time` should be about 1,456. A first (uncached) scenario takes about 5 s; repeats take under 0.1 s.

On the VM, `scripts/api_smoke.sh` and `scripts/serve_test.sh` run the API outside Docker for quick checks.

## Stop, restart, update

| Task | Laptop | VM |
| --- | --- | --- |
| Stop | `docker stop evac-ai-local` | `sudo docker rm -f evac-ai` |
| Start again | `docker start evac-ai-local` | `bash scripts/docker_run.sh` |
| Logs | `docker logs -f evac-ai-local` | `sudo docker logs -f evac-ai` |
| After a `git pull` | Nothing for code (it's mounted). Rebuild only if the Dockerfile changed | rsync (A.1), then rebuild (A.2) or restart (A.3) |
| New terrain on the VM | Re-run the data rsync (B.1), then `docker restart evac-ai-local` | Nothing |

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Cannot connect to the Docker daemon` | Start Docker Desktop (`open -a Docker`) and wait about 20 s |
| `port is already allocated` on 8000 | An SSH tunnel or another container holds it: `lsof -iTCP:8000 -sTCP:LISTEN` |
| `GRASS r.walk failed` / mapset owned by another user | On the VM, run the container as the owner of `data/` (`docker_run.sh` does this). On a laptop, delete stale locks: `find ../evac-ai-vmdata/grassdb -name .gislock -delete` |
| Page loads but scenarios 500 | `docker logs` for the traceback; usually a missing file under `data/proc` or `data/raw` (re-run the data copy) |
| Tunnel page stops responding | The tunnel died; reopen it (A.4) |
