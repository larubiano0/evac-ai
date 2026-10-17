# Damage model (packet B)

**What it predicts:** for every building and bridge near a river, the probability that it is **affected
(destroyed or damaged) if a flash flood comes down that river**. It doesn't predict *whether* a flood happens.
The engine supplies the flood path and flood line, and this model says what the flood takes with it.

**Trained on** the Aug 26 2026 Bhotekoshi–Trishuli debris flood: OSM/HOT damage tags mapped from post-event imagery.
**Applied to** any valley the engine builds, e.g. the Oct 11 Budhi Gandaki flood.
**Runs on** IBM LinuxONE (s390x). The table builds in 6 s, training takes 0.4 s, and scoring the 23.6k Aug rows takes 0.13 s.

## Results (spatial holdout, Aug 26)

The river is split at km 51.8 (the median km of the affected rows), with a 2 km gap. The model trains on one side and is tested on the other.

| Test side → | **Downstream** (train upstream) | **Upstream** (train downstream) |
|---|---|---|
| rows / affected | 18,222 / 1,474 | 4,445 / 1,492 |
| **v2 model** ROC AUC · PR AUC | **0.968 · 0.740** | 0.794 · 0.597 |
| **v1 model** (no freeboard) | 0.942 · 0.540 | **0.818 · 0.694** |
| Engine footprint rule (HAND ≤ flood line) | 0.713 · 0.398 | 0.699 · 0.482 |
| Height above river only (rank by HAND) | 0.937 · 0.475 | 0.751 · 0.477 |
| Freeboard only (no ML) | 0.977 · 0.747 | 0.751 · 0.477 |
| **Flagged, of the affected** (top-k, k = number affected) | **v2: 1,043 of 1,474** (footprint rule: 672) | **v1: 829 of 1,492** (footprint rule: 824) |

How to read this:
- **Both models beat the engine's footprint rule clearly.** Downstream, v2 ranks 1,043 of the 1,474 affected rows into its top 1,474 (71% precision), against 672 for the rule.
- **Most of v2's gain comes from freeboard**, i.e. height relative to *this flood's* line. Where that line is well estimated (downstream), freeboard alone does about as well as v2. The ML adds distance to channel and local terrain on top.
- **Where the flood line is poorly known** (upstream, extrapolated from downstream marks), the learned terrain model v1 is the best option (0.818 vs 0.751 for HAND).
- A 2 km corridor (the `AGENTS.md` spec) gives AUC 0.97 in both directions, but most of those extra negatives are trivially safe hillside houses. The 500 m numbers above are the honest ones.
- Counting only *destroyed* (dropping *damaged*) gives the same picture: v1 0.941 / 0.817.

**Calibration:** raw boosted probabilities were overconfident (0.97 predicted vs 0.45–0.77 observed). The model applies Platt scaling fitted on the out-of-fold spatial predictions, which cuts the Brier score from 0.086 to 0.068 (v2). Calibrated probabilities top out around 0.85.

## October 11 check (out of event; trained on August only)

| | Engine footprint | v1 | **v2** | Reported |
|---|---|---|---|---|
| Expected affected buildings (sum of p) | 365 in footprint | 271 | **146** | ~62–72 houses (35–45 destroyed + 27 partly damaged) |

- **v2 shrinks the over-prediction** the most, as intended: freeboard adapts to October's smaller flood. OSM counts sheds and outbuildings, so part of the remaining gap is building definition.
- Lost bridges (`replay/oct11.json`): v2 ranks a Dobhan-area bridge **#1 of 49** corridor bridges and a Sirdibas-area Manaslu Circuit bridge **#3**. The engine already flags these.
- **Soti and Arughat are still missed. Root causes found:**
  - **Arughat:** the DEM-derived (D8) channel runs **≥ 175 m** from the real Budhi Gandaki. Even the point of the bridge line closest to the channel is 175 m away, at HAND 17 m vs a ~6 m flood line, so every height there is overestimated. The fix is terrain-side: burn the OSM river into the DEM before deriving flow directions, in `pipeline/` (owned by claude-luis). The model was deliberately **not** tuned to hit these two bridges.
  - **Soti:** OSM has **no motorable bridge** mapped near Soti, so the "Soti iron bridge" can't be scored.
