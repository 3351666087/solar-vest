#!/bin/zsh
# [S2e] rip-up-and-reroute passes on a stripped board (after finish2.sh's strip stage): dump -> maze_rrr -> apply -> RF patch -> DRC;
# a pass with errors gets an errors-only strip (dangling router copper stays: the next pass reconnects it). Keeps the best 0-error board.
# usage: finish3.sh RUNDIR START_BASENAME OUT_PREFIX [MAXPASS]
R=$1; cur=$2; OUT=$3; MAXP=${4:-4}
T=/path/to/SolarVest_work/wristband/v3/layout/tools
PY=python3
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
export MAZE_KEEP_FROM=$R/v3f_g1_fan.kicad_pcb MAZE_GRID=${MAZE_GRID:-0.025}
cnt() { $PY -c "import json,sys;d=json.load(open(sys.argv[1]));print(len(d.get('unconnected_items',[])), sum(1 for v in d['violations'] if v['severity']=='error'))" $1; }
set -- $(cnt $R/drc_$cur.json); best=999; [[ $2 == 0 ]] && best=$1; bestb=$cur; stall=0
for p in $(seq 1 $MAXP); do
  nx=${OUT}_r$p
  $KPY -B $T/maze_finish.py dump $R/$cur.kicad_pcb $R/drc_$cur.json $R/geom.json $R/plate_forbidden_nets.json $R/rrr_${OUT}_$p.json > /dev/null 2>&1
  $PY -B $T/maze_finish.py rrr $R/rrr_${OUT}_$p.json $R/rrr_${OUT}_${p}_out.json > $R/rrr_${OUT}_$p.log 2>&1; tail -1 $R/rrr_${OUT}_$p.log
  $KPY -B $T/maze_finish.py apply $R/$cur.kicad_pcb $R/rrr_${OUT}_${p}_out.json $R/$nx.kicad_pcb 2>&1 | grep applied
  $KPY -B $T/rf_patch_s2e.py $R/$nx.kicad_pcb 2>&1 | grep "rf patch"
  python3 $T/drc.py $R/$nx.kicad_pcb $R/drc_$nx.json --refill > /dev/null
  set -- $(cnt $R/drc_$nx.json); echo "rrr $p: unconnected $1 errors $2"
  if [[ $2 != 0 ]]; then
    for e in kicad_pcb kicad_pro kicad_dru; do cp $R/$nx.$e $R/${nx}_raw.$e 2>/dev/null; done; cp $R/drc_$nx.json $R/drc_${nx}_raw.json
    MAZE_STRIP_ERRORS_ONLY=1 $KPY -B $T/maze_finish.py strip $R/$nx.kicad_pcb $R/drc_$nx.json $R/$nx.kicad_pcb 2>&1 | grep stripped
    python3 $T/drc.py $R/$nx.kicad_pcb $R/drc_$nx.json --refill > /dev/null; set -- $(cnt $R/drc_$nx.json); echo "   after errors-only strip: unconnected $1 errors $2"
  fi
  if [[ $2 == 0 && $1 -lt $best ]]; then best=$1; bestb=$nx; stall=0; else stall=$((stall + 1)); fi
  cur=$nx
  [[ $best == 0 || $stall -ge ${STALL:-2} ]] && break
done
echo "BEST $bestb $best"
