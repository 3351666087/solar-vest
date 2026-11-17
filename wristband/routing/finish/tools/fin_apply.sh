#!/bin/zsh
# [finish] apply ROUTES to board IN -> OUT, KiCad DRC (refill, board's own .kicad_dru); errors -> strip errors-only and re-check.
# usage: fin_apply.sh RUNDIR IN_BASENAME ROUTES.json OUT_BASENAME     prints "OUT unconnected U errors E"
R=$1; IN=$2; RT=$3; OUT=$4
T=/path/to/SolarVest_work/wristband/v3/finish/tools
PY=python3
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
cnt() { $PY -c "import json,sys;d=json.load(open(sys.argv[1]));print(len(d.get('unconnected_items',[])), sum(1 for v in d['violations'] if v['severity']=='error'))" $1; }
cd $R
$KPY -B $T/maze_finish.py apply $IN.kicad_pcb $RT $OUT.kicad_pcb 2>&1 | grep -v "Debug\|assert" | tail -1
for e in kicad_pro kicad_dru kicad_prl; do [[ -f $IN.$e ]] && sed "s/$IN.kicad_pro/$OUT.kicad_pro/g" $IN.$e > $OUT.$e; done
python3 $T/drc.py $OUT.kicad_pcb drc_$OUT.json --refill > /dev/null
set -- $(cnt drc_$OUT.json); echo "$OUT applied: unconnected $1 errors $2"
for k in 1 2 3; do
  [[ $2 == 0 ]] && break
  MAZE_STRIP_ERRORS_ONLY=1 $KPY -B $T/maze_finish.py strip $OUT.kicad_pcb drc_$OUT.json $OUT.kicad_pcb 2>&1 | grep -v "Debug\|assert" | tail -1
  python3 $T/drc.py $OUT.kicad_pcb drc_$OUT.json --refill > /dev/null; set -- $(cnt drc_$OUT.json); echo "   after strip: unconnected $1 errors $2"
done
echo "$OUT unconnected $1 errors $2"
