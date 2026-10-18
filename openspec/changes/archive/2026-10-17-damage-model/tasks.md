## 1. Setup and coordination

- [x] 1.1 `git pull --rebase` and re-read `AGENTS.md`, `engine/terrain.py`, `engine/flood.py`, `engine/scenario.py`, `replay/oct11.json`. Note the `Scenario` attribute names the adapter will read
- [x] 1.2 On the VM: create `~/work-agent-lcpizani` with a fresh clone of `main` (includes `data/processed`). Confirm `import engine.terrain` from `~/evac-ai` works read-only and that `Terrain('/home/linux1/evac-ai/data/proc_trishuli')` loads
- [x] 1.3 Build the Trishuli flood path (snap 85.383, 28.276, `radius=15` → `downstream_path` → `hand_to`). Sanity-check: path length ≈121 km, HAND at Timure and Betrawati plausible

## 2. Training table (damage-training-data)

- [x] 2.1 `scripts/damage/build_table.py`: load buildings (2026 flood → 1, no event → 0, other events dropped) and bridges (`destroyed:bridge` Aug → 1, `bridge=*` ways → 0, using line midpoints). Project to UTM 45N and map to grid cells
- [x] 2.2 Corridor selection: `drain_idx >= 0` and distance to path ≤ `max_dist_m` (500 default, 2000 for the comparison table)
- [x] 2.3 Features: `hand`, `river_km`, `dist_channel_m`, `slope_deg`, `valley_width_m`, `channel_slope`, `bend_curv`, `outside_bend`, `log_acc`, `ls_500m`, `kind`. Vectorized numpy/scipy only
- [x] 2.4 Write the table (`.npz` or parquet-free CSV) and the build report JSON (counts per kind × label, dropped rows, river-km range of positives). Check: positives ≈ 3,000 buildings + ≈60 bridges
- [x] 2.5 Push `[agent-lcpizani]` commit: `scripts/damage/` + `AGENTS.md` log line ("B features built"). **Target 16:00 ET**

## 3. v1 model and evaluation (damage-prediction)

- [x] 3.1 `scripts/damage/train_eval.py`: river-km split at the positives' median with a 2 km gap, both directions
- [x] 3.2 Train HGB v1 (fixed params from design D4). Logistic-regression sanity baseline
- [x] 3.3 Baselines on the same test rows: `−hand` ranking. Metrics: ROC/PR AUC, recall at top 10/20/30%, flagged X of Y, permutation importance. Also on the 2 km table
- [x] 3.4 Fit the final v1 on all rows, save `models/damage/v1.joblib` with its feature list and metadata. Write `metrics.json` with `arch` and timings

## 4. Aug 26 envelope and v2 (freeboard)

- [x] 4.1 Confirm `replay/aug26.json`'s height knots are outside the Trishuli grid, and the out-of-grid indexing hazard in `km_of`. Report it to claude-luis / agent-aayush in `AGENTS.md`
- [x] 4.2 Reconstruct the Aug envelope from damage marks (p90 HAND of positives per 5 km bin; train-side only in eval) → `FloodEnvelope`. Save knots to `models/damage/aug26_damage_envelope.json`. Add `freeboard`
- [x] 4.3 Train and evaluate v2 as in §3, adding the footprint-rule baseline (`hand ≤ height(km)`). Sensitivity: v2 AUC with envelope height ±30%
- [x] 4.4 Save `models/damage/v2.joblib`, update `metrics.json`

## 5. Inference module and October check

- [x] 5.1 `engine/damage_model.py`: `corridor_rows`, `features`, `load`, `predict` (NaN outside the corridor), `predict_scenario` (read-only adapter on `Scenario`)
- [x] 5.2 Check that load + predict on the VM reproduces the training-time predictions
- [x] 5.3 October: Budhi terrain + Oct 11 path + Oct 11 envelope. Score corridor buildings and bridges with v1 and v2
- [x] 5.4 Locate Soti iron bridge, Arughat bridge, Dobhan, Machhakhola, Sirdibas in OSM. Write `models/damage/oct11_check.json` (p, rank among bridges, v1 vs v2). Time the inference
- [x] 5.5 Push `[agent-lcpizani]` commit: module + models + metrics. **Target 19:00 ET**

## 6. Hand-off

- [x] 6.1 Post in `AGENTS.md` (log + packet B row): the result headline, the interface, and proposed API fields (`p_destroyed` per building and bridge, settlement `p_destroyed_mean` / `n_likely_destroyed`) for claude-luis to wire in
- [x] 6.2 Write `docs/models/damage.md`: what it predicts, data, features, split, results table, limits (one event, missed labels, tributaries excluded, approximate envelope knots)
- [x] 6.3 Mark packet B done in `AGENTS.md`. Next in queue: finish C, then D (or B2 if claude-luis approved)
