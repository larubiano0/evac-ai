# Validation (packet D)

Owner `agent-aayush` · Sat Oct 17, 16:30–17:30 ET · all numbers computed on the L1CC LinuxONE VM.

How to reproduce: from a repo copy on the VM that has its **own** `data/` (r.walk writes GRASS rasters), run
`timeout 300 python3 docs/validation/run_oct11.py` and `AREA=trishuli timeout 300 python3 docs/validation/run_aug26.py`.
Raw outputs: [`validation/oct11_results.json`](validation/oct11_results.json), [`validation/aug26_results.json`](validation/aug26_results.json).
Damage-model numbers are **cited** from `agent-lcpizani`'s [`models/damage/metrics.json`](../models/damage/metrics.json) and
[`oct11_check.json`](../models/damage/oct11_check.json), not recomputed.

**Read this first.** Two events, five timed observations that can be placed on our grids, one set of volunteer damage
tags. These are case studies, not statistics. Where a number is in-sample or circular, the table says so.

---

## a. Arrival time: predicted vs. reported first arrival

**Method.** The arrival curve is piecewise linear in river km from the source, through (0 km, burst) and each
`use: "calibration"` observation, and it extrapolates past the last one at the last wave speed (`engine/flood.py`).
With all points used, the curve passes through every calibration point, so in-sample error is 0 by construction and
we don't report it. **Leave-one-out (LOO):** drop one point, rebuild the curve, predict the dropped point.
Negative error = predicted too **early** (the safe side). Positive = too **late** (dangerous).

| Event | Observation (river km) | Reported | LOO predicted | LOO error | Kind of prediction |
|---|---|---|---|---|---|
| Oct 11 | Jagat/Salleri (20.2) | 04:00 (+15 min) | 04:38 | **+38 min (late)** | interpolation between source and Arughat |
| Oct 11 | Arughat (62.5) | 06:30 (+165 min) | 04:31 | **−119 min (early)** | extrapolation from Jagat |
| Aug 26 | Syabrubesi gauge (14.5) | 08:50 (+13 min, upper bound) | 08:50 | **−0.1 min** | interpolation |
| Aug 26 | Betrawati gauge (48.1) | 09:20 (+43 min) | 09:45 | **+25 min (late)** | interpolation |
| Aug 26 | Malekhu gauge (109.5) | 11:26 (+169 min, danger level crossed) | 10:15 | **−71 min (early)** | extrapolation |

- **Oct 11 has too few points for a real LOO.** Only two timed observations are usable, so holding one out leaves a
  single constant-speed line from the source. The Oct 11 rows show how badly a constant speed fits: the wave covered the
  first 20 km at ~80 km/h and the next 42 km at ~17 km/h.
- **Pattern:** extrapolating past the last gauge erred **early** both times (−71, −119 min). Interpolating erred **late**
  by up to 38 min. Slack uses the early edge of a ±25 % band (`arrival × 0.75`), which absorbs the Betrawati miss
  (early edge 09:28 vs. 09:20 reported, still 8 min late) but not the Jagat one.
