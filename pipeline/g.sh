#!/bin/bash
# Run a GRASS command in the project location for $AREA (default budhi).  usage: AREA=trishuli pipeline/g.sh <cmd...>
# The GRASS database lives in <repo>/data/grassdb (works on the VM and inside the Docker image).
AREA=${AREA:-budhi}
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec grass "$ROOT/data/grassdb/$AREA/PERMANENT" --exec "$@" 2> >(grep -vE "SyntaxWarning|fmt$" >&2)
