"""Fetch OSM layers for the study area into data/raw/osm_*.json (Overpass, ODbL)."""
import json, os, sys
from overpass import query

AREAS = {"budhi": (27.85, 84.70, 28.60, 85.10)}   # (south, west, north, east)
LAYERS = {
    "waterways": 'way["waterway"~"^(river|stream)$"]({bb});out geom tags;',
    "highways":  'way["highway"]({bb});out geom tags;',
    "bridges":   '(way["bridge"]({bb});way["man_made"="bridge"]({bb}););out geom tags;',
    "buildings": 'way["building"]({bb});out center tags;',
    "places":    'node["place"]({bb});out body;',
}

def main(area="budhi"):
    s, w, n, e = AREAS[area]; bb = f"{s},{w},{n},{e}"
    os.makedirs("../data/raw", exist_ok=True)
    for name, q in LAYERS.items():
        out = f"../data/raw/osm_{area}_{name}.json"
        if os.path.exists(out): print("skip", out); continue
        r = query(f"[out:json][timeout:170];{q.format(bb=bb)}", timeout=200)
        json.dump(r, open(out, "w"))
        print(name, len(r["elements"]))

if __name__ == "__main__":
    main(*sys.argv[1:])
