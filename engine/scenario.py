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
from engine.safety import time_to_safety, bridge_cells

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
    def __init__(self, V, replay, source_lonlat=None, extra_people=None):
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
        self.F = calibrate_from_replay(replay, self.km_of)
        self.t0 = hhmm_to_min(replay["burst_time"])
        kmz = np.nan_to_num(self.km)
        _, _, self.h_hi = self.F.height_band_at(kmz)
        self.flood = (drain >= 0) & (self.hand <= self.h_hi)
        safe = ~self.flood & ((drain < 0) | (self.hand > self.h_hi + SAFE_MARGIN_M))
        self.tts, self.walk_s = time_to_safety(T, safe, self.path, V.bridges)
        self.a_lo, self.a_mid, self.a_hi = self.F.arrival_band(kmz)
        self.runtime_s = time.time() - t_start
        self.extra_people = extra_people or {}

    def km_of(self, lon, lat):
        r, c = self.V.T.rc(*TF.transform(lon, lat)); return self.km[r, c]

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
            out.append({"name": name, "lon": float(V.p_ll[p, 0]), "lat": float(V.p_ll[p, 1]),
                        "buildings_at_risk": int(m.sum()), "people_at_risk": float(pop),
                        "people_without_time": float(pop_short),
                        "river_km": float(np.nanmedian(self.km.flat[V.b_flat[m]])),
                        "arrival_early": _clock(self.t0, float(np.min(arr_lo[m]))),
                        "arrival_minutes_after_burst": float(np.min(arr_lo[m])),
                        "walk_min_median": float(np.median(walk[m])), "walk_min_max": float(np.max(walk[m])),
                        "slack_min": s_min,
                        "status": "red" if s_min < 0 else ("amber" if s_min < AMBER_MIN else "green")})
        out.sort(key=lambda s: (s["arrival_minutes_after_burst"], -s["people_at_risk"]))
        for i, s in enumerate(out):
            s["alert_rank"] = i + 1
        return out

    def summary(self, warn_hhmm):
        S = self.settlements(warn_hhmm)
        return {"warning": warn_hhmm, "settlements_at_risk": len(S),
                "people_at_risk": sum(s["people_at_risk"] for s in S),
                "people_without_time": sum(s["people_without_time"] for s in S),
                "red": sum(s["status"] == "red" for s in S), "amber": sum(s["status"] == "amber" for s in S)}
