"""Escape destinations vs SATELLITE-observed flood extents (UNOSAT FL20260826NPL / FL20261011NPL as the primary
label; HOT (Aug 26) and MBRSC Sentinel-2 (Oct 11) as second products). Same start points and times as
docs/validation/audit_escape.py (its *_ux.json rows). old = main at 0c456c2 (before predict-clarity), new = current.
Results: docs/validation/escape_satellite_check.{json,md}. Run on the VM (labels live in ~/work-agent-lcpizani/events):
    mkdir -p ~/work-agent-lcpizani-ux/satcheck
    git show 0c456c2:engine/escape.py > ~/work-agent-lcpizani-ux/satcheck/escape_old.py
    cp engine/escape_search.c ~/work-agent-lcpizani-ux/satcheck/      # unchanged since 0c456c2
    cd ~/work-agent-lcpizani-ux/repo && python3 docs/validation/escape_satellite_check.py"""
import importlib.util, json, os, sys
import numpy as np

HOME = os.path.expanduser("~")
sys.path.insert(0, f"{HOME}/work-agent-lcpizani-ux/repo")
from engine import escape as new
spec = importlib.util.spec_from_file_location("engine.escape_old", f"{HOME}/work-agent-lcpizani-ux/satcheck/escape_old.py")
old = importlib.util.module_from_spec(spec); spec.loader.exec_module(old)
EV = f"{HOME}/work-agent-lcpizani/events"

out = {}
for valley, ev, extra_key in (("budhi", "oct11", "in_mbrsc_s2_extent"), ("trishuli", "aug26", "in_hot_extent")):
    z = np.load(f"{EV}/{ev}/area_table.npz"); e = np.load(f"{EV}/{ev}/area_labels_extra.npz")
    So, Sn = old.FloodScenario(valley), new.FloodScenario(valley)
    nc = Sn.V.T.shape[1]
    lab = np.full(Sn.V.T.shape[0] * nc, -1, np.int8); lab[z["flat_index"]] = z["y"]       # 1 flooded, 0 dry, -1 none
    ext2 = np.zeros(lab.shape, bool); ext2[z["flat_index"]] = e[extra_key]
    rows = json.load(open(f"docs/validation/audit_escape_{valley}_ux.json"))["rows"]

    def cell(pt):
        x, y = Sn.V.tf.transform(pt["lon"], pt["lat"]); r, c = Sn.V.T.rc(x, y); return r * nc + c

    acc = {"old_dest": [], "new_dest": [], "new_gohere": []}
    moved = []
    for rw in rows:
        a = So.escape(rw["lon"], rw["lat"], rw["t0"]); b = Sn.escape(rw["lon"], rw["lat"], rw["t0"])
        for k, res, key in (("old_dest", a, "destination"), ("new_dest", b, "destination"), ("new_gohere", b, "go_here")):
            d = res.get(key)
            if d:
                i = cell(d)
                safe = res["status"] == "route" and bool(res.get("destination_safe"))
                acc[k].append((safe, int(lab[i]), bool(ext2[i]), bool(Sn.below.flat[i])))
        da = a.get("destination")
        if a["status"] == "route" and a.get("destination_safe") and da and Sn.below.flat[cell(da)]:
            moved.append((int(lab[cell(da)]), bool(ext2[cell(da)])))   # old SAFE below the line: new no longer calls it safe
    res = {}
    for k, L in acc.items():
        safe = [x for x in L if x[0]]
        known = [x for x in safe if x[1] >= 0]
        res[k] = {"answers": len(L), "called_safe": len(safe), "safe_with_satellite_label": len(known),
                  "safe_but_satellite_flooded": sum(x[1] == 1 for x in known),
                  "safe_but_second_product_flooded": sum(x[2] for x in safe),
                  "safe_below_flood_line": sum(x[3] for x in safe)}
    res["old_safe_below_line"] = {"n": len(moved), "satellite_flooded": sum(m[0] == 1 for m in moved),
                                  "satellite_dry": sum(m[0] == 0 for m in moved), "no_label": sum(m[0] < 0 for m in moved),
                                  "second_product_flooded": sum(m[1] for m in moved)}
    out[f"{valley}/{ev}"] = res
    print(valley, ev, json.dumps(res, indent=1), flush=True)
json.dump(out, open("docs/validation/escape_satellite_check.json", "w"), indent=1)
