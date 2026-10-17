## Context

- **Project:** "Time to Safety" (see `latinos-ibmz-datathon-plan.md`, `AGENTS.md`).
  - The engine is owned by claude-luis. It computes, per event: the flood path (D8 downstream from a trigger), HAND relative to that path, an arrival/height envelope along river km, the footprint, walking time to safety (`r.walk`), escape routes, and slack per building.
  - The footprint rule is `HAND <= height(km)`. On Oct 11 it misses the lost Soti and Arughat bridges.
- **Labels:** the only ground truth for what floods destroy is the Aug 26 OSM damage tagging in the Bhotekoshi–Trishuli corridor.
  - Buildings: 2,759 destroyed + ~350 damaged.
  - Bridges: 63 destroyed.
  - Gorkha has none.
- **Terrain:** claude-luis has built `data/proc_trishuli` on the VM: UTM 45N, 30 m, 2663×2730 grid, a 121 km path from the Rasuwagadhi border.
  - `engine.terrain.Terrain` gives `dem`, `acc`, `streams`, `downstream_path`, `snap_to_channel`, and `hand_to(path) -> (hand, drain_idx)`.
- **Envelope:** `engine.flood.FloodEnvelope` / `calibrate_from_replay` give `height(km)` and bands. Only `replay/oct11.json` exists.
- **Constraints:**
  - L1CC: s390x, 3 vCPU, 7.8 GB, a shared VM.
  - sklearn 1.4 / numpy / rasterio / pyproj / scipy come from apt (system Python).
  - Use our own VM dir `~/work-agent-lcpizani`. `~/evac-ai` is read-only for us.
  - Don't edit other agents' files.
  - Deadlines: v1 features by 16:00 ET, model in the API by 19:00 ET.
- **Assumption (agreed with the user):** the flood is destructive. Anything it reaches counts as affected. So "destroyed" and "damaged" are both positives, which means the model predicts how far the destroyed zone reaches.

## Goals / Non-Goals

**Goals:**
- `P(affected | a flood passes down this path)` for every building and bridge near the path, in any valley the engine has built.
- Beat the footprint rule on a spatial holdout within August, and report it honestly.
- Transfer to Oct 11. Concrete check: are the Soti and Arughat bridges ranked high?
- Train and run inference on L1CC, with timings, as evidence of LinuxONE use.
- Give claude-luis a stable, small interface to wire into `scenario.py` and the API.

