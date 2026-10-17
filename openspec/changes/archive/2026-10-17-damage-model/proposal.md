## Why

The time-to-safety engine (claude-luis) draws the flood footprint with a single height-above-river rule. That rule shrinks downstream, and on the Oct 11 replay it misses the Soti and Arughat bridges that were actually lost. Nothing in the system learns from what floods really destroyed. This model is also the judged "AI/ML on LinuxONE" piece (packet B in `AGENTS.md`, owner `agent-lcpizani`). The Aug 26 OSM damage labels are now on `main`, which makes it buildable today.

## What Changes

- New **training table** built from the Aug 26, 2026 Bhotekoshi–Trishuli corridor:
  - one row per building or bridge near the flood river
  - label `destroyed` taken from the OSM tags (`damage:event=2026NepalFlood`, `destroyed:building`, `destroyed:bridge`)
  - terrain features computed with the engine's `Terrain` on the Trishuli build (`data/proc_trishuli`)
- New **gradient-boosting classifier** giving `P(destroyed | flood passes down this river path)` for buildings and bridges. Two versions:
  - **v1:** HAND-based features
  - **v2:** adds **freeboard** (HAND minus that event's envelope height), so the model transfers between floods of different size
- New **evaluation**:
  - spatial holdout by river km, in both directions
  - comparison with the engine's footprint rule as a baseline
  - AUC, recall at top-k, "flagged X of Y destroyed", feature importances
  - an out-of-event check on Oct 11: are the Soti iron bridge and Arughat bridge flagged?
- New **inference module** `engine/damage_model.py`, giving `features(...)` and `predict(...)` for any valley/scenario, plus a saved model under `models/damage/`.
- Minimal **Aug 26 calibration knots** for the flood envelope, needed for v2 freeboard. This is the start of packet C (`replay/aug26.json`).
- **Proposed API fields** for claude-luis to wire in: `p_destroyed` per building and bridge, plus a settlement mean. Proposed only: `api/` and `engine/scenario.py` are not edited by this change.

## Capabilities

### New Capabilities
- `damage-training-data`: building the labelled training table (rows, labels, corridor and negative selection, features) from OSM damage tags and the engine's terrain products.
- `damage-prediction`: training, evaluating and serving the damage classifier (model versions, spatial holdout, baseline, metrics, the October check, inference interface, model artefact, runs on L1CC).

### Modified Capabilities
<!-- none: openspec/specs/ is empty -->

## Impact

- **New files:** `engine/damage_model.py`, `models/damage/` (model + metrics JSON), training/eval scripts under `scripts/damage/`, `replay/aug26.json` (minimal knots, later completed by packet C).
- **Reads, does not modify:** `engine/terrain.py`, `engine/flood.py`, VM `~/evac-ai/data/proc_trishuli` and `data/proc` (read-only), `data/processed/osm/*`, `data/processed/landslides_2015.csv`.
- **Runs on:** L1CC VM in `~/work-agent-lcpizani`, using system Python (sklearn 1.4, numpy, rasterio installed via apt). No new dependencies.
- **Coordination:** the API/scenario integration is handed to claude-luis as a field proposal in `AGENTS.md`. B2 route reliability is out of scope here (it's pending his OK).
- **Not committed:** `openspec/` stays local. The team contract is `AGENTS.md` plus the `engine/damage_model.py` interface.
