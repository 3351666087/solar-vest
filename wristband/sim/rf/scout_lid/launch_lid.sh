#!/bin/bash
# usage: launch_lid.sh KIND [CASE]   (foreground; start as a background task). log logs/KIND_CASE_c.log
cd "$(dirname "$0")"; K=$1; C=${2:-body}
echo "$(date -u +%FT%TZ) start ${K}_${C}_c" >> logs/launch_history.log
/path/to/SolarVest_work/wristband/envs/emsim/bin/python -u run_lid.py --kind "$K" --case "$C" --decay 1e-4 --tmax 12 > "logs/${K}_${C}_c.log" 2>&1
RC=$?; echo "$(date -u +%FT%TZ) end   ${K}_${C}_c rc=${RC}" >> logs/launch_history.log; exit $RC
