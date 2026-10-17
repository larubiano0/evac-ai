#!/bin/bash
# Run a GRASS command (or script) in our project location.  usage: pipeline/g.sh <grass cmd...>
exec grass "$HOME/evac-ai/data/grassdb/budhi/PERMANENT" --exec "$@" 2> >(grep -vE "SyntaxWarning|fmt$" >&2)
