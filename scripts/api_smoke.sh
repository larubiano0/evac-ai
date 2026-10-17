#!/bin/bash
# Start the API for <=45 s, hit endpoints, print checks, stop. Run on VM from repo root.
pkill -f "uvicorn api.app:app" 2>/dev/null; sleep 1
timeout 45 ~/venv/bin/uvicorn api.app:app --host 127.0.0.1 --port 8000 >/tmp/uv.log 2>&1 &
sleep 4
curl -s -m 35 'localhost:8000/api/scenario?replay=oct11&warn=03:30' > /tmp/s.json
python3 - <<'PY'
import json; d = json.load(open('/tmp/s.json'))
for s in d['settlements'][4:9]:
    a = s['alerts']; print(s['name'], '|', s['name_ne'], '|', a['short_ne'], a['short_ne_chars'], 'ch', a['short_ne_bytes'], 'B')
print(d['settlements'][6]['alerts']['full_en'][180:330])
print(sorted(set(b['label'] for b in d['bridges_at_risk'])))
PY
grep -a -iE 'error|Traceback' /tmp/uv.log | head -3
pkill -f "uvicorn api.app:app"; echo done
