"""[finish] mark pair ends at the given points as 'on the plane' (pz) in a maze dump: used for a plane-net pad that KiCad DRC shows on
the main island (connected through a pour the dump flood does not see).  usage: pzpatch.py DUMP.json "x,y;x,y" """
import json, sys
d = json.load(open(sys.argv[1])); P = [tuple(map(float, s.split(","))) for s in sys.argv[2].split(";") if s]
k = 0
for pr in d["pairs"]:
    for e in pr:
        if any(abs(e["p"][0] - x) < 0.02 and abs(e["p"][1] - y) < 0.02 for x, y in P):
            e["pz"] = True; k += 1
json.dump(d, open(sys.argv[1], "w")); print("pz patched", k)
