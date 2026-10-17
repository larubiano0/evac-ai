#!/bin/bash
# Run the evac-ai container on L1CC (localhost:8000; reach it via SSH tunnel). Stop: sudo docker rm -f evac-ai
pkill -f "uvicorn api.app:app" 2>/dev/null
sudo docker rm -f evac-ai >/dev/null 2>&1
# run as the owner of data/ (GRASS refuses mapsets owned by another uid); HOME must be writable for GRASS
sudo docker run -d --name evac-ai --user "$(id -u):$(id -g)" -e HOME=/tmp -p 127.0.0.1:8000:8000 -v "$HOME/evac-ai/data:/app/data" evac-ai:latest >/dev/null
for i in $(seq 1 20); do curl -fs -o /dev/null localhost:8000/api/replays && break; sleep 1; done
curl -s -m 60 -o /tmp/c.json -w "scenario via container: %{http_code} in %{time_total}s\n" "localhost:8000/api/scenario?replay=oct11&warn=06:40"
python3 -c "import json;d=json.load(open('/tmp/c.json'));print('host',d['host'],'summary',d['summary'])"
sudo docker ps --format '{{.Names}} {{.Image}} {{.Status}} {{.Ports}}'
