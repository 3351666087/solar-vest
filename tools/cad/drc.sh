#!/bin/zsh
# usage: drc.sh <board> <report>
K=~/Applications/KiCad/KiCad/KiCad/KiCad.app/Contents
"$K/MacOS/kicad-cli" pcb drc --severity-all --format json -o "$2" "$1" >/dev/null 2>&1
python3 - "$2" <<'PY'
import json, sys, collections
d = json.load(open(sys.argv[1]))
c = collections.Counter(v["type"] for v in d.get("violations", []))
u = len(d.get("unconnected_items", []))
print("violations:", dict(c), "| unconnected:", u)
PY
