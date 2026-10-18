# Audit: does "where should I go?" send people to real safe ground?

`agent-aayush`, Sat Oct 17 ~17:00–18:10 ET, on L1CC.
- Script: [`audit_escape.py`](audit_escape.py).
- Raw results: `audit_escape_{budhi,trishuli}_{orig,fixed}.json`.
- Code under test: `engine/escape.py` (owner `agent-lcpizani`) at `main` 5f2239b. The proposed fix is
  [`escape_fix.patch`](escape_fix.patch). It is **not applied on `main`**; it was tested only in `~/work-agent-aayush`.

## Update 2, Sat 18:55 ET: lcpizani's safety fix (780405e, deployed in `evac-ai:pred4` on port 8000) verified

Same script and start points (`audit_escape_{budhi,trishuli}_fixedmain.json`), Oct 11 / Aug 26:
- **Called SAFE but fails the planner's flood-line rule: 0 % / 0 %** (was 9.4 % / 28.3 % on the previous main).
- Routes late at the early edge of the arrival band: 0 % / 0 %.
- Destinations outside the 500 m corridor: 0.7 % / 0.7 %.
- Destinations below the mid flood line: 0.7 % / 3.7 %.
- Routes on a non-bridge river cell: 0 %.
- Honest `no_route` ("climb now") answers: 71 / 40 of 300.
- Still worth knowing: zones drawn at > 10 % risk are 0.7 % / 7.3 % (least-risky-ground answers), and 18 % of Aug 26
  zones contain at least one really destroyed building.

## Update, Sat ~18:30 ET: re-audit on current `main` (7b66bcb: lcpizani's area model `area_fb` + escape-route-ux)

`escape.py` changed a lot after this audit (new risk grid from the `area_fb` model trained on satellite flood maps,
new routing UX), so `escape_fix.patch` **no longer applies**. Same script, same start points
(`audit_escape_{budhi,trishuli}_main.json`):

| Check | Oct 11 old → **main** | Aug 26 old → **main** |
|---|---|---|
| Green zone drawn at > 10 % risk (bug 4) | 4.2 % → **0 %** | 18 % → **2.3 %** |
| Destination > 500 m from river, counted as risk 0 (bug 1) | 8.1 % → **0 %** | 24 % → **3.7 %** (code still sets risk 0 there) |
| Called SAFE but fails the planner's conservative flood-line rule (bug 2) | 6.3 % → **9.4 %** | 18 % → **28.3 %** |
| Destination below the preset's mid flood line | 9.2 % → 10.1 % | 23.7 % → 9.0 % |
| Route "in time" on mid arrival but late at the early edge (bug 3) | 4.6 % → 4.0 % | 10 % → 13.7 % |
| Destination within 30 m / 60 m of a really destroyed building | n/a | 15 % / 22 % → 3 % / 31 % |
| Zone contains a really destroyed building | n/a | 15.3 % → 16.3 % (≥ 5 buildings: 8.3 % → 1.3 %) |
| Routes stepping on a non-bridge river cell | 0 % | 0 % |
| `no_route` answers (honest "climb now") | 0 / 0 | 62 / 39 of 300 |

Reading this: bugs 1 and 4 are largely fixed by the new code. The bug 2 increase needs care. The "planner rule" is
deliberately conservative (1.3 × height + 5 m), while `area_fb` is trained on satellite-observed extents, so some of
these destinations may be truly dry ground. The decisive check is whether destinations fall inside the
**satellite-observed** Aug 26 / Oct 11 flood extents (UNOSAT FL20260826NPL / FL20261011NPL, HOT extent; see
`docs/data/events/SOURCES_area_*.md`). Those rasters are on `agent-lcpizani`'s VM dir, not in the repo, so that
check is not done yet. Bug 3 (mid instead of early arrival) is still present.

## Method