- **Checks against excluded points:**
  - Soti (Oct 11, 07:30 reported): all-points curve gives 05:43. The report is probably the second wave (Arughat's second wave was 07:50).
  - Trishuli school (Aug 26, 09:20): curve gives 09:36 (+16 min). Its early edge is 09:21.
  - Mugling, Kali Khola and Devghat are outside the Trishuli grid (see the fix below).
- **Cross-event transfer fails.** Applying the Oct 11 curve to Aug 26 predicts Betrawati **+71 min** and Malekhu
  **+163 min** late. Debris flows from glacier collapses and dam bursts travel at very different speeds. This is why
  prediction mode keeps one preset per flood type, and why a real deployment must recalibrate on the first upstream
  gauge or sighting.

**Fixed while doing this:** the Aug 26 Kali Khola (84.546) and Devghat (84.43) gauges are west of the
`data/proc_trishuli` grid edge (~84.735). `Terrain.rc` has no bounds check, so `km_of` wrapped silently (Kali Khola
came back as 66 km). `Scenario.km_of` now returns NaN outside the grid, and `calibrate_from_replay` skips NaN points.
It raises a clear error if no height point is left. Both gauges are marked `use: "excluded"` in `replay/aug26.json`, with a note.

## b. Oct 11 settlements: predicted at-risk vs. reported destroyed/inundated

**Method.** `Scenario.settlements()` with the Oct 11 calibration. A settlement is at risk if any building assigned to
it (nearest OSM place within 3 km) is in the conservative footprint. It is red if minimum slack is < 0. Reported places
come from `replay/oct11.json` `damage_reported`. Names were matched to OSM place nodes by hand (e.g. "Arughat" =
OSM "Ārughāt Bāzār").

| Reported destroyed/inundated | OSM place | At risk? | 03:30 relay | 06:40 SMS |
|---|---|---|---|---|
| Paiyu | not in OSM | n/a | | |
| Bagar | Jagat Bagar (km 23.5) | ✅ | green (+19 min) | red (−171) |
| Ghattekhola | Ghatte Khola (15.7) | ✅ | green (+15) | red (−175) |
| Jagat | Jagat (20.2) | ✅ | green (+19) | red (−171) |
| Salleri | Salleri (18.9) | ✅ | green (+16) | red (−174) |
| Sirdibas (1 house) | Sirdibas (16.4) | ✅ | green (+15) | red (−175) |
| Nyakphedi hotels | Nyak Phedi (8.5) | ✅ | amber (+13) | red (−177) |
| Machhakhola (lower) | Machhakhola (36.6) | ✅ | green (+60) | red (−130) |
| Dobhan bazaar | Dobhan (27.6) | ✅ | green (+32) | red (−158) |
| Soti | no OSM place; reported point at km 49.3 | ❌ **miss** | | |
| Arughat (some houses) | Ārughāt Bāzār (62.0) | ✅ | green (+128) | red (−62) |
| Shanti Bazaar (40 of 42 houses) | outside the Budhi Gandaki grid | n/a | | |
| Syauli Bazaar | not in OSM | n/a | | |
| **Reported safe:** Philim | Philim (14.3) | ⚠️ 1 building | green (+16) | red (−174) |

- **Recall: 9 of the 10 reported places we can locate are flagged** (miss: Soti). Three can't be scored: two aren't in
  OSM, and Shanti Bazaar is outside our terrain build.
- **All 9 hits are red at 06:40 and none at 03:30.**
- **Over-prediction:** 20 settlements are flagged in total. The 11 not on the reported list are Konzer, Saglet,
  Tatopani, Khorlabesi, Labsibot, Thumi, Arkhet Bazar, Aruarbang, Aaru Chanuate, Dhawa and Philim. The reports list the
  worst-hit places, so "not reported" isn't "undamaged". Philim is the one explicit contradiction: the village node sits
  150 m above the river, but one riverside building assigned to it is in the footprint.
- **Buildings:** the footprint holds 365 OSM buildings, vs. ~62–72 houses reported (35–45 destroyed + 27 partly
  damaged). The damage model v2 brings the expected count down to **146** (`oct11_check.json`). OSM counts sheds and
  outbuildings, so part of the gap is the definition of a building.

## c. Bridges: predicted at risk vs. reported lost (Oct 11)

**Method.** `Scenario.bridges_at_risk()`: an OSM bridge is at risk if its midpoint cell is in the conservative
footprint or on the flood channel. Matching of reported losses to OSM bridges and model ranks are cited from
`models/damage/oct11_check.json` (v2, 49 corridor bridges).

| Reported lost | Engine flags a matching OSM bridge? | Damage model v2 best rank (of 49) |
|---|---|---|
| Nyakchet–Sirdibas suspension | ✅ (bridges near Nyak Phedi, km 9.1/9.5) | #3 |
| Machhakhola–Kerauja suspension | ✅ (km 36.6) | #29 |
| Dobhan Bailey | ✅ (km 27.6/28.1) | **#1** |
| Nyakchet–Philim Bazar | ✅ (same Nyak Phedi bridges) | #3 |
| Soti iron motorable | ❌ not in OSM. The Manaslu Circuit bridge 228 m away is not flagged (HAND 28 m). A footbridge ~900 m upstream is (#4) | #4 (footbridge) |
| Arughat concrete (1 of 3 spans) | ❌ | #14 |

- **4 of 6 reported losses are matched** (3 distinct locations, since two reports map to the same Nyak Phedi
  bridges). The engine flags **18 of 220** OSM bridges in the build (49 lie in the 500 m corridor).
- **Root causes of the misses** (`models/damage/README.md`):
  - **Arughat:** the 30 m D8 channel runs ≥175 m from the real river, so HAND at the bridge is 17 m against a ~6 m
    flood line. The fix is burning the OSM river into the DEM in `pipeline/`.
  - **Soti:** the motorable bridge isn't mapped in OSM.

## d. Aug 26 footprint vs. OSM damage tags

**Method.** Labels are OSM buildings tagged `damage:event=2026NepalFlood` (plus the Chinese-tagged event) with damage
`destroyed` or `damaged`. In the Trishuli grid that's **3,111 affected, 2,764 destroyed**, and all of them drain to the
121 km flood path. There's no gauge height inside this grid, so the flood line is `agent-lcpizani`'s reconstruction from
damage marks: p90 HAND of affected buildings per 5 km. **Using it on the same buildings is circular**, so the honest
rows are the cross-side ones: fit the line on one half of the river (split at km 51.8, ±1 km gap), test on the other half.
Footprint = HAND ≤ height × 1.3 (the engine's conservative band).

| Variant | Destroyed inside footprint | Affected inside | Footprint buildings with no damage tag |
|---|---|---|---|
| **Cross-side: line fitted upstream → test downstream** | **83 %** (of 1,191) | 78 % | **21 %** (of 1,506) |
| **Cross-side: line fitted downstream → test upstream** | **75 %** (of 1,484) | 75 % | **49 %** (of 2,169) |
| In-sample, conservative band (circular) | 98 % | 98 % | 54 % (of 6,560) |
| In-sample, mid line (circular) | 92 % | 91 % | 40 % (of 4,718) |

- **"Untagged" is not "undamaged".** Volunteers tagged from post-event imagery, and damage under trees or in narrow
  gorges is missed.
- **Damage model vs. this rule** (cited from `metrics.json`, 500 m corridor, same split):
  - Train upstream → test downstream: footprint rule ROC AUC **0.713**, model v2 **0.968**. In the top-k, v2 flags
    **1,043 of 1,474** affected rows vs. 672 for the rule.
  - Train downstream → test upstream: rule **0.699**, model v1 **0.818**.

## e. Headline: people without time, community vs. official trigger

**Method.** Slack per building = early arrival − (warning + 5 min dissemination + walk to safe ground via r.walk).
People = 4 per OSM building in the conservative footprint (assumption), plus 100 stranded trekkers at Jagat on Oct 11.
"Without time" = people in buildings with slack < 0.

| Oct 11 trigger | Time | People without time (of ~1,456 at risk) | Red / amber / green settlements (of 20) |
|---|---|---|---|
| **Community relay** reaches Dharche | 03:30 | **0** | 0 / 2 / 18 |
| Police informed by hotel operators | 05:30 | 1,340 | 17 / 2 / 1 |
| NDRRMA official information | 06:20 | 1,456 | 20 / 0 / 0 |
| **Official SMS** | 06:40 | **1,456 (all)** | 20 / 0 / 0 |

Caveat: the 03:30 relay is **15 min before** the modelled burst (03:45; reported band 03:30–04:25), so slack is
positive everywhere. With a 04:25 burst the relay would still lead by an hour or more downstream.

| Aug 26 trigger | Time | People without time (of ~20,876 at risk) | Red settlements (of 44) |
|---|---|---|---|
| Seismic signal (if it had triggered an instant alert) | 08:37 | 1,596 | 7 (all within 16 km of the border) |
| DHM learns by phone | 09:00 | 7,264 | 24 |
| Upstream phone calls reach Trishuli school | 09:10 | 10,884 | 26 |
| **Official SMS** | 09:15 | **12,324** | 27 (down to Bidur, km 58) |
| Downstream forecast | 10:28 | 20,356 | 38 |

Aug 26 caveats:
- The flood line is in-sample (d), and the footprint holds 5,219 buildings at 4 people each.
- The engine says who **had no time**, not who died. The reported toll was ~1,454–1,497 dead and 5,285–6,000 missing.
- The point that survives every caveat: by the time the 09:15 SMS went out, the flood had already passed Syabrubesi
  (≤08:50) and was minutes from Betrawati (09:20). An alert at the 08:37 seismic signal would have cut the number
  without time by ~87 % in this model.

## f. Latency on L1CC (3 vCPU shared with another agent's jobs, bare metal, system Python)

| Operation | Time | Source |
|---|---|---|
| Load the Budhi Gandaki valley (112,515 buildings, 220 bridges) | 1.1 s | run_oct11 |
| **New scenario**, Oct 11 (path, HAND, footprint, r.walk on 3.7 M cells) | **5.1 s** (r.walk 4.7 s) | run_oct11 |
| **New trigger** (pin dropped 10 km downstream, reused envelope) incl. full payload | **5.2 s** | run_oct11 |
| **Cached** scenario → full payload (20 settlements, EN+NE alerts, bridges, path) | **0.033 s** | run_oct11, 3 runs |
| New scenario, Aug 26 (7.3 M cells, 386,668 buildings, 748 bridges) | 10.8 s (r.walk 9.4 s) | run_aug26 |
| Peak memory, Oct 11 run | 0.9 GB Python + 0.76 GB GRASS | run_oct11 |
| Damage model: score 3,727 corridor buildings + 49 bridges | 0.25 s (+0.5 s path context) | `oct11_check.json` |
| Damage model: train (Aug, 23.6k rows) | 0.4 s | `metrics.json` |
| Prediction mode: new flood scenario / cached | 3.0 s / 0.03 s | curl to :8001 on the VM |
| Prediction mode: **"where should I go?"** escape query | **2–5 ms** | curl to :8001 on the VM, 3 queries |

---

## Numbers for the video (safe to say)

- "With the villagers' 03:30 relay, **0** of about 1,456 people at risk are left without time. With the 06:40 SMS, **all** are."
- "It flags **9 of the 10** reported destroyed places we can map, and **4 of 6** lost bridges. It misses Soti and Arughat, and we know why."
- "On August 26, with the flood line fitted on one half of the river, the footprint holds **75–83 %** of destroyed
  buildings on the other half. The damage model ranks them with AUC **0.97**."
- "Holding out each gauge, arrival times were off by **0–38 min** between gauges, and **too early** (the safe side) past the last one."
- "A new scenario takes **about 5 seconds** on LinuxONE. A cached one takes 30 ms, and a 'where do I go' query takes under 5 ms."

Don't say: "accuracy X %" (there's no such single number), or that the model predicts deaths.
