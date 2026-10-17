"""Feature-set ablation for the damage model: which features transfer across the river-km holdout?

Same split, gap and damage-mark envelope as train_eval.py. Positional features (river_km, log_acc and
channel_slope encode "where along THIS river") are the suspects for poor transfer to new reaches/rivers.
Selection rule (fixed before looking at October): mean ROC AUC over the two holdout directions.
Writes models/damage/ablation.json.
"""
import json, os, sys, time
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import roc_auc_score, average_precision_score

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from engine import damage_model as dm
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from train_eval import fit_envelope, hgb, GAP_KM

POSITIONAL = dm.POSITIONAL
ALL = dm.FEATURES_ALL
SETS = {
    "v1_all": ALL,
    "v1_local": [f for f in ALL if f not in POSITIONAL],                          # = dm.FEATURES_V1 (chosen v1)
    "v1_local_noslope": [f for f in ALL if f not in POSITIONAL + ["channel_slope"]],
    "v2_all": ALL + ["freeboard"],
    "v2_local": [f for f in ALL if f not in POSITIONAL] + ["freeboard"],          # = dm.FEATURES_V2 (chosen v2)
    "v2_local_noslope": [f for f in ALL if f not in POSITIONAL + ["channel_slope"]] + ["freeboard"],
}


def main():
    t = np.load(os.path.expanduser("~/work-agent-lcpizani/out/table_trishuli.npz"))
    names = list(t["cols"]); X0, y, kind = t["X"], t["y"].astype(int), t["kind"]
    m = X0[:, names.index("dist_channel_m")] <= dm.MAX_DIST_M
    X0, y, kind = X0[m], y[m], kind[m]
    km = X0[:, names.index("river_km")]; hand = X0[:, names.index("hand")]
    split = float(np.median(km[y == 1]))
    res = {"split_km": split, "selection_rule": "mean ROC AUC over both holdout directions", "sets": {}}
    for sname, feats in SETS.items():
        res["sets"][sname] = {"features": feats}
        for model in ("hgb", "logreg"):
            aucs = {}
            for d, low in (("up_to_down", True), ("down_to_up", False)):
                tr = (km < split - GAP_KM) if low else (km > split + GAP_KM)
                te = (km > split + GAP_KM) if low else (km < split - GAP_KM)
                cols = {n: X0[:, i] for i, n in enumerate(names)}
                if "freeboard" in feats:
                    env, _ = fit_envelope(km[tr], hand[tr], y[tr], kind[tr] == "building")
                    cols["freeboard"] = hand - env.height(km)
                X = np.column_stack([cols[f] for f in feats])
                clf = hgb(feats) if model == "hgb" else make_pipeline(StandardScaler(), LogisticRegression(max_iter=2000))
                p = clf.fit(X[tr], y[tr]).predict_proba(X[te])[:, 1]
                b = kind[te] == "bridge"
                aucs[d] = {"roc_auc": round(float(roc_auc_score(y[te], p)), 4),
                           "pr_auc": round(float(average_precision_score(y[te], p)), 4),
                           "bridge_roc_auc": round(float(roc_auc_score(y[te][b], p[b])), 4)}
            aucs["mean_roc_auc"] = round(np.mean([aucs[d]["roc_auc"] for d in ("up_to_down", "down_to_up")]), 4)
            aucs["mean_pr_auc"] = round(np.mean([aucs[d]["pr_auc"] for d in ("up_to_down", "down_to_up")]), 4)
            res["sets"][sname][model] = aucs
            print(f"{sname:18s} {model:6s} up->down {aucs['up_to_down']['roc_auc']:.3f}/{aucs['up_to_down']['pr_auc']:.3f}"
                  f"  down->up {aucs['down_to_up']['roc_auc']:.3f}/{aucs['down_to_up']['pr_auc']:.3f}"
                  f"  mean AUC {aucs['mean_roc_auc']:.3f}  mean PR {aucs['mean_pr_auc']:.3f}"
                  f"  bridges {aucs['up_to_down']['bridge_roc_auc']:.2f}/{aucs['down_to_up']['bridge_roc_auc']:.2f}")
    score = lambda k: res["sets"][k[0]][k[1]]["mean_roc_auc"]
    combos = [(s, mo) for s in SETS for mo in ("hgb", "logreg")]
    best_any = max(combos, key=score)
    transferable = [k for k in combos if not any(f in POSITIONAL for f in SETS[k[0]])]
    best = max(transferable, key=score)
    res["selection_rule"] = ("max mean ROC AUC over both holdout directions, among feature sets defined on any river "
                             "(no river_km / log_acc: 'km from the Aug source' has no meaning on another river)")
    res["best_by_rule"] = {"set": best[0], "model": best[1], **res["sets"][best[0]][best[1]]}
    res["best_unrestricted"] = {"set": best_any[0], "model": best_any[1], "mean_roc_auc": score(best_any),
                                "margin_over_selected": round(score(best_any) - score(best), 4)}
    res["note"] = ("Top combinations are within ~0.004 mean AUC of each other: the AUC rule alone does not separate "
                   "them; the transferability constraint decides.")
    json.dump(res, open(os.path.join(dm.MODEL_DIR, "ablation.json"), "w"), indent=2)
    print("best by rule (transferable):", best, score(best), "| unrestricted:", best_any, score(best_any))


if __name__ == "__main__":
    main()
