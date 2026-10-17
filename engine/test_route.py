"""Verify r.walk outdir tracing: tts must fall along the route and end at 0 (safe)."""
import sys, json; sys.path.insert(0, ".")
import numpy as np
from engine.scenario import Valley, Scenario
from engine.safety import time_to_safety, trace_route
V = Valley(); S = Scenario(V, json.load(open("replay/oct11.json")))
tdir = time_to_safety.tdir
at_risk, arr, walk, slack = S.buildings("06:40")
idx = np.flatnonzero(at_risk)[np.argsort(-walk[at_risk])][:8]          # 8 longest walks
for i in idx:
    r, c = V.b_rc[i]; rt = trace_route(tdir, S.tts, r, c)
    t = [S.tts[a, b] for a, b in rt]
    mono = all(t[k + 1] <= t[k] + 1e-6 for k in range(len(t) - 1))
    climb = V.T.dem[rt[-1]] - V.T.dem[rt[0]]
    print(f"bldg {i}: walk {walk[i]:.1f} min, steps {len(rt)}, tts {t[0]:.0f}->{t[-1]:.0f}s, monotone={mono}, climb {climb:.0f} m")
