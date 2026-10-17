## 0. Coordination

- [ ] 0.1 `git pull --rebase`; update my row in AGENTS.md to "NOW: escape-route-ux (engine/escape.py, escape_search.c, web/predict.html)"; push the claim before coding

## 1. Engine: destination choice

- [ ] 1.1 `escape_search.c`: add a trailing `double goal_p` parameter; the goal test becomes `p[u] <= goal_p` (passability still uses `tau`)
- [ ] 1.2 `escape.py`: update the ctypes `argtypes`
- [ ] 1.3 `_best`: first pass over the ladder with `goal_p = UNSAFE_P` (closest safe place through the least risky passage); if no τ finds one, second pass with `goal_p = tau` (today's behaviour) and mark `destination_safe = false`
- [ ] 1.4 The backup search uses the same rule (closest safe place outside the 300 m exclusion)
- [ ] 1.5 Add `HURRY_MIN = 10`, `RUN_MIN = 3` next to the other policy numbers; compute `urgency` (walk/hurry/run) from `min_margin_before_flood_min` and your own spot's time to flood

## 2. Engine: response fields

- [ ] 2.1 Add `destination_safe` (destination p ≤ UNSAFE_P) to route results
- [ ] 2.2 `escape()`: zone threshold = UNSAFE_P if `destination_safe`, else p_dest + 0.01
- [ ] 2.3 `_route`: compute `hazard` (`flooded` riskiest after-flood point, else `race` smallest-margin point; never the destination); `pass_before_min` relative to t0
- [ ] 2.4 `_advice`: the headline starts with RUN / Hurry / Leave now from `urgency`; wording for a best-effort destination ("best ground you can reach, N% risk") and the hazard ("pass the point marked ⚠ before N min")

## 3. Engine: checks

- [ ] 3.1 Extend `scripts/damage/test_escape.py`: determinism (same query twice gives identical output), the destination is ≤ UNSAFE_P whenever any safe cell is reachable, `destination_safe` ⇒ `safe_zone.max_risk ≤ UNSAFE_P`, `hazard` is never the destination, urgency thresholds
- [ ] 3.2 Re-run the screenshot case (Budhi, oct11, the click near the 2160 m contour) and confirm the destination is the closest safe ground
- [ ] 3.3 Time escape queries on the VM (s390x): p50/p95 stay < 50 ms

## 4. Page: route drawing

- [ ] 4.1 Replace `drawPath` per-segment colouring with one cased polyline (dark 9 px under white 5 px) plus an animated dash overlay; add `prefers-reduced-motion` handling
- [ ] 4.2 Remove the red unsafe dots; draw one ⚠ divIcon from `r.hazard` with a permanent tooltip
- [ ] 4.3 Destination pin label and zone colour from `destination_safe` (green "Safe ground" / amber "Best ground you can reach · N% risk")
- [ ] 4.4 Backup hidden by default; "Show another way (N min)" toggle in the card draws it thin and grey dashed
- [ ] 4.5 Banner leads with WALK / HURRY / RUN (RUN in the danger style), then walk time and time to spare
- [ ] 4.6 Update the legend (way out / safe ground / best ground / ⚠ hazard / backup)

## 5. Page: camera and overlay

- [ ] 5.1 Replace the `fitted !== you` refit with "fit only if the answer bounds are not inside `map.getBounds()` or zoom < 13"; no refit on time-slider re-queries
- [ ] 5.2 Dim the overlay (0.85 → 0.45) while a route is shown; restore it on no-route answers and scenario reload

## 6. Verify and ship

- [ ] 6.1 Manual pass on the VM (port 8001): click the same spot twice (same route, map still); a risky route shows one line, one ⚠, a matching pin and zone; the backup toggle works
- [ ] 6.2 Screenshot before/after for the demo
- [ ] 6.3 Commit, push, and log in AGENTS.md
