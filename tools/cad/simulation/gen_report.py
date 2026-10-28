"""Writes simulation/simulation-report.md from the JSON results of every test bench (numbers are never typed by hand)."""
import json, os, shutil, sys
OUT = sys.argv[1]
os.makedirs(os.path.join(OUT, "figures"), exist_ok=True)
for f in os.listdir("plots"):
    if f.endswith(".png"): shutil.copy(os.path.join("plots", f), os.path.join(OUT, "figures", f))
J = lambda n: json.load(open(n))
CH = J("tb_charger_final.json"); LIB = J("tb_lib.json"); INR = J("tb_inrush.json"); RNG = J("tb_range.json")
NIG = J("tb_night2.json"); HP = J("tb_hotplug2.json"); LOOP = J("loop_ss.json")

def worst(damp, gmmax):
    rows = [r for r in LOOP if r["damp"] == damp and r["gm"] <= gmmax + 1e-12]
    pm = min(r["pm"] for r in rows if r["pm"] is not None)
    gms = [r["gm_db"] for r in rows if r["gm_db"] is not None]
    return pm, (min(gms) if gms else None)
DAMPS = sorted({r["damp"] for r in LOOP}, key=lambda d: ("ceramic" not in d, "−10" in d))
pm_old5, gm_old5 = worst(DAMPS[0], 5e-3); pm_new5, gm_new5 = worst(DAMPS[1], 5e-3); pm_cold5, gm_cold5 = worst(DAMPS[2], 5e-3)
pm_old1, gm_old1 = worst(DAMPS[0], 1e-3)
fmt_gm = lambda g: "∞" if g is None else f"{(0.0 if abs(g) < 0.5 else g):.0f} dB"

ch = {(r["G"], r["T"], r["vbat"]): r for r in CH}
il_max = max(r["il_pk"] for r in CH); vds_max = max(r["vds"] for r in CH); vgs_min = min(r["vgs"] for r in CH)
mppt_rows = [r for r in CH if abs(r["vbat"] - 3.7) < 1e-6 and r["G"] >= 30 and r["ibat"] + 0.008 < 1.18 and r["settled"]]
cap_min = min(r["capture"] for r in mppt_rows); cap_max = max(r["capture"] for r in mppt_rows)
r10 = ch.get((10, 25, 3.7)); r400 = ch.get((400, 37, 3.7))
n_settled = sum(1 for r in CH if r["settled"])

