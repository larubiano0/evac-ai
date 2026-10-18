# Neural stand-in for area_fb (runs on the Telum AI accelerator)

Model files (bare file names on this page are in this folder): [`models/surrogate/`](../../models/surrogate/).

`area_fb_mlp.npz`: dense network 8 → 256 → 256 → 256 → 1 (ReLU, sigmoid output) distilled from
[`../area/area_fb.joblib`](area.md) across flood heights scaled within ±30%. Input standardisation and
area_fb's Platt calibration are folded into the weights, so it takes the same 8 feature columns and returns the
same calibrated P. Load and run it with [`engine/surrogate.py`](../../engine/surrogate.py) (numpy on the CPU, or
the NNPA via zDNN when `EVAC_NNPA_LIB` is set). Held-out agreement with area_fb is in `metrics.json`. Speed and
method are in [docs/linuxone-ai.md](../linuxone-ai.md). Rebuild it with `scripts/nnpa/train_surrogate.py`.
