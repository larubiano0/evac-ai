# Sources

Every dataset, report, library and method evac-ai uses, in one place. All of them are public. All code in this repo
was written during the event. Licences for the software are in the [README](../README.md#libraries--resources).

Links were checked on Sun Oct 18 2026, 01:00 ET. Two event reports, marked ⚠️, return HTTP 403 to automated requests (bot
protection); open them in a browser.

## 1. Data the app runs on

| Dataset | What we use it for | Where it is described |
|---|---|---|
| [Copernicus DEM GLO-30](https://registry.opendata.aws/copernicus-dem/) | Elevation: flow directions, height above the river (HAND), walking cost | [data/dem.md](data/dem.md) |
| [OpenStreetMap](https://www.openstreetmap.org/copyright) via [Geofabrik Nepal](https://download.geofabrik.de/asia/nepal.html) | Buildings, settlements (English + Nepali names), bridges, rivers, roads and trails, shelters | [data/osm.md](data/osm.md) |
| [WorldPop Global2 R2025A](https://hub.worldpop.org/) | Population per 100 m cell | [data/population.md](data/population.md) |
| [USGS 2015 Gorkha landslide inventory](https://doi.org/10.5066/F7DZ06F9) (Roback et al. 2017) | Distance to past landslides (model feature) | [data/landslides_2015.md](data/landslides_2015.md) |
| [DHM, Government of Nepal](https://hydrology.gov.np) | Gauge locations, warning and danger levels, live-feed snapshots | [data/dhm_feed.md](data/dhm_feed.md) |
| [BIPAD Portal API](https://bipadportal.gov.np/api/v1/) | Probed for river, rain and incident data. Not used by the app yet | [idea/nepal-disaster-research.md](idea/nepal-disaster-research.md) |
| Map tiles: [OpenStreetMap](https://www.openstreetmap.org/copyright), [OpenTopoMap](https://opentopomap.org/about), [Esri World Imagery](https://www.arcgis.com/home/item.html?id=10df2279f9684e4a9f6a7f08febac2a9) | Basemaps in the browser | [README](../README.md#libraries--resources) |

## 2. Labels the models learn from (real, published observations only)

| Dataset | Used for | Where it is described |
|---|---|---|
| [OSM Nepal Floods 2026 mapping](https://wiki.openstreetmap.org/wiki/Organised_Editing/Activities/Nepal_Floods_2026): 2,759 destroyed + 415 damaged buildings, Aug 26 | Building damage model (training, spatial holdout) | [data/osm_damage_labels.md](data/osm_damage_labels.md), [models/damage.md](models/damage.md) |
| [UNOSAT FL20260826NPL](https://data.humdata.org/dataset/mudflow-rockflow-impact-assessment-in-rasuwa-nuwakot-districts-bagmati-province-nepal-as-o), Aug 26 flood/mudflow extent | Flood-area model `area_fb` (training) | [data/events/SOURCES_area_aug26.md](data/events/SOURCES_area_aug26.md) |
| [UNOSAT FL20261011NPL](https://data.humdata.org/dataset/satellite-detected-mudflow-as-of-11-october-2026-in-gorkha-district-gandaki-province-nepal), Oct 11 extent | Flood-area model (training, and the unseen-flood test) | [data/events/SOURCES_area_oct11.md](data/events/SOURCES_area_oct11.md) |
| [Copernicus EMS EMSR517](https://mapping.emergency.copernicus.eu/activations/EMSR517), Ahr 2021 | Flood-area model test on a different country | [data/events/SOURCES_area_ahr.md](data/events/SOURCES_area_ahr.md) |
| [UNOSAT FL20230912LBY](https://data.humdata.org/dataset/flood-impact-assessment-in-derna-city-east-province-libya), Derna 2023 | Test flood (area model) and damage labels (damage model test) | [data/events/SOURCES_area_derna.md](data/events/SOURCES_area_derna.md), [data/events/SOURCES_derna.md](data/events/SOURCES_derna.md) |
| [Ahr building damage, Samprogna Mohor et al. 2025](https://doi.org/10.4121/8f7a21d3-9bb9-4808-ae51-761eb3fba986) | Damage model, leave-one-flood-out test | [data/events/SOURCES_ahr.md](data/events/SOURCES_ahr.md) |
| [Sentinel Asia](https://sentinel-asia.org/) (JAXA ALOS-2, MBRSC Sentinel-2), [HOT flood extent](https://data.humdata.org/dataset/hot_flood_npl) | Cross-checks of the UNOSAT maps only | [data/events/DATASETS_flood_extent.md](data/events/DATASETS_flood_extent.md) |

## 3. Event timelines (calibration of arrival time and flood height)

Each observation in [`replay/oct11.json`](../replay/oct11.json) and [`replay/aug26.json`](../replay/aug26.json) has its own
`src`. Points without a reliable time **and** place are marked `excluded`, with a note. Background and the full story of
both floods, with inline links (37 sources): [idea/nepal-disaster-research.md](idea/nepal-disaster-research.md).

**Oct 11 2026, Budhi Gandaki (Gorkha)**
- [BWSN/ADRRN SitRep 1](https://www.adrrn.net/wp-content/uploads/2026/10/Budhi_Gandaki_Flood_SitRep_1.pdf): flood enters Jagat area ~04:00
- [Kathmandu Post, NDRRMA chief interview](https://kathmandupost.com/interviews/2026/10/11/sms-alerts-helped-avert-loss-of-life-in-budhi-gandaki-floods-says-disaster-management-chief): SMS timing
- [Onlinekhabar, "Warnings saved lives"](https://english.onlinekhabar.com/warnings-saved-lives-budhi-gandaki.html): the villagers' phone relay
- [Wikipedia, 2026 Budhi Gandaki flood](https://en.wikipedia.org/wiki/2026_Budhi_Gandaki_flood): first wave at Arughat ~06:30, gauge 8.43 m, flood height "reportedly reached a record breaking 20 metres" upstream
- ⚠️ [Trekguard blog](https://trekguard.app/blog/budhi-gandaki-flash-flood-manaslu-circuit-safety-2026/): the **25 m** upper end of the 20–25 m height at Salleri. This is a commercial blog and the only source for 25 m; Wikipedia supports 20 m. The prediction preset (`models/damage/flood_presets.json`) uses 25 m as the upper end.

**Aug 26 2026, Bhotekoshi–Trishuli (Rasuwa/Nuwakot)**
- [Wikipedia, Timeline of the 2026 Nepal–Tibet floods](https://en.wikipedia.org/wiki/Timeline_of_the_2026_Nepal%E2%80%93Tibet_floods): gauge timeline
- [Wikipedia, 2026 Nepal–Tibet floods](https://en.wikipedia.org/wiki/2026_Nepal%E2%80%93Tibet_floods)
- [NDRRMA Rasuwa SitRep 01](https://ndrrma.gov.np/mediafiles/rasuwa/Rasuwa_Flood_SitRep_Temp_ENG_01_01092026.pdf)
- ⚠️ [Mongabay, community-based warning](https://news.mongabay.com/2026/09/during-nepal-floods-decentralized-community-based-warning-saved-lives/)
- [Onlinekhabar, "How many floods to react?"](https://english.onlinekhabar.com/how-many-floods-to-react.html)
- [DHM](https://hydrology.gov.np): gauge coordinates and warning/danger levels

## 4. Software

Libraries, tools and licences: [README, Libraries & Resources](../README.md#libraries--resources). Main pieces:
GRASS GIS, GDAL, NumPy, SciPy, rasterio, pyproj, Shapely, scikit-learn, FastAPI, Leaflet, Three.js, Docker, Ubuntu,
and IBM zDNN for the Telum on-chip AI accelerator. The 3D viewer's own credits: [viewer/README.md](viewer/README.md).

## 5. Methods we reimplemented

- HAND: Nobre, A.D. et al. (2011), *Height Above the Nearest Drainage, a hydrologically relevant new terrain model*, Journal of Hydrology 404.
- Time to safety on foot: after the [USGS Pedestrian Evacuation Analyst (PEAT)](https://www.usgs.gov/software/pedestrian-evacuation-analyst-tool), using GRASS `r.walk`.
- Damage grades for the Ahr labels: [Maiwald & Schwarz 2019](https://doi.org/10.1002/dama.201910014).

## 6. Infrastructure

[IBM LinuxONE Community Cloud](https://linuxone.cloud.marist.edu/): an IBM z17 VM (Ubuntu 24.04 s390x), free community-cloud terms.

## 7. Impact figures (pitch)

Global numbers quoted on the impact slide. Not used by the app or the models. Our own figures (people without time,
latency) come from [validation.md](validation.md).

| Figure | Source |
|---|---|
| Countries with comprehensive multi-hazard early warning have about **8× lower** disaster mortality than those with limited coverage (UNDRR/WMO report, Oct 2022) | [UNDRR, "The first step to zero climate disasters is early warning"](https://iddrr.undrr.org/2022/news/first-step-zero-climate-disasters-early-warning.html) |
| Only about **half** of the world's countries have a multi-hazard early warning system | [UN Fast Facts: Early Warnings](https://www.un.org/sites/un2.un.org/files/2025-12-02-fast-facts/EarlyWarnings_FastFacts.pdf) |
| **24 hours'** notice can cut damage by up to **30%**; US$800M invested in developing countries could avoid $3–16B in losses a year (Global Commission on Adaptation estimate) | [WMO, About EW4All](https://wmo.int/ru/node/25761) |
| UN Secretary-General: disaster mortality is at least **6× lower** in countries with good early warning (the 8× figure above is from the 2022 report) | [UN Geneva, Oct 2025](https://www.ungeneva.org/en/news-media/news/2025/10/112023/climate-science-and-early-warnings-key-saving-lives) |
| About **15 million** people exposed to glacial lake outburst floods worldwide, **9.3 million** in High Mountain Asia | Taylor et al. (2023), *Glacial lake outburst floods threaten millions globally*, [Nature Communications 14, 487](https://www.nature.com/articles/s41467-023-36033-x); summary in [Scientific American](https://www.scientificamerican.com/article/15-million-people-are-at-risk-from-bursting-glacial-lakes) |
