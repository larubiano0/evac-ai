"""Damage model (packet B): P(affected | a flood passes down this river path) for buildings and bridges.

Trained on the Aug 26 2026 Bhotekoshi-Trishuli OSM damage labels (scripts/damage/), applied to any valley
the engine has built (e.g. Budhi Gandaki, Oct 11). Features are terrain-only and are computed the same way
for training and inference, from an engine.terrain.Terrain and a flood path (flat cell indices):

  hand            height above the flood path (Terrain.hand_to), m
  river_km        river distance from the path source of the channel cell the row drains into, km
  dist_channel_m  straight-line distance to the nearest path cell, m
  slope_deg       ground slope at the row's cell
  valley_width_m  area with HAND <= 30 m draining into +-1 km of channel, divided by that channel length, m
  channel_slope   channel gradient over +-1 km (m/m)
  bend_curv       signed turn of the channel over +-10 cells, radians (+ = left / counter-clockwise)
  outside_bend    bend_curv signed by bank side: > 0 = outside of the bend (where floods climb higher)
  log_acc         log(1 + flow accumulation) at the drain cell (river size)
  ls_500m         2015 Gorkha-earthquake landslide centroids within 500 m (Roback et al. 2017)
  kind            0 = building, 1 = bridge
  freeboard       (v2 only) hand - envelope height at river_km, m; < 0 = below that event's flood line

Rows outside the corridor (not draining into the path, or more than max_dist_m from it) get NaN.
"""
import csv, os, time
import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree
from pyproj import Transformer

CELL = 30.0                      # m, engine grids are UTM 45N 30 m
WIN = 33                         # path cells (~1 km) each side for width / channel slope
BEND = 10                        # path cells each side for the bend angle
WIDTH_HAND_M = 30.0              # HAND level that defines the valley floor for valley_width_m
LANDSLIDE_R_M = 500.0
MAX_DIST_M = 500.0               # corridor half-width used for training and inference
FEATURES_V1 = ["hand", "river_km", "dist_channel_m", "slope_deg", "valley_width_m", "channel_slope",
               "bend_curv", "outside_bend", "log_acc", "ls_500m", "kind"]
FEATURES_V2 = FEATURES_V1 + ["freeboard"]
KIND = {"building": 0, "bridge": 1}

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANDSLIDES_CSV = os.path.join(REPO, "data", "processed", "landslides_2015.csv")
MODEL_DIR = os.path.join(REPO, "models", "damage")
TF = Transformer.from_crs(4326, 32645, always_xy=True)

_landslide_tree = None


def landslide_tree(path=LANDSLIDES_CSV):
    global _landslide_tree
    if _landslide_tree is None:
        with open(path) as f:
            ll = np.array([(float(r["lon"]), float(r["lat"])) for r in csv.DictReader(f)])
        x, y = TF.transform(ll[:, 0], ll[:, 1])
        _landslide_tree = cKDTree(np.c_[x, y])
    return _landslide_tree


class PathContext:
    """Per-(terrain, flood path) grids and per-path-cell profiles shared by all rows."""

    def __init__(self, T, path):
        t0 = time.time()
        self.T, self.path = T, np.asarray(path, np.int64)
        n = len(self.path)
        self.prc = np.array(np.unravel_index(self.path, T.shape))            # 2 x n (rows, cols)
        step = np.hypot(*np.diff(self.prc, axis=1)) * CELL
        self.km_path = np.concatenate([[0.0], np.cumsum(step)]) / 1000.0
        self.hand, self.drain = T.hand_to(self.path)
        self.pos = np.full(T.nxt.size, -1, np.int64)
        self.pos[self.path] = np.arange(n)
        on_path = np.zeros(T.shape, bool)
        on_path.flat[self.path] = True
        self.dist = ndimage.distance_transform_edt(~on_path) * CELL
        gy, gx = np.gradient(T.dem, CELL)
        self.slope = np.degrees(np.arctan(np.hypot(gx, gy)))

        i = np.arange(n)
        lo, hi = np.clip(i - WIN, 0, n - 1), np.clip(i + WIN, 0, n - 1)
        seg_m = (self.km_path[hi] - self.km_path[lo]) * 1000.0
        z = T.dem.flat[self.path]
        self.channel_slope = np.where(seg_m > 0, (z[lo] - z[hi]) / np.maximum(seg_m, 1e-9), 0.0)
        d, h = self.drain.ravel(), self.hand.ravel()
        floor = (d >= 0) & (h <= WIDTH_HAND_M)
        cnt = np.bincount(self.pos[d[floor]], minlength=n).astype(float)
        cs = np.concatenate([[0.0], np.cumsum(cnt)])
        self.valley_width = np.where(seg_m > 0, (cs[hi + 1] - cs[lo]) * CELL * CELL / np.maximum(seg_m, 1e-9), np.nan)

        X, Y = self.prc[1].astype(float), -self.prc[0].astype(float)          # east, north (rows grow south)
        b_lo, b_hi = np.clip(i - BEND, 0, n - 1), np.clip(i + BEND, 0, n - 1)
        h_in = np.arctan2(Y[i] - Y[b_lo], X[i] - X[b_lo])
        h_out = np.arctan2(Y[b_hi] - Y[i], X[b_hi] - X[i])
        turn = np.angle(np.exp(1j * (h_out - h_in)))
        turn[(b_lo == i) | (b_hi == i)] = 0.0                                 # path ends: no bend defined
        self.turn = turn
        self.dir_x, self.dir_y = X[b_hi] - X[b_lo], Y[b_hi] - Y[b_lo]
        self.log_acc = np.log1p(np.abs(T.acc.flat[self.path]))
        self.build_s = time.time() - t0

    def cells(self, x, y):
        """UTM x, y -> (row, col, inside-grid mask)."""
        c, r = ~self.T.transform * (np.asarray(x, float), np.asarray(y, float))
        r, c = np.floor(r).astype(np.int64), np.floor(c).astype(np.int64)
        ok = (r >= 0) & (r < self.T.shape[0]) & (c >= 0) & (c < self.T.shape[1])
        return np.where(ok, r, 0), np.where(ok, c, 0), ok


