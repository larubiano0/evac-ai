# Live river levels and rainfall: Nepal DHM feed

**Files:** `data/replay/dhm/<UTC timestamp>.json` (one snapshot each)
**Script:** `scripts/record_dhm.py` (`--loop 900` keeps recording)

## What it is

Nepal's Department of Hydrology and Meteorology (DHM) publishes real-time readings from its telemetry
stations at <https://hydrology.gov.np>. The site has no documented API. It pushes data to the browser over
Socket.IO (protocol v2), and our recorder connects the same way. The historical API
(`/gss/api/observation`) needs an API key, so we build our own history by recording snapshots.

## What we use it for

- **Live risk input:** river level relative to warning level on the stretch next to each segment;
  recent rainfall near each segment
- **Demo replay:** recorded snapshots let the demo run offline and deterministically
- **The pitch:** many gauges are silent, and there is no gauge on the Budhi Gandaki at all. That gap is
  the point.

## Snapshot format

```json
{ "recorded_utc": "20261017T151626Z",
  "river_test":     [ ...stations... ],
  "rainfall_watch": [ ...gauges... ],
  "river_discharge":[ ...stations... ] }
```

### `river_test`: water level (337 stations nationally, 39 in our bbox)

| Field | Example | Notes |
|---|---|---|
| `name` | `Trishuli River at Bhorle` | Often has leading/trailing spaces, so `.strip()` it |
| `id`, `series_id`, `stationIndex` | `236`, `3593`, `"581"` | `series_id` is the key for DHM's locked history API |
| `latitude`, `longitude` | `27.36`, `85.47` | |
| `basin`, `district` | `Narayani`, `Makawanpur` | Can be `null` |
| `waterLevel` | `{"datetime": "...+00:00", "value": 2.864}` | `null` value = no current reading |
| `warning_level`, `danger_level` | `"5.2"`, `"6.2"` | **Strings**, sometimes empty or `null` |
| `status` | `BELOW WARNING LEVEL` | DHM's own classification |
| `steady` | `STEADY` / `RISING` / `FALLING` | Empty when there is no reading |
| `tags` | `["HS", "RLS", ...]` | Station type codes |

### `rainfall_watch`: rain gauges (518 nationally, 57 in our bbox)

| Field | Notes |
|---|---|
| `name`, `id`, `series_id`, `latitude`, `longitude`, `elevation`, `district`, `basin` | As above |
| `latest_observation` | `{"datetime", "value"}`, the latest reading in mm |
| `averages` | List of `{"interval": 1/3/6/12/24 (hours), "value": mm, "status": {"warning", "danger"}}` |
| `status` | DHM's classification |

### `river_discharge`: flow stations (2 nationally)

Station metadata plus `discharge`. **The `meta_data` block is removed on save** because it contains
installer names and SIM phone numbers.

## Stations that matter for us

Trishuli corridor (August event): Trishuli at Galchi, Trishuli River at Bhorle, Trishuli River at Kali
Khola, Trishuli Khola at Dhunche, Trishuli at Betrawati, Bhote Koshi at Shyaprubesi, Bhotekoshi at
Rasuwagadi, Langtang Khola at Shyaprubesi.
Gorkha side: Daraudi Khola at Naya Sangu, Chepe Khola at Garambesi, Marsyangdi at Bimalnagar.
**Budhi Gandaki: no station.**

On 17 Oct 2026 about half of the in-bbox stations returned no current reading (`value: null`), including
both Rasuwa Bhote Koshi gauges.

## Caveats

- **Stations do not share a datum.** Most report stage (metres above a local zero, e.g. Bhorle 2.86 m,
  warning 9.5 m). Some report absolute elevation (Galchi 359.7 m, warning 367 m). Only compare a
  station with its *own* `warning_level` / `danger_level`, as a ratio or difference, never one station
  with another.
- Warning levels are set for monsoon floods. In August the Devghat peak (6.57 m) stayed under the 7.3 m
  warning while the debris flood killed over 1,400 people. Treat "below warning" as weak evidence.
- Updates arrive every 10–15 minutes, so recording faster than every 10 minutes only creates duplicates.
- Unofficial access. Keep a polite interval and the identifying User-Agent the script sets.

## Source

Department of Hydrology and Meteorology, Government of Nepal, <https://hydrology.gov.np>.
