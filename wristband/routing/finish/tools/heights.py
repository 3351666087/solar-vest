"""ref -> maximum seated height (mm) of every main-board part, from the SIM-14 tables (sim/thermal-mech/sim14_stack.py
BOM_MAP / HEIGHTS, each with its datasheet page) plus the Integrate additions (integrate/checks/sim14_integrate.py).
Cached in layout/work/heights.json. Parts not in the BOM (copper-only, DNP) get 0.0 (DNP pads carry nothing)."""
import json, os, sys, io, contextlib
W = "/path/to/SolarVest_work/wristband"
CACHE = W + "/layout/work/heights.json"


def _compute():
    sys.path.insert(0, W + "/sim/thermal-mech"); sys.path.insert(0, W + "/mech")
    cwd = os.getcwd(); os.chdir(W + "/sim/thermal-mech")
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            import sim14_stack as S
            G = S.G
            add = {"X2SON_DQN_TPS7A20": ((0.30, 0.35, 0.40), "U3"), "SC70-6_SIP32431": ((0.80, 0.95, 1.10), "U12"),
                   "SOT23_BAS21": ((0.90, 1.00, 1.10), "D1"), "SOT23_MMBT3904": ((0.89, 1.00, 1.12), "Q2 Q3")}
            for k, (h, refs) in add.items():
                G.HEIGHTS[k] = dict(h=h, src="integrate/checks/sim14_integrate.py", refs=refs); S.H[k] = h
            S.BOM_MAP.update({"C5220164": "X2SON_DQN_TPS7A20", "C141606": "SC70-6_SIP32431", "C8661": "SOT23_BAS21",
                              "C20526": "SOT23_MMBT3904", "C76886": "0402_PASSIVE", "C2220990": "0402_PASSIVE",
                              "C521065": "0402_PASSIVE", "C76951": "0402_PASSIVE"})
            bom = S.bom_table(S.allowances(S.dims(ppg="W")))
    finally:
        os.chdir(cwd)
    out = {}
    for r in bom:
        for ref in r["refs"].split(","):
            out[ref.strip()] = dict(h=r["h_max"], key=r["key"], part=r["part"])
    return out


def heights(full=False):
    if os.path.exists(CACHE):
        d = json.load(open(CACHE))
    else:
        d = _compute()
        os.makedirs(os.path.dirname(CACHE), exist_ok=True)
        json.dump(d, open(CACHE, "w"), indent=1)
    return d if full else {k: v["h"] for k, v in d.items()}


if __name__ == "__main__":
    d = heights(True)
    print(len(d), sorted(((v["h"], k) for k, v in d.items()), reverse=True)[:22])
