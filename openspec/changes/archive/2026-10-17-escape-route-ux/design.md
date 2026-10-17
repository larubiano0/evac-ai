## Context

Prediction mode answers "where do I go from here, at minute t?" with a time-dependent Dijkstra (`engine/escape_search.c`) driven by `FloodScenario._best` in `engine/escape.py`:

- A risk ladder `TAUS = [0.01 … 0.90]` is tried in order. At level τ, a cell with `p > τ` cannot be entered once the flood has reached it.
- At each τ the search **stops at the first settled cell with `p ≤ τ`**, and that cell becomes the destination.
- Path confidence = `1 − max(risk)`, where risk counts only for cells reached after the flood, plus the destination itself.

The page (`web/predict.html`) then draws one polyline per 30 m step, coloured by that step's end point (`unsafe ? red : green`). It also draws a red dot on every unsafe point, a green zone polygon built at the final τ (so it can include ground above `UNSAFE_P = 0.10`), a "Go here" pin, a dashed grey backup, and refits the map after every click (`fitted !== you` compares object identity, so it is always true).

What we saw in a real answer: a route about 60 m long, green then red, ending on a 15% cell at the edge of the red band. On that spot sat a "Go here" pin, a red "Unsafe" dot and a green zone, with 0-5% ground about 100 m further uphill.

Already fixed and not part of this change: stale responses overwriting newer clicks (the `seq` guard in `escape()`), and the overlay's green meaning `p ≤ UNSAFE_P`.

## Goals / Non-Goals

**Goals:**
- Every route answer reads as one instruction: one line, one direction, one destination, at most one hazard. Urgency is shown in the card.
- The destination is always the closest safe place (P(destroyed) ≤ `UNSAFE_P`), not the first cell that clears τ.
- The answer says WALK / HURRY / RUN based on time to spare.
- Pin, zone, overlay and card never contradict each other.
- A repeat click on the same spot gives the same answer.

**Non-Goals:**
- Changing the damage model, flood presets, `UNSAFE_P`/`WILL_HIT_P`, or the τ ladder values.
- Stabilizing answers near nearest-goal boundaries (two neighbouring cells legitimately sending you to different places). Revisit if it still feels jumpy after the camera fix.
- The `viewer/` Three.js app and the `viewer-live-predict` change.

## Decisions

### D1. Closest safe place, always (engine)
Today one number, τ, controls two things:
- which risky cells you may enter after the flood (passability);
- where you may stop (goal `p ≤ τ`).

When the ladder climbs to τ = 0.15 to get past a risky stretch, it also accepts a 15% cell as the destination. That is the bug in the screenshot.

Split the two:
- **Goal:** the first settled cell with `p ≤ UNSAFE_P`, which is the closest safe ground by walking time (Dijkstra order).
- **Passability:** the ladder τ, unchanged. Try τ = 0.01, 0.02, … and take the first τ at which safe ground is reachable. That gives the least risky passage to the closest safe place.
- **Fallback:** only if no τ reaches safe ground, use today's behaviour (goal `p ≤ τ`) and return `destination_safe = false`. The `no_route` / `ignore_flood` fallback is unchanged.

Change to `escape_search.c`: add a trailing `double goal_p` parameter, and make the goal test `p[u] <= goal_p`. The current behaviour is `goal_p = tau`.

Alternatives considered:
- A two-phase "safest within +N min" search: it picks the safest ground, not the closest safe place, and needs an arbitrary budget. Rejected per team direction: always show the closest place in safety.
- A lexicographic score inside C: more C changes for no gain over the split thresholds.

### D1b. Urgency: WALK / HURRY / RUN (engine + UI)
`urgency` is computed from the path's tightest margin `m = min_margin_before_flood_min`, i.e. flood arrival minus your arrival, over risky points on the path and your own spot:

| Value | Condition | Banner |
|---|---|---|
| `"walk"` | `m` is None (nothing risky to race) or `m ≥ HURRY_MIN` (10) | "Leave now. Walk to safe ground (N min)." |
| `"hurry"` | `RUN_MIN` (3) ≤ `m` < `HURRY_MIN` | "Hurry. N min to safe ground." |
| `"run"` | `m` < `RUN_MIN`, the flood reaches you before you can finish, or the flood is already here | "**RUN** to safe ground. N min." |

- `HURRY_MIN = 10` and `RUN_MIN = 3` are policy numbers, explicit beside `UNSAFE_P`.
- `no_route` keeps its own "Climb now" wording, with urgency `run`.
- `safe_here` / `outside` have no urgency.

The page shows the urgency word as the banner's first, largest line.

### D2. Zone threshold follows the destination
- If the destination's `p ≤ UNSAFE_P`: `destination_safe = true`, and the zone is built at `UNSAFE_P`, so the green zone matches the green overlay exactly.
- Otherwise: `destination_safe = false`, and the zone is built at `p_dest + 0.01` and labelled "least risky ground".

`_zone`'s `max_risk` stays in the GeoJSON.

### D3. One hazard per route
`hazard` = among path points with `p > UNSAFE_P`:
- if any were reached after the flood, the riskiest one (`kind: "flooded"`);
- else the one with the smallest margin `a − t` (`kind: "race"`, `pass_before_min = a − t0`, minutes from now);
- `null` if there is none.

The destination is never the hazard; its risk is shown on the pin. `unsafe_points` stays for compatibility and tooltips but is no longer drawn as dots.

