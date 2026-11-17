#!/bin/zsh
# [finish] one rip-and-reroute trial: rip router copper in WINDOWS (rip.py) -> DRC -> dump -> pfroute (PRM) -> apply + DRC + strip.
# usage: fin_try.sh RUNDIR IN OUT "WINDOWS" PRM.json [KEEP] [ONLY]      (MAZE_KEEP_FROM must name the fan-out board)
R=$1; IN=$2; OUT=$3; WIN=$4; PRM=$5; KEEP=${6:-GND,VDD_1V8}; ONLY=${7:-}
T=/path/to/SolarVest_work/wristband/v3/finish/tools
PY=python3
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
cd $R
$KPY -B $T/rip.py $IN.kicad_pcb ${OUT}_x.kicad_pcb "$WIN" "$KEEP" "$ONLY" 2>&1 | grep -v "Debug\|assert\|swig"
for e in kicad_pro kicad_dru kicad_prl; do [[ -f $IN.$e ]] && sed "s/$IN.kicad_pro/${OUT}_x.kicad_pro/g" $IN.$e > ${OUT}_x.$e; done
python3 $T/drc.py ${OUT}_x.kicad_pcb drc_${OUT}_x.json --refill > /dev/null
for k in 1 2 3 4; do                                   # remove dangling router stubs left by the rip, inside the windows only
  nd=$(python3 $T/drcwin.py drc_${OUT}_x.json "$WIN" drcw_${OUT}.json)
  [[ $nd == 0 ]] && break
  $KPY -B $T/maze_finish.py strip ${OUT}_x.kicad_pcb drcw_${OUT}.json ${OUT}_x.kicad_pcb 2>&1 | grep -v "Debug\|assert\|swig" | tail -1
  python3 $T/drc.py ${OUT}_x.kicad_pcb drc_${OUT}_x.json --refill > /dev/null
done
$KPY -B $T/maze_finish.py dump ${OUT}_x.kicad_pcb drc_${OUT}_x.json geom.json plate_forbidden_nets.json d_$OUT.json 2>&1 | grep dumped
[[ -n "$PZ" ]] && python3 $T/pzpatch.py d_$OUT.json "$PZ"
$PY -B $T/pfroute.py d_$OUT.json r_$OUT.json $PRM | tail -1
$T/fin_apply.sh $R ${OUT}_x r_$OUT.json $OUT | tail -1
