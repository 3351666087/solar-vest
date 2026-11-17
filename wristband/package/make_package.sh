#!/bin/bash
# SolarBand V3-F production package, one command (LEAD_NOTES §2n G-7).
#   usage: v3/package/make_package.sh BOARD.kicad_pcb OUTDIR
# Builds: DRC, Gerbers + drill (zip) + fab README, JLC BOM + not-fitted / hand-fitted lists, CPL from the placement
# gate (G0-G6, G9) with the independent closed-loop check (G7) and mutation tests (G8), review pictures + checklist,
# summary. The upload folder OUTDIR/upload is written ONLY when every check passes. Exit 0 = orderable.
# Offline: no network access; EasyEDA footprints and symbols come from v3/design/lib.
# Step 0 (ruling P-6) adds pin-1 / polarity silk marks to a COPY of the board (OUTDIR/board/<name>_silk.kicad_pcb) and re-runs DRC;
# every later step uses that copy. SILK=0 skips it (the gate's R4 then turns those parts YELLOW). 6- and 8-layer boards (plan B, In5/In6)
# are both handled: the Gerber layer list is read from the board.
# Gate states: GREEN, PREVIEW (ruling P-6: only the JLC preview check remains; listed in upload/PREVIEW_CHECKS.md), YELLOW, RED, UNKNOWN.
set -u
[ $# -eq 2 ] || { echo "usage: $0 BOARD.kicad_pcb OUTDIR"; exit 2; }
BOARD=$(cd "$(dirname "$1")" && pwd)/$(basename "$1"); OUT=$2
HERE=$(cd "$(dirname "$0")" && pwd); T=$HERE/tools
PY=${PY:-python3}
KICAD_CLI=${KICAD_CLI:-kicad-cli}
export KICAD_CLI
EE=${V3_DESIGN:-$HERE/../design}/lib/easyeda.pretty
NAME=$(basename "$BOARD" .kicad_pcb)
rm -rf "$OUT/fab" "$OUT/assembly" "$OUT/gate" "$OUT/review" "$OUT/upload" "$OUT/work" "$OUT/board" "$OUT/silk"
mkdir -p "$OUT"/{fab/gerbers,assembly,gate,review,work,board,silk}
OUT=$(cd "$OUT" && pwd)
log() { echo "[$(date -u +%H:%M:%S)] $*" | tee -a "$OUT/make_package.log"; }
: > "$OUT/make_package.log"
log "board $BOARD -> $OUT"

C_SILK=0
if [ "${SILK:-1}" != "0" ]; then
  log "0/8 silk pin-1 / polarity marks on a board copy + DRC before/after"
  "$PY" "$T/add_silk_marks.py" --board "$BOARD" --out "$OUT/board/${NAME}_silk.kicad_pcb" --report "$OUT/silk" | tee -a "$OUT/make_package.log"; C_SILK=${PIPESTATUS[0]}
  if [ -f "$OUT/board/${NAME}_silk.kicad_pcb" ] && [ "$C_SILK" -ne 2 ]; then BOARD="$OUT/board/${NAME}_silk.kicad_pcb"; else log "silk step failed (code $C_SILK): original board used"; fi
  log "board used from here: $BOARD"
fi
INNER=$(grep -oE '\([0-9]+ "In[0-9]+\.Cu"' "$BOARD" | grep -oE 'In[0-9]+\.Cu' | sort -t n -k2 -n | uniq | paste -sd, -)
CU="F.Cu,${INNER:+$INNER,}B.Cu"; NCU=$(echo "$CU" | tr ',' '\n' | wc -l | tr -d ' ')
log "copper layers ($NCU): $CU"

log "1/8 DRC (board rules, zones refilled)"
"$KICAD_CLI" pcb drc --format json --severity-error --refill-zones -o "$OUT/fab/drc.json" "$BOARD" >> "$OUT/make_package.log" 2>&1; C_DRC=$?

log "2/8 Gerbers + drill (place/drill origin, Protel names, X2 attributes)"
"$KICAD_CLI" pcb export gerbers --layers "$CU",F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts \
  --subtract-soldermask --use-drill-file-origin --check-zones -o "$OUT/fab/gerbers" "$BOARD" >> "$OUT/make_package.log" 2>&1
"$KICAD_CLI" pcb export drill --format excellon --drill-origin plot --excellon-units mm --excellon-zeros-format decimal \
  --excellon-oval-format alternate --excellon-separate-th --generate-map --map-format gerberx2 -o "$OUT/fab/gerbers/" "$BOARD" >> "$OUT/make_package.log" 2>&1
rm -f "$OUT/fab/gerbers/"*.gbrjob
mkdir -p "$OUT/fab/drill_maps" && mv "$OUT/fab/gerbers/"*drl_map* "$OUT/fab/drill_maps/" 2>/dev/null  # maps stay out of the upload zip
(cd "$OUT/fab/gerbers" && zip -q -X "../${NAME}_gerbers_JLC.zip" *); C_GBR=$?
"$KICAD_CLI" pcb export pos --format csv --units mm --side both --use-drill-file-origin -o "$OUT/work/kicad_pos.csv" "$BOARD" >> "$OUT/make_package.log" 2>&1

log "3/8 BOM (JLC format) checked against v3/design"
"$PY" "$T/bom_jlc.py" --board "$BOARD" --out "$OUT/assembly" | tee -a "$OUT/make_package.log"; C_BOM=${PIPESTATUS[0]}
if [ "${STOCK:-0}" = "1" ]; then  # optional online step: JLC stock today (public parts API, read-only) -> assembly/stock_today.{json,md}
  log "3b stock today (STOCK=1)"; "$PY" "$T/stock_today.py" --out "$OUT" | tee -a "$OUT/make_package.log"
fi

log "4/8 placement gate G0-G6 + overlays G9"
"$PY" "$T/cplgate.py" --board "$BOARD" --pos "$OUT/work/kicad_pos.csv" --out "$OUT/gate" --waivers "$HERE/waivers.yaml" | tee -a "$OUT/make_package.log"; C_GATE=${PIPESTATUS[0]}

log "5/8 G7 closed loop: CPL vs Gerber copper / paste / silk"
"$PY" "$T/g7_verify.py" --cpl "$OUT/gate/candidate_NOT_FOR_UPLOAD/CPL_JLC.csv" --bom "$OUT/assembly/BOM_JLC.csv" \
  --gerbers "$OUT/fab/gerbers" --easyeda "$EE" --out "$OUT/gate/g7.json" | tee -a "$OUT/make_package.log"; C_G7=${PIPESTATUS[0]}

log "6/8 G8 mutation tests"
"$PY" "$T/mutate.py" --board "$BOARD" --pos "$OUT/work/kicad_pos.csv" --gate "$OUT/gate" --bom "$OUT/assembly/BOM_JLC.csv" \
  --gerbers "$OUT/fab/gerbers" --work "$OUT/work/mutants" --out "$OUT/gate/mutation_report.json" | tee -a "$OUT/make_package.log"; C_MUT=${PIPESTATUS[0]}

log "7/8 fab README, review pictures, checklist"
"$PY" "$T/fab_info.py" --board "$BOARD" --gerbers "$OUT/fab/gerbers" --drc "$OUT/fab/drc.json" --zip "$OUT/fab/${NAME}_gerbers_JLC.zip" --out "$OUT/fab" | tee -a "$OUT/make_package.log"
"$PY" "$T/review_pics.py" --board "$BOARD" --gate "$OUT/gate" --out "$OUT/review" | tee -a "$OUT/make_package.log"

log "8/8 summary"
"$PY" "$T/summary.py" --out "$OUT" --codes "silk=$C_SILK,drc=$C_DRC,gerber=$C_GBR,bom=$C_BOM,gate=$C_GATE,g7=$C_G7,mutations=$C_MUT" | tee -a "$OUT/make_package.log"; C_SUM=${PIPESTATUS[0]}
[ "$C_SILK" -eq 1 ] && { log "silk marks made DRC worse: not orderable (see $OUT/silk/silk_marks.md)"; C_SUM=1; }

if [ "$C_SUM" -eq 0 ]; then
  mkdir -p "$OUT/upload"
  cp "$OUT/fab/${NAME}_gerbers_JLC.zip" "$OUT/assembly/BOM_JLC.csv" "$OUT"/gate/upload_*/CPL_JLC.csv "$OUT"/gate/upload_*/PREVIEW_CHECKS.md "$OUT/upload/"
  (cd "$OUT/upload" && shasum -a 256 * > manifest.sha256)
  NP=$(grep '^| ☐ |' "$OUT/upload/PREVIEW_CHECKS.md" | grep -vc '| Ref |')  # header row excluded
  log "ORDERABLE after $NP JLC preview checks: upload set in $OUT/upload; tick upload/PREVIEW_CHECKS.md and review/checklist.md in the JLC preview before paying"
  exit 0
fi
log "NOT ORDERABLE: no upload folder written; see $OUT/summary.md and $OUT/gate/cplgate_report.md"
exit 1
