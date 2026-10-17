## Why

In prediction mode (`/predict`) the "where do I go" answer is hard to read and sometimes wrong in the way that matters most. The route is drawn as green and red pieces that look like two routes. A "Go here" pin, a green "safe zone" and a red "Unsafe 15%" dot can sit on the same spot. The search often stops on the first cell that is just good enough, at the edge of the red band, even though clearly safer ground is a short walk further. The map also re-zooms after every click, so clicking the same spot on screen asks about a different place and returns a different route. Someone evacuating needs one clear instruction: this way, this far, this much time.

## What Changes

- **Engine: always go to the closest safe place.** The destination must be safe ground (P(destroyed) ≤ `UNSAFE_P`), and it is the closest such ground by walking time. The risk ladder now only decides which risky points the path may cross on the way. It no longer lowers the bar for where you end up. Only when no safe ground can be reached at all does the answer fall back to the least risky ground.
- **Engine + UI: say RUN when time is short.** The walk time is compared with the time before the flood reaches the path's tightest point. With plenty of margin the answer says "Leave now, walk"; with little margin it says "Hurry"; with almost none, or when the flood gets there first, it says **RUN**. Additive key `urgency`.
- **Engine: the zone agrees with the destination.** The safe zone is built from ground at or below `UNSAFE_P` when the destination is safe. Otherwise it is labelled "least risky ground", and the response says which case applies (`destination_safe`).
- **Engine: one hazard per route.** The response names at most one hazard on the path (the point with the least time to spare, or the riskiest point reached after the flood) with a "pass before" time. Additive key `hazard`; the existing `unsafe_points` key stays.
- **UI: one route, one colour.** The main route is a single continuous line in a colour that is not in the risk palette (white with a dark outline), with an animated direction of travel. No per-segment green/red.
- **UI: one destination label.** The pin reads "Safe ground" when `destination_safe`, and "Best ground you can reach (N% risk)" in amber otherwise. No red dot on the destination, and the zone styling matches the label.
- **UI: one hazard marker** with its instruction ("⚠ pass here before 14 min") instead of red segments and dots.
- **UI: urgency goes in the result card banner** (WALK / HURRY / RUN, walk time, time to spare), not in line colours.
- **UI: the backup route is secondary.** It is hidden by default and shown through "Show another way" in the card.
- **UI: a stable camera.** The map only refits when the new route is not fully in view, so a repeat click on the same spot asks about the same place.
- **UI: the risk overlay is dimmed** while a route is shown.

No API breaking changes: all new response keys are additive.

## Capabilities

### New Capabilities
- `escape-destination`: how the prediction-mode search chooses the destination, the safe-zone polygon and the single route hazard.
- `escape-route-display`: how the prediction page draws a route answer (line, destination, hazard, backup, camera, overlay).

### Modified Capabilities
(none: `openspec/specs/` has no prediction-mode specs yet)

## Impact

- `engine/escape_search.c`: a separate goal threshold, so passability (τ) and "where you may stop" (`UNSAFE_P`) are independent.
- `engine/escape.py`: `_best` (destination choice), `_zone` threshold, new `destination_safe`, `hazard` and `urgency` keys, `_advice` wording.
- `web/predict.html`: `drawPath`, `draw`, legend, camera refit, backup toggle, overlay opacity.
- `api/app.py`: no change (it passes `S.escape()` through).
- Performance: each escape query is currently 2-5 ms on s390x. Searching on to the closest safe ground settles more cells, but it must stay well under 100 ms.