### D4. Route drawing
- The main route is drawn as one polyline with a casing: a dark `#111` line at 9 px under a white line at 5 px, plus a white animated dash overlay showing the direction of travel (CSS `stroke-dashoffset` animation via `className`; no new library).
- **Why white/dark:** the overlay uses green/orange/red, the flood path is blue `#4c9dff`, and bridges use the risk colours. Any of those for the route would blend in.
- Respect `prefers-reduced-motion` (no animation, static chevrons via dashes).

### D5. Destination and card
- **Pin labels:**
  - `destination_safe`: "Safe ground", with a green zone.
  - otherwise: "Best ground you can reach · N% risk", with an amber zone (`#f2a33a`).
  - `no_route`: the existing red-banner wording; the zone is amber.
- Remove the per-segment legend entries and replace them with "━ your way out · ◉ safe ground · ⚠ hazard".
- The hazard marker is a ⚠ divIcon with a permanent short tooltip: "Pass before 14 min" for `race`, "May already be flooded (N%)" for `flooded`.

### D6. Backup route
Not drawn by default. The card shows a "Show another way (N min)" toggle that draws the backup as a thin grey dashed line, with no hazard or destination dressing.

### D7. Camera
Replace `fitted !== you` with: fit only if the route bounds are not fully inside `map.getBounds()`, or the zoom is below 13. Never refit on a time-slider re-query. As a result, a second click on the same pixel hits the same place unless the first answer was off-screen.

### D8. Overlay dimming
While a route is drawn, set the overlay opacity from 0.85 to 0.45. Restore it when the answer has no route (`outside`, `safe_here`) or the scenario reloads.

## Risks / Trade-offs

- **[Safe ground needs a riskier passage]** Requiring a safe destination can raise τ, meaning the path crosses riskier points after the flood than it would to reach a 15% cell. → This is the agreed trade-off (end safe). The single hazard marker and RUN urgency make the risky crossing explicit, and the backup route offers the alternative.
- **[Latency]** The goal is reached later, so more cells are settled. → It is bounded by the existing 4 km window. Measure on s390x and keep it under 50 ms.
- **[White route on light basemap]** → The dark casing keeps contrast on both the light topo tiles and the dimmed overlay.
- **[Hiding unsafe points]** One marker hides the others. → All of them stay in the API and the tooltip lists the count. The single marker is the one that decides whether you make it.

## Migration Plan

Additive API keys and a C function with a new trailing parameter (the `.so` is rebuilt automatically when its mtime changes). Deploy by pulling on the VM and restarting the 8001 server. Roll back with `git revert`.

## Open Questions

- Are `HURRY_MIN = 10` / `RUN_MIN = 3` the right cut-offs? (They are policy, so we can tune them in the demo.)
- Should `safe_here` answers also show nearby safer ground ("you can stay; safer ground 3 min uphill")?

## Addendum: time-aware destination choice (approved by Lucas)

Replaces the "least risky crossing first, however long" rule of D1. With the ladder, a click at 84.93884, 28.46081 (oct11, t=0, flood 2 min away) was sent on a 128 min, +407 m climb, while a 32 min way existed.

### D9. Feasibility along the whole route
A risky cell (P > `UNSAFE_P`) can only be passed if you reach it before the flood does (arrival grid `A`), anywhere on the route, not only at your own spot. Safe cells can be passed at any time. The τ ladder is no longer used: the search always runs with τ = `UNSAFE_P`. `risk_ladder_tau` stays in the response (always `UNSAFE_P`) for compatibility.

### D10. Pace
- Walking: Tobler, as before.
- Running: `RUN_SPEEDUP` = 2 × walking speed for the first `RUN_LIMIT_MIN` = 5 minutes of the trip, then walking. An edge that straddles the 5-minute mark is split exactly. Arrival stays monotone in departure time, so Dijkstra stays exact.
- `escape_search.c` takes two more trailing parameters: `run_factor`, `run_min`. `goal_p < 0` means "never stop" (exhaustive), used for (c).

### D11. Choice
| | Condition | Destination | Urgency |
|---|---|---|---|
| a | safe ground reachable walking | closest safe ground (walking time) | walk / hurry / run from the margin, as before |
| b | else reachable at the running pace | closest safe ground (running time) | run |
| c | else | the lowest-P cell reachable before the flood at the running pace; ties (P to 3 decimals) → sooner | run, `destination_safe = false` |

If nothing reachable is safer than your own spot, the answer is `no_route` (unchanged fallback: least risky ground ignoring the flood). A route that arrives after the flood is never chosen over one in time.

New response keys (additive): `pace` (`walk`/`run`), `choice` (`closest_safe`/`safest_reachable`), `can_run`, and `walk_only`: when the answer relies on running, the same answer computed for someone who cannot run.

### D12. "I can't run"
`escape(..., can_run=False)` uses the walking pace only. Because `api/app.py` is not changed in this change, the page does not need a new request field: it shows `walk_only` when the toggle is on. (The page also sends `can_run`; today's API ignores the extra field. Passing it through is a one-line change in `api/app.py` for its owner, if wanted.) The card says "assumes you can run for about 5 min" whenever the running pace was used.

### Trade-offs
- Once the flood has passed your spot and every neighbouring cell is risky, nothing is reachable "before the flood" and the answer becomes `no_route` ("RUN uphill / climb now"). In the oct11 test points this happens for Jagat at t ≥ 30 and Soti at t ≥ 120.
- (c) can pick a cell only 30 m away when the flood is 1-2 minutes out: that is the honest answer ("the safest ground you can still reach").
