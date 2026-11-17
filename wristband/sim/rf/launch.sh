#!/bin/bash
# usage: launch.sh TAG CASE LEVEL 'CAND_JSON' 'VAR_JSON' [extra args]   (foreground; start it as a background task)
# log: logs/TAG_CASE_LEVEL.log ; stop: touch runs/TAG_CASE_LEVEL.STOP
cd "$(dirname "$0")"
TAG=$1; CASE=$2; LEVEL=$3; CAND=${4:-'{}'}; VAR=${5:-'{}'}; shift 5
rm -f "runs/${TAG}_${CASE}_${LEVEL}.STOP"
echo "$(date -u +%FT%TZ) start ${TAG}_${CASE}_${LEVEL} cand=${CAND} var=${VAR} $*" >> logs/launch_history.log
/path/to/SolarVest_work/wristband/envs/emsim/bin/python -u run_v3f.py --tag "$TAG" --case "$CASE" --level "$LEVEL" \
   --cand "$CAND" --var "$VAR" "$@" > "logs/${TAG}_${CASE}_${LEVEL}.log" 2>&1
RC=$?
echo "$(date -u +%FT%TZ) end   ${TAG}_${CASE}_${LEVEL} rc=${RC}" >> logs/launch_history.log
exit $RC
