"""Prediction mode: for ANY flood trigger, predict what every point near the river suffers and, from wherever
you are at whatever time, the safest walking path to safe ground with its confidence.

Deterministic. All flood behaviour comes from real past floods (models/damage/flood_presets.json, built by
scripts/damage/build_presets.py); damage probabilities come from the damage model trained on real destruction
(engine/damage_model.py, models/damage/v2.joblib); walking uses the real DEM and OSM trails.

Rules (agreed with the team):
  * A point you pass BEFORE the flood reaches it costs nothing. A point you pass after the flood could be
    there carries its P(destroyed). Where you end up carries its P(destroyed) (you stay there).
  * A path is only as safe as its riskiest point: confidence = 1 - max(risk along the path, risk at the end).
    It is "safe" only if no point on it is unsafe (risk > UNSAFE_P); otherwise the unsafe points are listed.
  * The search picks the path with the highest confidence; among equally confident paths, the fastest.
  * Points outside the modelled impact zone (not draining to the flood river, or > 500 m from it: 99.6% of
    the Aug 26 destruction was inside) are reported as outside the impact zone.
Policy numbers (not data): UNSAFE_P, the risk ladder TAUS and the search radius are explicit below.
"""
import ctypes, json, os, subprocess, time
import numpy as np
from scipy import ndimage

from engine.terrain import Terrain
from engine.flood import FloodEnvelope
from engine import damage_model as dm

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = dm.REPO
DATA = os.path.join(REPO, "data") if os.path.isdir(os.path.join(REPO, "data", "proc")) else "/home/linux1/evac-ai/data"
UNSAFE_P = 0.10                     # a point whose risk exceeds this is marked unsafe (route shown as NOT safe)
TAUS = [0.01, 0.02, 0.03, 0.05, 0.07, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.70, 0.90]
SEARCH_RADIUS_M = 4000.0
CELL = 30.0
VALLEYS = {
    "budhi": {"proc": f"{DATA}/proc", "name": "Budhi Gandaki (Gorkha)", "default_preset": "oct11",
              "trails": ("overpass", f"{DATA}/raw/osm_budhi_highways.json"),
              "bridges": ("overpass", f"{DATA}/raw/osm_budhi_bridges.json")},
    "trishuli": {"proc": f"{DATA}/proc_trishuli", "name": "Bhotekoshi-Trishuli (Rasuwa/Nuwakot)", "default_preset": "aug26",
                 "trails": ("geojson", os.path.join(REPO, "data", "processed", "osm", "roads.geojson")),
                 "bridges": ("geojson", os.path.join(REPO, "data", "processed", "osm", "roads.geojson"))},
}

# ---------------- C search (compiled once on first use) ----------------
_lib = None


def _search_lib():
    global _lib
    if _lib is None:
        src = os.path.join(HERE, "escape_search.c")
        so = os.path.join(os.environ.get("EVAC_BUILD_DIR", os.path.expanduser("~/.cache/evac-ai")), "escape_search.so")
        os.makedirs(os.path.dirname(so), exist_ok=True)
        if not os.path.exists(so) or os.path.getmtime(so) < os.path.getmtime(src):
            subprocess.run(["cc", "-O2", "-shared", "-fPIC", "-o", so, src, "-lm"], check=True)
        lib = ctypes.CDLL(so)
        f, d, u8, i32 = ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_double), \
            ctypes.POINTER(ctypes.c_ubyte), ctypes.POINTER(ctypes.c_int)
        lib.escape_search.argtypes = [ctypes.c_int, ctypes.c_int, f, u8, u8, f, f, ctypes.c_int, ctypes.c_double,
                                      ctypes.c_double, ctypes.c_double, d, i32]
        lib.escape_search.restype = ctypes.c_int
        _lib = lib
    return _lib


def _ptr(a, ct):
    return a.ctypes.data_as(ctypes.POINTER(ct))


# ---------------- valleys (static, loaded once) ----------------

