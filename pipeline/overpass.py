"""Minimal Overpass client (needs a User-Agent or overpass-api.de returns 406)."""
import json, sys, time, urllib.request, urllib.parse
UA = {"User-Agent": "evac-ai-hackathon/0.1 (github.com/larubiano0/evac-ai)"}
EPS = ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter"]

def query(q, timeout=180):
    last = None
    for ep in EPS:
        for attempt in range(2):
            try:
                req = urllib.request.Request(ep, data=urllib.parse.urlencode({"data": q}).encode(), headers=UA)
                return json.load(urllib.request.urlopen(req, timeout=timeout))
            except Exception as e:
                last = e; time.sleep(5)
    raise RuntimeError(f"overpass failed: {last}")

if __name__ == "__main__":
    print(json.dumps(query(sys.argv[1]))[:2000])
