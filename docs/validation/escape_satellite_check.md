# Escape destinations vs satellite flood extents

`agent-lcpizani-ux`, Sat Oct 17 2026, on L1CC (s390x). Follow-up to [`escape_audit.md`](escape_audit.md), as asked there.

**Question:** when "Where do I go?" calls a place safe, did that ground stay dry in the real flood?

**Method:**
- Start points and times: the same 300 queries per valley as `audit_escape.py`.
- Engines compared: the engine before `predict-clarity` (`main` at 0c456c2) and the current one.
- Ground truth: the cell label from the satellite flood extents that `area_fb` is trained on.
  - Oct 11: UNOSAT FL20261011NPL, with MBRSC Sentinel-2 as a second product.
  - Aug 26: UNOSAT FL20260826NPL, with HOT as a second product.
- Script: [`escape_satellite_check.py`](escape_satellite_check.py). Raw numbers: [`escape_satellite_check.json`](escape_satellite_check.json).

## Results

| Called "safe", but the satellite saw it flooded | Before | Now (destination) | Now ("Go here" flag) |
|---|---|---|---|
| Oct 11 (UNOSAT) | 28 of 236 | **0 of 227** | **0 of 227** |
| Oct 11 (MBRSC) | 26 | **0** | **0** |
| Aug 26 (UNOSAT) | 19 of 254 | **7 of 238** | **5 of 238** |
| Aug 26 (HOT) | 40 | 32 | **10** |

## Trade-off

The new rule (below the planner's flood line = never safe) is cautious.
- Of the 85 Aug 26 spots the old engine called safe below the flood line, the satellite saw 75 stay dry.
- In those cases people are now sent somewhat further than strictly needed.
- On Oct 11, all 28 such spots really flooded.

## Audit re-run on the current engine

`audit_escape.py`, 300 queries per valley:

| Check | Oct 11 | Aug 26 |
|---|---|---|
| Called SAFE below the flood line | 0 % | 0 % |
| Destination below the flood line | 0.7 % | 3.7 % |
| Late at the early edge of the arrival band | 0 % | 0 % |
| Zone drawn at > 10 % risk | 0.7 % | 7.3 % |

Raw rows: `audit_escape_{budhi,trishuli}_ux.json`. `audit_escape_trishuli_ux_gohere.json` measures the "Go here" flag instead of the destination: within 60 m of really destroyed buildings 28.7 % (destination 33 %).
