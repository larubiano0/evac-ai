"""Out-of-event check: apply the Aug-trained damage model to the Oct 11 Budhi Gandaki flood.

Builds the engine's Valley (read-only) and repeats Scenario's flood geometry exactly (snap -> D8 path ->
river km -> calibrate_from_replay). It does NOT construct engine.scenario.Scenario, because that runs GRASS
r.walk and writes into the GRASS database (owned by claude-luis); the model does not need walking times.
predict_scenario() gets a stand-in exposing the same attributes it reads (V, path, F).

Reports, for v1 and v2 and the engine's footprint rule (HAND <= high-band height):
  - the reported-lost bridges (replay/oct11.json damage_reported.bridges_lost): best OSM candidates near each
    named place, with p and rank among all corridor bridges
  - expected number of affected buildings (sum of p) vs. reports (35-45 destroyed + 27 partly damaged)
Writes models/damage/oct11_check.json.
"""
import json, os, platform, sys, time
import numpy as np

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, REPO)
from engine import damage_model as dm
from engine.scenario import Valley, TF
from engine.flood import calibrate_from_replay

EVAC = "/home/linux1/evac-ai"
# Reported-lost bridges (replay/oct11.json) -> OSM place names (or lon/lat) to search near, and a road-type hint.
LOST = [
    ("Nyakchet-Sirdibas suspension", ["Sirdibas", "Nyak"], "path"),
    ("Machhakhola-Kerauja suspension", ["Machha Khola", "Machhakhola", "Kerauja"], "path"),
    ("Dobhan Bailey", ["Dobhan"], "road"),
    ("Soti iron motorable", (84.8547, 28.1353), "road"),              # no OSM place node: replay coordinates
    ("Arughat concrete (1 of 3 spans)", (84.8089, 28.0416), "road"),
    ("Nyakchet-Philim Bazar", ["Philim", "Nyak"], "path"),
]
ROAD_KINDS = {"primary", "secondary", "tertiary", "trunk", "unclassified", "track", "residential", "service"}


class FloodView:
    """The attributes of engine.scenario.Scenario that damage_model.predict_scenario reads."""
    def __init__(self, V, replay):
        T = V.T
        lon, lat = replay["source"]["lon"], replay["source"]["lat"]
        r, c = T.snap_to_channel(*T.rc(*TF.transform(lon, lat)))          # same call as Scenario.__init__
        self.V, self.path = V, T.downstream_path(r, c)
        prc = np.array(np.unravel_index(self.path, T.shape))
        self.km_path = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(prc, axis=1)) * 30.0)]) / 1000
        self.hand, drain = T.hand_to(self.path)
        pos = np.full(T.nxt.size, -1); pos[self.path] = np.arange(len(self.path))
        self.km = np.where(drain >= 0, self.km_path[pos[np.maximum(drain, 0)]], np.nan)
        self.drain = drain

        def km_of(lo, la):
            rr, cc = T.rc(*TF.transform(lo, la))
            if not (0 <= rr < T.shape[0] and 0 <= cc < T.shape[1]):
                return np.nan
            return self.km[rr, cc]
        self.F = calibrate_from_replay(replay, km_of)
        _, _, self.h_hi = self.F.height_band_at(np.nan_to_num(self.km))
        self.flood = (drain >= 0) & (self.hand <= self.h_hi)                 # engine's footprint rule


