#!/bin/zsh
# [track2] trymove chain: zsh fix_t2.sh DIR "REF:MAX:STEP REF:MAX:STEP ..."  (DIR/placement.json -> DIR/placement_fix.json)
D=$1; T=/path/to/SolarVest_work/wristband/v3/track2/tools; PY=python3
export TMPDIR=$D/tmp OMP_NUM_THREADS=1 G1_ZFILE=/path/to/SolarVest_work/wristband/v3/track2/work/board_zones_t2_layout.json G1_NO_ISLAND=1 G1_VARIANT=v3f
export G1_OPTS="gap=dru,jlc=full,ufpc" G1_ZONES=L43W37_t2 G1_CRIT_W=200 G1_HOVR="D14:1.0" G1_TAG=grow
cp $D/placement.json $D/fx.json
for spec in ${=2}; do r=${spec%%:*}; rest=${spec#*:}; mx=${rest%%:*}; st=${rest#*:}
  $PY -B $T/trymove.py $D/fx.json $D/fx2.json $r $mx $st && [ -f $D/fx2.json ] && mv $D/fx2.json $D/fx.json; done
cp $D/fx.json $D/placement_fix.json
$PY -B $T/check_placement.py $D/placement_fix.json $D/chk_fix.json