def _lines(kind, path, bridges_only):
    if kind == "overpass":
        out = []
        for e in json.load(open(path))["elements"]:
            g = e.get("geometry") or []
            if len(g) >= 2:
                out.append(([(p["lon"], p["lat"]) for p in g], e["id"], e.get("tags", {}).get("name", "")))
        return out
    out = []
    for f in json.load(open(path))["features"]:
        p, g = f["properties"], f["geometry"]
        if g["type"] != "LineString" or "highway" not in p:
            continue
        if bridges_only and p.get("bridge") in (None, "no"):
            continue
        out.append((g["coordinates"], f.get("id", ""), p.get("name", "")))
    return out


class Valley:
    def __init__(self, key):
        cfg = VALLEYS[key]
        self.key, self.name, self.cfg = key, cfg["name"], cfg
        self.T = Terrain(cfg["proc"])
        epsg = self.T.crs.to_epsg()
        self.tf = dm.Transformer.from_crs(4326, epsg, always_xy=True)
        self.inv = dm.Transformer.from_crs(epsg, 4326, always_xy=True)
        self.dem32 = self.T.dem.astype(np.float32)
        self.dem32[~np.isfinite(self.dem32) | (self.dem32 < -100)] = np.nan
        self.trail = self._rasterize(_lines(*cfg["trails"], bridges_only=False))
        b = _lines(*cfg["bridges"], bridges_only=True)
        x0, y0, x1, y1 = self._bbox_lonlat()
        self.bridges = [(ll, i, n) for ll, i, n in b if any(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for p in ll)]

    def _bbox_lonlat(self):
        nr, nc = self.T.shape
        pts = [self.inv.transform(*self.T.xy(r, c)) for r, c in ((0, 0), (0, nc - 1), (nr - 1, 0), (nr - 1, nc - 1))]
        return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)

    def cells_of_lines(self, lines, step_m=10.0):
        out = []
        for ll in lines:
            ll = np.asarray(ll, float)
            x, y = self.tf.transform(ll[:, 0], ll[:, 1])
            for j in range(len(x) - 1):
                n = max(int(np.hypot(x[j + 1] - x[j], y[j + 1] - y[j]) / step_m), 1)
                t = np.linspace(0, 1, n + 1)
                c, r = ~self.T.transform * (x[j] + t * (x[j + 1] - x[j]), y[j] + t * (y[j + 1] - y[j]))
                r, c = np.floor(r).astype(int), np.floor(c).astype(int)
                ok = (r >= 0) & (r < self.T.shape[0]) & (c >= 0) & (c < self.T.shape[1])
                out.append(r[ok] * self.T.shape[1] + c[ok])
        return np.unique(np.concatenate(out)) if out else np.array([], np.int64)

    def _rasterize(self, lines):
        m = np.zeros(self.T.shape, np.uint8)
        m.flat[self.cells_of_lines([l for l, _, _ in lines])] = 1
        return m


_valleys, _presets, _bundle = {}, None, None


def valley(key):
    if key not in _valleys:
        _valleys[key] = Valley(key)
    return _valleys[key]


def presets():
    global _presets
    if _presets is None:
        _presets = json.load(open(os.path.join(dm.MODEL_DIR, "flood_presets.json")))["presets"]
    return _presets


def envelope(preset_key):
    p = presets()[preset_key]
    # decay_km huge: hold the last observed height constant downstream (no invented decay rate)
    return FloodEnvelope([tuple(a) for a in p["arrival_knots"]], [tuple(h) for h in p["height_knots"]],
                         decay_km=1e12, floor_m=0.0)


def model():
    global _bundle
    if _bundle is None:
        _bundle = dm.load("v2")
    return _bundle


# ---------------- one flood scenario ----------------