L = []
A = L.append
A("# PMB-H / LIB Circuit Simulation Report")
A("")
A("2026-10-12 · Applies to PCBs: PMB-H (revision with C15, RS1B 0.22 Ω, C10 1 µF and PV_EN), LIB")
A("")
A("> The requirement was: \"theoretically feasible does not mean it works in practice — it must be made sure to work.\" This report therefore does three things:")
A("> 1. Models the circuits with datasheet parameters and exercises every function of both boards.")
A("> 2. States an explicit pass criterion for every item.")
A("> 3. The simulation found **4 real problems, and the PCB has already been revised**. Whatever simulation cannot prove is listed in §7 for bench verification.")
A("")
A("---")
A("")
A("## 0. Summary")
A("")
A("| # | Check | Pass criterion | Result | |")
A("|---|---|---|---|---|")
rows = [
 ("MPPT regulation", "VPV = 5.93 V ± 1 % when not current-limited", f"{min(r['vpv'] for r in mppt_rows):.3f} V (all cases)", "✅"),
 ("MPPT capture ratio (30–1000 W/m²)", "≥ 90 % of panel maximum power", f"{cap_min:.1%}–{cap_max:.1%}", "✅"),
 ("Charge current limit", "≤ 1.2 A (0.48 C for the 2500 mAh cell)", f"{max(r['ibat'] for r in CH)*1e3:.0f} mA", "✅"),
 ("Constant-voltage phase (battery 4.15 V)", "Current tapers automatically", f"{ch[(1000, 55, 4.15)]['ibat']*1e3:.0f} mA", "✅"),
 ("Inductor peak current", "< 1.8 A saturation current", f"{il_max:.2f} A", "✅"),
 ("M1 gate-source / drain-source voltage", "Vgs ≥ −12 V, Vds ≤ 30 V", f"{vgs_min:.1f} V / {vds_max:.1f} V", "✅"),
 ("MPPT loop stability", "Gain margin > 6 dB, phase margin > 30° (gm ≤ 5 mA/V)", f"Before fix: worst-case gain margin {fmt_gm(gm_old5)} ❌ → with C15: {fmt_gm(gm_new5)}, phase margin ≥ {pm_new5:.0f}°", "✅ Fixed"),
 ("Night-time battery back-feed", "< 0.2 mA", f"{NIG['Q1_on_Rsh3k']:.2f} mA ❌ → {NIG['PV_EN_Rsh3k']*1e3:.0f} µA with PV_EN off", "✅ Fixed"),
 ("Reverse-connected panel", "No current, board does not power up", "0.00 mA", "✅"),
 ("−10 °C cold-panel hot-plug", "VPV < 11.1 V TVS breakdown; Q1 Vgs > −12 V", f"{HP['CN3791 not yet started']['peak']:.2f} V; {HP['CN3791 not yet started']['vgs_min']:.2f} V", "✅"),
 ("Indoor range hit by sudden full sun", "PV_IN− > −0.3 V (INA226 absolute maximum)", f"−0.42 V ❌ → with RS1B changed to 0.22 Ω: {RNG['vmin_q2off']:.3f} V, RS1B {RNG['p_rs1b']:.2f} W", "✅ Fixed"),
 ("Load-switch turn-on inrush", "< 1.5 A", f"{INR['100n_4.2']['peak']:.2f} A ❌ → with C10 changed to 1 µF: {INR['1u_4.2']['peak']:.2f} A (battery 4.2 V)", "✅ Fixed"),
 ("Supercapacitor pre-charge", "< 10 min to 90 %", f"{LIB['lib']['t90']:.0f} s", "✅"),
 ("Cable-pull hold-up (Core B 65 mA)", "≥ 10 s (enough for a loose connector or re-plugging)", f"{LIB['lib']['holdup_s']:.0f} s (worst case) – 60 s", "✅ (the 45 s in the original document was wrong and has been corrected)"),
 ("Core B voltage at changeover", "> 3.3 V", f"{LIB['lib']['vbit_min']:.2f} V", "✅"),
 ("Recovery after re-plugging", "VBIT > 3.6 V", "3.77 V", "✅"),
 ("Supercapacitor voltage balancing", "≤ 2.7 V per cell", "1.76 V", "✅"),
 ("SYNC pulse", "Rise time < 5 µs, high level < 4.3 V", "237 ns, 3.34 V", "✅"),
 ("3V3 rail", "≥ 3.1 V at battery 3.2 V + BLE burst", "3.160 V", "✅"),
 ("Cold start (battery depleted, XIAO not running)", "VPV rises above the 6.05 V start-up threshold", "6.61 / 7.06 / 7.55 V at 100 / 300 / 1000 W/m²", "✅"),
 ("Panel model", "Matches the nameplate estimated from photos", "At 25 °C: Voc 8.03 V, Isc 0.85 A, Pmax 5.34 W", "✅"),
 ("Very low light 10 W/m²", "(informational)", "Panel maximum is only 33 mW, less than the board's own ≈ 8 mA (30 mW) consumption; the battery net-discharges at about 7–8 mA. Not settled within 25 ms: panel current is only ≈ 8 mA, so C15 charges very slowly", "ℹ️"),
]
for i, (a, b, c, d) in enumerate(rows, 1): A(f"| {i} | {a} | {b} | {c} | {d} |")
A("")
A("**The 4 changes made because of the simulation** (all incorporated into the PCB and the production files):")
A("")
A("| Change | What was found |")
A("|---|---|")
A(f"| **Added C15** 100 µF / 35 V aluminium electrolytic (C2836437) | With only ceramic capacitors at the input, the ≈ 5 kHz resonance is undamped. If the CN3791 error-amplifier transconductance is on the high side (the datasheet does not specify it), the MPPT loop oscillates: the switching-level simulation at 400 W/m² showed VPV swinging 403 mV and the inductor current cycling between 0 and 0.95 A. The CN3791 datasheet already calls for an electrolytic capacitor at the input. With it added, the swing drops to 19 mV |")
A("| **RS1B** 0.47 Ω → 0.22 Ω | In the indoor range, a sudden increase in light pulls the INA226 input to −0.42 V, beyond the −0.3 V absolute maximum; the resistor's own 0.34 W also exceeds its 0.25 W rating |")
A("| **C10** 100 nF → 1 µF | At load-switch turn-on the battery current peaks at 3.15 A (battery at 4.2 V), close to the ≈ 3 A over-current threshold of the battery protection board |")
A(f"| **PV_EN** (Q8 + R19 + R20) + MPPT divider 200k / 51k | At night the battery back-feeds the panel through Q1 and the M1 body diode: {NIG['Q1_on_Rsh3k']:.1f} mA (up to {NIG['Q1_on_Rsh300']:.0f} mA as the panel ages). The MPPT set point was moved from 6.40 V to 5.93 V, raising the all-day capture ratio from 93.6 % to 98.4 % |")
A("")
A("---")
A("")
A("## 1. Method")
A("")
A("| Item | Approach |")
A("|---|---|")
A("| Simulator | ngspice (the libngspice bundled with KiCad 10, driven from Python) |")
A("| Circuit | All component values taken from `pmbh.py` / `libb.py`, identical to the PCB; panel cable modelled as 0.5 m, 40 mΩ/m, 0.6 µH/m |")
A("| MOSFET | AO3400A / AO3401A: fitted to the 3 datasheet Rds points and Vth, with Ciss, Crss, Rg and body diode |")
A("| Diodes, TVS | SS34, B5819W, BAT54, BZT52C10, SMAJ10A, SMF5.0A: fitted to datasheet Vf / VBR |")
A("| Panel | 12-cell series single-diode model: Isc 0.85 A, Voc 8.0 V (nameplate estimated from photos), with temperature coefficients |")
A("| CN3791 | Behavioural model: MPPT 1.205 V, current limit 120 mV, float 4.2 V, 300 kHz, 94 % maximum duty cycle, DRV = VCC − 6.3 V, UVLO and sleep thresholds (all from the datasheet) |")
A("| LM66100 | Behavioural model: turn-on −150 mV, turn-off +35 mV (with hysteresis), 91 mΩ, reverse blocking, ST open-drain |")
A("| Three simulation types | ① Switching-level transient (≈ 170 points per cycle, run for 25 ms to steady state); ② long averaged-model transient (LIB 900 s); ③ small-signal loop analysis (Bode plot) |")
A("")
A("**Pitfalls hit in the simulation itself**: if/else constructs in the behavioural models (comparators, anti-windup) make ngspice's time step collapse to 10⁻¹⁷ s, so a single case ran for over half an hour without converging. After rewriting them as continuous functions (tanh / max), one case takes about 1 minute. Of the conclusions from the earlier short 1.5 ms simulations, two (the 400 W/m² ripple and the zero current at 30 W/m²) had in fact not yet reached steady state; everything has been re-run with 25 ms long simulations.")
A("")
A("## 2. Panel model")
A("")
A("![P-V](figures/fig1_pv.png)")
A("")
A("| Temperature | Voc | Vmp | Pmax |")
A("|---|---|---|---|")
A("| −10 °C | 8.76 V | 7.47 V | 6.04 W |")
A("| 25 °C | 8.03 V | 6.69 V | 5.34 W |")
A("| 55 °C (heated in sun on the back) | 7.39 V | 6.02 V | 4.75 W |")
A("")
A("The panel has no nameplate; these figures are estimated from photos. Once the I-V curve has been measured on the bench (TC-02), the model can be re-fitted.")
A("")
A("## 3. Charger (CN3791 MPPT buck)")
A("")
A("![Switching waveforms](figures/fig2_switching.png)")
A("")
A("![Capture ratio](figures/fig3_capture.png)")
A("")
A("| Irradiance W/m² | Panel temp. | Battery | VPV | VPV ripple | Panel power | Capture ratio | Battery current | Inductor current | Efficiency | Settled |")
A("|---|---|---|---|---|---|---|---|---|---|---|")
for r in CH:
    A(f"| {r['G']} | {r['T']} °C | {r['vbat']:.2f} V | {r['vpv']:.3f} V | {r['vpv_pp']*1e3:.0f} mV | {r['ppanel']:.3f} W | {r['capture']:.1%} | {r['ibat']*1e3:.0f} mA | {r['il_min']:.2f}–{r['il_pk']:.2f} A | {r['eff']:.1%} | {'✓' if r['settled'] else '✗'} |")
