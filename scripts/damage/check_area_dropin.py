import sys, os, time, json, numpy as np
repo = os.path.expanduser("~/work-agent-lcpizani/repo"); sys.path.insert(0, repo)
from engine import damage_model as dm
from engine.terrain import Terrain
from engine.flood import FloodEnvelope
E = os.path.expanduser("~/work-agent-lcpizani/events")
b = dm.load("area_fb", os.path.join(E, "area_model"))
pre = json.load(open(os.path.join(repo, "models/damage/flood_presets.json")))["presets"]
for ev, proc in (("oct11", "/home/linux1/evac-ai/data/proc"), ("aug26", "/home/linux1/evac-ai/data/proc_trishuli")):
    p = pre[ev]; F = FloodEnvelope([tuple(x) for x in p["arrival_knots"]], [tuple(h) for h in p["height_knots"]], decay_km=1e12, floor_m=0.0)
    rep = json.load(open(f"{E}/{ev}/area_build_report.json")); T = Terrain(proc)
    sx, sy = dm.Transformer.from_crs(4326, 32645, always_xy=True).transform(*rep["terrain"]["source_lonlat"])
    r, c = T.snap_to_channel(*T.rc(sx, sy), radius=15); path = T.downstream_path(r, c); ctx = dm.PathContext(T, path)
    corr = (ctx.drain >= 0) & (ctx.dist <= dm.MAX_DIST_M); idx = np.flatnonzero(corr)
    rr, cc = np.unravel_index(idx, T.shape); x, y = T.transform * (cc + 0.5, rr + 0.5)
    lon, lat = ctx.inv.transform(x, y)
    t = time.time(); pa = dm.predict(b, ctx, np.c_[lon, lat], ["building"] * len(idx), F); ta = time.time() - t
    t = time.time(); pv = dm.predict(dm.load("v2"), ctx, np.c_[lon, lat], ["building"] * len(idx), F); tv = time.time() - t
    ok = np.isfinite(pa) & np.isfinite(pv)
    print(ev, "cells", len(idx), "finite", int(ok.sum()), f"area {ta:.2f}s v2 {tv:.2f}s",
          "share P<=0.10: area %.3f v2 %.3f" % ((pa[ok] <= 0.1).mean(), (pv[ok] <= 0.1).mean()),
          "mean P: area %.3f v2 %.3f" % (pa[ok].mean(), pv[ok].mean()))