class FloodScenario:
    """Impact of one flood (trigger point + real-flood preset) on every cell near the river."""

    def __init__(self, valley_key, trigger_lonlat=None, preset_key=None):
        t0 = time.time()
        V = self.V = valley(valley_key)
        T = V.T
        self.preset_key = preset_key or V.cfg["default_preset"]
        self.preset = presets()[self.preset_key]
        if trigger_lonlat is None:
            rep = json.load(open(os.path.join(REPO, "replay", f"{V.cfg['default_preset']}.json")))
            trigger_lonlat = (rep["source"]["lon"], rep["source"]["lat"])
        self.trigger = tuple(trigger_lonlat)
        r, c = T.rc(*V.tf.transform(*self.trigger))
        if not (0 <= r < T.shape[0] and 0 <= c < T.shape[1]):
            raise ValueError("trigger is outside this valley's terrain")
        r, c = T.snap_to_channel(r, c, radius=15)
        self.path = T.downstream_path(r, c)
        if len(self.path) < 10:
            raise ValueError("trigger does not lie on a river channel (path too short)")
        self.ctx = ctx = dm.context_for(T, self.path)
        self.F = envelope(self.preset_key)
        nr, nc = T.shape
        corridor = (ctx.drain >= 0) & (ctx.dist <= dm.MAX_DIST_M)
        idx = np.flatnonzero(corridor)
        rr, cc = np.unravel_index(idx, T.shape)
        x, y = T.transform * (cc + 0.5, rr + 0.5)
        lon, lat = V.inv.transform(x, y)
        p = dm.predict(model(), ctx, np.c_[lon, lat], ["building"] * len(idx), self.F)
        self.p = np.full(T.shape, np.nan, np.float32)
        self.p.flat[idx] = p
        km = np.where(ctx.drain >= 0, ctx.km_path[ctx.pos[np.maximum(ctx.drain, 0)]], np.nan)
        self.km = km
        self.A = np.where(ctx.drain >= 0, self.F.arrival(np.nan_to_num(km)), np.inf).astype(np.float32)

        # flood river strip is a barrier except where a bridge crosses (same rule as engine/safety.py)
        ch = np.zeros(T.shape, bool); ch.flat[self.path] = True
        barrier = ndimage.binary_dilation(ch, iterations=1)
        self.bridge_info = []
        bcells = np.zeros(T.shape, bool)
        # only bridges with a cell within the corridor matter; work in a small window around each one
        near = []
        for ll, bid, name in V.bridges:
            cells = V.cells_of_lines([ll])
            if len(cells) and (ctx.dist.ravel()[cells] <= dm.MAX_DIST_M).any():
                near.append((ll, bid, name, cells))
        if near:
            xing = dm.crossing_points(ctx, [n[0] for n in near])
            pb = dm.predict(model(), ctx, xing, ["bridge"] * len(xing), self.F)
            for (ll, bid, name, cells), (blon, blat), pbi in zip(near, xing, pb):
                br, bc = np.unravel_index(cells, T.shape)
                r0, r1 = max(br.min() - 2, 0), min(br.max() + 3, nr)
                c0, c1 = max(bc.min() - 2, 0), min(bc.max() + 3, nc)
                m = np.zeros((r1 - r0, c1 - c0), bool); m[br - r0, bc - c0] = True
                m = ndimage.binary_dilation(m, iterations=1)
                open_ = m & barrier[r0:r1, c0:c1]
                crosses = bool(open_.any())
                bx, by = V.tf.transform(blon, blat)
                br_r, br_c, ok = ctx.cells([bx], [by])
                a_b = float(self.A[br_r[0], br_c[0]]) if ok[0] else float("inf")
                if crosses:
                    # crossing the flood river on this bridge: its risk/arrival are the bridge's own
                    self.p[r0:r1, c0:c1][open_] = np.float32(pbi if np.isfinite(pbi) else 0.0)
                    self.A[r0:r1, c0:c1][open_] = np.float32(a_b)
                    bcells[r0:r1, c0:c1] |= open_
                self.bridge_info.append({"id": bid, "name": name, "lon": float(blon), "lat": float(blat),
                                         "crosses_flood_river": crosses,
                                         "p_destroyed": None if not np.isfinite(pbi) else round(float(pbi), 3),
                                         "flood_arrival_min": None if not np.isfinite(a_b) else round(a_b, 1)})
        self.blocked = (barrier & ~bcells).astype(np.uint8)
        self.blocked[~np.isfinite(V.dem32)] = 1
        self.p_search = np.nan_to_num(self.p, nan=0.0).astype(np.float32)      # outside corridor: not at risk
        self.runtime_s = time.time() - t0

    # ---- one query: where am I, what time is it ----
    def escape(self, lon, lat, minutes_after_start):
        t_start = time.time()
        V, T = self.V, self.V.T
        x, y = V.tf.transform(lon, lat)
        r, c = T.rc(x, y)
        if not (0 <= r < T.shape[0] and 0 <= c < T.shape[1]):
            return {"status": "outside_terrain", "message": "This point is outside the terrain of this valley."}
        t0 = float(minutes_after_start)
        here = self._point(r, c, t0)
        base = {"you": here, "minutes_after_start": t0, "flood": self.describe(short=True)}
        if here["p_destroyed"] is None:
            return {**base, "status": "outside_impact_zone", "safe": True, "confidence": None,
                    "message": "You are outside the predicted impact zone of this flood: no need to move."}
        if here["p_destroyed"] <= UNSAFE_P:
            return {**base, "status": "safe_here", "safe": True, "confidence": round(1 - here["p_destroyed"], 3),
                    "message": f"Safe here: {100 * (1 - here['p_destroyed']):.0f}% confidence this spot is not hit."}
        if self.blocked[r, c]:                                    # standing in the river strip: step out first
            d, (ri, ci) = ndimage.distance_transform_edt(self.blocked.astype(bool), return_indices=True)
            r, c = int(ri[r, c]), int(ci[r, c])
        main = self._best(r, c, t0, exclude=None)
        out = {**base, "status": "route" if main else "no_route", "runtime_s": None}
        if main:
            out.update(main)
            gr, gc = main["_goal_rc"]
            backup = self._best(r, c, t0, exclude=(gr, gc, 300.0))
            out["backup"] = {k: v for k, v in backup.items() if not k.startswith("_")} if backup else None
            out.pop("_goal_rc", None)
        else:
            out["safe"] = False
            out["message"] = (f"No escape found within {SEARCH_RADIUS_M / 1000:.0f} km that reaches ground with at least "
                              f"{100 * (1 - TAUS[-1]):.0f}% confidence before the flood. Go as high as you can, now.")
        out["runtime_s"] = round(time.time() - t_start, 2)
        return out

    def _point(self, r, c, t):
        p = self.p[r, c]
        a = self.A[r, c]
        return {"lon": round(float(V_inv(self, r, c)[0]), 6), "lat": round(float(V_inv(self, r, c)[1]), 6),
                "p_destroyed": None if not np.isfinite(p) else round(float(p), 3),
                "flood_arrival_min": None if not np.isfinite(a) else round(float(a), 1),
                "flood_already_here": bool(np.isfinite(p) and np.isfinite(a) and t >= a)}

    def _window(self, r, c, exclude):
        R = int(SEARCH_RADIUS_M / CELL)
        r0, r1 = max(r - R, 0), min(r + R + 1, self.V.T.shape[0])
        c0, c1 = max(c - R, 0), min(c + R + 1, self.V.T.shape[1])
        sl = (slice(r0, r1), slice(c0, c1))
        blocked = self.blocked[sl].copy()
        if exclude is not None:                                   # backup: avoid the main destination area
            gr, gc, rad = exclude
            yy, xx = np.ogrid[r0:r1, c0:c1]
            blocked[(yy - gr) ** 2 + (xx - gc) ** 2 <= (rad / CELL) ** 2] = 1
        arrs = [np.ascontiguousarray(a) for a in (self.V.dem32[sl], self.V.trail[sl], blocked,
                                                  self.p_search[sl], self.A[sl])]
        return (r0, c0, r1 - r0, c1 - c0), arrs

    def _best(self, r, c, t0, exclude):
        (r0, c0, nr, nc), (dem, trail, blocked, p, A) = self._window(r, c, exclude)
        lib = _search_lib()
        Tm = np.empty(nr * nc, np.float64); prev = np.empty(nr * nc, np.int32)
        start = (r - r0) * nc + (c - c0)
        blocked.flat[start] = 0
        for tau in TAUS:
            g = lib.escape_search(nr, nc, _ptr(dem, ctypes.c_float), _ptr(trail, ctypes.c_ubyte),
                                  _ptr(blocked, ctypes.c_ubyte), _ptr(p, ctypes.c_float), _ptr(A, ctypes.c_float),
                                  start, t0, tau, CELL, _ptr(Tm, ctypes.c_double), _ptr(prev, ctypes.c_int))
            if g == -2:
                raise MemoryError("escape_search allocation failed")
            if g >= 0:
                return self._route(g, start, Tm, prev, (r0, c0, nr, nc), t0, tau)
        return None

    def _route(self, g, start, Tm, prev, win, t0, tau):
        r0, c0, nr, nc = win
        seq = [g]
        while seq[-1] != start:
            seq.append(int(prev[seq[-1]]))
            if seq[-1] < 0:
                raise RuntimeError("broken predecessor chain")
        seq.reverse()
        pts, risks, margins, unsafe = [], [], [], []
        for k, i in enumerate(seq):
            rr, cc = r0 + i // nc, c0 + i % nc
            p, a, t = self.p[rr, cc], float(self.A[rr, cc]), float(Tm[i])
            pv = float(p) if np.isfinite(p) else 0.0
            last = k == len(seq) - 1
            after = np.isfinite(a) and t >= a
            risk = pv if (after or last) else 0.0
            if np.isfinite(a) and pv > UNSAFE_P:
                margins.append(a - t)
            lo, la = V_inv(self, rr, cc)
            pt = {"lon": round(float(lo), 6), "lat": round(float(la), 6), "t_min": round(t, 2),
                  "flood_arrival_min": None if not np.isfinite(a) else round(a, 1), "p_destroyed": round(pv, 3),
                  "risk": round(risk, 3), "unsafe": bool(risk > UNSAFE_P)}
            pts.append(pt); risks.append(risk)
            if pt["unsafe"]:
                unsafe.append(k)
        conf = 1.0 - max(risks)
        gr, gc = r0 + g // nc, c0 + g % nc
        seg = np.array([[r0 + i // nc, c0 + i % nc] for i in seq])
        dist = float(np.hypot(*np.diff(seg, axis=0).T).sum() * CELL) if len(seg) > 1 else 0.0
        climb = float(self.V.dem32[gr, gc] - self.V.dem32[seg[0][0], seg[0][1]])
        safe = len(unsafe) == 0
        walk = pts[-1]["t_min"] - t0
        msg = (f"{'SAFE' if safe else 'NOT SAFE everywhere'}: walk {walk:.0f} min, {dist:.0f} m, "
               f"{'+' if climb >= 0 else ''}{climb:.0f} m to ground with {100 * (1 - pts[-1]['risk']):.0f}% confidence; "
               f"path confidence {100 * conf:.0f}%"
               + ("" if safe else f"; {len(unsafe)} point(s) on the path are unsafe (shown in red)"))
        return {"safe": safe, "confidence": round(conf, 3), "risk_ladder_tau": tau, "walk_min": round(walk, 1),
                "distance_m": round(dist), "climb_m": round(climb), "destination": pts[-1],
                "min_margin_before_flood_min": None if not margins else round(min(margins), 1),
                "unsafe_points": [pts[k] for k in unsafe], "path": pts, "message": msg, "_goal_rc": (gr, gc)}

    def describe(self, short=False):
        d = {"valley": self.V.key, "valley_name": self.V.name, "preset": self.preset_key,
             "preset_label": self.preset["label"], "trigger": {"lon": self.trigger[0], "lat": self.trigger[1]},
             "path_km": round(float(self.ctx.km_path[-1]), 1)}
        if short:
            return d
        km = self.ctx.km_path
        st = [{"km": round(float(km[i]), 1), "lon": round(float(V_inv(self, *np.unravel_index(self.path[i], self.V.T.shape))[0]), 5),
               "lat": round(float(V_inv(self, *np.unravel_index(self.path[i], self.V.T.shape))[1]), 5),
               "arrival_min": round(float(self.F.arrival(km[i])), 1), "height_m": round(float(self.F.height(km[i])), 1)}
              for i in list(range(0, len(self.path), 15)) + [len(self.path) - 1]]
        corr = np.isfinite(self.p)
        return {**d, "stations": st, "bridges": self.bridge_info, "runtime_s": round(self.runtime_s, 2),
                "cells_scored": int(corr.sum()), "cells_p_gt_unsafe": int((self.p[corr] > UNSAFE_P).sum()),
                "rules": {"unsafe_p": UNSAFE_P, "search_radius_m": SEARCH_RADIUS_M,
                          "impact_zone": f"cells draining to the flood river within {dm.MAX_DIST_M:.0f} m",
                          "path_confidence": "1 - max(risk); risk = P(destroyed) where reached after the flood, and at the end"},
                "preset_sources": self.preset.get("sources", []), "height_notes": self.preset.get("height_notes", []),
                "arrival_observations": self.preset.get("arrival_observations", [])}

    def p_png(self):
        """P(destroyed) as an RGBA PNG warped to Web Mercator + its lon/lat bounds (Leaflet imageOverlay)."""
        import io
        from PIL import Image
        from rasterio.warp import reproject, Resampling, calculate_default_transform, transform_bounds
        T = self.V.T
        rows, cols = np.where(np.isfinite(self.p))
        r0, r1, c0, c1 = rows.min(), rows.max() + 1, cols.min(), cols.max() + 1
        src = self.p[r0:r1, c0:c1].astype(np.float32)
        src_tf = T.transform * T.transform.translation(c0, r0)
        crs = T.crs
        h, w = src.shape
        left, top = src_tf * (0, 0); right, bottom = src_tf * (w, h)
        dst_tf, dw, dh = calculate_default_transform(crs, "EPSG:3857", w, h, left, bottom, right, top)
        dst = np.full((dh, dw), np.nan, np.float32)
        reproject(src, dst, src_transform=src_tf, src_crs=crs, dst_transform=dst_tf, dst_crs="EPSG:3857",
                  resampling=Resampling.nearest, src_nodata=np.nan, dst_nodata=np.nan)
        rgba = np.zeros((dh, dw, 4), np.uint8)
        ok = np.isfinite(dst)
        v = np.clip(np.nan_to_num(dst), 0, 1)
        # yellow (low) -> red (high); transparent below 2%
        rgba[..., 0] = 255
        rgba[..., 1] = (220 * (1 - v)).astype(np.uint8)
        rgba[..., 2] = 40
        rgba[..., 3] = np.where(ok & (v >= 0.02), (60 + 170 * v).astype(np.uint8), 0)
        buf = io.BytesIO(); Image.fromarray(rgba, "RGBA").save(buf, "PNG")
        x0, y1 = dst_tf * (0, 0); x1, y0 = dst_tf * (dw, dh)
        w_, s_, e_, n_ = transform_bounds("EPSG:3857", "EPSG:4326", x0, y0, x1, y1)
        return buf.getvalue(), [[s_, w_], [n_, e_]]


def V_inv(S, r, c):
    x, y = S.V.T.xy(int(r), int(c))
    return S.V.inv.transform(x, y)
