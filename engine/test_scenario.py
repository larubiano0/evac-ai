"""Oct 11 scenario: compare warning triggers (VM, repo root)."""
import sys, json, time
sys.path.insert(0, ".")
from engine.scenario import Valley, Scenario

t = time.time(); V = Valley(); print(f"valley load {time.time()-t:.1f}s, buildings={len(V.b_flat)}, places={len(V.p_name)}, bridges={len(V.bridge_meta)}")
rep = json.load(open("replay/oct11.json"))
S = Scenario(V, rep, extra_people={"Jagat": 100})          # ~100 trekkers stranded in Jagat (MCAP via Onlinekhabar)
print(f"scenario {S.runtime_s:.1f}s (r.walk {S.walk_s:.1f}s)")
for k, trig in rep["triggers"].items():
    print(k.ljust(16), S.summary(trig["time"]))
print("\nTop settlements, warning at official SMS 06:40:")
for s in S.settlements("06:40")[:14]:
    print(f'  #{s["alert_rank"]:2d} {s["name"][:18]:18s} km {s["river_km"]:5.1f} arrival {s["arrival_early"]} '
          f'bldg {s["buildings_at_risk"]:4d} ppl {s["people_at_risk"]:6.0f} walk {s["walk_min_median"]:4.1f}/{s["walk_min_max"]:4.1f} '
          f'slack {s["slack_min"]:7.1f} {s["status"]}')
