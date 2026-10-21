"""PMB-H — back power & measurement board (v3.1).

Chain: panel → PPTC → reverse-polarity P-MOS → TVS → CN3791 MPPT buck charger → 1S LiPo (2500 mAh)
Measurement: 6 × INA226 on one I2C bus
  0x40 panel current, high range (0.05 Ω low-side)       0x43 panel current, indoor range (0.22 Ω, auto-ranged)
  0x41 battery current, bidirectional (0.05 Ω)            0x42 load current to the chest unit (0.1 Ω)
  0x44 reference cell #1 (panel plane)                    0x45 reference cell #2 (ambient, horizontal)
Control (XIAO nRF52840 Sense, plugged into J4/J5): charge inhibit, load switch, indoor-range select,
sync pulse and LIB enable to the chest cable J6, NTC battery temperature, charger status.
"""
import sys
from hwcommon import *

gnd, vpv, vsys, v3 = Net("GND"), Net("VPV"), Net("VSYS"), Net("3V3")
sda, scl = Net("SDA"), Net("SCL")
pv_mid_s, pv_in_s, vpv_s = Net("PV_MID_S"), Net("PV_IN_S"), Net("VPV_S")     # Kelvin sense taps
for _n in (gnd, vpv, vsys): _n.drive = POWER          # sourced by connectors / battery

# ---------------- input protection ----------------
J1 = mk("KF350", "input", ref="J1")                      # panel: 1 = PV+, 2 = PV−
pv_in_p, pv_in_n, pv_f = Net("PV_IN+"), Net("PV_IN-"), Net("PV_F")
J1[1] += pv_in_p; J1[2] += pv_in_n
F1 = mk("PPTC", "input", ref="F1"); F1[1] += pv_in_p; F1[2] += pv_f
Q1 = mk("AO3401A", "input", ref="Q1")                    # reverse-polarity P-MOS (CN3791 datasheet Fig. 3)
q1g = Net("Q1_G")
Q1["D"] += pv_f; Q1["S"] += vpv; Q1["G"] += q1g
# PV_EN (sim TB2): Q1's channel is bidirectional, so at night the battery back-feeds the panel through M1's body diode
# (0.25–10 mA depending on the panel's shunt resistance). Q8 lets the MCU turn Q1 off in the dark; R20 keeps it ON
# by default (MCU absent / unflashed), and Q1's body diode bootstraps a flat battery.
pv_en, q8d = Net("PV_EN"), Net("Q8_D")
R1 = mk("R22k", "input", ref="R1"); R1[1] += q1g; R1[2] += q8d
Q8 = mk("AO3400A", "input", ref="Q8"); Q8["D"] += q8d; Q8["S"] += gnd; Q8["G"] += pv_en
R19 = mk("R1M", "input", ref="R19"); R19[1] += q1g; R19[2] += vpv          # holds Q1 off when Q8 is off
R20 = mk("R100k", "input", ref="R20"); R20[1] += pv_en; R20[2] += v3        # default ON
D1 = mk("Z10V", "input", ref="D1"); D1["K"] += vpv; D1["A"] += q1g   # clamps |Vgs| ≤ 10 V (AO3401A max 12 V)
D2 = mk("SMAJ10A", "input", ref="D2"); D2[1] += vpv; D2[2] += gnd    # pin 1 = cathode band
for ref, key in (("C1", "C22u"), ("C2", "C22u"), ("C3", "C1u"), ("C4", "C100n")):
    c = mk(key, "input", ref=ref); c[1] += vpv; c[2] += gnd
# damping electrolytic (CN3791 datasheet: input = electrolytic + ceramic + HF cap). Its ESR damps the ~5 kHz input LC
# resonance (L1 vs the ceramics) so the MPPT loop keeps infinite gain margin whatever the IC's error-amp gm (sim TB1c)
C15 = mk("CP100u35", "input", ref="C15"); C15[1] += vpv; C15[2] += gnd