- Disclosure: scoring bridges at their **crossing point** (below) was prompted by inspecting the Arughat bridge. It's a geometric correction applied identically in training, and it did not change the October outcome.

## Retrained on three real floods (v3): does it transfer? (`scripts/damage/train_events.py`)

Two more real events were added (tables built by `scripts/damage/events/`, sources in `SOURCES_ahr.md` / `SOURCES_derna.md`):
**Ahr, Germany, Jul 2021** (4TU damage grades, 7,014 affected / 4,521 unaffected buildings within 500 m) and
**Derna, Libya, Sep 2023** (UNOSAT damaged buildings + OSM, 567 / 637; wadi corridor only). Buildings only, no bridges.
Rules fixed before looking: v3 replaces v2 in the app only if it is at least as good on the Nepal holdout and on Oct 11.

**A. Leave one flood out** (train on two floods, test on the third; ROC AUC):

| Test flood | Model (2 floods) | HAND alone | Distance alone |
|---|---|---|---|
| Nepal Aug 26 | 0.889 | 0.882 | 0.886 |
| Ahr | **0.650** | 0.826 | 0.783 |
| Derna | 0.835 | 0.842 | 0.792 |

**B. Nepal spatial holdout** (mean of both directions): v2 **0.881**, v3 (Nepal + Ahr + Derna) 0.872. Bridges, downstream test: v2 0.854, v3 0.605.

**Verdict: v3 failed B, so the app keeps v2** (C was not needed). v3 is saved outside the repo (`~/work-agent-lcpizani/out/v3.joblib`).

**A2 (post-hoc, decided after seeing A):** forcing risk to only fall with HAND and distance, buildings only:

| Test flood | All features | All features, monotone | HAND + distance only, monotone | HAND alone |
|---|---|---|---|---|
| Nepal Aug 26 | 0.890 | 0.877 | **0.900** | 0.882 |
| Ahr | 0.669 | 0.751 | 0.815 | 0.826 |
| Derna | 0.831 | 0.846 | 0.846 | 0.842 |

**What this means:**
- On a flood it has never seen, the model is no better than ranking by HAND (height above the river).
- The extra terrain features (slope, valley width, bends) learned in one valley do not carry over to another.
- Inside Nepal they do help: v2 0.881 vs HAND 0.844.
- For a new valley or flood type, the simplest physics-shaped model (HAND + distance, monotone) is the honest choice.
- Label definitions differ between floods: Ahr counts any damage grade D1+; Nepal counts OSM damage tags. Some of the Ahr gap may come from this.

## How it works

1. **Rows:** OSM buildings and bridges that drain into the flood path and lie ≤ 500 m from it.
   - Aug table: 3,093 affected / 20,358 unaffected buildings (99.6% of all Aug positives), 63 / 73 bridges.
   - **Bridges are scored at their crossing point**, the spot on the bridge line closest to the flood channel, not at the midpoint (which can sit on a terrace beside the 30 m channel).
