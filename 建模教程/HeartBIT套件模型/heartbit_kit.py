"""HeartBIT kit — every part from an official source, nothing measured by hand.

part                 source                                                        accuracy
main unit casing     BITalinoWorld STL, Thingiverse thing:2286560 (CC-BY), the same  exact (print file)
                     casing shown on PLUX's HeartBIT product photo ("3DP by BEEVERYCREATIVE")
BITalino Core        traced from PLUX user manual Fig. 8; fits the casing within 0.1-0.7 mm  ±1 mm
ECG sensor housing   BITalinoWorld STL, thing:2286812 (two halves share one design frame)  exact
PulseSensor          pulsesensor.com: 0.625" dia x 0.125" (15.9 x 3.2 mm); housing thing:2286840 (CC0)  exact
electrodes           PLUX disposable Ag/AgCl: dia 24 mm x 1 mm, snap stud                 datasheet
700 mAh LiPo         PLUX accessory listing: 29 x 36 x 4.75 mm, JST-PH 2P, 70 mm lead      ⚠ PLUX asked by email
"""
from build123d import *
import importlib.util
import os
HERE = os.path.dirname(os.path.abspath(__file__))
def S_(name):   # official STLs: casing in ../BITalino官方外壳_Thingiverse2286560, sensor housings in 官方STL/ (ECG halves: download thing:2286812)
    for d in (os.path.join(HERE, "..", "BITalino官方外壳_Thingiverse2286560"), os.path.join(HERE, "官方STL")):
        if os.path.exists(os.path.join(d, name)): return os.path.join(d, name)
    raise FileNotFoundError(f"{name}: download it from Thingiverse (see THIRD_PARTY_NOTICES.md)")
spec = importlib.util.spec_from_file_location("bc", os.path.join(HERE, "..", "bitalino_core.py")); bc = importlib.util.module_from_spec(spec); spec.loader.exec_module(bc)
RED, WHITE, GREY = Color(0.80, 0.12, 0.12), Color(0.95, 0.95, 0.95), Color(0.55, 0.55, 0.6)

def tag(s, label, color): s.label = label; s.color = color; return s

# ---- main unit: tray + lid exactly as designed (same frame), Core on the inner ledge at z = -2.5 ----
tray = tag(import_stl(S_("1_Plugged_Bot_4.0.stl")), "casing_tray", RED)
lid = tag(import_stl(S_("2_Plugged_Top_v1.2.stl")), "casing_lid", RED)
core = Pos(102.12, 30.55, -2.5) * Rot(0, 0, 90) * bc.core
unit = Compound(children=[tray, lid, core], label="heartbit_main_unit")
c = unit.bounding_box().center()
unit = Pos(-c.X, -c.Y, -unit.bounding_box().min.Z) * unit          # origin: centre of the base

# ---- ECG sensor: two housing halves (top half sits 70.05 mm away in X in the design file) ----
ecg_b = import_stl(S_("ecg_sensor_bot.stl")); ecg_t = Pos(-70.05, 0, 0) * import_stl(S_("ecg_top.stl"))
ecg_house = Compound(children=[tag(ecg_b, "ecg_bot", RED), tag(ecg_t, "ecg_top", RED)])
eb = ecg_house.bounding_box(); ecg_house = Pos(-eb.center().X, -eb.center().Y, -eb.min.Z) * ecg_house
H_ECG = eb.size.Z
leads = []
for i, (dx, col) in enumerate(((-4, Color(0.9, 0.1, 0.1)), (0, WHITE), (4, Color(0.1, 0.1, 0.1)))):   # 3 leads leave the top end
    path = Line((dx, 0, H_ECG), (dx*6, 0, H_ECG + 120))                                           # ⚠ lead length from PLUX
    leads.append(tag(sweep(Pos(dx, 0, H_ECG) * Circle(0.9), path=path), f"lead_{i}", WHITE))
    leads.append(tag(Pos(dx*6, 0, H_ECG + 120) * Sphere(5), f"lead_snap_{i}", col))
uce6 = tag(sweep(Pos(0, 0, 0) * Circle(1.5), path=Line((0, 0, 0), (0, 0, -150))), "uce6_cable", WHITE)   # ⚠ length
ecg = Compound(children=[ecg_house, *leads, uce6], label="ecg_sensor")

# ---- PulseSensor in its official cup housing ----
ps_cup = tag(import_stl(S_("PulseSensor_Housing.stl")), "pulse_housing", Color(0.15, 0.15, 0.15))
ps_pcb = tag(Pos(0, 0, 1.0) * Cylinder(15.875/2, 3.175, align=(Align.CENTER, Align.CENTER, Align.MIN)), "pulsesensor", Color(0.1, 0.1, 0.1))
ps_face = tag(Pos(0, 0, 1.0 + 3.175) * Cylinder(6, 0.3, align=(Align.CENTER, Align.CENTER, Align.MIN)), "pulsesensor_face", WHITE)
pulse = Compound(children=[ps_cup, ps_pcb, ps_face], label="pulsesensor")

# ---- electrode (PLUX disposable, dia 24 x 1 mm, snap stud) ----
electrode = Compound(children=[tag(Cylinder(12, 1, align=(Align.CENTER, Align.CENTER, Align.MIN)), "electrode_pad", Color(0.85, 0.9, 0.95)),
                               tag(Pos(0, 0, 1) * Cylinder(2.0, 2.2, align=(Align.CENTER, Align.CENTER, Align.MIN)), "electrode_stud", GREY)], label="electrode")

# ---- 700 mAh LiPo ----
bat = Compound(children=[tag(fillet(Box(29, 36, 4.75).edges().filter_by(Axis.Y), 1.8), "lipo_700", Color(0.75, 0.75, 0.8)),
                         tag(Pos(0, 18 + 35, 0) * Box(4, 70, 1.5), "lipo_leads", Color(0.8, 0.2, 0.2))], label="lipo_700mAh")

parts = {"heartbit_main_unit": unit, "ecg_sensor": ecg, "pulsesensor": pulse, "electrode": electrode, "lipo_700mAh": bat}
for k, v in parts.items():
    bb = v.bounding_box(); print(f"{k:20s} {bb.size.X:6.1f} x {bb.size.Y:6.1f} x {bb.size.Z:6.1f} mm")
    export_gltf(v, f"{k}.glb", binary=True)
kit = Compound(children=[Pos(0, 0, 0) * unit, Pos(70, 0, 0) * ecg, Pos(110, 0, 0) * pulse, Pos(140, 0, 0) * electrode, Pos(0, -80, 0) * bat], label="heartbit_kit")
export_gltf(kit, "heartbit_kit_all.glb", binary=True); print("ok")