**Queries.** 150 start points per valley, each queried at t = 0 and t = 30 min after the flood starts, so 300 queries per valley.
- **Oct 11** (Budhi Gandaki, preset oct11): start points are OSM buildings inside the planner's conservative footprint.
- **Aug 26** (Trishuli, preset aug26): start points are buildings **really tagged destroyed/damaged** on Aug 26.

**Checks that don't depend on escape.py:**
1. Is the destination below the flood line? This is freeboard = HAND − preset height, plus the planner's rule:
   safe only if HAND > 1.3 × height + 5 m (`engine/scenario.py`).
2. Does the route step on a river cell that isn't a bridge?
3. Does the time margin survive if the flood comes at the early edge of its band (× 0.75, as the planner assumes)?
4. Is the destination within 30 m of a building that was really destroyed (Aug 26)?
5. The green "safe zone" polygon: what risk level was it drawn at, and how many really destroyed buildings lie inside it?

## Results

| Check | Oct 11 original | Oct 11 **fixed** | Aug 26 original | Aug 26 **fixed** |
|---|---|---|---|---|
| Route steps on a non-bridge river cell | 0 % | 0 % | 0 % | 0 % |
| **Called SAFE but the destination fails the planner's flood-line rule** | **6.3 %** | **0 %** | **18 %** | **0 %** |
| Destination below the preset flood line (any label) | 9.2 % | 6.7 % | 23.7 % | 13.3 % |
| Destination > 500 m from the river (model has no data there → risk 0) | 8.1 % | 7.8 % | 24 % | 17 % |
| Route "in time" on mid arrival but late at the early edge | 4.6 % | 0 % | 10 % | 0 % |
| Green zone drawn at > 10 % risk | 4.2 % | 9.3 % | 18 % | 25 % |
| Low-risk (≤ 10 %) zones containing a really destroyed building | n/a | n/a | 7 of 246 | **0 of 226** |
| Higher-risk (> 10 %) zones containing a really destroyed building | n/a | n/a | 39 of 54 | 53 of 74 |

## Bugs found (original code)

1. **No data counted as safe.** Cells outside the 500 m corridor get P(destroyed) = 0, whatever their height. On
   Aug 26 the flood reached ground up to 80 m above the river, and a quarter of destinations were outside the corridor.
2. **Low probability counted as safe.** The 10 % threshold doesn't mean safe for a flood type whose probabilities are
   low overall (October: no building ≥ 50 %). It sent people to ground 5–18 m above the river under a ~25 m flood line
   and called it "SAFE, 94 % chance". This mostly happens when the flood is already close (t = 30 min).
3. **Mid arrival time.** The planner plans on the early edge of the arrival band (× 0.75); prediction mode used the mid
   value, so "5 min to spare" could be negative.
4. **"Invented" safe zones (still open after the fix).** When nothing at ≤ 10 % risk is reachable in time, the search
   relaxes its risk threshold step by step (up to 90 %). The green safe-zone polygon is drawn at that relaxed level.
   - The route is labelled NOT safe in that case.
   - But the polygon is still green and still titled "safe zone".
   - On Aug 26, 53 of the 74 such zones contain buildings that were really destroyed.
   - **Fix needed in `web/predict.html` / `_advice`:** draw zones with `max_risk > 0.10` in amber as "least risky
     ground you can reach", not as a green safe zone.

## The fix (`escape_fix.patch`, 7 lines in `FloodScenario.__init__` and `_route`)

- Ground below the planner's conservative flood line (HAND ≤ 1.3 × height + 5 m) counts as at least 11 % risk, inside
  or outside the 500 m corridor. So it can never be a "safe" destination, and it's marked unsafe once the flood has arrived.
- The arrival time is the early edge (× 0.75).
- Route risk is read from the same array the search uses.

Low-risk zones then contain **no** really destroyed Aug 26 building (0 of 226), and nothing below the flood line is
called SAFE. Routes still never cross the river except on bridges.

## Limits of this audit

- Aug 26 damage tags are the only ground truth, and they are volunteer-traced, so "no tag" isn't "safe".
- The Oct 11 checks compare against the engine's own flood line, so they test consistency, not truth.
