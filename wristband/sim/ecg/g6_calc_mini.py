"""Stage-2b ECO re-check of ECG.md case 4 (reversed head -5 V) with the real ECO parts (hand model, no SPICE; g6_calc.py stays as "before").
Loop with a reversed head (head + on J18 / GND_K, head - on J15 / VBUS_K):
  GND_K -> Q20 off (IDSS <= 1 uA at 20 V, PMZ290UNE2 pin map; D15 ESD761 <= 50 nA) -> board GND -> R510 + R509 1.1 MOhm (and D13, and
  R145 + R144 -> VBUS -> D14 reverse) -> VBUS_K. Q20 gate = -(R510 / 1.1 M) x V(GND - VBUS_K): off.
Single fault Q20 shorted (= the pre-ECO topology): the full 5 V sits across D14 PMEG10020AELR; VBUS = -IR x 2 MOhm unless D16 clamps.
PMEG10020AELR IR (datasheet 1 Jan 2023, Fig. 5 typ, read 2026-11-15): about 7 nA at 5 V, 25 C; about 1.5 uA at 5 V, 85 C; max / typ at 100 V,
  25 C = 300 / 70 nA (p.5) used as the spread factor (estimate). 45 C by log interpolation (estimate).
D16 NSR0240: VF 0.21 V typ at 0.1 mA (pin map C896422.yaml); at <= 1 uA about 0.21 - 2 x 0.06 V (60 mV / decade, estimate).
Writes results/eco/g6_calc_eco.json."""
# ===== mini-ECO copy (F-1): D15 leakage 100 nA. Writes results/mini/g6_calc_mini.json.
import json, math, pathlib
HERE = pathlib.Path(__file__).resolve().parent
ir25, ir85 = 7e-9, 1.5e-6
ir45_typ = ir25 * (ir85 / ir25) ** (20 / 60); spread = 300 / 70; ir45_max = ir45_typ * spread
i_loop = 1e-6 + 100e-9   # [mini-ECO F-1] D15 TPD1E10B06 100 nA max (was ESD761 50 nA)
v_gnd_vbk = i_loop * 1.1e6
out = dict(
    q20_intact=dict(i_loop_max_uA=i_loop * 1e6, v_board_gnd_above_vbus_k_V=v_gnd_vbk, q20_vgs_V=-v_gnd_vbk / 1.1, q20_vds_V=5.0 - v_gnd_vbk,
                    d14_reverse_V=v_gnd_vbk, vbus_min_V=-(ir45_max * v_gnd_vbk / 5.0) * 2e6,
                    note="Q20 blocks the reversed head; D14 sees <= 1.2 V reverse (IR scaled linearly from 5 V: conservative for a Schottky)"),
    q20_shorted=dict(d14_ir45_typ_nA=ir45_typ * 1e9, d14_ir45_max_nA=ir45_max * 1e9, vbus_unclamped_typ_V=-ir45_typ * 2e6, vbus_unclamped_max_V=-ir45_max * 2e6,
                     vbus_with_d16_V=-(0.21 - 2 * 0.06), u15_in_absmax_V=-0.3,
                     note="without D16 the scaled maximum (-0.36 V) is below -0.3 V: E-5 clamp kept (D16)"),
    before=dict(d14="NSR0240 0.55 uA at 25 V (25 C) -> -0.04 V typ, -0.3...-0.4 V at max IR (g6_calc.json)"))
(HERE / "results" / "eco").mkdir(parents=True, exist_ok=True)
(HERE / "results" / "mini" / "g6_calc_mini.json").write_text(json.dumps(out, indent=1))
print(json.dumps(out, indent=1))
