## ADDED Requirements

### Requirement: Gradient-boosting damage classifier, two versions
The system SHALL train a `HistGradientBoostingClassifier` that outputs P(affected) per row. Version v1 SHALL use the features without `freeboard`. Version v2 SHALL also use `freeboard`. Both SHALL be saved under `models/damage/` with the exact feature list and training metadata (event, corridor width, split, timestamp, host architecture).

#### Scenario: Both versions are saved
- **WHEN** training completes
- **THEN** `models/damage/v1.joblib` and `models/damage/v2.joblib` exist, each storing its feature list

#### Scenario: Model loads on LinuxONE
- **WHEN** `damage_model.load("v2")` runs on the L1CC VM
- **THEN** it returns a model whose predictions on the training table match those recorded at training time

### Requirement: Spatial holdout evaluation by river km
Evaluation SHALL split rows at the river km that halves the positives, exclude a 2 km gap on each side, train on one side and test on the other, in both directions. For each direction it SHALL report ROC AUC, PR AUC, recall at the top 10/20/30% of rows, "flagged X of Y affected" at top-k = the number of positives, and feature importances (permutation importance on the test side).

#### Scenario: Both directions are reported
- **WHEN** evaluation runs
- **THEN** `models/damage/metrics.json` contains upstream→downstream and downstream→upstream results for v1 and v2

#### Scenario: Gap rows are excluded
- **WHEN** a row's river km is within 2 km of the split point
- **THEN** it is used in neither train nor test for that split

### Requirement: Baselines are reported next to the model
Evaluation SHALL score the same test rows with (a) a HAND ranking (`−hand`) and (b) the engine's footprint rule `hand ≤ envelope.height(river_km)` with the Aug envelope, and SHALL report the same metrics for them. Metrics SHALL also be reported for the 2 km corridor table.

#### Scenario: Model vs. footprint rule
- **WHEN** metrics are written
- **THEN** each holdout direction lists model v1, model v2, the HAND ranking and the footprint rule side by side

### Requirement: October out-of-event check
The system SHALL apply v1 and v2 to the Oct 11 Budhi Gandaki scenario (Budhi terrain, Oct 11 path and envelope) and SHALL report P(affected) and rank for the Soti iron bridge and the Arughat bridge. It SHALL also report the same for the bridges the engine already flags (Dobhan, Machhakhola, Sirdibas), in `models/damage/oct11_check.json`.

#### Scenario: Known-miss bridges are scored
- **WHEN** the October check runs
- **THEN** `oct11_check.json` lists Soti and Arughat with p and rank among all corridor bridges, for v1 and v2

### Requirement: Inference interface for the engine
`engine/damage_model.py` SHALL expose `features(...)`, `load(version)`, `predict(model, terrain, path, points_lonlat, kinds, envelope=None)` returning one probability per input point (NaN outside the corridor), and `predict_scenario(scenario)`, which reads an `engine.scenario.Scenario` without modifying it. The module SHALL NOT modify files owned by other agents.

#### Scenario: Points outside the corridor
- **WHEN** `predict` receives a point 3 km from the path
- **THEN** that point's probability is NaN

#### Scenario: Scenario adapter
- **WHEN** `predict_scenario` is called with the Oct 11 scenario object
- **THEN** it returns per-building probabilities aligned with the scenario's building list, plus per-bridge probabilities

### Requirement: Runs and is timed on L1CC
Feature building, training and October inference SHALL run on the L1CC VM in `~/work-agent-lcpizani` with system Python, and SHALL log wall-clock times and the machine architecture (`s390x`) in the metrics file.

#### Scenario: Timing evidence
- **WHEN** training finishes on the VM
- **THEN** `metrics.json` records `arch = s390x` and the train and inference durations in seconds
