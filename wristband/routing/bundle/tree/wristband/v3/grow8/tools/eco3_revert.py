"""[eco3] After legalize.py: put every moved part (except U19 / U20) back to its original spot when the board stays LEGAL with 0 critical pairs.
Passes repeat until nothing changes. usage: venv-python eco3_revert.py ORIG.json LEG.json OUT.json"""
import json, math, subprocess, sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
orig, leg, outp = sys.argv[1:4]
A = json.load(open(orig)); B = json.load(open(leg))
def ok(pl):
    json.dump(pl, open(outp + ".tmp.json", "w"), indent=1)
    r = subprocess.run([sys.executable, "-B", HERE + "/check_placement.py", outp + ".tmp.json", outp + ".chk.json"], capture_output=True, text=True)
    l = ([x for x in r.stdout.splitlines() if "LEGAL" in x] or ["?"])[0]
    return l.startswith("LEGAL") and "critical-pair 0 " in l
def moved(pl):
    return sorted((math.hypot(pl["parts"][r]["x"] - q["x"], pl["parts"][r]["y"] - q["y"]), r) for r, q in A["parts"].items()
                  if r in pl["parts"] and r not in ("U19", "U20") and (pl["parts"][r]["x"], pl["parts"][r]["y"], pl["parts"][r]["rot"]) != (q["x"], q["y"], q["rot"]))
assert ok(B)
changed = True
while changed:
    changed = False
    for d, r in moved(B):
        t = json.loads(json.dumps(B)); t["parts"][r].update({k: A["parts"][r][k] for k in ("x", "y", "rot")})
        if ok(t): B = t; changed = True; print("reverted", r, round(d, 3), flush=True)
B["eco3"] = dict(from_placement=orig, method="legalize.py (greedy minimum displacement) + eco3_revert.py",
                 moved={r: dict(old={k: A["parts"][r][k] for k in ("x", "y", "rot")}, new={k: B["parts"][r][k] for k in ("x", "y", "rot")}, d_mm=round(math.hypot(B["parts"][r]["x"] - A["parts"][r]["x"], B["parts"][r]["y"] - A["parts"][r]["y"]), 3))
                        for r in ["U19", "U20"] + [r for _, r in moved(B)]})
json.dump(B, open(outp, "w"), indent=1); assert ok(B)
print("moved", len(B["eco3"]["moved"]), {r: v["d_mm"] for r, v in B["eco3"]["moved"].items()})