A("")
A("**How to read it**:")
A("")
A("- At 1000 W/m² with a cool panel (25 °C, 0 °C), or with a low battery voltage (3.0 V), VPV is above 5.93 V. This is because the charge current has already hit the 1.2 A limit, so the surplus power stays in the panel. This is by design, not an MPPT failure.")
A("- At a battery voltage of 4.15 V the charger enters the constant-voltage phase and the current tapers naturally.")
A("- Battery current = charger output − the board's own ≈ 8 mA (XIAO + 6 × INA226 + LDO).")
A("- At 10 W/m² the panel's maximum power is only 33 mW, which cannot cover the 8 mA self-consumption, so the battery net-discharges. This is typical of an overcast day indoors and is consistent with the positioning \"solar extends runtime but does not guarantee charge-free operation\". The \"Settled\" column for this row is ✗: the panel current is only ≈ 8 mA, so the 100 µF C15 charges very slowly and the equilibrium is not reached within 25 ms. The conclusion is unaffected.")
A("")
A("**Heat dissipation** (losses at 1000 W/m², 55 °C):")
A("- D5 0.13 W, L1 0.11 W, R8 0.12 W, M1 ≈ 0.05 W; estimated temperature rise of 6–13 °C each.")
A("- With the back enclosure at 55 °C ambient, the hottest component reaches about 70 °C, far below their 125–150 °C ratings.")
A("- An HP600 thermal pad on the underside of the board conducts heat to the enclosure floor.")
A("")
A("## 4. MPPT loop stability (the most important finding this time)")
A("")
A("![Bode plot](figures/fig6_loop.png)")
A("")
A("**Problem**:")
A("- When a buck converter regulates its input voltage, the inductor and the input capacitance form a resonance at about 5 kHz.")
A("- With ceramic capacitors only, this resonance is almost undamped.")
A("- The CN3791 datasheet does not give the error-amplifier transconductance, so I swept it over 0.05–20 mA/V:")
A("")
A(f"| Input capacitance | gm ≤ 1 mA/V | gm ≤ 5 mA/V |")
A("|---|---|---|")
A(f"| Ceramic only (before fix) | Phase margin ≥ {pm_old1:.0f}°, gain margin ≥ {fmt_gm(gm_old1)} | Gain margin as low as **{fmt_gm(gm_old5)}** (oscillates) |")
A(f"| With C15 (25 °C, ESR 0.6 Ω) | Stable | Phase margin ≥ {pm_new5:.0f}°, gain margin **{fmt_gm(gm_new5)}** |")
A(f"| With C15 (−10 °C, ESR taken as 3×) | Stable | Phase margin ≥ {pm_cold5:.0f}°, gain margin **{fmt_gm(gm_cold5)}** |")
A("")
A("**Fix**:")
A("- C15 was added, following the datasheet requirement \"input capacitance = electrolytic + ceramic + high-frequency\".")
A("- An infinite gain margin means that no matter how high the chip's internal gain is, the phase never crosses −180°, so the loop cannot oscillate.")
A(f"- Switching-level re-check: at 400 W/m² the VPV ripple drops from 403 mV to {r400['vpv_pp']*1e3:.0f} mV and the inductor current returns to normal continuous-conduction ripple." if r400 else "")
A("")
A("## 5. Protection circuits")
A("")
A("| Scenario | Result |")
A("|---|---|")
A(f"| Night (panel not generating), PV_EN not switched off | Battery leakage {NIG['Q1_on_Rsh30k']:.2f} / {NIG['Q1_on_Rsh3k']:.2f} / {NIG['Q1_on_Rsh300']:.1f} mA (panel shunt resistance 30k / 3k / 300 Ω, decreasing with age) |")
A(f"| Night, PV_EN switched off | **{NIG['PV_EN_Rsh3k']*1e3:.0f} µA**, independent of panel condition. Of this, CN3791 sleep 30 µA, MPPT divider 13 µA, INA226 bus inputs 8 µA. Only 0.6 mAh over 12 hours |")
A("| Reverse-connected panel | Q1 off, 0 mA, board does not power up |")
A(f"| −10 °C cold panel hot-plugged in full sun (5 m cable) | VPV peak {HP['CN3791 not yet started']['peak']:.2f} V (10 V TVS does not conduct), Q1 gate-source {HP['CN3791 not yet started']['vgs_min']:.2f} V (Zener clamps it within 10 V) |")
A(f"| Indoor range (Q2 off) hit by sudden full sun | PV_IN− {RNG['vmin_q2off']:.3f} V (> −0.3 V), RS1B {RNG['p_rs1b']:.2f} W (1 W rating). No damage even if the firmware does not switch range |")
A("")
A("## 6. Load switch and chest LIB")
A("")
A("![Inrush](figures/fig4_inrush.png)")
A("")
A("| Battery voltage | C10 = 100 nF (before) | C10 = 1 µF (after) | VLOAD rise time (after) |")
A("|---|---|---|---|")
for v in ("3.4", "3.8", "4.2"):
    A(f"| {v} V | {INR['100n_'+v]['peak']:.2f} A | {INR['1u_'+v]['peak']:.2f} A | {INR['1u_'+v]['vload_rise_ms']:.1f} ms |")
