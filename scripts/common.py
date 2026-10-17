"""Shared paths, study-area bounds and HTTP helpers for the fetch scripts.

Only uses requests + stdlib so it runs unchanged on the L1CC s390x VM.
"""
import json
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
REPLAY = ROOT / "data" / "replay"

USER_AGENT = "evac-ai/0.1 (IBM Z Datathon 2026, team Latinos)"

# Study area: Gorkha (Budhi Gandaki, Oct 11 dam burst) + Rasuwa / Nuwakot
# (Trishuli corridor, Aug 26 debris flood). Overwritten by fetch_districts.py
# with the exact union of the district boundaries once that has run.
DEFAULT_BBOX = {"south": 27.70, "west": 84.40, "north": 28.95, "east": 85.65}
DISTRICTS = ["Gorkha", "Rasuwa", "Nuwakot"]

OVERPASS_URLS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
]


def bbox():
    """Study-area bbox as a dict; prefers the one derived from district boundaries."""
    path = PROCESSED / "study_area.json"
    if path.exists():
        return json.loads(path.read_text())["bbox"]
    return DEFAULT_BBOX


def overpass_bbox(b):
    return f'{b["south"]},{b["west"]},{b["north"]},{b["east"]}'


def log(*args):
    print(*args, file=sys.stderr, flush=True)


def session():
    s = requests.Session()
    s.headers["User-Agent"] = USER_AGENT
    return s


def overpass(query, timeout=600, attempts=6):
    """Run an Overpass QL query, rotating mirrors and backing off on 429/504."""
    s = session()
    for i in range(attempts):
        url = OVERPASS_URLS[i % len(OVERPASS_URLS)]
        try:
            r = s.post(url, data={"data": query}, timeout=timeout + 60)
            if r.status_code == 200:
                return r.json()
            log(f"  overpass {url} -> HTTP {r.status_code}: {r.text[:200]!r}")
        except (requests.RequestException, ValueError) as e:
            log(f"  overpass {url} -> {e}")
        time.sleep(min(60, 10 * (i + 1)))
    raise RuntimeError("Overpass failed on all mirrors")


def download(url, dest, chunk=1 << 20):
    """Stream url to dest; skips if dest already exists. Returns dest or None on 404."""
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > 0:
        log(f"  have {dest.relative_to(ROOT)}")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with session().get(url, stream=True, timeout=120) as r:
        if r.status_code == 404:
            return None
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for block in r.iter_content(chunk):
                f.write(block)
    tmp.rename(dest)
    log(f"  got {dest.relative_to(ROOT)} ({dest.stat().st_size / 1e6:.1f} MB)")
    return dest


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, separators=(",", ":"), ensure_ascii=False))
    log(f"  wrote {path.relative_to(ROOT)} ({path.stat().st_size / 1e6:.1f} MB)")


def write_geotiff(path, arr, west, north, dx, dy):
    """Write a north-up EPSG:4326 GeoTIFF with plain zlib (readable on s390x without imagecodecs)."""
    import tifffile
    geokeys = (1, 1, 0, 3,
               1024, 0, 1, 2,      # GTModelType = Geographic
               1025, 0, 1, 1,      # RasterType = PixelIsArea
               2048, 0, 1, 4326)   # GeographicType = WGS84
    tifffile.imwrite(
        path, arr, compression="zlib", tile=(256, 256),
        extratags=[
            (33550, "d", 3, (dx, dy, 0.0), True),
            (33922, "d", 6, (0.0, 0.0, 0.0, west, north, 0.0), True),
            (34735, "H", len(geokeys), geokeys, True),
        ],
    )
