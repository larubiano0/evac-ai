## ADDED Requirements

### Requirement: Baked P(destroyed) raster
The bake SHALL write an optional layer `pdestroyed.u16.bin` with these properties:
- **Source**: `engine.escape.FloodScenario` for the bundle's valley, trigger and preset
- **Encoding**: little-endian uint16, value = P × 10000, 65535 = outside the corridor
- **Grid**: the same as the other layers

The bake SHALL also record `predict: {valley, preset, trigger}` in `scenario.json`.

#### Scenario: Parity with the engine
- **WHEN** `validate.py` runs on a bundle with the layer
- **THEN** the decoded raster matches `FloodScenario.p` to within 1e-4 on every corridor cell, and its NaN cells are exactly the 65535 cells

#### Scenario: Old bundle
- **WHEN** a bundle has no `pdestroyed.u16.bin`
- **THEN** the viewer loads normally and the "Chance of destruction" option is hidden

### Requirement: Damage heat option
The heat-map selector SHALL offer "Chance of destruction", drawn with a sequential ramp from 0 to the bundle's 99th-percentile P. The legend SHALL show the real end values. The viewer SHALL NOT apply any fixed 0.5 threshold.

#### Scenario: Select damage layer
- **WHEN** the user selects "Chance of destruction"
- **THEN** corridor cells are coloured by P, cells outside the corridor stay uncoloured, and the legend shows 0 % and the 99th-percentile value

### Requirement: Bridge risk labels
Each bridge in `scenario.json` SHALL carry `p_destroyed` and `crosses_flood_river` when the engine provides them. The bridge label or details SHALL show the chance of destruction for bridges that cross the flood river.

#### Scenario: Dobhan bridge
- **WHEN** the user opens the Dobhan-area bridge on the Oct 11 bundle
- **THEN** its details show its P(destroyed) as a percentage, in addition to the existing "Don't cross · flood HH:MM" warning