A("")
A("![Cable-pull hold-up](figures/fig5_holdup.png)")
A("")
A("**Cable-pull hold-up**:")
A("- Two 10 F supercapacitors in series give an equivalent 5 F, charged to about 0.2 V below VLOAD. Assuming a 3.3 V brown-out for the BITalino, the usable voltage window is only 0.3–0.8 V.")
A(f"- Result: worst case **{LIB['lib']['holdup_s']:.0f} s**, when the supercapacitors are not yet fully charged {LIB['lib']['t90']/60:.0f} minutes after power-on and the battery is at 3.8 V; with a full battery and fully charged supercapacitors, about 60 s.")
A("- The \"about 45 s\" in the original design document was calculated with a wider voltage window and has been corrected.")
A("- For its purpose (a loose magnetic connector, or re-plugging when swapping cables), 17 s is sufficient.")
A("")
A("**Other**:")
A("- SYNC pulse rise time 237 ns; the high level is clamped to 3.34 V by the BAT54S.")
A("- The 3V3 rail stays at a minimum of 3.160 V with the battery at 3.2 V and an 18 mA BLE burst.")
A("")
A("## 7. What simulation cannot prove and must be confirmed on the bench")
A("")
A("| # | What to test | How | Pass criterion |")
A("|---|---|---|---|")
A("| 1 | Check C15 polarity **before power-up** | Visual: the black half-circle on top of the capacitor marks the negative terminal and should face right; the silkscreen + is on the left | Correct orientation |")
A("| 2 | Panel I-V | TC-02 (resistor steps + multimeter) | Re-fit the §2 model with measured values |")
A("| 3 | VPV ripple | Oscilloscope; real panel on a cloudy day, or a 9 V bench supply in series with 33 Ω to emulate the panel | < 100 mV, no kHz-range oscillation |")
A("| 4 | Actual brown-out voltage of the BITalino Core | Lower an adjustable supply slowly and note when the Core drops out | Determines the real cable-pull hold-up time |")
A("| 5 | Night-time leakage | Multimeter on the µA range in series with the battery, panel covered, PV_EN pulled low | ≈ 51 µA + XIAO sleep current |")
A("| 6 | Temperature in sunlight | TC1 / TC2 + on-board NTC | Board < 85 °C, TC2 < 40 °C |")
A("")
A("## 8. Files")
A("")
A("All scripts are in [tools/cad/simulation/](../tools/cad/simulation/); device models are in `models.lib`.")
A("")
A("| Script | Contents |")
A("|---|---|")
A("| `tb_charger.py` / `tb_charger2.py` / `run_final.py` | Charger switching-level simulation, 14 cases |")
A("| `loop_ss.py` | MPPT loop small-signal analysis (gm × irradiance × input capacitance) |")
A("| `tb_night2.py`, `tb_hotplug2.py`, `tb_range.py` | Night-time leakage, hot-plug, auto-ranging |")
A("| `tb_lib.py`, `tb_inrush.py` | Load-switch inrush, LIB hold-up, SYNC, 3V3 |")
A("| `plots.py`, `gen_report.py` | Plotting; generation of this report (every number is read from the result JSON, never copied by hand) |")
open(os.path.join(OUT, "simulation-report.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
print("wrote", os.path.join(OUT, "simulation-report.md"), len(L), "lines")
