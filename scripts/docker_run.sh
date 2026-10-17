#!/bin/bash
# Run the evac-ai container on L1CC (localhost:8000; reach it via SSH tunnel). Stop: sudo docker rm -f evac-ai
# Overrides (defaults = the original setup): IMAGE, NAME, PORT, DATA (host data/ dir; it must contain processed/ for
# the damage model and prediction mode, e.g. a full repo checkout's data/ plus proc/, raw/, grassdb/).
IMAGE=${IMAGE:-evac-ai:latest}; NAME=${NAME:-evac-ai}; PORT=${PORT:-8000}; DATA=${DATA:-$HOME/evac-ai/data}
[ "$PORT" = 8000 ] && pkill -f "uvicorn api.app:app --host 127.0.0.1 --port 8000" 2>/dev/null
sudo docker rm -f "$NAME" >/dev/null 2>&1
# run as the owner of data/ (GRASS refuses mapsets owned by another uid); HOME must be writable for GRASS
sudo docker run -d --name "$NAME" --user "$(id -u):$(id -g)" -e HOME=/tmp -p 127.0.0.1:$PORT:8000 -v "$DATA:/app/data" "$IMAGE" >/dev/null
for i in $(seq 1 20); do curl -fs -o /dev/null localhost:$PORT/api/replays && break; sleep 1; done
curl -s -m 60 -o /tmp/c.json -w "scenario via container: %{http_code} in %{time_total}s\n" "localhost:$PORT/api/scenario?replay=oct11&warn=06:40"
python3 -c "import json;d=json.load(open('/tmp/c.json'));print('host',d['host'],'summary',d['summary'])"
sudo docker ps --format '{{.Names}} {{.Image}} {{.Status}} {{.Ports}}'
