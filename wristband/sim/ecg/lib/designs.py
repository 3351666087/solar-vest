"""The ECG input-network designs compared by SIM-06/07 (single source of truth for every script).

INITIAL  ARCHITECTURE.md §3.3 / §7.2 as frozen: C_CM 22 pF per input, C_DIFF 100 pF, RLD feedback = TI's
         "typical values" REXT 1 MΩ ‖ CEXT 1.5 nF (SBAS502C p36 Fig 40), internal RLDREF = (AVDD+AVSS)/2, gain 6,
         AVDD_ECG from TPS7A0230PDBVR (U3).
FINAL    outcome of sim07_design_sweep.py (C_CM / C_DIFF stage 1, RLD stage 2) and of SIM-06:
           C_CM   : DNP (0402 pads kept)       C_DIFF : DNP (0402 pad kept)
           RLD    : CEXT 150 pF C0G in series with Rz 470 kΩ between RLDOUT and RLDINV, REXT DNP (0402 pad kept)
           RLDREF : internal (RLDREF_INT = 1), as in ARCH
           PGA gain 4
           U3     : TPS7A2030PDBVR (C963429), same SOT-23-5 footprint and pinout as TPS7A0230PDBVR   <- SIM-06 change
EXTREF   FINAL network with RLDREF from AVDD by 2 × 10 MΩ + 1 µF (RLDREF_INT = 0): the first SIM-06 candidate, rejected
         because it lowers the AVDD-noise coupling only if the ADS1291 input impedance is not referenced to AVDD and
         raises it otherwise (sim06 table, 'extref' rows).
FINAL_REXT = FINAL with REXT 10 MΩ fitted (fallback if the bench shows RLD wind-up problems), reported for comparison.
The sweep script re-derives the RLD choice from its selection rule and warns if it disagrees with FINAL.
"""
from params import P

_ref = P["rldref_ext"]["value"]
RLDREF_EXT = ("ext", _ref["r_top"], _ref["r_bot"], _ref["c"])

INITIAL = dict(Ccm=[22e-12, 22e-12], Cdiff=100e-12, rext=1e6, cext=1.5e-9, rz=0, rldref="int")
FINAL = dict(Ccm=[0.0, 0.0], Cdiff=0.0, rext=0, cext=150e-12, rz=470e3, rldref="int")
EXTREF = dict(FINAL, rldref=RLDREF_EXT)
FINAL_REXT = dict(FINAL, rext=10e6)
LDO = {"initial": "TPS7A0230PDBVR", "final": "TPS7A2030PDBVR"}
GAIN = {"initial": 6, "final": 4}
FINAL_INTREF = FINAL            # kept for scripts written before the RLDREF decision
DESIGNS = {"initial": (INITIAL, 6), "final": (FINAL, 4), "final+REXT10M": (FINAL_REXT, 4)}
