"""LIB — chest interface board (v3.1).

VLOAD from the back unit (cable J6 ↔ J1) feeds the BITalino Core battery input through an LM66100 ideal diode.
Two 2.7 V 10 F supercaps in series (precharged through B5819W + 33 Ω, so they sit ~0.2 V below VLOAD)
take over through a P-MOS when VLOAD disappears (cable pulled, magnetic connector glitch): sim TB5 gives 17 s (stack
not yet fully precharged, 3.3 V brown-out assumed) to ~60 s (full battery, fully precharged) at 65 mA. Precharge to 90 % takes ~7 min.
This is LM66100 datasheet §9.2.3 "ORing with discrete MOSFET": CE tied to the backup rail, ST drives the backup P-FET.
SYNC from the back unit goes to BITalino digital input I1 through 1 kΩ and a BAT54S clamp.
"""
from hwcommon import *

gnd, vload, vbit, vsc, scmid = Net("GND"), Net("VLOAD"), Net("VBIT"), Net("VSC"), Net("SC_MID")
for n in (gnd, vload): n.drive = POWER
J1 = mk("PH5", "input", ref="J1")                       # from PMB-H J6: 1 VLOAD, 2 GND, 3 SYNC, 4 LIB_EN, 5 GND
sync_in, liben = Net("SYNC_IN"), Net("LIB_EN")
J1[1] += vload; J1[2] += gnd; J1[3] += sync_in; J1[4] += liben; J1[5] += gnd
D1 = mk("SMF5V0A", "input", ref="D1", value="SMF5.0A"); D1["A1"] += vload; D1["A2"] += gnd
C1 = mk("C22u", "input", ref="C1"); C1[1] += vload; C1[2] += gnd
C2 = mk("C100n", "input", ref="C2"); C2[1] += vload; C2[2] += gnd

# ideal-diode path VLOAD → VBIT, backup path VSC → VBIT
st = Net("ST_N")
U1 = mk("LM66100", "oring", ref="U1"); U1[1] += vload; U1[2] += gnd; U1[3] += vsc; U1[4] += NC; U1[5] += st; U1[6] += vbit
R1 = mk("R100k", "oring", ref="R1"); R1[1] += st; R1[2] += vbit
Q1 = mk("AO3401A", "oring", ref="Q1"); Q1["S"] += vbit; Q1["D"] += vsc; Q1["G"] += st
C3 = mk("C22u", "oring", ref="C3"); C3[1] += vbit; C3[2] += gnd
C4 = mk("C100n", "oring", ref="C4"); C4[1] += vbit; C4[2] += gnd

# supercap stack, precharge, balancing
pre = Net("PRE")
D2 = mk("B5819W", "holdup", ref="D2"); D2["A"] += vload; D2["K"] += pre
R2 = mk("R33_2512", "holdup", ref="R2"); R2[1] += pre; R2[2] += vsc
SC1 = mk("SUPERCAP", "holdup", ref="SC1"); SC1[1] += vsc; SC1[2] += scmid
SC2 = mk("SUPERCAP", "holdup", ref="SC2"); SC2[1] += scmid; SC2[2] += gnd
R3 = mk("R100k", "holdup", ref="R3"); R3[1] += vsc; R3[2] += scmid
R4 = mk("R100k", "holdup", ref="R4"); R4[1] += scmid; R4[2] += gnd

# outputs
J2 = mk("PH2", "output", ref="J2"); J2[1] += vbit; J2[2] += gnd               # → BITalino battery socket
sync_out = Net("SYNC_OUT")
R5 = mk("R1k", "output", ref="R5"); R5[1] += sync_in; R5[2] += sync_out
D3 = mk("BAT54S", "output", ref="D3"); D3["A"] += gnd; D3["K"] += vbit; D3["COM"] += sync_out
J3 = mk("PH2", "output", ref="J3"); J3[1] += sync_out; J3[2] += gnd           # → BITalino I1 (UC-E6 adapter)

for i, n in enumerate((vload, vbit, vsc, gnd, liben), 1):
    t = mk("TP", "test", ref=f"TP{i}"); t[1] += n
for i in range(1, 3): mk("HOLE", "mech", ref=f"H{i}")

if __name__ == "__main__":
    ERC()
    generate_netlist(file_="libb.net")
    export_parts("libb_parts.json")
