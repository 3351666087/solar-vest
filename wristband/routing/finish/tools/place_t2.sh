#!/bin/zsh
# [track2 Q-5] placement chain of the layout lane on the 40 x 34 zone file, with placer-only spreading and escape halos.
#   zsh place_t2.sh OUTDIR SEED SPREAD_MM HALO_MM
# autoplace + refine x2 run with G1_SPREAD / G1_HALO (pair_gap in place_main.py); legalize and check_placement run with the real rules only.
set -e
OUT=$1; SEED=$2; SP=$3; HA=$4
T=/path/to/SolarVest_work/wristband/v3/track2/tools
PY=python3
mkdir -p $OUT/tmp
export TMPDIR=$OUT/tmp OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 VECLIB_MAXIMUM_THREADS=1
export G1_ZFILE=/path/to/SolarVest_work/wristband/v3/track2/work/board_zones_t2_layout.json G1_NO_ISLAND=1 G1_VARIANT=v3f
export G1_OPTS="gap=dru,jlc=full,ufpc" G1_ZONES=L43W37_t2 G1_CRIT_W=200 G1_HOVR="D14:1.0" G1_TAG=grow
S="G1_SPREAD=$SP G1_HALO=$HA"
date
env ${=S} $PY -B $T/autoplace.py --iters 1500000 --seed $SEED --out $OUT/pl.json
$PY -B $T/legalize.py $OUT/pl.json $OUT/pl_L.json
env ${=S} $PY -B $T/refine.py $OUT/pl_L.json $OUT/pl_R.json --iters 2000000 --seed $SEED
env ${=S} $PY -B $T/refine.py $OUT/pl_R.json $OUT/placement.json --iters 1500000 --seed 9 --t0 0.3
$PY -B $T/check_placement.py $OUT/placement.json $OUT/chk.json || true
date
