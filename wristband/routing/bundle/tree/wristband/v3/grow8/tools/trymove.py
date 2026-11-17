"""[layout] small translations of one part (grid, smallest first); keep the first legal one with 0 critical pairs.
usage: venv-python trymove.py IN.json OUT.json REF [MAXSTEP_MM] [STEP]"""
import json, subprocess, sys, os, itertools
inp, out, A = sys.argv[1:4]; MX = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5; ST = float(sys.argv[5]) if len(sys.argv) > 5 else 0.05
PY = sys.executable; T = os.path.dirname(os.path.abspath(__file__))
src = json.load(open(inp))
import re
def ncrit(line):
    m = re.search(r"critical-pair (\d+)", line); return int(m.group(1)) if m else 99
_r = subprocess.run([PY, "-B", T + "/check_placement.py", inp, out + ".chk.json"], capture_output=True, text=True)
_l = ([l for l in _r.stdout.splitlines() if "LEGAL" in l] or ["?"])[0]
BASE_N = ncrit(_l) if _l.startswith("LEGAL") else 99
n = int(round(MX / ST)); steps = sorted(((i * ST, j * ST) for i in range(-n, n + 1) for j in range(-n, n + 1) if i or j), key=lambda d: d[0]**2 + d[1]**2)
for dx, dy in steps:
    d = json.loads(json.dumps(src)); d["parts"][A]["x"] = round(d["parts"][A]["x"] + dx, 3); d["parts"][A]["y"] = round(d["parts"][A]["y"] + dy, 3)
    tmp = out + ".tmp.json"; json.dump(d, open(tmp, "w"), indent=1)
    r = subprocess.run([PY, "-B", T + "/check_placement.py", tmp, out + ".chk.json"], capture_output=True, text=True)
    line = ([l for l in r.stdout.splitlines() if "LEGAL" in l] or ["?"])[0]
    if line.startswith("LEGAL") and ncrit(line) < BASE_N:
        json.dump(d, open(out, "w"), indent=1); print("ACCEPT", A, dx, dy, line); sys.exit(0)
print("none")
