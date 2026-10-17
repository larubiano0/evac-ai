"""Scenario runner: trigger -> footprint -> time to safety -> per-building / per-settlement slack.

slack = (first-wave arrival, early band) - (warning time + dissemination delay + walking time to safety)
Buildings outside the conservative footprint are not at risk. Population per building is an
ASSUMPTION (PERSONS_PER_BUILDING); trekker counts from replay files are added to named places.
"""
import json, time
import numpy as np
from scipy.spatial import cKDTree
from pyproj import Transformer
from engine.terrain import Terrain
from engine.flood import calibrate_from_replay, hhmm_to_min
from engine.safety import time_to_safety, bridge_cells, trace_route

PERSONS_PER_BUILDING = 4.0      # assumption: Nepal census 2021 avg household 4.37; some OSM buildings are sheds
DISSEMINATION_MIN = 5.0         # assumption: minutes from warning issued to people starting to move
SAFE_MARGIN_M = 5.0             # metres above the conservative flood height counted as safe
AMBER_MIN = 15.0                # slack below this (but >= 0) is amber
TF = Transformer.from_crs(4326, 32645, always_xy=True)
INV = Transformer.from_crs(32645, 4326, always_xy=True)


class Valley:
    """Static data for one valley, loaded once (kept in memory by the API)."""
    def __init__(self, area="budhi", proc="data/proc", raw="data/raw"):
        self.T = Terrain(proc)
        self.bridges = bridge_cells(self.T, f"{raw}/osm_{area}_bridges.json")
        self.bridge_meta = self._bridges(f"{raw}/osm_{area}_bridges.json")
        b = json.load(open(f"{raw}/osm_{area}_buildings.json"))["elements"]
        ll = np.array([(e["center"]["lon"], e["center"]["lat"]) for e in b if "center" in e])
        x, y = TF.transform(ll[:, 0], ll[:, 1])
        rc = np.array([self.T.rc(xi, yi) for xi, yi in zip(x, y)])
        ok = (rc[:, 0] >= 0) & (rc[:, 0] < self.T.shape[0]) & (rc[:, 1] >= 0) & (rc[:, 1] < self.T.shape[1])
        self.b_ll, self.b_rc = ll[ok], rc[ok]
        self.b_flat = self.b_rc[:, 0] * self.T.shape[1] + self.b_rc[:, 1]
        pl = [e for e in json.load(open(f"{raw}/osm_{area}_places.json"))["elements"]
              if e["tags"].get("place") in ("town", "village", "hamlet") and "name" in e["tags"]]
        self.p_name = [e["tags"].get("name:en") or e["tags"]["name"] for e in pl]
        dev = lambda t: t if any("\u0900" <= ch <= "\u097f" for ch in t) else None
        self.p_name_ne = [e["tags"].get("name:ne") or dev(e["tags"]["name"]) for e in pl]
        self.p_ll = np.array([(e["lon"], e["lat"]) for e in pl])
        px, py = TF.transform(self.p_ll[:, 0], self.p_ll[:, 1])
        d, self.b_place = cKDTree(np.c_[px, py]).query(np.c_[x[ok], y[ok]])
        self.b_place[d > 3000] = -1                   # buildings > 3 km from any named place: unassigned

    def _bridges(self, path):
        out = []
        for e in json.load(open(path))["elements"]:
            g = e.get("geometry") or []
            if g:
                m = g[len(g) // 2]
                out.append({"id": e["id"], "name": e["tags"].get("name", ""), "lon": m["lon"], "lat": m["lat"],
                            "kind": e["tags"].get("highway", e["tags"].get("man_made", "")),
                            "geometry": [[p["lon"], p["lat"]] for p in g]})
        return out


def _clock(t0_min, minutes):
    m = (t0_min + minutes) % (24 * 60); return f"{int(m // 60):02d}:{int(m % 60):02d}"


class Scenario:
    def __init__(self, V, replay, source_lonlat=None, extra_people=None, envelope=None, burst_hhmm=None):
        self.V, self.rep, T = V, replay, V.T
        t_start = time.time()
        lon, lat = source_lonlat or (replay["source"]["lon"], replay["source"]["lat"])
        r, c = T.snap_to_channel(*T.rc(*TF.transform(lon, lat)))
        self.path = T.downstream_path(r, c)
        prc = np.array(np.unravel_index(self.path, T.shape))
        self.km_path = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(prc, axis=1)) * 30.0)]) / 1000
        self.hand, drain = T.hand_to(self.path)
        pos = np.full(T.nxt.size, -1); pos[self.path] = np.arange(len(self.path))
        self.km = np.where(drain >= 0, self.km_path[pos[np.maximum(drain, 0)]], np.nan)
        # A new trigger location reuses an envelope calibrated on a replay (curves are in km from source).
        self.F = envelope or calibrate_from_replay(replay, self.km_of)
        self.t0 = hhmm_to_min(burst_hhmm or replay["burst_time"])
        kmz = np.nan_to_num(self.km)
        _, _, self.h_hi = self.F.height_band_at(kmz)
        self.flood = (drain >= 0) & (self.hand <= self.h_hi)
        safe = ~self.flood & ((drain < 0) | (self.hand > self.h_hi + SAFE_MARGIN_M))
        self.tts, self.walk_s = time_to_safety(T, safe, self.path, V.bridges)
        self.tdir = time_to_safety.tdir                       # keep per scenario (several are cached)
        self.near = getattr(time_to_safety, "nearest", None)
        self.a_lo, self.a_mid, self.a_hi = self.F.arrival_band(kmz)
        self.runtime_s = time.time() - t_start
        self.extra_people = extra_people or {}

    def bridges_at_risk(self):
        """OSM bridges whose midpoint cell is in the conservative footprint (or on the flood channel)."""
        out = []
        on_path = set(self.path.tolist())
        for b in self.V.bridge_meta:
            r, c = self.V.T.rc(*TF.transform(b["lon"], b["lat"]))
            if not (0 <= r < self.V.T.shape[0] and 0 <= c < self.V.T.shape[1]):
                continue
            i = r * self.V.T.shape[1] + c
            if self.flood[r, c] or i in on_path:
                km = self.km[r, c]
                out.append({**b, "river_km": float(km), "arrival_early": _clock(self.t0, float(self.a_lo[r, c])),
                            "arrival_minutes_after_burst": float(self.a_lo[r, c])})
        px, py = TF.transform(self.V.p_ll[:, 0], self.V.p_ll[:, 1]); tree = cKDTree(np.c_[px, py])
        for b in out:
            _, k = tree.query(TF.transform(b["lon"], b["lat"]))
            trail = b["name"] in ("", "Manaslu Circuit", "Tsum Valley Path") or b["name"].lower().endswith("path")
            b["label"] = f"bridge near {self.V.p_name[k]}" if trail else b["name"]
            b["label_ne"] = f"{self.V.p_name_ne[k] or self.V.p_name[k]} नजिकको पुल" if trail else b["name"]
        out.sort(key=lambda b: b["river_km"])
        return out

    def path_geojson(self, every=10):
        idx = self.path[::every].tolist() + [int(self.path[-1])]
        kms = self.km_path[::every].tolist() + [float(self.km_path[-1])]
        coords, props = [], []
        for i, k in zip(idx, kms):
            x, y = self.V.T.xy(*np.unravel_index(i, self.V.T.shape)); lo, la = INV.transform(x, y)
            coords.append([round(lo, 5), round(la, 5)])
            props.append({"km": round(k, 2), "arrival": _clock(self.t0, float(self.F.arrival(k) * (1 - self.F.time_band))),
                          "arrival_min": round(float(self.F.arrival(k) * (1 - self.F.time_band)), 1),
                          "height_m": round(float(self.F.height_band_at(k)[2]), 1)})
        return {"type": "Feature", "geometry": {"type": "LineString", "coordinates": coords}, "properties": {"stations": props}}

    def footprint_geojson(self, simplify_m=20):
        """Conservative footprint as lon/lat polygons (rasterio.features + shapely simplify)."""
        from rasterio import features
        from shapely.geometry import shape, mapping
        from shapely.ops import transform as stransform
        geoms = []
        for g, v in features.shapes(self.flood.astype(np.uint8), mask=self.flood, transform=self.V.T.transform):
            poly = shape(g).simplify(simplify_m)
            poly = stransform(lambda x, y, z=None: INV.transform(x, y), poly)
            geoms.append({"type": "Feature", "geometry": mapping(poly), "properties": {}})
        return {"type": "FeatureCollection", "features": geoms}

    def km_of(self, lon, lat):
        """River km of the channel cell that (lon, lat) drains into; NaN outside the grid or off the path.
        Terrain.rc has no bounds check, and numpy wraps negative indices silently (Aug 26 Kali Khola gave 66 km)."""
        r, c = self.V.T.rc(*TF.transform(lon, lat))
        if not (0 <= r < self.V.T.shape[0] and 0 <= c < self.V.T.shape[1]):
            return np.nan
        return self.km[r, c]

    def buildings(self, warn_hhmm):
        """Per-building arrays for a given warning time."""
        V = self.V; f = V.b_flat
        at_risk = self.flood.flat[f]
        arr_lo = self.a_lo.flat[f]; walk = np.nan_to_num(self.tts.flat[f] / 60.0, nan=999.0)
        warn = hhmm_to_min(warn_hhmm) - self.t0
        slack = arr_lo - (warn + DISSEMINATION_MIN + walk)
        return at_risk, arr_lo, walk, slack

    def settlements(self, warn_hhmm):
        at_risk, arr_lo, walk, slack = self.buildings(warn_hhmm)
        V = self.V; out = []
        for p in np.unique(V.b_place[at_risk & (V.b_place >= 0)]):
            m = at_risk & (V.b_place == p)
            name = V.p_name[p]; pop = m.sum() * PERSONS_PER_BUILDING + self.extra_people.get(name, 0)
            s_min = float(np.min(slack[m]))
            short = m & (slack < 0)
            pop_short = short.sum() * PERSONS_PER_BUILDING + (self.extra_people.get(name, 0) if s_min < 0 else 0)
            out.append({"name": name, "name_ne": V.p_name_ne[p] or name, "lon": float(V.p_ll[p, 0]), "lat": float(V.p_ll[p, 1]),
                        "buildings_at_risk": int(m.sum()), "people_at_risk": float(pop),
                        "people_without_time": float(pop_short),
                        "river_km": float(np.nanmedian(self.km.flat[V.b_flat[m]])),
                        "arrival_early": _clock(self.t0, float(np.min(arr_lo[m]))),
                        "arrival_minutes_after_burst": float(np.min(arr_lo[m])),
                        "walk_min_median": float(np.median(walk[m])), "walk_min_max": float(np.max(walk[m])),
                        "slack_min": s_min,
                        "status": "red" if s_min < 0 else ("amber" if s_min < AMBER_MIN else "green"),
                        **self._route(np.flatnonzero(m)[np.argmax(walk[m])])})
        out.sort(key=lambda s: (s["arrival_minutes_after_burst"], -s["people_at_risk"]))
        for i, s in enumerate(out):
            s["alert_rank"] = i + 1
        return out

    def _route(self, b):
        """Escape route from building b (the settlement's longest walk) to safe ground."""
        r, c = self.V.b_rc[b]
        rt = trace_route(self.tdir, self.tts, int(r), int(c), self.near)
        coords = []
        for rr, cc in rt:
            lo, la = INV.transform(*self.V.T.xy(rr, cc)); coords.append([round(lo, 5), round(la, 5)])
        seg = np.hypot(*np.diff(np.array(rt).T, axis=1)) * 30.0 if len(rt) > 1 else np.array([0.0])
        return {"route": coords, "route_len_m": float(seg.sum()),
                "route_climb_m": float(self.V.T.dem[rt[-1]] - self.V.T.dem[rt[0]]),
                "route_from": [float(self.V.b_ll[b, 0]), float(self.V.b_ll[b, 1])]}

    def summary(self, warn_hhmm):
        S = self.settlements(warn_hhmm)
        return {"warning": warn_hhmm, "settlements_at_risk": len(S),
                "people_at_risk": sum(s["people_at_risk"] for s in S),
                "people_without_time": sum(s["people_without_time"] for s in S),
                "red": sum(s["status"] == "red" for s in S), "amber": sum(s["status"] == "amber" for s in S)}
