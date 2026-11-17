#!/bin/bash
# usage: launch_lid.sh TAG CASE 'OPT_JSON'   (foreground; start as a background task). log logs/TAG_CASE_f.log
cd "$(dirname "$0")"; T=$1; C=${2:-body}; O=${3:-{\}}
echo "$(date -u +%FT%TZ) start ${T}_${C}_f ${O}" >> logs/launch_history.log
/path/to/SolarVest_work/wristband/envs/emsim/bin/python -u run_lid.py --tag "$T" --case "$C" --opt "$O" --decay 1e-4 --tmax 12 > "logs/${T}_${C}_f.log" 2>&1
RC=$?; echo "$(date -u +%FT%TZ) end   ${T}_${C}_f rc=${RC}" >> logs/launch_history.log; exit $RC
