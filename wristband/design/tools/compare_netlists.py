"""Cross-check: the netlist KiCad derives from the generated schematic (kicad-cli sch export netlist) must contain exactly the
same (net -> set of ref.pin) connectivity as the SKiDL source (out/<board>/parts.json). Catches any label/placement bug in
tools/sch.py.   usage: python compare_netlists.py <board> <kicad_netlist.net>
"""
import json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from kisexp import parse, find, first
board, kn = sys.argv[1], sys.argv[2]
DESIGN = os.path.dirname(HERE)
parts = json.load(open(os.path.join(DESIGN, "out", board, "parts.json")))
sk = {}
for ref, p in parts.items():
    for num, net in p["pins"].items():
        if net: sk.setdefault(net, set()).add(f"{ref}.{num}")
tree = parse(open(kn).read())
ki = {}
for nets in find(tree, "nets"):
    for n in find(nets, "net"):
        name = first(n, "name")[1].lstrip("/")
        nodes = {f"{first(x, 'ref')[1]}.{first(x, 'pin')[1]}" for x in find(n, "node")}
        if name.startswith("unconnected-") or len(nodes) == 0: continue
        ki[name] = nodes
# KiCad names a net after its label; single-pin "unconnected" nets are NC pins
diff = []
for net in sorted(set(sk) | set(ki)):
    a, b = sk.get(net, set()), ki.get(net, set())
    if a != b: diff.append(f"{net}: only SKiDL {sorted(a - b)} only KiCad {sorted(b - a)}")
print(f"{board}: {len(sk)} SKiDL nets, {len(ki)} KiCad nets, {len(diff)} differences")
for d in diff[:40]: print("  ", d)
sys.exit(1 if diff else 0)