# ---------------- panel current, low side, auto-ranged ----------------
pv_mid, pv_ret = Net("PV_MID"), Net("PV_RET")
RS1B = mk("RS_220m", "pv_sense", ref="RS1B"); RS1B[1] += pv_mid; RS1B[2] += pv_in_n   # 0.22 Ω: Q2 off at full sun keeps PV_IN− > −0.3 V (INA226 abs max), RS1B ≤ 0.17 W
RS1A = mk("RS_50m", "pv_sense", ref="RS1A"); RS1A[1] += pv_ret; RS1A[2] += pv_mid
NT1 = mk("NETTIE", "pv_sense", ref="NT1"); NT1[1] += pv_ret; NT1[2] += gnd          # Kelvin point of RS1A
Q2 = mk("AO3400A", "pv_sense", ref="Q2")                 # bypasses RS1B in daylight (default ON while the panel has voltage)
q2g = Net("Q2_G"); Q2["D"] += pv_mid; Q2["S"] += pv_in_n; Q2["G"] += q2g
R2 = mk("R100k", "pv_sense", ref="R2"); R2[1] += vpv_s; R2[2] += q2g
D3 = mk("Z10V", "pv_sense", ref="D3"); D3["K"] += q2g; D3["A"] += pv_in_n
Q3 = mk("AO3400A", "pv_sense", ref="Q3")                 # MCU turns the bypass off → indoor range
rng = Net("RANGE_LO"); Q3["D"] += q2g; Q3["S"] += gnd; Q3["G"] += rng
R3 = mk("R100k", "pv_sense", ref="R3"); R3[1] += rng; R3[2] += gnd
D4 = mk("B5819W", "pv_sense", ref="D4"); D4["K"] += pv_in_n; D4["A"] += gnd   # clamps PV_IN− ≥ −0.4 V if light jumps in indoor range

# Kelvin sense taps (thin nets) for the INA226 inputs, split off at the shunt pads by net ties
NT5 = mk("NETTIE", "pv_sense", ref="NT5"); NT5[1] += pv_mid; NT5[2] += pv_mid_s
NT6 = mk("NETTIE", "pv_sense", ref="NT6"); NT6[1] += pv_in_n; NT6[2] += pv_in_s
NT7 = mk("NETTIE", "input", ref="NT7"); NT7[1] += vpv; NT7[2] += vpv_s

# ---------------- CN3791 MPPT charger ----------------
U1 = mk("CN3791", "charger", ref="U1")
sw, csp, cn_bat, mppt, com_rc, drv = Net("SW"), Net("CSP"), Net("CN_BAT"), Net("MPPT"), Net("COM_RC"), Net("DRV")
chrg, done, inh = Net("CHRG_N"), Net("DONE_N"), Net("CHG_INH")
vg = Net("VG")
U1[9] += vpv; U1[2] += gnd; U1[1] += vg; U1[10] += drv; U1[8] += csp; U1[7] += cn_bat; U1[6] += mppt
U1[3] += chrg; U1[4] += done
C5 = mk("C100n", "charger", ref="C5"); C5[1] += vg; C5[2] += vpv          # VG ↔ VCC
com = Net("COM"); U1[5] += com
R4 = mk("R120", "charger", ref="R4"); R4[1] += com; R4[2] += com_rc
C6 = mk("C220n", "charger", ref="C6"); C6[1] += com_rc; C6[2] += gnd
# V_MPPT = 1.205 × (1 + 200/51) = 5.93 V (sim study: 98 % of ideal daily energy for a hot worn panel, vs 94 % at 6.40 V;
# start threshold 1.23 × 4.92 = 6.05 V so indoor light can start the charger). ×10 values cut the night drain to ~12 µA.
R5 = mk("R200k", "charger", ref="R5"); R5[1] += vpv_s; R5[2] += mppt
R6 = mk("R51k", "charger", ref="R6"); R6[1] += mppt; R6[2] += gnd
Q4 = mk("AO3400A", "charger", ref="Q4")                  # charge inhibit: pulls MPPT low → charge current → 0 (default off = charging)
Q4["D"] += mppt; Q4["S"] += gnd; Q4["G"] += inh
R7 = mk("R100k", "charger", ref="R7"); R7[1] += inh; R7[2] += gnd
M1 = mk("AO3401A", "charger", ref="M1"); M1["S"] += vpv; M1["D"] += sw; M1["G"] += drv
D5 = mk("SS34", "charger", ref="D5"); D5["K"] += sw; D5["A"] += gnd
L1 = mk("L22u", "charger", ref="L1"); L1[1] += sw; L1[2] += csp
RCS = mk("RS_100m", "charger", ref="R8"); RCS[1] += csp; RCS[2] += cn_bat        # I_ch = 120 mV / 0.1 Ω = 1.2 A
NT2 = mk("NETTIE", "charger", ref="NT2"); NT2[1] += cn_bat; NT2[2] += vsys        # Kelvin: CN3791 BAT pin senses at R8
C7 = mk("C22u", "charger", ref="C7"); C7[1] += vsys; C7[2] += gnd
C8 = mk("C100n", "charger", ref="C8"); C8[1] += vsys; C8[2] += gnd
R9 = mk("R100k", "charger", ref="R9"); R9[1] += chrg; R9[2] += v3
R10 = mk("R100k", "charger", ref="R10"); R10[1] += done; R10[2] += v3

