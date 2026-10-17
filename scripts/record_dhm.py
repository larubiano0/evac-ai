"""Record snapshots of Nepal DHM's live river-level and rainfall feed.

Source: Department of Hydrology and Meteorology, https://hydrology.gov.np
The site pushes data over Socket.IO v2 (Engine.IO v3), hence python-socketio 4.x.

Usage
  python record_dhm.py            one snapshot, then exit
  python record_dhm.py --loop 900 snapshot every 900 s (leave running on the VM)

Each snapshot is data/replay/dhm/<UTC timestamp>.json with one key per channel.
"""
import argparse
import json
import threading
import time
from datetime import datetime, timezone

import socketio

from common import REPLAY, USER_AGENT, log

URL = "https://hydrology.gov.np"
PATH = "gss/socket.io"
CHANNELS = ["river_test", "rainfall_watch", "river_discharge"]


def snapshot(wait=45):
    got, done = {}, threading.Event()
    sio = socketio.Client(reconnection=False)

    def handler(name):
        def on(data):
            got[name] = data
            if len(got) == len(CHANNELS):
                done.set()
        return on

    for ch in CHANNELS:
        sio.on(ch, handler(ch))

    @sio.event
    def connect():
        for ch in CHANNELS:
            sio.emit("client_request", ch)

    sio.connect(URL, socketio_path=PATH, transports=["websocket", "polling"],
                headers={"User-Agent": USER_AGENT, "Origin": URL})
    done.wait(wait)
    sio.disconnect()
    return got


def scrub(got):
    """Drop river_discharge meta_data: it holds installer names and SIM phone numbers."""
    for st in got.get("river_discharge") or []:
        if isinstance(st, dict):
            st.pop("meta_data", None)
    return got


def save(got):
    got = scrub(got)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = REPLAY / "dhm" / f"{ts}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"recorded_utc": ts, **got}, ensure_ascii=False))
    sizes = {k: len(v) if isinstance(v, (list, dict)) else type(v).__name__ for k, v in got.items()}
    log(f"  {out.name}: {sizes} ({out.stat().st_size / 1e3:.0f} kB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--loop", type=int, metavar="SECONDS", help="repeat every N seconds")
    args = ap.parse_args()
    while True:
        try:
            got = snapshot()
            if got:
                save(got)
            else:
                log("  no data received")
        except Exception as e:  # keep the recorder alive through feed hiccups
            log(f"  snapshot failed: {e}")
        if not args.loop:
            break
        time.sleep(args.loop)


if __name__ == "__main__":
    main()
