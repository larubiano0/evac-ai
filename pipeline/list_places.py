"""Print OSM place nodes whose names match the Oct 11 timeline (sanity check of coordinates)."""
import json, sys
d = json.load(open("data/raw/places.json"))["elements"]
want = sys.argv[1:] or ("arughat soti arkhet machha khorla dobhan jagat sall saler sirdi philim nyak chumling "
        "lokpa chhek chek ghatt paiyu bagar tatopani yaru shanti tharo salyan beni dharche namrung chumchet gumda "
        "bhum lapu deng").split()
print(len(d), "places")
for e in sorted(d, key=lambda e: -e["lat"]):
    t = e["tags"]; n = (t.get("name:en") or "") + " | " + t.get("name", "")
    if any(x in n.lower() for x in want):
        print(f'{e["lat"]:.4f} {e["lon"]:.4f} {t["place"]:9s} {n}')