# ---------------- battery, NTC ----------------
rs2p, bat = Net("RS2_P"), Net("BAT+")
RS2 = mk("RS_50m", "battery", ref="RS2"); RS2[1] += rs2p; RS2[2] += bat
NT3 = mk("NETTIE", "battery", ref="NT3"); NT3[1] += rs2p; NT3[2] += vsys
J2 = mk("PH2", "battery", ref="J2"); J2[1] += bat; J2[2] += gnd
bat_s = Net("BAT_S"); NT8 = mk("NETTIE", "battery", ref="NT8"); NT8[1] += bat; NT8[2] += bat_s               # 1S LiPo 2500 mAh with PCM
ntc_adc, ntc_en = Net("NTC_ADC"), Net("NTC_EN")
J3 = mk("PH2", "battery", ref="J3"); J3[1] += ntc_adc; J3[2] += gnd           # 10k B3950 NTC taped to the cell
R11 = mk("R10k", "battery", ref="R11"); R11[1] += ntc_en; R11[2] += ntc_adc
C9 = mk("C100n", "battery", ref="C9"); C9[1] += ntc_adc; C9[2] += gnd

# ---------------- load switch to the chest unit ----------------
rs3p, vl_in, vload = Net("RS3_P"), Net("VL_IN"), Net("VLOAD")
RS3 = mk("RS_100m", "load", ref="RS3"); RS3[1] += rs3p; RS3[2] += vl_in
NT4 = mk("NETTIE", "load", ref="NT4"); NT4[1] += rs3p; NT4[2] += vsys
Q5 = mk("AO3401A", "load", ref="Q5"); q5g = Net("Q5_G")
Q5["S"] += vl_in; Q5["D"] += vload; Q5["G"] += q5g
R12 = mk("R100k", "load", ref="R12"); R12[1] += vl_in; R12[2] += q5g
C10 = mk("C1u", "load", ref="C10"); C10[1] += vl_in; C10[2] += q5g            # soft start: τ ≈ 9 ms, inrush < 1 A (sim TB5a)
q6d, load_en = Net("Q6_D"), Net("LOAD_EN")
R13 = mk("R10k", "load", ref="R13"); R13[1] += q5g; R13[2] += q6d
Q6 = mk("AO3400A", "load", ref="Q6"); Q6["D"] += q6d; Q6["S"] += gnd; Q6["G"] += load_en
R14 = mk("R100k", "load", ref="R14"); R14[1] += load_en; R14[2] += gnd
C11 = mk("C22u", "load", ref="C11"); C11[1] += vload; C11[2] += gnd
vl_in_s, vload_s = Net("VL_IN_S"), Net("VLOAD_S")
NT9 = mk("NETTIE", "load", ref="NT9"); NT9[1] += vl_in; NT9[2] += vl_in_s
NT10 = mk("NETTIE", "load", ref="NT10"); NT10[1] += vload; NT10[2] += vload_s
D6 = mk("SMF5V0A", "load", ref="D6", value="SMF5.0A"); D6["A1"] += vload; D6["A2"] += gnd
J6 = mk("PH5", "load", ref="J6")                     # chest cable: 1 VLOAD, 2 GND, 3 SYNC, 4 spare (NC), 5 GND
sync_out, sync_j = Net("SYNC_OUT"), Net("SYNC_J6")
J6[1] += vload; J6[2] += gnd; J6[3] += sync_j; J6[4] += NC; J6[5] += gnd
R15 = mk("R1k", "load", ref="R15"); R15[1] += sync_out; R15[2] += sync_j

