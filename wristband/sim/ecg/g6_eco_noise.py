"""Stage-2b ECO re-check of the ECG noise and the display artefact with the electrode chains 2 x 680 k (R301-R306) and the window
frame grounded (E-1). Nothing in the existing scripts is edited:
  (1) g6_display.py is run unchanged (runpy) with params r_prot = 680 k; its output is redirected to results/eco/g6_display_680k.json
      (frame floating / grounded / none rows of results/com_caps.json; "grounded" = the E-1 fix as built).
  (2) in-vivo noise: the v2 SIM-07 noise function (v2/sim/ecg/sim07_v2_verify.py section F: ngspice .noise of the network incl.
      the chain resistors, TVS + lead-off shot noise through (Z_el + chain), ADS1291 gain-4 noise over 0.5-40 Hz) for 330 k and 680 k,
      nominal in-vivo electrodes and the worst in-vivo set of v2 (k2/0.5/2 ph-80 a3 0.5), plus the ARCH grid corners 1M|10n, 10M|1n.
  (3) signal attenuation 0.5-40 Hz and the phase at 40 Hz (sim07_common.signal_att), nominal in-vivo, 330 k vs 680 k.
M2 (ARCH, as written): <= 10 uVpp input-referred over 0.5-40 Hz with the display running; bench floor = input short 3.99 uVpp.
Writes results/eco/g6_eco_noise.json."""
import json, math, time, runpy, pathlib, sys
import numpy as np
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / "lib"))
from params import P
from sim07_v2_common import S, FINAL, STRUCT, V, add_caps, default_cfg, netlist, Q, signal_att
t0 = time.time(); (HERE / "results" / "eco").mkdir(parents=True, exist_ok=True)
S_RULE = "V2-B rule: B.Cu + L5 void"; NF = V("ads_noise_500sps"); kT = 1.380649e-23 * 310; q = 1.602e-19
OUT = {}


def noise(relist, il, rch):
    cfg = add_caps(default_cfg(**FINAL, Rin=V("ads_rin_loff")), STRUCT[S_RULE]); cfg["Re"] = relist
    S.run(netlist(dict(cfg, vecg_ac=1.0), ".noise v(inp,inn) Vecg dec 40 0.5 40")); S.cmd("setplot noise1")
    f = S.vec("frequency").real; on = np.abs(S.vec("onoise_spectrum")); th = math.sqrt(np.trapezoid(on ** 2, f))
    sh = 0.0
    for (Rr, C), itv in ((relist[0], V("i_tvs_leak_typ")), (relist[2], V("i_tvs_leak_typ"))):
        z = abs(Rr / (1 + 2j * math.pi * f * Rr * C)); sh += np.trapezoid(2 * q * itv * z ** 2, f) + np.trapezoid(2 * q * il * (z + 2 * rch) ** 2, f)
    ads = NF[4][0] * math.sqrt((40 - 0.5) / 131) * 1e-6; tot = math.sqrt(th ** 2 + sh + ads ** 2)
    return dict(thermal_uV=th * 1e6, shot_uV=math.sqrt(sh) * 1e6, ads_uV=ads * 1e6, total_uVrms=tot * 1e6, total_uVpp=tot * 1e6 * 6.6)


SETS = {"in-vivo nominal": Q.invivo_electrodes((1.0, 1.0, 1.0), -60.0, 0.75), "in-vivo worst of v2 (k2/0.5/2 ph-80 a3 0.5)": Q.invivo_electrodes((2.0, 0.5, 2.0), -80.0, 0.5),
        "ARCH 1M|10n": [(1e6, 10e-9)] * 3, "ARCH 10M|1n": [(10e6, 1e-9)] * 3}
for rch in (330e3, 680e3):
    P["r_prot"]["value"] = rch
    key = f"2 x {rch/1e3:.0f} k"; OUT[key] = {}
    for sn, rel in SETS.items():
        OUT[key][sn] = {n: noise(rel, il, rch) for n, il in (("lead-off off", 0.0), ("lead-off 6 nA", 6e-9))}
    c = add_caps(default_cfg(**FINAL, Rin=V("ads_rin_loff")), STRUCT[S_RULE]); c["Re"] = SETS["in-vivo nominal"]
    a = signal_att(c); OUT[key]["signal_att_nominal"] = dict(max_att=a[0], phase40_deg=a[1])
    print(key, {sn: round(v["lead-off 6 nA"]["total_uVpp"], 2) for sn, v in OUT[key].items() if sn in SETS}, "att", OUT[key]["signal_att_nominal"], flush=True)
OUT["input_short_uVpp"] = NF[4][0] * math.sqrt((40 - 0.5) / 131) * 6.6

# (1) display artefact with 680 k chains (g6_display.py unchanged, output redirected)
P["r_prot"]["value"] = 680e3
_wt = pathlib.Path.write_text
def _redirect(self, data, *a, **k):
    if self.name == "g6_display.json": self = HERE / "results" / "eco" / "g6_display_680k.json"
    return _wt(self, data, *a, **k)
pathlib.Path.write_text = _redirect
runpy.run_path(str(HERE / "g6_display.py"), run_name="__main__")
pathlib.Path.write_text = _wt
OUT["runtime_s"] = time.time() - t0
(HERE / "results" / "eco" / "g6_eco_noise.json").write_text(json.dumps(OUT, indent=1))
print("done %.0f s" % (time.time() - t0))
