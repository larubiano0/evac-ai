# Impacted-area model (`area_fb`)

**What it predicts:** for every 30 m square of ground near a river, the probability that the square ends up
**inside the flood/debris footprint** when a flash flood comes down that river. "Footprint" means what satellite
analysts mapped as flooded or covered by mud/rock after a real flood.

**Why it exists:** the damage model (`models/damage/v2.joblib`) learned only from buildings and bridges, the only
places that had labels. Prediction mode (`engine/escape.py`) still applied it to every square, including
riverbanks, gravel bars, fields and gorge walls that it had never seen. This model is trained on the ground itself.

**Not for bridges.** Bridges keep v2: no bridge rows are in this training data.

## Inputs (all computed by `engine/damage_model.features()`, same code as v2)

For each square's centre, given the terrain grid and the flood's path down the river:

| Feature | Meaning |
|---|---|
| `hand` | height above the flood path (the river channel the square drains into), m |
| `dist_channel_m` | straight-line distance to the nearest path cell, m |
| `slope_deg` | ground slope at the square |
| `valley_width_m` | how wide the valley floor (HAND ≤ 30 m) is around the drain point, m |
| `channel_slope` | river gradient over ±1 km of channel |
| `bend_curv` | how much the river turns there (radians, + = left) |
| `outside_bend` | the same turn signed by bank side: > 0 = outside of a bend, where floods ride higher |
| `freeboard` | `hand` minus the height of this flood's water line at that river km (from the flood preset) |

`freeboard` is what makes the model flood-specific. A small flood (Oct 11) has a low water line, so less ground gets
a high P. The water line comes from `models/damage/flood_presets.json`, the same presets prediction mode uses today.
They are built only from real observations of past floods (see that file's `rules`).

Deliberately left out: `river_km` and `log_acc` (where along the river: hurt transfer between rivers in the damage
ablation), `ls_500m` (a Nepal-only landslide inventory), and `kind` (every row is ground).

**Model:** scikit-learn `HistGradientBoostingClassifier` (`max_depth=4`, `learning_rate=0.05`, 300 iterations,
`l2=1.0`, the same settings as v1/v2). It has two **monotone constraints**: P may only go down as `hand` grows and
as `dist_channel_m` grows. Higher and further from the river can never look more dangerous. Probabilities are
**Platt-calibrated** on out-of-fold predictions (5 folds by 10 km river blocks). The calibration is stored in the
bundle and applied by `dm.predict()`.

**Trained on:** Aug 26 2026 (Bhotekoshi–Trishuli) and Oct 11 2026 (Budhi Gandaki). These are the two floods with a
flood preset. Each flood gets equal total weight. 214,182 squares within 500 m of the flood path, of which 40,716
are inside the footprint.

## Labels (only real, published observations)

| Flood | Product (producer) | What is mapped | Image | Squares ≤ 500 m: in / out |
|---|---|---|---|---|
| Aug 26 2026, Nepal | UNOSAT FL20260826NPL (UNITAR-UNOSAT) | flood + mudflow/rockflow extent | Sentinel-2 (27 Aug) + PlanetScope (26 Aug), multisensor 26–28 Aug | 28,458 / 98,070 |
| Oct 11 2026, Nepal | UNOSAT FL20261011NPL | flood water and/or mudflow extent | Sentinel-2, 11 Oct | 12,258 / 75,396 |
| Ahr 2021, Germany (test only) | Copernicus EMS EMSR517 AOI15, monitoring v3 | flooded area + flood traces | aerial 0.12 m (16 Jul) + Pléiades 0.5 m (20 Jul) | 10,680 / 36,131 |
| Derna 2023, Libya (test only) | UNOSAT FL20230912LBY | flood extent, cloud mask | Sentinel-2, 12 Sep | 669 / 800 |

Rule for each square, using its centre:
- `y = 1`: the centre is inside the mapped extent.
- `y = 0`: inside the area the analysts checked, outside the extent and outside any cloud/not-analysed mask.
- Anything else gets no label.

Built by `scripts/damage/events/build_area_table.py`. Citations and licences are in `scripts/damage/events/SOURCES_area_<event>.md`.

## How it was tested (rules written before any result was seen; `scripts/damage/train_area.py`)

**The decisive test (B):** the Oct 11 flood, which the candidates never trained on. This is exactly prediction mode's
situation: a new flood, with only its preset water line known. The candidate trains on Aug 26 only and is compared
with **what the app uses today** (v2 on squares, same preset, same path as `engine/escape.py`).

Rule: replace v2 only if ROC AUC ≥ v2 **and** Brier score ≤ v2.

| On Oct 11 (87,654 squares, 14% flooded) | ROC AUC (ranking) | PR AUC | Brier (probability error, lower = better) |
|---|---|---|---|
| **`area_fb`** (trained on Aug 26) | **0.937** | **0.781** | **0.057** |
| v2, what the app uses now | 0.932 | 0.652 | 0.090 |
| terrain only, no water line (trained on Aug 26 + Ahr + Derna) | 0.919 | 0.688 | 0.077 |
| distance to river alone | 0.935 | 0.776 | n/a |
| height above river alone | 0.903 | 0.752 | n/a |
| engine footprint rule (below the water line) | 0.912 | 0.762 | n/a |

**Result: `area_fb` passes the rule and replaces v2 for the ground squares.** In plain terms:

- **It's not better at ranking.** Its AUC is +0.004 over v2, with a 95% interval of −0.047 to +0.042 (block
  bootstrap over 2 km river blocks, because neighbouring squares are not independent). Distance alone ranks about
  as well.
