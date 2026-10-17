import sys
from overpass import query
pat = sys.argv[1]
r = query(f'[out:json][timeout:90];nwr["name"~"{pat}",i](27.85,84.70,28.65,85.20);out center tags;')
for e in r["elements"]:
    c = e.get("center", e); t = e["tags"]
    print(f'{c.get("lat",0):.4f} {c.get("lon",0):.4f} {e["type"]:8s} {t.get("name","")} | {t.get("name:en","")} | ' +
          ",".join(f"{k}={v}" for k, v in t.items() if k in ("place","highway","bridge","waterway","amenity","man_made","natural")))