def features(ctx, lonlat, kinds, envelope=None, max_dist_m=MAX_DIST_M):
    """Feature matrix for points (lon, lat) of the given kinds ('building' / 'bridge' or 0 / 1).

    Returns (X, cols, in_corridor, extra) where X has NaN rows outside the corridor and extra holds
    per-row river_km / dist (also for rows outside, NaN when undefined) for reporting.
    """
    lonlat = np.asarray(lonlat, float).reshape(-1, 2)
    k = np.array([KIND.get(v, v) for v in kinds], float)
    x, y = TF.transform(lonlat[:, 0], lonlat[:, 1])
    r, c, inside = ctx.cells(x, y)
    flat = r * ctx.T.shape[1] + c
    d = np.where(inside, ctx.drain.ravel()[flat], -1)
    j = np.where(d >= 0, ctx.pos[np.maximum(d, 0)], -1)
    dist = np.where(inside, ctx.dist.ravel()[flat], np.nan)
    corridor = inside & (j >= 0) & (dist <= max_dist_m)
    jj = np.maximum(j, 0)

    hand = ctx.hand.ravel()[flat]
    river_km = ctx.km_path[jj]
    vx = c - ctx.prc[1][jj]
    vy = -(r - ctx.prc[0][jj])
    side = np.sign(ctx.dir_x[jj] * vy - ctx.dir_y[jj] * vx)                 # + = left bank (looking downstream)
    turn = ctx.turn[jj]
    ls = landslide_tree().query_ball_point(np.c_[x, y], LANDSLIDE_R_M, return_length=True).astype(float)
    cols = {"hand": hand, "river_km": river_km, "dist_channel_m": dist, "slope_deg": ctx.slope.ravel()[flat],
            "valley_width_m": ctx.valley_width[jj], "channel_slope": ctx.channel_slope[jj], "bend_curv": turn,
            "outside_bend": -side * turn, "log_acc": ctx.log_acc[jj], "ls_500m": ls, "kind": k}
    names = list(FEATURES_V1)
    if envelope is not None:
        cols["freeboard"] = hand - np.asarray(envelope.height(river_km), float)
        names = list(FEATURES_V2)
    X = np.column_stack([cols[n] for n in names]).astype(np.float64)
    corridor &= np.isfinite(X).all(axis=1)
    X[~corridor] = np.nan
    extra = {"river_km": np.where(j >= 0, river_km, np.nan), "dist_channel_m": dist, "inside_grid": inside,
             "drains_to_path": j >= 0}
    return X, names, corridor, extra


# ---------------- model artefacts ----------------

def load(version="v2", model_dir=MODEL_DIR):
    import joblib
    return joblib.load(os.path.join(model_dir, f"{version}.joblib"))


def predict(bundle, ctx, lonlat, kinds, envelope=None, max_dist_m=MAX_DIST_M):
    """P(affected) per point; NaN outside the corridor. `bundle` is what load() returns."""
    need_env = "freeboard" in bundle["features"]
    if need_env and envelope is None:
        raise ValueError(f"model {bundle['version']} needs a flood envelope (freeboard)")
    X, names, ok, _ = features(ctx, lonlat, kinds, envelope if need_env else None, max_dist_m)
    assert names == bundle["features"], (names, bundle["features"])
    p = np.full(len(X), np.nan)
    if ok.any():
        p[ok] = bundle["model"].predict_proba(X[ok])[:, 1]
    return p


_ctx_cache = {}


def context_for(T, path):
    key = (id(T), len(path), int(path[0]), int(path[-1]))
    if key not in _ctx_cache:
        _ctx_cache.clear()
        _ctx_cache[key] = PathContext(T, path)
    return _ctx_cache[key]


def predict_scenario(S, version="v2", bundle=None):
    """Read-only adapter for engine.scenario.Scenario (uses S.V.T, S.path, S.F, S.V.b_ll, S.V.bridge_meta).

    Returns {"version", "p_building": array aligned with S.V.b_ll (NaN outside corridor),
             "bridges": [{"id", "name", "lon", "lat", "p_destroyed"}], "runtime_s"}.
    """
    t0 = time.time()
    bundle = bundle or load(version)
    ctx = context_for(S.V.T, S.path)
    env = S.F if "freeboard" in bundle["features"] else None
    p_b = predict(bundle, ctx, S.V.b_ll, ["building"] * len(S.V.b_ll), env)
    bm = S.V.bridge_meta
    p_br = predict(bundle, ctx, [(b["lon"], b["lat"]) for b in bm], ["bridge"] * len(bm), env) if bm else []
    bridges = [{"id": b["id"], "name": b.get("name", ""), "lon": b["lon"], "lat": b["lat"],
                "p_destroyed": None if not np.isfinite(p) else round(float(p), 4)} for b, p in zip(bm, p_br)]
    return {"version": bundle["version"], "p_building": p_b, "bridges": bridges, "runtime_s": time.time() - t0}
