# LinuxONE AI: the Telum on-chip AI accelerator (NNPA), measured

**What runs on the accelerator: 100 what-if floods in 2.7 s instead of 83 s.** A flood's height is uncertain (the
engine's own band is ±30%). Showing that uncertainty means scoring every 30 m cell under many flood heights:
100 heights × 126,528 Trishuli cells = **12.7 million predictions per map**. Today's model (300 boosted trees)
does that in 83 s on the VM's CPU. A neural stand-in for it, run on the z17's on-chip AI accelerator, does it in
**2.7 s (31× faster)**, and its uncertainty ranges match the tree model's within 0.01 on average. That turns
"how sure are we?" from a batch job into something a page can ask for live.

All numbers were measured on Sat Oct 17 2026 on our L1CC VM: IBM z17 (machine type 9175, `nnpa` CPU flag), 3 vCPU,
7.8 GB, Ubuntu 24.04, Python 3.12, numpy 1.26 (OpenBLAS), sklearn 1.4.1, Snap ML 1.17.2, IBM zDNN 1.0.1.

## What-if floods: 100 flood heights, CPU vs Telum accelerator

Scripts: [`engine/surrogate.py`](../engine/surrogate.py) (the stand-in, with CPU and accelerator paths),
[`scripts/nnpa/train_surrogate.py`](../scripts/nnpa/train_surrogate.py) (training),
[`scripts/nnpa/bench_ensemble.py`](../scripts/nnpa/bench_ensemble.py) (this table).

- **The stand-in:** a dense network (8 inputs → 256 → 256 → 256 → 1) distilled from area_fb, the production
  impacted-area model. Its training rows are the real corridor cells of both valleys, each with its flood
  height scaled at random within ±30%. It was trained on the CPU in 131 s; area_fb's calibration is folded into
  the last layer.
- **Held-out agreement with area_fb:** mean probability error 0.012 (95th percentile 0.057), correlation 0.9965,
  same flood/no-flood call on 99.0% of cells ([models/surrogate/metrics.json](../models/surrogate/metrics.json)).
- **What-if floods:** 100 flood heights drawn uniformly within ±30% of the scenario's own height. For each
  cell we keep the mean probability and the 10th–90th percentile range. All three runs use the same rows and the
  same code around the model.

| Trishuli, 126,528 cells × 100 flood heights (12.7 M rows) | Wall time | Rows/s | Range error vs exact (mean abs, low / high end) |
|---|---:|---:|---|
| Today: area_fb trees on the CPU (the exact answer) | 82.9 s | 153 k | — |
| Neural stand-in on the CPU (numpy) | 93.2 s | 136 k | 0.012 / 0.011 |
| **Neural stand-in on the Telum accelerator** | **2.7 s** | **4.7 M** | 0.012 / 0.011 |

- The accelerator is **31× faster than today's CPU path** and 35× faster than the same network on the CPU.
- On 2.2% of cells, either end of the range is off by more than 0.1.
- **Why it's useful:** 11% of the corridor cells have a 10–90% range wider than 0.2. That is ground whose risk
  depends on how big the flood turns out to be. A single run can't show which cells those are.

## Live in the app

The planner (`/planner`) has a **"What if the flood is bigger?"** card. It calls `GET /api/predict/whatif`
([`engine/whatif.py`](../engine/whatif.py)), which runs the 100 flood heights on the accelerator inside the
container. Measured in the container on the Budhi Oct 11 scenario: 98,652 cells × 101 flood heights =
**10.0 M predictions in 2.6 s** (`"backend": "nnpa"`), cached after the first call. The map shows in purple the
ground that is safe in this flood (P ≤ 0.10) but unsafe in a bigger one (90th-percentile P > 0.10): 0.91 km², a
fringe along the edge of the flood footprint. The image builds `zdnn_mlp.so` against Ubuntu's `libzdnn` (see
`Dockerfile`). Without the accelerator, the same endpoint falls back to numpy and says so.

## The gate: the same dense network, CPU vs Telum accelerator

