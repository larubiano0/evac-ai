#!/bin/bash
# Serve the UI for a bounded test window (default 20 min). Open via SSH tunnel: http://localhost:8000
pkill -f "uvicorn api.app:app" 2>/dev/null; sleep 1
nohup timeout ${1:-1200} ~/venv/bin/uvicorn api.app:app --host 127.0.0.1 --port 8000 >/tmp/uv.log 2>&1 &
sleep 5; curl -s -m 30 -o /dev/null -w "warmup /api/scenario: %{http_code} in %{time_total}s\n" "localhost:8000/api/scenario?replay=oct11&warn=06:40"
curl -s -m 30 -o /dev/null -w "footprint: %{http_code} in %{time_total}s\n" "localhost:8000/api/footprint?replay=oct11"
