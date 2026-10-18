# Documentation

Everything about evac-ai ("Time to Safety"), from the problem to the sources. The project overview, API and run
steps are in the [main README](../README.md).

## 1. The problem
- [idea/nepal-disaster-research.md](idea/nepal-disaster-research.md): Nepal's recent floods (Oct 11 and Aug 26 2026 in detail), how warnings reached people, existing systems, with sources.

## 2. How it works
- [architecture.md](architecture.md) (also as [architecture.html](architecture.html), figures in [figures/](figures/)): the big picture, every component, file and route.
- [linuxone-ai.md](linuxone-ai.md): what runs on the IBM z17 Telum on-chip AI accelerator, with measurements.
- [viewer/README.md](viewer/README.md) and [viewer/data-schema.md](viewer/data-schema.md): the 3D replay and its data format.

## 3. What it looks like
- [media/screenshots/](media/screenshots/): the landing page, planner, "Where should I go?" and the phone view.
- [media/demo.mp4](media/demo.mp4): the demo video.

## 4. Data and sources
- [sources.md](sources.md): **every dataset, report, library and method used, with links.**
- [data/README.md](data/README.md): the committed study-area layers and how to re-create them. One page per dataset: [DEM](data/dem.md), [OSM](data/osm.md), [OSM damage labels](data/osm_damage_labels.md), [population](data/population.md), [2015 landslides](data/landslides_2015.md), [DHM feed](data/dhm_feed.md).
- [data/events/](data/events/): satellite flood extents and the other floods used to train and test the models (`DATASETS_flood_extent.md`, one `SOURCES_*.md` per event).

## 5. Models
- [models/damage.md](models/damage.md): building and bridge damage model (labels, features, spatial holdout, results).
- [models/area.md](models/area.md): flood-area model `area_fb` on satellite flood maps (the per-cell risk map).
- [models/surrogate.md](models/surrogate.md): the neural stand-in that runs on the Telum accelerator.

## 6. Does it work?
- [validation.md](validation.md): the numbers on the two real floods (people with time to escape, places and bridges flagged, arrival errors, latency).
- [validation/escape_audit.md](validation/escape_audit.md) and [validation/escape_satellite_check.md](validation/escape_satellite_check.md): safety audits of the "Where should I go?" answers.

## 7. Running it
- [deploy.md](deploy.md): how to run it on a LinuxONE VM or on a laptop.
