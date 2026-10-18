## Context

Prediction mode (`engine/escape.py`) already holds, for a flood scenario:
- `p`: the chance each 30 m square is hit (area model `area_fb`);
- `A`: the minutes until the flood reaches each square;
- an escape search that, from any point, finds the closest safe ground (P ≤ 0.10) reachable before the flood. With `escape-route-ux` it also handles a short running burst and a `can_run` flag.

One query takes ~3 ms on the LinuxONE VM. Alerts exist only as generic per-settlement texts (`engine/alerts.py`, EN + NE, Nepali review pending).
Status: **idea, not started**.

## Goals / Non-Goals

**Goals:**
- A per-household leave-by time that accounts for that household's pace and the flood's timing along the whole route, with a 10-minute buffer.
- One clear alert per household, sent at the right moment.
- A short list of who cannot get out alone, for responders.
- Collect as little personal data as possible.

**Non-Goals:**
- Live tracking of people's phones (we use the home location only).
- Medical or disability records.
- Choosing an SMS provider or app store work.
- Shelter capacity or crowding on paths (no documented congestion data; see AGENTS.md routing notes).

## Decisions

- **Leave-by computed backwards from the flood, not forwards from now.** For each profile:
  1. Find the route to the closest safe ground at that pace (escape search).
  2. Compute the slack: the smallest value over the route's cells of flood arrival at the cell minus walking time to that cell. Departure = now + slack.
  3. Leave-by = departure − 10 min.

  The search output already has per-cell times along the route, so this needs no new search. *Alternative:* re-running the search for many departure times; that is slower and gives the same answer.
- **Pace as a factor on Tobler walking time.**
  - `normal` = 1.0.
  - `slow` = a fixed factor (to be set from published walking-speed studies of older adults, cited; not invented).
  - `needs_help` = cannot self-evacuate: always listed for responders, with an alert to the household as well.
  - Running = 2× for the first ~5 min, only if `can_run` (same rule as escape-route-ux).
- **Batch per scenario.** Profiles in the flood's reach are evaluated in one pass when a scenario starts or changes. At 3 ms per query, 10,000 households take ~30 s on one core. *Alternative:* computing on demand per profile, which would leave alert timing to request luck.
- **Scheduler, not polling clients.** A small server-side queue holds (profile, send_at). It is rebuilt whenever the scenario changes, and only changed times are re-sent.
- **Data minimisation by design.** Store location, pace class, can_run, one contact, language and consent timestamp. Nothing else. The responder list is generated per scenario and not stored after the event ends.

## Risks / Trade-offs

- [Detection comes too late for any buffer near the source] → say so honestly ("leave now, N minutes"); the profile helps most further downstream (e.g. Arughat had ~2¾ h on Oct 11).
- [Home location ≠ where the person is] → the alert also links to prediction mode's "I am here" answer for wherever they are.
- [Pace class is self-reported and may be optimistic] → default new profiles to `slow` when unsure; the 10-minute buffer absorbs some error.
- [Sensitive list of vulnerable people] → access only for named responders and nominated neighbours; delete after the event; audit who viewed it.
- [SMS delivery delays] → send at leave-by minus the gateway's typical delay; document the assumed delay.
- [Model or DEM errors (e.g. channel drift at Arughat)] → the alert names safe ground the model rates P ≤ 0.10, which inherits the area model's known limits (see `docs/models/area.md`).

## Open Questions

- Which published source sets the `slow` speed factor?
- Who are the "responders" in practice (ward office, Nepal Red Cross volunteers, police)? How are they authenticated?
- SMS gateway in Nepal (NTC/Ncell bulk SMS) and cost?
- Does consent need to be per household member or per household?
