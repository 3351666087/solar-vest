"""[layout] try swapping part A with nearby parts (or moving it to given spots) and keep the first legal result with fewer critical pairs.
usage: venv-python tryswap.py IN.json OUT.json A NEAR_REF RADIUS"""
import json, math, subprocess, sys, os
inp, out, A, NEAR, RAD = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5])
PY = sys.executable; T = os.path.dirname(os.path.abspath(__file__))
src = json.load(open(inp)); pl = src["parts"]
a = pl[A]; n = pl[NEAR]
cands = sorted([r for r, q in pl.items() if r != A and not q.get("anchor") and q["side"] == a["side"]
                and math.hypot(q["x"] - n["x"], q["y"] - n["y"]) < RAD], key=lambda r: math.hypot(pl[r]["x"] - n["x"], pl[r]["y"] - n["y"]))
def check(d):
    tmp = out + ".tmp.json"; json.dump(d, open(tmp, "w"), indent=1)
    r = subprocess.run([PY, "-B", T + "/check_placement.py", tmp, out + ".chk.json"], capture_output=True, text=True)
    c = json.load(open(out + ".chk.json"))
    line = [l for l in r.stdout.splitlines() if "LEGAL" in l]
    return line[0] if line else r.stdout[-300:], c
for r in cands:
    for rot_a in (None, 0, 90, 180, 270):
        d = json.loads(json.dumps(src)); p = d["parts"]
        p[A]["x"], p[A]["y"], p[r]["x"], p[r]["y"] = p[r]["x"], p[r]["y"], p[A]["x"], p[A]["y"]
        if rot_a is not None:
            p[A]["rot"] = rot_a
        line, c = check(d)
        ok = line.startswith("LEGAL") and "critical-pair 0" in line and "zone 0" in line
        print(r, rot_a, line[:120], flush=True)
        if ok:
            json.dump(d, open(out, "w"), indent=1); print("ACCEPT swap", A, "<->", r, "rot", rot_a); sys.exit(0)
print("no swap found")
