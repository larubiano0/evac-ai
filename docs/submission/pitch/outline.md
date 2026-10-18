# Pitch deck outline (draft, for Lucas to direct)

Target: PDF ≤ 5 MB, 10 slides, readable without a speaker. Judging: community value, novelty, LinuxONE + AI/ML use with evidence, execution and pitch (10 points each).

| # | Slide | Content | Visual (exists in repo) |
|---|---|---|---|
| 1 | Title | "Time to Safety" · Nepal can't predict when the mountain falls. It can predict who has time to run. · Team Latinos | `screenshots/S0-landing.jpg` |
| 2 | The problem | Oct 11: villagers' relay 03:30, first wave Arughat ~06:30, official SMS 06:40. Aug 26: 4 gauges destroyed, generic Nepali-only SMS | timeline graphic |
| 3 | The question nobody answers | Who is hit, when, and who still has time to walk to safe ground? | — |
| 4 | How it works | trigger → flood path → arrival + height → AI: what gets hit → walk to safety → slack | `figures/fig1-core-loop.png` |
| 5 | Result on a real flood | 03:30 relay: 0 of 1,456 without time · 06:40 SMS: 1,456. 9/10 places, 4/6 bridges flagged | `S6` vs `S5` side by side |
| 6 | AI/ML trained on real floods | building damage AUC 0.968 (Aug 26 holdout); flood-area model on satellite maps: trained on Aug 26 only, AUC 0.937 / Brier 0.057 on unseen Oct 11 (shipped model retrained on both) | `S8-planner-damage-model.jpg` |
| 7 | IBM z17 Telum accelerator | 12.7 M predictions: 2.7 s vs 83 s (31×); live what-if map 10 M in 2.6 s | `figures/fig6-telum-accelerator.png`, `S8b` |
| 8 | Runs on LinuxONE | one container, z17, nothing leaves the machine, 5.1 s per scenario | `S2-l1cc-terminal-z17-docker.jpg`, `fig2` |
| 9 | For residents | "Where should I go?" + panic-proof /go page, Nepali, offline | `S9`, `S10`, `S12` |
| 10 | Impact + next steps | who benefits, open data only, any valley; next: DHM/BIPAD live triggers, LoRa mesh, cell broadcast · repo + video links | — |