Scripts: [`scripts/nnpa/zdnn_mlp.c`](../scripts/nnpa/zdnn_mlp.c) calls IBM's zDNN library directly
(`zdnn_matmul_bcast_op` + `zdnn_relu`/`zdnn_sigmoid` per layer). [`scripts/nnpa/bench_mlp.py`](../scripts/nnpa/bench_mlp.py)
runs the same weights and rows through numpy on the CPU (fp32, OpenBLAS, all 3 vCPUs). The accelerator time is
end to end: fp32 rows in, conversion to the accelerator's format, every layer, fp32 out. Weights are converted
once, as a server would do at start-up. Each figure is the best of 5 after a warm-up call, on 262,144 rows with 16
inputs.

| Network | CPU (numpy) | Telum accelerator | Speed-up | Throughput, CPU → accelerator | Max output difference |
|---|---:|---:|---:|---|---:|
| 16 → 64 → 64 → 1 | 0.090 s | 0.010 s | **9×** | 2.9 M → 26 M rows/s | 0.004 |
| 16 → 256 → 256 → 256 → 1 | 1.150 s | 0.062 s | **18×** | 0.23 M → 4.2 M rows/s (62 → 1,137 GFLOP/s) | 0.007 |
| 16 → 512 → 512 → 512 → 1 | 3.314 s | 0.149 s | **22×** | 79 k → 1.76 M rows/s (84 → 1,873 GFLOP/s) | 0.005 |

- The difference comes from the accelerator's 16-bit internal number format. It is well below what matters for
  a flood-risk probability.
- The accelerator is on the chip and isn't one of our 3 vCPUs. While it scores, the CPUs stay free to serve the
  app.

## Why not a single scenario: where its time goes (cProfile, cold `FloodScenario`)

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

## Why not our tree model: Snap ML trees, CPU vs NNPA

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
- An earlier synthetic test showed the same (0.44 s NNPA vs 0.05 s CPU for 23.6k rows).
- Why (our reading, not measured): Snap ML's zDNN path turns each tree into dense tensor operations. A depth-4 tree is only 15 comparisons per row. The CPU walks it in a few nanoseconds, while the tensor
  route pays for layout conversion and data movement on every call. The NNPA is built for large dense layers
  (LSTMs, transformers, wide MLPs), not for 8-feature shallow trees.

## What we did not do, and why

- **Moving the current single-scenario scoring to a neural net.** Inference is ≤ 0.67 s of a 12–67 s cold
  scenario, so the accelerator can't change that wait. Its use is the what-if workload at the top.
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

## The line for the video (0:55 beat)

> "A flood's height is never certain, so we score every spot on the map under a hundred possible floods. That's
> 12 million predictions. The z17's on-chip AI accelerator does it in under 3 seconds, 31 times faster than the
> processor."

## Reproduce (on the VM, in your own work directory)

```bash
apt-get download libzdnn0 libzdnn-dev && for d in libzdnn*.deb; do dpkg -x $d zdnn/root; done
Z=$PWD/zdnn/root/usr; gcc -O2 -shared -fPIC -I$Z/include scripts/nnpa/zdnn_mlp.c -L$Z/lib/s390x-linux-gnu -lzdnn -o build/zdnn_mlp.so
LD_LIBRARY_PATH=$Z/lib/s390x-linux-gnu python3 scripts/nnpa/bench_mlp.py build/zdnn_mlp.so 262144 16 256 3
EVAC_BUILD_DIR=$PWD/build timeout 600 python3 scripts/nnpa/train_surrogate.py
LD_LIBRARY_PATH=$Z/lib/s390x-linux-gnu EVAC_NNPA_LIB=$PWD/build/zdnn_mlp.so EVAC_BUILD_DIR=$PWD/build   timeout 420 python3 scripts/nnpa/bench_ensemble.py trishuli 100
EVAC_BUILD_DIR=$PWD/build timeout 300 python3 scripts/nnpa/profile_scenario.py trishuli budhi
python3 -m venv --system-site-packages venv-snap && venv-snap/bin/pip install snapml==1.17.2
SNAPML_ZDNN_LIB=$PWD/zdnn/root/usr/lib/s390x-linux-gnu/libzdnn.so.0 EVAC_BUILD_DIR=$PWD/build \
  timeout 280 venv-snap/bin/python -W ignore scripts/nnpa/bench_cells.py
```
