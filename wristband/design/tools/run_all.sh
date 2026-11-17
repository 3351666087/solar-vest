#!/bin/bash
# Re-run the SolarBand V3-F schematic flow for every build variant: v3f (baseline, dense since gate-1 level 0), v3f_fldnp (front light DNP, research build)
# and the gate-1 option variants (v3/g1/dense/DENSE.md).
# Network is used only by the fetch steps (EasyEDA footprints of new C-numbers, JLC stock with --refresh-jlc); raw answers stay outside the project.
# usage: tools/run_all.sh [--refresh-jlc] [--main]
set -uo pipefail
D=/path/to/SolarVest_work/wristband/v3/design
PY=python3
K=kicad-cli
# main variants (full outputs) and the gate-1 option variants (levels 0 and 4: netlist, ERC, cross-check, parts.json, BOM, area check); "--main" skips the options
MAIN="v3f v3f_fldnp"
OPTIONS="v3f_o2m v3f_o2pack v3f_noled v3f_noled_o2pack v3f_nofl v3f_nomotor v3f_erm7 v3f_erm6 v3f_nofl_noled_nomotor"
VARIANTS="$MAIN $OPTIONS"; for a in "$@"; do [ "$a" = "--main" ] && VARIANTS="$MAIN"; done
# switches of a variant tag (src/common.py builds the same tag from them)
envof() { FL=fit; LED=fit; MOTOR=erm8; O2=std
  case "$1" in *_fldnp*) FL=dnp;; *_nofl*) FL=none;; esac
  case "$1" in *_noled*) LED=none;; esac
  case "$1" in *_nomotor*) MOTOR=none;; *_erm7*) MOTOR=erm7;; *_erm6*) MOTOR=erm6;; esac
  case "$1" in *_o2m*) O2=merged;; *_o2pack*) O2=pack;; esac; }
cd "$D/tools"
# kicad-cli in English (the system locale is zh-TW): private config copy with language = English
export KICAD_CONFIG_HOME="${TMPDIR:-/tmp}/solarband_kicfg_v3f"
mkdir -p "$KICAD_CONFIG_HOME/10.0"
for f in kicad_common.json sym-lib-table fp-lib-table; do
  [ -f "$HOME/Library/Preferences/kicad/10.0/$f" ] && cp "$HOME/Library/Preferences/kicad/10.0/$f" "$KICAD_CONFIG_HOME/10.0/"
done
sed -i '' 's/"language": "Default"/"language": "English"/' "$KICAD_CONFIG_HOME/10.0/kicad_common.json" 2>/dev/null || true

echo "== 1. reviewed footprint copy lib/easyeda_rev.pretty (copper unchanged), pin maps, copper-only footprints"
$PY review_footprints.py | head -1
$PY write_pinmaps.py
$PY gen_footprints.py | tail -1
REFRESH=0; for a in "$@"; do [ "$a" = "--refresh-jlc" ] && REFRESH=1; done
if [ $REFRESH = 1 ]; then echo "== 2. JLC stock refresh"; $PY jlc_query.py --refresh $(cat jlc_list.txt) > jlc_refresh.log; echo "   [rc] jlc_query.py $?"; fi
echo "== 3. SKiDL netlists, KiCad schematics, ERC, PDF, schematic-netlist cross-check (per variant)"
mkdir -p "$D/erc" "$D/netlist" "$D/pdf"
for V in $VARIANTS; do
  envof "$V"; mkdir -p "$D/out/$V" "$D/kicad/$V"
  ( cd "$D/src"; SB_FL=$FL SB_LED=$LED SB_MOTOR=$MOTOR SB_O2=$O2 $PY main_board.py 2>&1 | grep -v "^WARNING: \(KICAD\|fp-lib\)" | tail -1 )
  $PY sch.py $V > /dev/null
  P=solarband_${V}
  ( cd "$D/kicad/$V"
    $K sch erc --severity-all --format report -o "$D/erc/erc_$V.rpt" $P.kicad_sch 2>&1 | grep -v Fontconfig || true
    $K sch export pdf -o "$D/pdf/${P}_schematic.pdf" $P.kicad_sch 2>&1 | grep -v Fontconfig | tail -1 || true
    $K sch export netlist --format kicadsexpr -o "$D/out/$V/${P}_from_schematic.net" $P.kicad_sch 2>&1 | grep -v Fontconfig | tail -1 || true )
  $PY compare_netlists.py $V "$D/out/$V/${P}_from_schematic.net"
  cp "$D/out/$V/solarband_main.net" "$D/netlist/${P}.net"; cp "$D/out/$V/${P}_from_schematic.net" "$D/netlist/${P}_kicad.net"
done
echo "== 4. BOM, stock report, netclasses, parts.json (area + height), pin budget, footprint audit, placement proof table, area check, diff vs V2-B"
# [S1] every step prints its exit code (stage 1 found audit_footprints.py failing silently with exit 1)
for T in make_outputs.py pin_budget.py audit_footprints.py placement_proof.py area_check.py diff_v2.py; do $PY $T; echo "   [rc] $T $?"; done
grep -H "ERC messages\|Errors\|Warnings" "$D"/erc/erc_*.rpt