def main():
    t0 = time.time()
    replay = json.load(open(os.path.join(REPO, "replay", "oct11.json")))
    V = Valley("budhi", proc=f"{EVAC}/data/proc", raw=f"{EVAC}/data/raw")
    t_valley = time.time() - t0
    S = FloodView(V, replay)
    T = V.T
    names = np.array(V.p_name)
    out = {"event": replay["event"], "arch": platform.machine(), "path_km": float(S.km_path[-1]),
           "envelope_height_knots": S.F.hk.tolist(), "versions": {}}
    br_ll = np.array([(b["lon"], b["lat"]) for b in V.bridge_meta])
    bx, by = TF.transform(br_ll[:, 0], br_ll[:, 1])
    br_rc = [T.rc(x, y) for x, y in zip(bx, by)]                       # midpoint cell, as the engine uses
    ctx = dm.context_for(T, S.path)
    xing = dm.crossing_points(ctx, [b.get("geometry") or [(b["lon"], b["lat"])] for b in V.bridge_meta])
    Xb, nb, okb, exb = dm.features(ctx, xing, ["bridge"] * len(xing), S.F, max_dist_m=1e9, names=dm.FEATURES_V2)
    on_path = set(S.path.tolist())
    br_engine = np.array([0 <= r < T.shape[0] and 0 <= c < T.shape[1] and
                          (S.flood[r, c] or (r * T.shape[1] + c) in on_path) for r, c in br_rc])
    b_rc = V.b_rc
    b_engine = S.flood[b_rc[:, 0], b_rc[:, 1]]

    for ver in ("v1", "v2"):
        bundle = dm.load(ver)
        t1 = time.time()
        res = dm.predict_scenario(S, ver, bundle=bundle)
        t_pred = time.time() - t1
        pb = res["p_building"]; pbr = np.array([np.nan if b["p_destroyed"] is None else b["p_destroyed"]
                                                for b in res["bridges"]])
        corr = np.isfinite(pbr)
        order = np.argsort(-np.where(corr, pbr, -1))
        rank = np.empty(len(pbr), int); rank[order] = np.arange(1, len(pbr) + 1)
        lost = []
        for label, places, hint in LOST:
            if isinstance(places, tuple):
                px, py = TF.transform([places[0]], [places[1]]); px, py = np.array(px), np.array(py)
                matched = [f"lon/lat {places}"]
            else:
                idx = [i for i, n in enumerate(names) if any(p.lower() in n.lower() for p in places)]
                if not idx:
                    lost.append({"reported": label, "found_place": None, "candidates": []}); continue
                px, py = TF.transform(V.p_ll[idx, 0], V.p_ll[idx, 1])
                matched = sorted(set(names[idx].tolist()))
            d = np.min(np.hypot(bx[:, None] - px[None, :], by[:, None] - py[None, :]), axis=1)
            cand = [i for i in np.argsort(d) if d[i] <= 2000 and corr[i]]
            typed = [i for i in cand if (V.bridge_meta[i]["kind"] in ROAD_KINDS) == (hint == "road")] or cand
            top = typed[:3]
            lost.append({"reported": label, "places_matched": matched,
                         "candidates": [{"osm_id": V.bridge_meta[i]["id"], "name": V.bridge_meta[i]["name"],
                                         "kind": V.bridge_meta[i]["kind"], "dist_to_place_m": round(float(d[i])),
                                         "river_km": round(float(exb["river_km"][i]), 1),
                                         "crossing_hand_m": round(float(Xb[i, nb.index("hand")]), 1),
                                         "crossing_dist_channel_m": round(float(Xb[i, nb.index("dist_channel_m")]), 0),
                                         "crossing_freeboard_m": round(float(Xb[i, nb.index("freeboard")]), 1),
                                         "p": round(float(pbr[i]), 3), "rank": int(rank[i]),
                                         "engine_at_risk": bool(br_engine[i])} for i in top]})
        exp_aff = float(np.nansum(pb))
        out["versions"][ver] = {
            "features": bundle["features"], "predict_s": round(t_pred, 2),
            "corridor_buildings": int(np.isfinite(pb).sum()), "corridor_bridges": int(corr.sum()),
            "expected_affected_buildings": round(exp_aff, 1),
            "buildings_p_ge_0.5": int(np.nansum(pb >= 0.5)),
            "bridges_p_ge_0.5": int(np.nansum(pbr >= 0.5)),
            "lost_bridges": lost,
        }
    out["engine_rule"] = {"buildings_in_footprint": int(b_engine.sum()), "bridges_at_risk": int(br_engine.sum())}
    out["reported"] = {"houses": "35-45 destroyed + 27 partly damaged (research §1.1); Shanti Bazaar 40 of 42",
                       "bridges_lost": [l for l, _, _ in LOST]}
    out["timing_s"] = {"valley_load": round(t_valley, 2), "path_context_build": round(ctx.build_s, 2),
                       "total": round(time.time() - t0, 2)}
    json.dump(out, open(os.path.join(dm.MODEL_DIR, "oct11_check.json"), "w"), indent=2)
    print(json.dumps({k: v for k, v in out.items() if k != "versions"}, indent=1))
    for ver, r in out["versions"].items():
        print(f"== {ver}: expected affected buildings {r['expected_affected_buildings']} "
              f"(p>=0.5: {r['buildings_p_ge_0.5']}), bridges p>=0.5: {r['bridges_p_ge_0.5']} of {r['corridor_bridges']}, "
              f"predict {r['predict_s']} s")
        for l in r["lost_bridges"]:
            print("  ", l["reported"], "->", [(c["name"] or c["osm_id"], c["kind"], c["dist_to_place_m"],
                                              f"hand {c['crossing_hand_m']}", f"p {c['p']}", f"rank {c['rank']}",
                                              f"engine {c['engine_at_risk']}") for c in l.get("candidates", [])])


if __name__ == "__main__":
    main()
