#!/bin/bash
# [track2e] v3/track2/bundle + ECO3 (U19/U20 TLV7031DCKR C2863637 SC70-5) -> v3/track2e/bundle. Seed = v3/eco3/runs/e1.
# Laptop only; copies files, fetches nothing. Placeholder scheme as tools/make_bundle_t2.sh (@SVROOT@, @MACKICAD@).
set -e
SRC=/path/to/SolarVest_work
V=wristband/v3
E=$SRC/$V/eco3
B=$SRC/$V/track2e/bundle
T=$B/tree
G=$T/$V/grow8
rm -rf "$B"; cp -R $SRC/$V/track2/bundle "$B"; rm -f "$B/env.sh"
# 1. tools: eco3/tools_t2 (the tools the e1 evaluation ran); its eco3 path edits mapped back onto the bundle tree layout
rm -f $G/tools/*.py
cp $E/tools_t2/tools/*.py $G/tools/
cp $E/tools_t2/src/pf.c $G/src/
for f in lgeom.py fpdump.py; do
  sed -i '' -e 's#os.environ.get("G1_WORK", V3 + "/eco3/work_t2")#os.environ.get("G1_WORK", V3 + "/layout/work")#' $G/tools/$f
  grep -q '"/layout/work")' $G/tools/$f || { echo "STOP: $f WORK patch failed"; exit 1; }
done
# 2. design: parts.json, SC70-5 footprint
cp $SRC/$V/design/parts.json $T/$V/design/parts.json
cp "$SRC/$V/design/lib/easyeda_rev.pretty/C2863637_SC-70-5_L2.1-W1.3-P0.65-LS2.2-BR.kicad_mod" $T/$V/design/lib/easyeda_rev.pretty/
# 3. footprint geometry cache (U19/U20 SC70)
cp $E/work_t2/fpgeom_v3f.json $T/$V/layout/work/fpgeom_v3f.json
# 4. seed = eco3/runs/e1 (also the --base default; the X2SON-era h4 placement is dropped)
rm -rf $G/work/seed8; mkdir -p $G/work/seed8
for f in placement.json candidate.json drc_final.json routes.json score.json board_stats.json final.kicad_pcb final.kicad_pro final.kicad_dru; do
  cp "$E/runs/e1/$f" $G/work/seed8/
done
cp $E/runs/e1/placement.json $G/work/b0_src/placement.json
rm -rf $T/$V/track2/runs
sed -i '' -e "s#$SRC/$V/eco3/work/placement_eco3.json#$SRC/$V/grow8/work/seed8/placement.json#" $G/work/seed8/candidate.json
# 5. run.sh: tmux session t2e, default run rent_t2e
sed -i '' -e 's/new-session -d -s grow8/new-session -d -s t2e/' -e "s/tmux session 'grow8' (tmux attach -t grow8)/tmux session 't2e' (tmux attach -t t2e)/" \
  -e 's/RUNNAME=${RUN:-rent8}/RUNNAME=${RUN:-rent_t2e}/' -e 's/in tmux session "grow8"/in tmux session "t2e"/' -e 's/RUN (default rent8)/RUN (default rent_t2e)/' $B/run.sh
# machine paths -> placeholders (install.sh puts the real root back)
find "$T" -name "*.py" -print0 | xargs -0 sed -i '' -e "s#$SRC#@SVROOT@#g" -e "s#/Applications/KiCad/KiCad.app/Contents#@MACKICAD@#g"
find "$T" -name "*.json" -print0 | xargs -0 sed -i '' -e "s#$SRC#@SVROOT@#g"
if grep -rl "/Users/" "$T" --include="*.py" --include="*.json" --include="*.sh" --include="*.kicad_*"; then echo "WARNING: machine paths left (above)"; fi
cd $SRC/$V/track2e && tar czf t2e_bundle.tgz bundle
du -sh "$T" $SRC/$V/track2e/t2e_bundle.tgz