**Non-Goals:**
- Road-segment rows (later, if time allows).
- Route reliability / Monte Carlo (B2, pending claude-luis's OK).
- Any edits to `engine/{terrain,flood,safety,scenario,alerts}.py`, `api/`, `web/`, `pipeline/`.
- Hydrodynamic or debris-flow simulation.
- Hyperparameter search beyond a small fixed grid.

## Decisions

**D1. Rows = buildings + bridges, with a `kind` column.**
- **Buildings** come from `data/processed/osm/buildings.csv`:
  - label 1 if `damage_event == 2026NepalFlood` (destroyed or damaged)
  - label 0 if `damage_event` is empty
  - other events (2015 earthquake) are excluded
- **Bridge positives:** `destroyed:bridge` lines in `damage.geojson` with the Aug event, using the line midpoint.
- **Bridge negatives:** `bridge=*` ways in `roads.geojson` inside the corridor.
- *Alternatives:* buildings only (the `AGENTS.md` spec), but that ignores the engine's known bridge miss; adding roads needs segment splitting, so it's deferred.
- A `destroyed`-only label is also reported as a sensitivity check.

**D2. Corridor = cells that drain into the main flood path, within 500 m of it.**
- Snap the source at (85.383, 28.276), `radius=15`, as described in `AGENTS.md`. Then `downstream_path` and `hand_to(path)`.
- A row is kept if its cell drains into the path (`drain_idx >= 0`) and its straight-line distance to the nearest path cell is ≤ 500 m.
- AUC is also reported at 2 km, to match the `AGENTS.md` spec.
- *Why 500 m:* in the earlier analysis, 98% of failures were within 250 m of the flood rivers. At 2 km, the negatives are mostly obviously safe hillside houses, which inflates AUC.
- Tributary damage (Salankhu, Chilime, Langtang…) drains into side channels. That makes its HAND relative to the main path large, so most of it falls outside the corridor. Accepted for v1 and documented as a limit.

**D3. Features, all computed from `Terrain` + OSM + the 2015 landslide CSV.**

| Feature | How |
|---|---|
| `hand` | `hand_to(path)` at the row's cell |
| `river_km` | Cumulative path length (m) at `drain_idx` ÷ 1000 |
| `dist_channel_m` | Euclidean distance transform of the path mask × 30 |
| `slope_deg` | `np.gradient(dem, 30)` at the cell |
| `valley_width_m` | At the drain cell: cells within a 1 km window with HAND ≤ 30 m × 30 m², ÷ (2 km of channel). An area-per-length proxy for floodplain width |
| `channel_slope` | Path elevation drop over ±1 km around the drain cell |
| `bend_curv` | Signed change of path heading over ±10 cells at the drain cell |
| `outside_bend` | Sign(bend) × side of channel (cross product): +1 means the outside of a bend |
| `log_acc` | log of flow accumulation at the drain cell (river size) |
| `ls_500m` | Count of 2015 landslide centroids within 500 m (scipy `cKDTree` in UTM) |
| `kind` | 0 = building, 1 = bridge |
| `freeboard` (v2 only) | `hand − envelope.height(river_km)` |

- **Excluded:** building footprint size (destroyed footprints were traced from post-event imagery, so it could leak the label), absolute elevation, lon/lat.
- lon/lat → UTM 45N via pyproj (EPSG:4326 → 32645), then `Terrain.rc`.

**D4. Model = `HistGradientBoostingClassifier`.**
- Settings: `max_depth=4`, `learning_rate=0.05`, `max_iter=300`, `l2_regularization=1.0`, `categorical_features=[kind]`, early stopping on an internal validation split.
- **No `class_weight`** (revised): the positive rate is ~13%, which HGB handles fine, and balanced weights would inflate the probabilities the API shows. A reliability table is reported on each test side.
- A small fixed grid only.
- *Alternatives:* logistic regression (kept as a sanity baseline), random forest (no advantage, slower).
- Probabilities are calibrated (isotonic, on held-out folds) only if the reliability plot shows strong miscalibration. A ranking is enough for the metrics; the API needs probabilities.

**D5. Spatial holdout by river km.**
- Split at the river km that halves the positives. Leave a **2 km gap** of excluded rows on each side of the split, so neighboring buildings don't leak between train and test.
- Train upstream → test downstream, then the reverse. Report both.
- *Alternative:* the north/south latitude split (157/157 failures). Equivalent along this river, but river km also works for Oct 11 and matches `AGENTS.md`.

**D6. Baselines.**
- **v1:** rank by `−hand`, i.e. a HAND threshold with every possible cutoff.
- **v2:** the engine's footprint rule `hand ≤ envelope.height(km)` with the Aug envelope, scored as a 0/1 ranking.
- Metrics for every model and baseline, on each holdout direction: ROC AUC, PR AUC, recall at the top 10/20/30% of rows, "flagged X of Y affected" at the top-k equal to the number of positives, and the false-positive count.

**D7. v2 freeboard needs an Aug 26 envelope.**
- **Revised during implementation.** `replay/aug26.json` (packet C, agent-aayush) exists, but its only height knots used for calibration (Kali Khola gauge, lon 84.546; Devghat, lon 84.43) lie **west of the Trishuli grid** (edge 84.735). The in-corridor heights (Timure, Galchhi) are rightly marked `excluded`. So no observed August height constrains the training corridor.
- **The August flood line is reconstructed from damage marks** (the high-water-mark method):
  - For each 5 km river-km bin with ≥ 30 affected buildings, the knot height is the 90th percentile of HAND of the affected buildings.
  - Knots go into `engine.flood.FloodEnvelope(arrival_knots=[(0,0),(1,1)], height_knots=...)`, which uses the engine's own interpolation and decay beyond the last knot.
- **No leakage across the holdout:** in each holdout direction, knots are fitted on the **training side only**. Test-side heights come from the envelope's extrapolation (decay downstream, held constant upstream), which mimics having observations on one side only. The final v2 is fitted with knots from all rows.
- **At inference** (Oct 11), freeboard uses the scenario's own envelope (`S.F`, calibrated by the engine from observed heights). This is a mismatch: observed peak height vs. the August reach of destruction. It's documented, and v1 vs v2 on October shows its effect.
- The knots and the method are saved in `models/damage/aug26_damage_envelope.json`.

**D8. October application.**
- Use `Terrain('/home/linux1/evac-ai/data/proc')` (Budhi Gandaki), the same path construction the engine uses for Oct 11, and the Oct 11 envelope from `replay/oct11.json`.
- Score all buildings and bridges in the corridor.
- **The check:** the ranks and probabilities of the Soti iron bridge and the Arughat bridge, located from OSM by name or position, plus the bridges the engine already gets right (Dobhan, Machhakhola, Sirdibas).
- Report v1 vs v2. v1 is expected to over-predict on October (a smaller flood), and v2 should correct it.

**D9. Interface (`engine/damage_model.py`, a new file we own).**
```python
FEATURES_V1 = [...]; FEATURES_V2 = FEATURES_V1 + ["freeboard"]
def corridor_rows(terrain, path, points_lonlat, kinds, max_dist_m=500) -> dict   # indices + per-row cells
def features(terrain, path, rows, envelope=None) -> np.ndarray                 # (n, n_features)
def load(version="v2") -> Model
def predict(model, terrain, path, points_lonlat, kinds, envelope=None) -> np.ndarray  # p per row, NaN outside corridor
def predict_scenario(scenario) -> dict   # adapter: reads attributes of engine.scenario.Scenario, returns
                                         # {"p_building": array aligned with scenario buildings, "bridges": [...]}
```
- `predict_scenario` only *reads* the `Scenario` object. Its attribute names are confirmed by reading `engine/scenario.py` before coding.
- Proposed API fields are posted in `AGENTS.md` for claude-luis: `p_destroyed` per building, `p_destroyed_mean` and `n_likely_destroyed` per settlement, and `p_destroyed` per bridge in `bridges_at_risk`.

**D10. Where things run.**
- Feature building, training and evaluation all run on the VM in `~/work-agent-lcpizani`, from a git checkout of `main` (it includes `data/processed`). The engine is imported read-only via `sys.path.insert(0, '/home/linux1/evac-ai')`.
- The model is saved with `joblib` on the VM and loaded on the VM. It is never trained on the Mac and loaded on s390x, which avoids byte-order and pickle issues.
- Jobs are wrapped in `timeout` (VM etiquette). Train and inference timings are logged for the video.
- Artefacts committed:
  - `models/damage/{v1,v2}.joblib` (small)
  - `models/damage/metrics.json`
  - `models/damage/oct11_check.json`

## Risks / Trade-offs

- **Labels missed by mappers** (damage under trees, in gorges), so some negatives are actually positives → report ranking metrics and recall, not precision. State this in the video.
- **One training event** → v2 freeboard normalizes flood size. The October check is the only out-of-event evidence: frame it as an indication, not proof.
- **Tributary damage excluded** by the main-path HAND → document it. v2+ could take the union of tributary paths if time allows.
- **Aug envelope knots are sparse and partly approximate** (">20 m", "+9 m rise") → use midpoints, carry the band, and report the sensitivity of v2 AUC to ±30% height.
- **Spatial autocorrelation** inflates scores → river-km split with a 2 km gap, in both directions.
- **Shared 3-vCPU VM** → building features over ~100k rows is vectorized numpy (seconds). HGB trains in seconds. Wrap jobs in `timeout`.
- **Interface drift** if claude-luis changes `Scenario` → the adapter is isolated in `predict_scenario`, and the core functions take plain arrays.
- **Deadline** (v1 by 16:00) → v1 first with no freeboard dependency; the minimal Aug knots are done in parallel; v2 after.

## Migration Plan

Additive only: new files, no changes to existing behavior. Integration is opt-in by claude-luis via the proposed API fields. Rollback = don't call `predict_scenario`.

## Open Questions

- Should the API show `p_destroyed` per building, or only settlement aggregates plus bridges? This is claude-luis/UI's call.
- Whether to add tributary paths to the corridor in v2+.
- B2 (route reliability) depends on claude-luis's answer in `AGENTS.md`.
