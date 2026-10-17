#!/bin/bash
# Bake a viewer bundle on the L1CC VM with claude-luis's engine and copy it into viewer/data/<replay>/.
# usage (from anywhere):  L1CC_KEY=<path to team key> L1CC_HOST=linux1@<VM_IP> viewer/bake/run_on_vm.sh [replay]
# Isolation (AGENTS.md): only ~/work-claude-lucas on the VM is written. ~/evac-ai is read-only here:
#   - code: this repo's engine/ pipeline/ replay/ viewer/bake/ are synced to ~/work-claude-lucas/repo
#   - data: data/raw is a symlink to ~/evac-ai/data/raw, and data/proc/*.tif are symlinks; data/proc/work is local
#   - GRASS: pipeline/g.sh uses <repo>/data/grassdb, so the repo copy gets a private copy of the grassdb
#     (r.walk writes maps there); HOME also points to a private directory for GRASS's own config files
set -euo pipefail
REPLAY=${1:-oct11}
KEY=${L1CC_KEY:?set L1CC_KEY to the team ssh key path}
HOST=${L1CC_HOST:?set L1CC_HOST to linux1@<VM_IP>}
W=work-claude-lucas
RSH="ssh -i $KEY -o BatchMode=yes"
cd "$(dirname "$0")/../.."

$RSH "$HOST" "mkdir -p ~/$W/repo/viewer ~/$W/repo/data/proc/work ~/$W/repo/data/grassdb ~/$W/home ~/$W/out"
rsync -a --delete -e "$RSH" --exclude __pycache__ engine pipeline replay "$HOST:$W/repo/"
rsync -a --delete -e "$RSH" --exclude __pycache__ viewer/bake "$HOST:$W/repo/viewer/"

$RSH "$HOST" bash -s -- "$W" "$REPLAY" <<'REMOTE'
set -euo pipefail
W=$HOME/$1; REPLAY=$2; SRC=$HOME/evac-ai/data
ln -sfn "$SRC/raw" "$W/repo/data/raw"
for f in dem_g sdir streams acc; do ln -sfn "$SRC/proc/$f.tif" "$W/repo/data/proc/$f.tif"; done
rsync -a --delete "$SRC/grassdb/" "$W/repo/data/grassdb/"
find "$W/repo/data/grassdb" -name .gislock -delete
rm -rf "$W/home/evac-ai"                                 # grassdb copy used by an older g.sh; no longer needed
cd "$W/repo"
rm -rf "$W/out/$REPLAY"                                  # never ship a stale bundle if the bake fails
HOME="$W/home" python3 viewer/bake/bake_scenario.py "$REPLAY" "$W/out/$REPLAY"
REMOTE

mkdir -p "viewer/data/$REPLAY"
rsync -a -e "$RSH" "$HOST:$W/out/$REPLAY/" "viewer/data/$REPLAY/"
echo "bundle in viewer/data/$REPLAY"
