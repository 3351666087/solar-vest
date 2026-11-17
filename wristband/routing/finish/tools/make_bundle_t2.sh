#!/bin/bash
# [track2 Q-5] Assemble v3/track2/bundle/tree (track2 tools placed at grow8/tools so run.sh is unchanged) from the project (run on the laptop; copies files only, fetches nothing).
# usage: make_bundle8.sh SEED_EVAL_DIR [OUT_TREE]
#   SEED_EVAL_DIR: an evaluation folder (placement.json, candidate.json, drc_final.json, routes.json, score.json): the search starts there
#   OUT_TREE: default v3/grow8/bundle/tree (a local test can build a second tree elsewhere)
set -e
SRC=/path/to/SolarVest_work
V=wristband/v3
T=${2:-$SRC/$V/track2/bundle/tree}
rm -rf "$T"; mkdir -p "$T"
cp_rel() { mkdir -p "$T/$(dirname "$1")"; cp -R "$SRC/$1" "$T/$1"; }
mkdir -p $T/$V/grow8/tools $T/$V/grow8/src $T/$V/grow8/work/seed8 $T/$V/grow8/runs
cp $SRC/$V/track2/tools/*.py $T/$V/grow8/tools/
cp $SRC/$V/track2/src/pf.c $T/$V/grow8/src/
mkdir -p $T/$V/grow8/work/b0_src
cp $SRC/$V/grow8/work/b0_src/placement.json $T/$V/grow8/work/b0_src/
for f in placement.json candidate.json drc_final.json routes.json score.json; do cp "$1/$f" $T/$V/grow8/work/seed8/; done
cp_rel $V/layout/work/board_zones_s2e_layout.json
cp_rel $V/track2/work/board_zones_t2_layout.json
cp_rel $V/track2/runs/h4/placement_fix.json
cp_rel $V/layout/work/fpgeom_v3f.json
cp_rel $V/layout/lib/rf.pretty
cp_rel $V/design/parts.json
cp_rel $V/design/netclasses.json
cp_rel $V/design/lib/easyeda_rev.pretty
cp_rel $V/design/lib/solarband.pretty
# machine paths -> placeholders (install.sh puts the real root back)
find "$T" -name "*.py" -print0 | xargs -0 sed -i '' -e "s#/path/to/SolarVest_work#@SVROOT@#g" -e "s#/Applications/KiCad/KiCad.app/Contents#@MACKICAD@#g"
find "$T" -name "*.json" -print0 | xargs -0 sed -i '' -e "s#/path/to/SolarVest_work#@SVROOT@#g"
if grep -rl "/Users/" "$T" --include="*.py" --include="*.json" --include="*.sh"; then echo "WARNING: machine paths left (above)"; fi
du -sh "$T"
