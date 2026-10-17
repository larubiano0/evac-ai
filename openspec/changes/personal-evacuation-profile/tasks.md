> Idea only. Do not start until Lucas says so. Prerequisite: the time-aware run rule (`can_run`, 2× for ~5 min) merged from `escape-route-ux`.

## 1. Decisions before code

- [ ] 1.1 Pick and cite a published walking-speed source for the `slow` factor
- [ ] 1.2 Decide who the responders are and how they log in; write the consent text (EN + NE)
- [ ] 1.3 Agree API ownership with agent-aayush (owner of `api/`) and claim in AGENTS.md

## 2. Engine

- [ ] 2.1 `escape.py`: accept a pace factor and `can_run`; return per-route-cell walking time and flood arrival
- [ ] 2.2 Add `latest_departure(profile, scenario)`: min over route cells of (arrival - walk time), and leave_by = latest_departure - 10 min
- [ ] 2.3 Batch evaluation of all profiles in the flood's reach; time it on the VM (target: 10k households < 60 s)
- [ ] 2.4 Tests: plenty of time / already late / needs_help / slow vs normal / recomputation on scenario change

## 3. Profiles

- [ ] 3.1 Profile storage (location, pace class, can_run, contact, language, consent timestamp) with create / update / delete
- [ ] 3.2 Reject without consent; delete removes computed times and list entries
- [ ] 3.3 Household form on the page: map pin for home, pace class, can-run checkbox

## 4. Alerts

- [ ] 4.1 Personal templates in `engine/alerts.py` (leave by HH:MM / leave now / RUN), EN + NE; send to the Nepali reader for review
- [ ] 4.2 Scheduler: queue of (profile, send_at), rebuilt on scenario change, re-send only changed times
- [ ] 4.3 Gateway adapter (SMS / push), stubbed to a log file until a provider is chosen

## 5. Responders

- [ ] 5.1 "Cannot make it" list per scenario (needs_help + too late), with minutes to flood
- [ ] 5.2 Access control for responders and nominated neighbours; delete the list after the event

## 6. Verify

- [ ] 6.1 Replay Oct 11 with a set of test profiles (made-up test households, clearly marked as test data) and check alert times against the arrival grid
- [ ] 6.2 Write up results and limits; log in AGENTS.md
