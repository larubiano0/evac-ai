# LinuxONE AI: the Telum on-chip AI accelerator (NNPA), measured

**Verdict (Sat 20:45): GO for dense neural networks, NO-GO for our tree model.** The same neural network runs
**18× faster on the z17's on-chip AI accelerator than on the VM's CPU** (22× at 512 wide, 9× even at 64 wide),
with outputs within 0.007. Our current 300-tree model is the wrong shape for the chip: it runs 1.5–6× *slower*
there (sections 1–2). So the accelerator gets the job it is built for, a neural stand-in for the flood model that
scores many what-if floods at once (section 0; work in progress).

All numbers were measured on Sat Oct 17 2026 on our L1CC VM: IBM z17 (machine type 9175, `nnpa` CPU flag), 3 vCPU,
7.8 GB, Ubuntu 24.04, Python 3.12, numpy 1.26 (OpenBLAS), sklearn 1.4.1, Snap ML 1.17.2, IBM zDNN 1.0.1.

## 0. Dense neural network: CPU vs Telum accelerator (the gate)

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

- **Moving the current single-scenario scoring to a neural net.** Inference is ≤ 0.67 s of a 12–67 s cold
  scenario, so the accelerator can't change that wait. Its use is the many-scenario workload in section 0.
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

> "The z17 has an AI accelerator on the chip. On the same neural network it scores our map 18 times faster than
> the processor."

## Reproduce (on the VM, in your own work directory)

```bash
apt-get download libzdnn0 libzdnn-dev && for d in libzdnn*.deb; do dpkg -x $d zdnn/root; done
Z=$PWD/zdnn/root/usr; gcc -O2 -shared -fPIC -I$Z/include scripts/nnpa/zdnn_mlp.c -L$Z/lib/s390x-linux-gnu -lzdnn -o build/zdnn_mlp.so
LD_LIBRARY_PATH=$Z/lib/s390x-linux-gnu python3 scripts/nnpa/bench_mlp.py build/zdnn_mlp.so 262144 16 256 3
EVAC_BUILD_DIR=$PWD/build timeout 300 python3 scripts/nnpa/profile_scenario.py trishuli budhi
python3 -m venv --system-site-packages venv-snap && venv-snap/bin/pip install snapml==1.17.2
SNAPML_ZDNN_LIB=$PWD/zdnn/root/usr/lib/s390x-linux-gnu/libzdnn.so.0 EVAC_BUILD_DIR=$PWD/build \
  timeout 280 venv-snap/bin/python -W ignore scripts/nnpa/bench_cells.py
```
