# LinuxONE AI: profiling the flood scoring and testing the Telum on-chip accelerator (NNPA)

**Verdict: NO-GO for the NNPA in the demo, based on measurements.** We profiled the prediction-mode scenario on the
z17 guest and ran our real per-cell batch through the Telum AI accelerator (Snap ML + IBM zDNN). Model
inference is only 1–5% of a cold scenario. On the NNPA, the same 300-tree model scored **1.5× slower than
sklearn on the CPU and 6× slower than Snap ML on the CPU**, with identical outputs. So we serve on the CPU.

All numbers were measured on Sat Oct 17 2026 on our L1CC VM: IBM z17 (machine type 9175, `nnpa` CPU flag present),
3 vCPU, 7.8 GB, Ubuntu 24.04, Python 3.12, sklearn 1.4.1, Snap ML 1.17.2, libzdnn 1.0.1 (Ubuntu `libzdnn0`).

## 1. Where the time goes (cProfile, cold `FloodScenario`, prediction mode)

Script: [`scripts/nnpa/profile_scenario.py`](../scripts/nnpa/profile_scenario.py). It wraps the area model's
`predict_proba` (models/area/area_fb.joblib: sklearn HistGradientBoosting, 300 trees of depth 4, 8 terrain + flood
features), the feature builder and the corridor context with wall-clock timers.

| Valley | Cells scored (30 m) | Cold total | Model inference | Features | Corridor context | Biggest cost |
|---|---:|---:|---:|---:|---:|---|
| Trishuli (Oct 11) | 126,528 | 67.4 s | **0.67 s (1.0%)** | 0.35 s | 1.46 s | rasterizing roads/rivers onto the grid: 57.7 s (86%) |
| Budhi (Aug 26) | 98,652 | 11.9 s | **0.63 s (5.3%)** | 0.23 s | 0.64 s | the same rasterization: 9.1 s (77%) |

- The cold cost is `Valley.cells_of_lines` (engine/escape.py): a Python loop calling `np.linspace` and an affine
  transform once per line segment, 1.5 M times for Trishuli. It runs once per valley per process and is then
  cached, so the live server pays it once, at warm-up.
- A new trigger point in an already-loaded valley costs about 4.8 s (Trishuli) or 1.9 s (Budhi) under the
  profiler. Inference is about 14% and 33% of that. Even an infinitely fast accelerator would therefore save at most
  0.67 s per scenario (Amdahl).
- This is the honest LinuxONE profiling result: **the hot spot is geometry in Python, not the neural/AI part.**

## 2. CPU vs NNPA on the real cell batch

Script: [`scripts/nnpa/bench_cells.py`](../scripts/nnpa/bench_cells.py). It scores the exact feature rows saved by
step 1. Snap ML can't load an sklearn HGB model, so we fit a Snap ML booster of the same shape (300 trees, depth 4,
lr 0.05) to reproduce area_fb's own call on those rows. It matches area_fb's call with AUC 0.999. We then time
`predict_proba` three ways. Each figure is the best of 5 after one warm-up call, using 3 threads.

| Batch | sklearn HGB, CPU (production) | Snap ML, CPU | **Snap ML, NNPA** (`zdnn_tensors`) |
|---|---:|---:|---:|
| Trishuli, 126,528 cells | 0.66 s (191k cells/s) | **0.16 s** (776k cells/s) | 1.02 s (124k cells/s) |
| Trishuli ×10, 1,265,280 cells (≈ precomputing 10 triggers) | 6.58 s | **1.68 s** | 10.25 s |
| Budhi, 98,652 cells | 0.52 s | **0.13 s** | 0.86 s |
| Budhi ×10, 986,520 cells | 5.17 s | **1.33 s** | 7.79 s |

- The CPU and NNPA outputs are identical (max abs difference ≤ 2e-16; AUC 0.999 both ways). Accuracy is not the
  issue. Speed is.
- Larger batches don't help: NNPA time scales linearly (×10 rows → ×10 time). So the gap is not a one-off setup cost.
- This matches the earlier synthetic test in [judge-review.md](judge-review.md) (0.44 s NNPA vs 0.05 s CPU for 23.6k
  rows).
- Why (our reading, not measured): Snap ML's zDNN path turns each tree into dense tensor operations. A depth-4 tree is only 15 comparisons per row. The CPU walks it in a few nanoseconds, while the tensor
  route pays for layout conversion and data movement on every call. The NNPA is built for large dense layers
  (LSTMs, transformers, wide MLPs), not for 8-feature shallow trees.

## 3. What we did not try, and why

- **A dense MLP copy of area_fb on the NNPA (PyTorch/ONNX with zDNN).** We skipped this on purpose. Inference is
  ≤ 0.67 s of a 12–67 s cold scenario, so even a perfect accelerator can't change what a user waits for. Pulling
  IBM's multi-GB JupyterLab image onto a shared 3-vCPU/7.8 GB VM the night before the freeze wasn't worth that
  ceiling.
- **Swapping in Snap ML on the CPU.** It is 4× faster than sklearn for this model, but that saves about 0.5 s per
  scenario, and `engine/escape.py` belongs to another agent. We noted it as a possible follow-up.
- **Speeding up the real hot spot.** Vectorizing `cells_of_lines`, or caching the rasterized road/river masks on
  disk, would cut the 57 s cold Trishuli start much more than any accelerator could. It's a follow-up for the
  file's owner, not part of this test.

## Caveats

- We didn't read hardware counters, so we can't independently show which instructions ran on the NNPA. The
  evidence is: libzdnn reports `zdnn_is_nnpa_installed() = True`, Snap ML loads its zDNN build, and the
  `zdnn_tensors` path runs a different engine from the CPU one (different timings, same outputs).
- The VM is shared and has 3 vCPUs, so absolute times can move between runs. This is a single benchmark run;
  the ratios agree with the earlier synthetic test, run on a different day.
- The cProfile wall times include profiler overhead. The timer-wrapped figures (inference, features, context)
  are measured directly.

## The one honest line (video, 0:50 beat)

> "We profiled it on the z17 and tested the Telum AI accelerator through Snap ML and zDNN. Our 300-tree model
> scores 126 thousand cells in 0.16 s on the CPU and 1 s on the accelerator. AI inference is under 5% of the
> work, so we serve on the CPU."

## Reproduce (on the VM, in your own work directory)

```bash
EVAC_BUILD_DIR=$PWD/build timeout 300 python3 scripts/nnpa/profile_scenario.py trishuli budhi
python3 -m venv --system-site-packages venv-snap && venv-snap/bin/pip install snapml==1.17.2
apt-get download libzdnn0 && dpkg -x libzdnn0_*.deb zdnn/root
SNAPML_ZDNN_LIB=$PWD/zdnn/root/usr/lib/s390x-linux-gnu/libzdnn.so.0 EVAC_BUILD_DIR=$PWD/build \
  timeout 280 venv-snap/bin/python -W ignore scripts/nnpa/bench_cells.py
```