- **It is much better at the actual number.** That matters because prediction mode calls ground "safe" when
  P ≤ 10%. v2 says the lowest ground (HAND < 2 m) has a 28% chance; in reality 92% of it flooded. On HAND 20–50 m
  ground, v2 says 9% (so "safe"), while 11% of it actually flooded. `area_fb` says 21%, so that ground is no longer
  called safe.
- **Expected flooded area:** observed 11.0 km², `area_fb` 13.0 km² (slightly cautious), v2 6.0 km² (half of reality).

Calibration on Oct 11 by height above the river (observed share flooded vs predicted mean):

| HAND | observed | `area_fb` | v2 |
|---|---|---|---|
| < 2 m | 0.92 | 0.96 | 0.28 |
| 2–5 m | 0.87 | 0.91 | 0.29 |
| 5–10 m | 0.68 | 0.83 | 0.24 |
| 10–20 m | 0.37 | 0.60 | 0.16 |
| 20–50 m | 0.11 | 0.21 | 0.09 |
| ≥ 50 m | 0.03 | 0.01 | 0.04 |

It overestimates on mid-slope ground (10–50 m). That is the safe side for an evacuation tool, but it means more
ground counts as unsafe: on Oct 11, 70% of the corridor is at P ≤ 10% (v2: 80%).

**Leave one flood out (A), terrain-only model, all four floods**, to see whether it travels to other countries:

| Test flood | Terrain model AUC | HAND alone | Distance alone | Brier |
|---|---|---|---|---|
| Aug 26 | 0.966 | 0.961 | 0.935 | 0.076 |
| Oct 11 | 0.919 | 0.903 | 0.935 | 0.077 |
| Ahr | 0.886 | 0.896 | 0.787 | 0.226 |
| Derna | 0.989 | 0.989 | 0.985 | 0.221 |

Ranking travels, but the probabilities do not: Ahr is over-predicted and Derna under-predicted (Brier ~0.22).
Without knowing how big the flood is, terrain alone can't set the level. That's why the app model needs the water
line (`freeboard`), and why it only applies where a flood preset exists (Nepal).

**Aug 26 reference only (not a test, since v2 was trained on Aug 26 buildings):** v2 AUC 0.970, Brier 0.107.

## Using it

```python
from engine import damage_model as dm
b = dm.load("area_fb", os.path.join(dm.REPO, "models", "area"))
p = dm.predict(b, ctx, cell_lonlat, ["building"] * n, envelope)   # kind is ignored; envelope = preset water line
```

Same call and same cost as v2: 0.8–0.9 s per scenario on s390x (`scripts/damage/check_area_dropin.py`). The file is an
s390x pickle (scikit-learn from Ubuntu apt), so load it on the VM.

## Known problems

- **Timing.** Images were taken hours to days after the peak:
  - Oct 11: Sentinel-2 the same day (the package gives no time).
  - Aug 26: 26–28 Aug.
  - Ahr: 1 and 5 days after.

  Water that had drained away by then can be missed. For debris floods the mud and rock stay, so the footprint
  holds up well. At Ahr, 82% of the mapped squares are "flood traces", not water.
- **Extent vs debris.** UNOSAT mixes water, mud and rockflow in one class. The model predicts "touched by the
  flood", not depth or destruction.
- **Clouds.** The UNOSAT Nepal packages publish **no cloud mask**, so any cloud gaps inside the analysed area count
  as "not flooded". Copernicus EMSR927 (Aug 26) had to cancel two areas for persistent cloud. Where Copernicus did
  map Aug 26 (with its own "not analysed" masks), it agrees with UNOSAT on 95.6% of squares.
- **DEM channel drift.** The river path comes from the 30 m DEM, not the real river. On Oct 11, 25% of the flooded
  squares sit ≥ 20 m above the DEM channel. That is partly real (debris runs up), partly the DEM channel being off
  the real river (≥ 175 m at Arughat, see `models/damage/README.md`). At Ahr, 31% of path cells fall outside the
  mapped extent.
- **Only two floods train it.** Both are Himalayan debris floods. A different kind of flood (slow monsoon flooding
  on the plains) is outside what it has seen.
