"""[rf final] chosen net vs the as-built dZ assumption (edge C 0 / 0.02 / 0.05 pF). usage: emsim-python sens_cedge.py -> sens_cedge.json"""
import sys, os, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0], "--dz-json", "none"]
exec(open(os.path.join(HERE, "rf_final.py")).read().split("R = dict(model=")[0])   # chain + runs only
import numpy as np
pi = ML.pi_from_json(json.load(open(os.path.join(HERE, "rf_final.json")))["chosen"]["pi"])
out = {}
for c in ("0.0", "0.02", "0.05"):
    env = dict(os.environ, C_EDGE_PF=c)
    subprocess.run([sys.executable, os.path.join(HERE, "asbuilt_dz.py")], env=env, capture_output=True, check=True)
    J = json.load(open(os.path.join(HERE, "asbuilt_dz.json")))
    d = np.interp(f, np.array(J["f"]), np.array(J["dZ_re"])) + 1j * np.interp(f, np.array(J["f"]), np.array(J["dZ_im"]))
    out[c] = {k: (round(v["eta_min"] * 100, 2), round(v["S11_max_dB"], 2)) for k, v in
              (("body", ev(dict(E, Z=E["Z"] + d), pi)), ("free", ev(dict(Bx, Z=Bx["Z"] + d), pi)), ("corner D", ev(dict(D, Z=D["Z"] + d), pi)))}
subprocess.run([sys.executable, os.path.join(HERE, "asbuilt_dz.py")], capture_output=True, check=True)   # restore the 0.02 pF file
json.dump(out, open(os.path.join(HERE, "sens_cedge.json"), "w"), indent=1); print(out)
