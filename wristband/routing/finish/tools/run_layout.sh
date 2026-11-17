#!/bin/zsh
# [layout] one command chain: placement -> legal check (+ critical-pair nudge) -> board -> plane fan-out -> Freerouting -> DRC / stats / pictures
# usage: run_layout.sh RUN SEED [PASSES]
#   env: G1_ZONES (tag) or G1_ZFILE (zone-file path); G1_DESIGN (design dir with parts.json, lib/, netclasses.json); G1_VARIANT (v3f);
#        G1_NO_ISLAND=1 when the zone file already carries the U10 island; NUDGE="C131 ..." parts to nudge if a critical pair is off by < 0.3 mm
set -e
RUN=$1; SEED=${2:-13}; PASSES=${3:-20}
D=/path/to/SolarVest_work/wristband/v3/layout; T=$D/tools; WK=$D/work; R=$WK/$RUN
PY=python3
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
export G1_VARIANT=${G1_VARIANT:-v3f} G1_OPTS=${G1_OPTS:-gap=dru,jlc=full,ufpc} G1_TAG=$RUN
export G1_ZONES=${G1_ZONES:-L41W34_fold1p9_fpcdwg_jointzif_raise0p15} G1_ZFILE=${G1_ZFILE:-/path/to/SolarVest_work/wristband/v3/cad/board_zones.json} G1_NO_ISLAND=${G1_NO_ISLAND:-1}
mkdir -p $R; LOG=$D/logs/chain_$RUN.log; : > $LOG
step() { echo "== $(date -u +%T) $*" | tee -a $LOG; }
if [[ "${STAGE:-all}" != route ]]; then
step fpdump;   $KPY -B $T/fpdump.py $G1_VARIANT >> $LOG 2>&1
step place;    export G1_HOVR=${G1_HOVR-D14:1.0}
               $PY -B $T/autoplace.py --iters 1500000 --seed $SEED --out $R/pl.json >> $LOG 2>&1
               $PY -B $T/legalize.py $R/pl.json $R/pl_L.json >> $LOG 2>&1
               $PY -B $T/refine.py $R/pl_L.json $R/pl_R.json --iters 2000000 --seed $SEED >> $LOG 2>&1
               $PY -B $T/refine.py $R/pl_R.json $R/pl_R2.json --iters 1500000 --seed 9 --t0 0.3 >> $LOG 2>&1
               cp $R/pl_R2.json $R/placement.json
               export G1_HOVR=${G1_HOVR_SAVE-D14:1.0}; for p in ${=NUDGE:-C131 X1 C313 C310 L202}; do rm -f $R/pl_N.json; $PY -B $T/trymove.py $R/placement.json $R/pl_N.json $p 0.3 0.05 >> $LOG 2>&1 && [ -f $R/pl_N.json ] && cp $R/pl_N.json $R/placement.json || true; done
step check;    unset G1_HOVR
               $PY -B $T/check_placement.py $R/placement.json $R/chk.json | tee -a $LOG | grep -A2 "LEGAL"
               $PY -B $T/view.py $R/placement.json $R/place.png "$RUN placement" >> $LOG 2>&1
fi
[[ "${STAGE:-all}" == place ]] && exit 0
step board;    $PY -B $T/dump_geom.py $R/geom.json >> $LOG 2>&1
               G1_GEOM=$R/geom.json $KPY -B $T/build_board.py $R/placement.json $R --l4-net VDD_1V8 --pmic-no-pour --plates-open >> $LOG 2>&1
step fanout;   $KPY -B $T/fanout_planes.py $R >> $LOG 2>&1; grep "fan-out vias" $LOG
step route;    $KPY -B $T/route_staged.py $R v3f_g1_fan v3f_$RUN --passes ${PASSES} --retry-passes ${RPASSES:-20} --threads 4 --timeout ${RTIMEOUT:-2400} ${=RFROM:+--from $RFROM} ${=RTO:+--to $RTO} >> $LOG 2>&1
step analyse;  $KPY -B $T/analyze_route.py $R v3f_$RUN >> $LOG 2>&1
               $PY $T/drc.py $R/v3f_$RUN.kicad_pcb $R/drc.json --refill | tee -a $LOG
               $KPY -B $T/layout_stats.py $R/v3f_$RUN.kicad_pcb $R/chk.json $R/drc.json $R/layout_stats.json >> $LOG 2>&1
               python3 $T/render_layers.py $R/v3f_$RUN.kicad_pcb $R/img $RUN >> $LOG 2>&1
step done
