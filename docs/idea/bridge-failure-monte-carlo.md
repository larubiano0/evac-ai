# Bridge/Tunnel Failure Probability: Monte Carlo Approach

Context file for later work. Goal: for an uncertain upstream flood trigger (landslide-dam burst, avalanche), estimate a **probability array, `P[b]`, of each bottleneck (bridge or tunnel) failing**, fast enough to run live (target: under 10 s per valley on L1CC, CPU only, numpy and scipy).

Related: `docs/idea/project-plan.md` (P1 bridge bottleneck check, P1 damage model), `docs/idea/nepal-disaster-research.md` (event timelines and bridge losses).

---

## Core idea

**Don't run a 3D, 2D or CFD flood simulation for each sample.** HEC-RAS 2D and r.avaflow take minutes to hours per run, probably won't install on s390x, and are out of scope in the plan (§4.3).

Instead:
1. **Use the 3D terrain once, offline**, to build a small lookup table for each bridge.
2. Each Monte Carlo sample is then about 10 vectorized numpy operations.
3. 100k samples × about 50 bridges takes under 1 s.

## Pipeline

### 1. Precompute once per valley (DEM + OSM)
For each bridge or tunnel `b`:
- **River distance** from each possible trigger point, using the river graph (networkx on OSM waterways).
- **Cross-section at the bridge:** cut a line perpendicular to the river in the DEM, giving width as a function of height.
- **Rating curve, Q → (depth h, velocity v):** use Manning's equation on that cross-section, with the slope from the DEM. Store it as an array (e.g. 200 flow values).
- **Bridge attributes:** deck height above the riverbed, type (suspension, Bailey, concrete/motorable) and span. Use OSM tags where they exist (`bridge:structure`, `layer`, etc.). Otherwise use assumptions based on type, and **sample them as uncertain inputs**.

### 2. Sample the initial conditions
Use quasi-random sampling (`scipy.stats.qmc.Sobol` or Latin hypercube), which converges faster than plain random sampling. Sample:
- Trigger location along the river
- Released volume V (log-uniform, roughly 1e5–1e8 m³)
- Peak outflow at the breach, Q0, from an empirical dam-break formula (Froehlich, or Walder & O'Connor), with its scatter
- How fast the peak shrinks downstream (attenuation length L)
- Manning roughness n
- Debris concentration (debris raises the water level)
- Each bridge's strength (deck height, force it can withstand)

### 3. Physics for each sample (vectorized, no grid simulation)
```
Q_b     = Q0 * exp(-dist_b / L)          # peak flow when it reaches bridge b
h_b,v_b = interp(rating_curve_b, Q_b)    # water depth and speed at bridge b
F_b     = 0.5*rho*Cd*A(h_b)*v_b**2       # force of the water on the bridge
```

### 4. Decide whether each bridge fails
- Hard rule: overtopped (`h_b > deck_b`) or `F_b > capacity_b`, **or**
- A **fragility curve**, a smooth probability of failure:
  `P(fail) = sigmoid(a_type + β1·(h − deck) + β2·v²)`
- **Calibrate it on real outcomes** (this is the predictive ML component):
  - Aug 26 Bhotekoshi–Trishuli: 68 suspension and 41 motorable bridges damaged (33 suspension bridges beyond repair).
  - Oct 11 Budhi Gandaki: at least 6 bridges lost (3 suspension, 1 Bailey, 2 motorable), including the Soti iron bridge and one span at Arughat.
  - Validate by fitting on one event and testing on the other.

### 5. Output
```python
fail = rng.random((N, B)) < p_fail      # N×B array of yes/no outcomes
P    = fail.mean(axis=0)                # probability array, one value per bridge
se   = np.sqrt(P*(1-P)/N)               # Monte Carlo error; N=10k gives about ±0.5%
```
Keeping the full N×B array also gives:
- **Joint failures:** e.g. P(both bridges into a village fail), meaning the village is cut off.
- **Route cut-off:** for each sample, remove the failed bridges from the road/trail graph and check connectivity. That gives **P(isolated) per settlement**.
- **Live conditioning:** once a report pins the trigger location, fix it and resample only the other uncertain inputs. It still runs in under 1 s.

## Why it's fast
- The terrain work (cross-sections, rating curves, distances) happens once, offline.
- Each sample is about 10 numpy operations, run as arrays over all samples at once. No Python loops, no grid stepping.
- Sobol sampling plus a convergence estimate means 10k–50k samples are enough.
- It only uses numpy and scipy (plus networkx), which matches the L1CC constraints (no GDAL, rasterio or numba).

## Limitations (for the README)
- A 30 m DEM is coarse for cross-sections in narrow gorges, and bridge deck heights are mostly unknown. Sample these uncertainties; don't fix them.
- The model uses only the peak flow. It ignores the multiple waves on Oct 11 and the debris blockage that builds up against bridges.
- Few calibration examples (on the order of 100 damaged bridges).
- Tunnels are rare in these corridors. Treat them as road segments with a flooding threshold at the entrance.

## Integration with the main plan
- Extends the **P1 bridge bottleneck check** and the **P1 damage model**.
- Feed the probability that a bridge survives until the flood arrives into the time-to-safety Dijkstra: allow a crossing only if that probability is above a threshold (alongside the existing rule that the bridge must be reached before the flood).
- Suggested modules: `precompute_bridges.py` (cross-sections and rating curves from the DEM) and `bridge_mc.py` (sampling, vectorized physics, fragility curves, P array, P(isolated)).
