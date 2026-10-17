"""Check that load() + predict() through engine/damage_model.py reproduces the training-time predictions.

Uses the 300-row sample saved by train_eval.py (models/damage/train_pred_sample.json): rebuilds the Trishuli
path context, recomputes features from lon/lat via the public interface, and compares calibrated p.
For v2 the Aug 26 damage-mark envelope stored in the bundle is used. Exit code 1 on mismatch.
"""
import json, os, platform, sys, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from engine import damage_model as dm
from engine.terrain import Terrain
from engine.flood import FloodEnvelope
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_table import SOURCE


def main(proc="/home/linux1/evac-ai/data/proc_trishuli"):
    s = json.load(open(os.path.join(dm.MODEL_DIR, "train_pred_sample.json")))
    T = Terrain(proc)
    r, c = T.snap_to_channel(*T.rc(*dm.TF.transform(*SOURCE)), radius=15)
    ctx = dm.PathContext(T, T.downstream_path(r, c))
    ok = True
    for ver in ("v1", "v2"):
        b = dm.load(ver)
        env = FloodEnvelope([(0.0, 0.0), (1.0, 1.0)], b["aug26_envelope_knots"]) if ver == "v2" else None
        t0 = time.time()
        p = dm.predict(b, ctx, s["rows_lonlat"], s["kind"], env)
        dt = time.time() - t0
        ref = np.array(s[f"p_{ver}"])
        err = np.nanmax(np.abs(p - ref))
        good = bool(np.isfinite(p).all() and err < 1e-5)
        ok &= good
        print(f"{ver}: {len(p)} rows, max |p - p_train| = {err:.2e}, finite={np.isfinite(p).all()}, "
              f"{'OK' if good else 'MISMATCH'} ({dt:.2f} s, {platform.machine()}, trained on {b['meta']['arch']})")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
