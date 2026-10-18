# Architecture

Two diagrams. The first shows the big picture: who uses what, and what happens in between. The second shows every
component, the file it lives in, and what it runs on. GitHub renders both.

**Figures (PNG, for slides and the submission):** rendered from [`architecture.html`](architecture.html), the long-form
architecture page (open it in a browser).

| | |
|---|---|
| ![Core loop](figures/fig1-core-loop.png) | ![Deployment on LinuxONE](figures/fig2-deployment-linuxone.png) |
| ![Data and training](figures/fig3-data-training.png) | ![Request paths](figures/fig4-request-paths.png) |
| ![Go page offline](figures/fig5-go-offline.png) | ![Telum accelerator](figures/fig6-telum-accelerator.png) |

## 1. Big picture

```mermaid
flowchart TB
  SEE["Someone sees a flood start<br/>(phone call from upstream, river gauge, seismic signal)<br/><i>'the river burst here, at 03:45'</i>"]

  subgraph Z["IBM LinuxONE (L1CC, z17, s390x) · one Docker container · nothing leaves the machine"]
    direction TB
    P1["1 · Flood path<br/>follow the river downhill from that point"]
    P2["2 · When and how high<br/>arrival time + water height for every river km,<br/>calibrated on two real 2026 Nepal floods"]
    P3["3 · AI: what gets hit<br/>P(destroyed) for every building and bridge,<br/>P(flooded) for every 30 m square of ground"]
    P4["4 · Time to run<br/>walking time uphill to safe ground,<br/>crossing the river only on bridges"]
    P5["5 · Slack = arrival − warning − walk<br/>red: no time · amber: under 15 min · green"]
    P1 --> P2 --> P3 --> P4 --> P5
  end

  SEE --> P1
  P5 --> OFF["<b>Officials</b> · planner (/)<br/>who to warn first · SMS text in Nepali + English<br/>bridges to close · who had time under each warning"]
  P5 --> RES["<b>Residents</b> · 'Where should I go?' (/predict)<br/>tap where you are → route to safe ground,<br/>leave-by time, how sure we are"]
  P5 --> REP["<b>Story / training</b> · 3D replay (viewer/)<br/>watch a real flood move down the valley"]
  P5 --> GO["<b>Residents in a panic</b> · Go (/go)<br/>GPS → one instruction, countdown, arrow,<br/>EN/नेपाली, works offline"]
```

## 2. Components

```mermaid
flowchart LR
  subgraph DATA["Data (precomputed once per valley, on L1CC)"]
    DEM["Copernicus GLO-30 DEM"] --> GR["GRASS r.watershed<br/>flow directions, streams<br/>pipeline/"]
    OSM["OpenStreetMap<br/>buildings · places · trails · bridges"]
    DMG["Aug 26 OSM damage tags<br/>(2,759 destroyed)"]
    SAT["Satellite flood maps<br/>UNOSAT Aug 26 + Oct 11 · CEMS Ahr · UNOSAT Derna"]
    REPL["Real flood timelines<br/>replay/oct11.json · replay/aug26.json"]
  end

  subgraph TRAIN["Model training (on L1CC, seconds)"]
    DMOD["Damage model v2<br/>gradient boosting, buildings + bridges<br/>models/damage/ · AUC 0.968 unseen river"]
    AMOD["Area model area_fb<br/>gradient boosting, ground cells<br/>models/area/ · AUC 0.937 on unseen Oct 11"]
  end
  DMG --> DMOD
  SAT --> AMOD

  subgraph ENGINE["engine/ (Python + one C search, in memory)"]
    TER["terrain.py<br/>flood path + height above it (HAND)"]
    FLD["flood.py<br/>arrival(km), height(km) + uncertainty bands"]
    SCN["scenario.py<br/>footprint · per-building slack · settlements"]
    SAF["safety.py<br/>GRASS r.walk: walking time to safe ground"]
    ALR["alerts.py<br/>one-SMS alerts, EN + NE (reviewed)"]
    DM["damage_model.py<br/>features + scoring"]
    ESC["escape.py + escape_search.c<br/>time-aware safest route from any point"]
  end
  GR --> TER
  REPL --> FLD
  OSM --> SCN
  TER --> SCN
  FLD --> SCN
  SAF --> SCN
  SCN --> ALR
  DMOD --> DM
  AMOD --> ESC
  DM --> ESC
  TER --> ESC
  FLD --> ESC
  DM --> SCN

  subgraph API["api/app.py (FastAPI) · container evac-ai on 127.0.0.1:8000"]
    A1["/api/scenario · /api/compare · /api/trigger<br/>(+ damage_model keys)"]
    A2["/api/predict/scenario · /api/predict/escape"]
  end
  SCN --> A1
  ALR --> A1
  ESC --> A2

  A1 --> UI1["web/index.html<br/>planner (Leaflet)"]
  A2 --> UI2["web/predict.html<br/>resident view"]
  A2 --> UI4["web/go.html + go-sw.js<br/>Go view, offline"]
  SCN -. baked once .-> UI3["viewer/<br/>Three.js 3D replay (static)"]

  USER(["Browser"]) -->|SSH tunnel only, no open ports| API
```

## Where it runs

| Piece | Where | Notes |
|---|---|---|
| Container `evac-ai` | L1CC VM, `127.0.0.1:8000` | Ubuntu 24.04 s390x image. Scientific stack from Ubuntu's s390x packages. The C search is compiled in a build stage (`Dockerfile`) |
| Data (`data/`) | Mounted into the container | DEM products, OSM extracts, GRASS database. Not in the image |
| Models (`models/`) | Inside the image | Trained and pickled on s390x |
| Access | SSH tunnel | Port 22 is the only one open. The API binds to localhost |

## Speed (measured on L1CC; details in `validation.md`)

| Step | Time |
|---|---|
| New flood scenario (path, footprint, walking times for 112k buildings) | ~5 s |
| Same scenario again (cached) with all alerts | 0.03 s |
| Damage model on 3,727 buildings + 49 bridges | 0.25 s (+0.5 s setup per new path) |
| Resident "where should I go?" query | 2–5 ms |
| Resident flood grid, cold: Budhi Gandaki / Trishuli | ~10 s / ~53 s |
