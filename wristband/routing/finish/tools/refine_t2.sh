#!/bin/zsh
# [track2] extra refine pass with a stronger critical-pair pull: zsh refine_t2.sh IN.json OUTDIR SEED SPREAD HALO CRIT_W
set -e
IN=$1; OUT=$2; SEED=$3; SP=$4; HA=$5; CW=$6
T=/path/to/SolarVest_work/wristband/v3/track2/tools; PY=python3
mkdir -p $OUT/tmp
export TMPDIR=$OUT/tmp OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
export G1_ZFILE=/path/to/SolarVest_work/wristband/v3/track2/work/board_zones_t2_layout.json G1_NO_ISLAND=1 G1_VARIANT=v3f
export G1_OPTS="gap=dru,jlc=full,ufpc" G1_ZONES=L43W37_t2 G1_HOVR="D14:1.0" G1_TAG=grow
env G1_SPREAD=$SP G1_HALO=$HA G1_CRIT_W=$CW $PY -B $T/refine.py $IN $OUT/pl_C.json --iters 2000000 --seed $SEED --t0 ${T0:-0.3}
env G1_SPREAD=$SP G1_HALO=$HA G1_CRIT_W=$CW $PY -B $T/refine.py $OUT/pl_C.json $OUT/placement.json --iters 1000000 --seed 9 --t0 0.1
G1_CRIT_W=200 $PY -B $T/check_placement.py $OUT/placement.json $OUT/chk.json || true
