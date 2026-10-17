#!/bin/bash
# Run a GRASS command in the project location for $AREA (default budhi).  usage: AREA=trishuli pipeline/g.sh <cmd...>
AREA=${AREA:-budhi}
exec grass "$HOME/evac-ai/data/grassdb/$AREA/PERMANENT" --exec "$@" 2> >(grep -vE "SyntaxWarning|fmt$" >&2)