# ---------------- 3.3 V rail ----------------
U8 = mk("ME6211", "power", ref="U8"); U8[1] += vsys; U8[2] += gnd; U8[3] += vsys; U8[5] += v3; U8[4] += NC
for ref, key, n in (("C12", "C1u", vsys), ("C13", "C1u", v3), ("C14", "C10u", v3)):
    c = mk(key, "power", ref=ref); c[1] += n; c[2] += gnd

# ---------------- INA226 × 6 ----------------
def ina(ref, a1, a0, inp, inn, vbus):
    u = mk("INA226", "meter", ref=ref)
    u["VS"] += v3; u["GND"] += gnd; u["SDA"] += sda; u["SCL"] += scl
    u["A1"] += a1; u["A0"] += a0; u["Vin+"] += inp; u["Vin-"] += inn; u["Vbus"] += vbus; u[3] += NC   # ALERT unused
    c = mk("C100n", "meter", ref="C" + ref[1:] + "0"); c[1] += v3; c[2] += gnd
    return u
ref1, ref2 = Net("REF1+"), Net("REF2+")
ina("U2", gnd, gnd, pv_ret, pv_mid_s, vpv_s)      # 0x40 panel high range
ina("U3", gnd, scl, pv_mid_s, pv_in_s, vpv_s)     # 0x43 panel indoor range
ina("U4", gnd, v3, rs2p, bat_s, bat_s)            # 0x41 battery (bidirectional)
ina("U5", gnd, sda, rs3p, vl_in_s, vload_s)       # 0x42 load
ina("U6", v3, gnd, ref1, gnd, ref1)               # 0x44 reference cell 1 (short-circuit current)
ina("U7", v3, v3, ref2, gnd, ref2)                # 0x45 reference cell 2
RS4 = mk("RS_470m", "meter", ref="RS4"); RS4[1] += ref1; RS4[2] += gnd
RS5 = mk("RS_470m", "meter", ref="RS5"); RS5[1] += ref2; RS5[2] += gnd
J7 = mk("PH2", "meter", ref="J7"); J7[1] += ref1; J7[2] += gnd
J8 = mk("PH2", "meter", ref="J8"); J8[1] += ref2; J8[2] += gnd
R17 = mk("R4k7", "meter", ref="R17"); R17[1] += sda; R17[2] += v3
R18 = mk("R4k7", "meter", ref="R18"); R18[1] += scl; R18[2] += v3

# ---------------- MCU sockets (XIAO nRF52840 Sense, pre-soldered pins) ----------------
xmap = {1: ntc_adc, 2: ntc_en, 3: sync_out, 4: load_en, 5: sda, 6: scl, 7: inh,
        8: rng, 9: chrg, 10: done, 11: pv_en, 12: v3, 13: gnd, 14: None}
J4 = mk("SOCK7", "mcu", ref="J4")                   # XIAO pins 1..7 (D0..D6), pin 1 at the USB end
J5 = mk("SOCK7", "mcu", ref="J5")                   # XIAO pins 14..8 (5V, GND, 3V3, D10..D7)
for i in range(7):
    J4[i + 1] += xmap[i + 1]
    n = xmap[14 - i]
    J5[i + 1] += n if n is not None else NC
M_X = mk("XIAO", "mcu", ref="M1X")                  # schematic-only symbol (no footprint): shows the pin functions
for pin_no, n in xmap.items():
    M_X[pin_no] += n if n is not None else NC

# ---------------- test points, mounting holes ----------------
for i, n in enumerate((vpv, vsys, bat, vload, v3, gnd, sda, scl), 1):
    t = mk("TP", "test", ref=f"TP{i}"); t[1] += n
for i in range(1, 5): mk("HOLE", "mech", ref=f"H{i}")

if __name__ == "__main__":
    ERC()
    generate_netlist(file_="pmbh.net")
    export_parts("pmbh_parts.json")