2. **Features** (all from the engine's `Terrain` + the 2015 landslide inventory):
   - `hand`: height above the flood path
   - `dist_channel_m`
   - `slope_deg`
   - `valley_width_m`
   - `channel_slope`
   - `bend_curv`, `outside_bend`
   - `ls_500m`: 2015 landslides within 500 m
   - `kind`: building or bridge
   - v2 adds `freeboard` = `hand` − the event's flood-line height at that river km
3. **Feature choice** (`ablation.json`): `river_km` and `log_acc` (river size) describe *where along the August river* a row is. They don't transfer to another river, so they're excluded. Among transferable sets, v2 = freeboard + local terrain wins on mean holdout AUC (0.881) and has the best mean PR-AUC of all 12 combinations (0.669). The top candidates are within ~0.004 AUC, so the transferability constraint is what decides. Logistic regression on all features would score +0.003 but relies on positional features.
4. **August flood line for freeboard:** `replay/aug26.json` has no usable height observation inside the Trishuli grid. Its Kali Khola and Devghat knots are west of the grid, see `AGENTS.md`. So the line is **reconstructed from damage marks**: the 90th percentile HAND of affected buildings per 5 km of river, put into the engine's `FloodEnvelope` (`aug26_damage_envelope.json`). In each holdout direction it's fitted on the training side only. At inference, freeboard uses the scenario's own envelope (`S.F`), which the engine calibrates from observed heights.
5. **Model:** `sklearn` `HistGradientBoostingClassifier` (depth 4, 300 iterations, lr 0.05, L2 1.0, `kind` categorical), plus Platt calibration.

## Using it (engine / API)

```python
from engine import damage_model as dm
res = dm.predict_scenario(S)          # S = engine.scenario.Scenario; read-only; default v2
res["p_building"]                     # np.array aligned with S.V.b_ll (NaN outside the 500 m corridor)
res["bridges"]                        # [{"id", "name", "lon", "lat", "p_destroyed"}] aligned with S.V.bridge_meta
```
- **Cost per new flood path:** ~0.5 s to set up the path context on the Budhi grid, plus ~0.3 s to score about 3.7k corridor buildings and 49 bridges. It's cached per path.
- **Don't threshold at 0.5.** October probabilities are low overall (v2 has none ≥ 0.5). Show `p` as a colour scale, rank within the scenario, or sum it for expected counts.
- **Load models on s390x.** They were trained and pickled on L1CC. To rebuild them elsewhere, run the scripts below.

## Reproduce (on the VM, from the repo root, ~1 min total)

```bash
python3 scripts/damage/build_table.py      # -> ~/work-agent-lcpizani/out/table_trishuli.npz, build_report.json
python3 scripts/damage/ablation.py         # -> ablation.json
python3 scripts/damage/train_eval.py       # -> v1/v2.joblib, metrics.json, aug26_damage_envelope.json
python3 scripts/damage/check_reproduce.py  # load + predict == training predictions (max err 5e-7)
python3 scripts/damage/oct11_check.py      # -> oct11_check.json (no GRASS writes)
python3 scripts/damage/train_events.py     # -> events_metrics.json (needs ~/work-agent-lcpizani/events/{ahr,derna}/table.npz)
```
These need the engine's `data/proc_trishuli` and `data/proc` + `data/raw` (Budhi) builds on the VM.

## Limits (say these in the video)

- **Transfer to other floods is weak** (section above): outside Nepal the model is no better than HAND.
- **One training event** for v2, with labels traced by volunteers from satellite imagery. Damage under trees or in narrow gorges may be missed, so some "unaffected" rows are really affected. That's why results are reported as rankings and recall.
- **Tributary damage** is only included where it drains into the main path within 500 m.
- **Freeboard is only as good as the flood line.** In August the line comes from damage marks; in October from the engine's envelope. The two are related but not the same quantity.
- **30 m DEM:** the D8 channel can drift from the real river (Arughat ≥ 175 m), which corrupts every height measured there.
- **Earthquake landslides (2015)** are a weak proxy for slope weakness under a debris flood.

## Files

| File | What |
|---|---|
| `v1.joblib`, `v2.joblib` | Model bundles: `model`, `features`, `version`, `calibration`, `meta` (+ `aug26_envelope_knots` in v2) |
| `metrics.json` | All holdout metrics, baselines, reliability tables, permutation importances, calibration, timings |
| `ablation.json` | Feature-set × model comparison and the selection rule |
| `oct11_check.json` | October application: lost-bridge candidates with p/rank, expected affected counts |
| `build_report.json` | Training-table counts, dropped rows and reasons |
| `aug26_damage_envelope.json` | Reconstructed Aug flood line (knots, method) |
| `events_metrics.json` | Three-flood retrain: leave-one-flood-out, post-hoc monotone test, Nepal holdout v2 vs v3 |
| `train_pred_sample.json` | 300-row prediction sample used by `check_reproduce.py` |

Data: © OpenStreetMap contributors (ODbL); Copernicus DEM GLO-30; Roback et al. 2017 landslide inventory (USGS, public domain);
Ahr labels: Samprogna Mohor et al. 2025, 4TU.ResearchData, doi:10.4121/8f7a21d3-9bb9-4808-ae51-761eb3fba986 (ODbL 1.0);
Derna labels: UNITAR-UNOSAT FL20230912LBY via HDX (CC BY-SA).
