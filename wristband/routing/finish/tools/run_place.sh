#!/bin/zsh
# V3-G1 placement run: anneal -> legalise -> independent check -> picture.
# usage: run_place.sh TAG ZONES VARIANT OPTS SEED ITERS      (OPTS: comma list or "-")
TAG=$1; export G1_ZONES=$2; export G1_VARIANT=$3; O=$4; SEED=${5:-7}; ITERS=${6:-1200000}
[[ "$O" == "-" ]] && O=""
export G1_OPTS=$O; export G1_TAG=$TAG
PY=python3
D=/path/to/SolarVest_work/wristband/v3/layout
T=$D/tools; WK=$D/work
LOG=$D/logs/place_${TAG}_s${SEED}.log
{
echo "== $(date -u +%FT%TZ) run_place $TAG zones=$G1_ZONES variant=$G1_VARIANT opts=$G1_OPTS seed=$SEED iters=$ITERS"
$PY -B $T/autoplace.py --iters $ITERS --seed $SEED --out $WK/pl_${TAG}_s${SEED}.json
$PY -B $T/legalize.py $WK/pl_${TAG}_s${SEED}.json $WK/pl_${TAG}_s${SEED}_L.json
$PY -B $T/refine.py $WK/pl_${TAG}_s${SEED}_L.json $WK/pl_${TAG}_s${SEED}_R.json --iters ${REFINE:-1500000} --seed $SEED
$PY -B $T/evalpl.py $WK/pl_${TAG}_s${SEED}_R.json
$PY -B $T/check_placement.py $WK/pl_${TAG}_s${SEED}_R.json $WK/chk_${TAG}_s${SEED}.json
$PY -B $T/slack.py $WK/pl_${TAG}_s${SEED}_R.json $WK/slack_${TAG}_s${SEED}.json
$PY -B $T/view.py $WK/pl_${TAG}_s${SEED}_R.json $D/img/place_${TAG}_s${SEED}.png "$TAG: anneal seed $SEED + legalise + refine"
echo "== $(date -u +%FT%TZ) done"
} > $LOG 2>&1
tail -22 $LOG
