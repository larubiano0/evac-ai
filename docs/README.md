# Documentation

Everything about evac-ai ("Time to Safety"), from the idea to the sources. Read top to bottom for the full story. The
project overview, API and run steps are in the [main README](../README.md).

## 1. The idea and the problem
- [idea/project-plan.md](idea/project-plan.md): the project spec: constraints, what we build and why, judging criteria, decision log.
- [idea/nepal-disaster-research.md](idea/nepal-disaster-research.md): the research behind it: Nepal's recent floods (Oct 11 and Aug 26 2026 in detail), how warnings reached people, existing systems, with sources.
- [idea/bridge-failure-monte-carlo.md](idea/bridge-failure-monte-carlo.md): design note on estimating bridge failure under an uncertain flood.

## 2. How it works
- [architecture.md](architecture.md) (also as [architecture.html](architecture.html), figures in [figures/](figures/)): the big picture, every component, file and port.
- [linuxone-ai.md](linuxone-ai.md): what runs on the IBM z17 Telum on-chip AI accelerator, with measurements.
- [viewer/README.md](viewer/README.md) and [viewer/data-schema.md](viewer/data-schema.md): the 3D replay and its data format.

## 3. Data and sources
- [sources.md](sources.md): **every dataset, report, library and method used, with links.**
- [data/README.md](data/README.md): the committed study-area layers and how to re-create them. One page per dataset: [DEM](data/dem.md), [OSM](data/osm.md), [OSM damage labels](data/osm_damage_labels.md), [population](data/population.md), [2015 landslides](data/landslides_2015.md), [DHM feed](data/dhm_feed.md).
- [data/events/](data/events/): satellite flood extents and the other floods used to train and test the models (`DATASETS_flood_extent.md`, one `SOURCES_*.md` per event).

## 4. Models
- [models/damage.md](models/damage.md): building and bridge damage model (labels, features, spatial holdout, results).
- [models/area.md](models/area.md): flood-area model `area_fb` on satellite flood maps (the per-cell risk map).
- [models/surrogate.md](models/surrogate.md): the neural stand-in that runs on the Telum accelerator.

## 5. Does it work?
- [validation.md](validation.md): the numbers on the two real floods (people with time to escape, places and bridges flagged, arrival errors, latency).
- [validation/escape_audit.md](validation/escape_audit.md) and [validation/escape_satellite_check.md](validation/escape_satellite_check.md): safety audits of the "Where should I go?" answers.
- [judge-review.md](judge-review.md): our own judge's-eye review and fix list.

## 6. Running it
- [deploy.md](deploy.md): runbook for the LinuxONE VM and a laptop.
- [ibm-labs.md](ibm-labs.md): the optional IBM LinuxONE labs.

## 7. Submission
- [submission/README.md](submission/README.md): deliverables checklist, screenshots, demo video and shot list.
- [video-script.md](video-script.md): video script.
- [submission/pitch/outline.md](submission/pitch/outline.md): pitch deck outline.

Team coordination (agents and humans) is in [`AGENTS.md`](../AGENTS.md) at the repo root.
