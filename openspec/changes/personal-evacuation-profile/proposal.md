> **Status: idea only, not started.** Written down so it isn't lost; Lucas may not build it during the datathon.
> Depends on the time-aware run rule being added to `escape-route-ux` (running = 2× walking speed for the first ~5 minutes only, `can_run` flag).

## Why

Today every resident gets the same warning: "the flood reaches X at HH:MM". Whether that is enough depends on who you are. A fit adult 300 m from safe ground has plenty of time. An elderly person, or a family carrying a child, on the same street may not. The engine can already compute, in milliseconds, how long a given pace needs to reach safe ground before the flood. A small profile per household turns the generic warning into a personal one: **"leave by 09:12"**. It also tells responders who cannot get out alone, early enough for help to reach them.

## What Changes

- **New: a household evacuation profile.**
  - Fields: home location, and a pace class: `normal`, `slow`, or `needs_help` (cannot walk to safety alone). The slowest member sets the household's pace.
  - Optional flag "can run for a few minutes".
  - Optional contact (phone) and language (EN/NE).
  - No medical details. Created only with explicit consent, and deletable at any time.
- **New: a personal leave-by time per profile when a flood is predicted.** For the active flood scenario, prediction mode's escape search runs from the profile's home at the profile's pace. It uses the flood arrival grid along the whole route.
  - **Leave-by time** = the latest departure that still passes every route cell before the flood arrives there, **minus a 10-minute buffer**.
  - It is recomputed whenever the scenario changes (new trigger, new arrival estimate).
- **New: personal leave-by alerts.**
  - The alert goes out at the leave-by time, or **immediately** if that time has already passed (then the text says "leave now").
  - It states: leave by HH:MM, which way, how far, to which safe ground.
  - EN + NE text, from the same template family as `engine/alerts.py`.
  - Sent by SMS, and by push notification where available.
- **New: a "cannot make it" list for responders.** It lists households whose route cannot reach safe ground before the flood at their pace, even when leaving now, and all `needs_help` households in the flood's reach. Each entry has name, location, pace class and minutes until the flood reaches them. It goes to local responders and nominated neighbours.
- No change to existing endpoints. New endpoints and keys are additive.

## Capabilities

### New Capabilities
- `evacuation-profile`: creating, storing, updating and deleting a household profile (location, pace class, can-run, contact, language, consent), with data minimisation.
- `personal-leave-by-alert`: computing each profile's leave-by time from the active flood scenario, sending the personal alert at that time, and producing the "cannot make it" list for responders.

### Modified Capabilities
(none: `escape-destination` from `escape-route-ux` is used as-is through its pace / `can_run` inputs)

## Impact

- `engine/escape.py`: needs a pace multiplier input (normal = 1.0, slow < 1.0, run boost per the escape-route-ux rule) and a "latest feasible departure" query. These are small additions to the escape search, which already has per-cell flood arrival.
- `engine/alerts.py`: new personal templates (EN + NE). The Nepali review (packet H) is required again for them.
- `api/`: new profile endpoints and an alert dispatcher (owner: agent-aayush / claude-luis; coordinate first).
- New storage for profiles (small, local to the deployment; no third-party analytics).
- An SMS/push gateway: an external service, not chosen yet.
- Privacy and legal: consent text, retention, and who can see the responder list.
