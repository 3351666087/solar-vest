#!/bin/bash
# [grow G-4] Assemble v3/grow/bundle/tree from the project (run on the laptop; copies files only, fetches nothing).
# usage: make_bundle.sh [SEED_DIR]   (SEED_DIR: a run's best/ folder; it becomes tree/.../grow/work/seed)
set -e
SRC=/path/to/SolarVest_work
B=$SRC/wristband/v3/grow/bundle
T=$B/tree
rm -rf "$T"; mkdir -p "$T"
cp_rel() { mkdir -p "$T/$(dirname "$1")"; cp -R "$SRC/$1" "$T/$1"; }
V=wristband/v3
mkdir -p $T/$V/grow/tools $T/$V/grow/src $T/$V/grow/work/e_s2
cp $SRC/$V/grow/tools/*.py $T/$V/grow/tools/
cp $SRC/$V/grow/src/pf.c $T/$V/grow/src/
cp_rel $V/grow/work/b0
cp $SRC/$V/grow/work/e_s2/drc_final.json $SRC/$V/grow/work/e_s2/routes.json $SRC/$V/grow/work/e_s2/score.json $T/$V/grow/work/e_s2/
cp_rel $V/layout/work/board_zones_s2e_layout.json
cp_rel $V/layout/work/fpgeom_v3f.json
cp_rel $V/layout/lib/rf.pretty
cp_rel $V/design/parts.json
cp_rel $V/design/netclasses.json
cp_rel $V/design/lib/easyeda_rev.pretty
cp_rel $V/design/lib/solarband.pretty
if [ -n "$1" ]; then
  mkdir -p $T/$V/grow/work/seed
  for f in placement.json candidate.json drc_final.json routes.json score.json; do cp "$1/$f" $T/$V/grow/work/seed/; done
fi
# machine paths -> placeholders (install.sh puts the real root back)
find "$T" -name "*.py" -print0 | xargs -0 sed -i '' -e "s#/path/to/SolarVest_work#@SVROOT@#g" -e "s#/Applications/KiCad/KiCad.app/Contents#@MACKICAD@#g"
find "$T" -name "*.json" -print0 | xargs -0 sed -i '' -e "s#/path/to/SolarVest_work#@SVROOT@#g"
if grep -rl "/Users/" "$T" --include="*.py" --include="*.json" --include="*.sh"; then echo "WARNING: machine paths left (above)"; fi
du -sh "$T"
