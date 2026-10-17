## ADDED Requirements

### Requirement: Viewer is served by the API
The API SHALL serve `viewer/` at `/viewer/` from the same origin as `/api/predict/*`, without changing any existing endpoint.

#### Scenario: Same-origin load
- **WHEN** a browser opens `/viewer/?scenario=oct11` on the API host
- **THEN** the viewer loads its bundle and its requests to `../api/predict/*` succeed without CORS headers

### Requirement: Live mode detection
On load, the viewer SHALL probe `GET ../api/predict/options` with a timeout of 3 s or less. It SHALL enable live controls only if the probe succeeds, and SHALL otherwise behave exactly as the offline replay.

#### Scenario: Static server
- **WHEN** the viewer is served by `python3 -m http.server`
- **THEN** no "Where do I go?" control is shown, the replay works unchanged, and no error is shown to the user

#### Scenario: API host
- **WHEN** the viewer is served by the API
- **THEN** the "Where do I go?" control is shown, and the viewer POSTs `/api/predict/scenario` once with the bundle's `predict` values and keeps the returned `sid`

### Requirement: Click to get an escape path
With live mode on, a click or tap on the terrain SHALL query `POST /api/predict/escape` with:
- the clicked lon/lat
- `minutes_after_start = t − burst_min` at the current slider time
- the stored `sid`

The viewer SHALL then draw:
- the returned path, coloured by `safe`
- every `unsafe_points` entry in red
- the destination
- a result card with confidence, walk time, climb and `min_margin_before_flood_min`

#### Scenario: Safe path
- **WHEN** the user clicks a point in Jagat at 03:50 NPT on the Oct 11 bundle and the API returns `safe: true`
- **THEN** a green path runs to the destination flag, and the card shows the walk minutes and confidence from the response

#### Scenario: Unsafe points
- **WHEN** the response has `safe: false` and two `unsafe_points`
- **THEN** the path is amber, two red dots mark those points, and the card says the path is not safe everywhere

#### Scenario: Outside the zone
- **WHEN** the response `status` is `outside_impact_zone` or `safe_here`
- **THEN** no path is drawn, and the card shows a one-line plain-language message

### Requirement: Query follows the slider
While a query point is set, changing the slider time SHALL re-query once on release (debounced) and SHALL NOT query during playback.

#### Scenario: Later time
- **WHEN** the user drags the slider from 03:50 to 06:30 with a point set
- **THEN** exactly one new escape request is sent after release, and the path and card update

### Requirement: Expired scenario recovery
If an escape request returns 404, the viewer SHALL re-POST the scenario once and retry the escape request before showing an error.

#### Scenario: Cache evicted
- **WHEN** the API has evicted the `sid`
- **THEN** the user still gets a path after one automatic retry

### Requirement: LinuxONE evidence badge
For every live answer, the viewer SHALL show the `host.machine`, `host.byteorder` and measured round-trip time from the response.

#### Scenario: On L1CC
- **WHEN** an escape answer arrives from the VM
- **THEN** the badge reads "Computed live on IBM LinuxONE · s390x · big-endian · <time> s"
