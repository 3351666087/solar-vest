"""Everything that is not the solar chain: the three BITalinos, skin-contact sensors, instruments, pockets,
lead ports and every cable route. Body frame (m): y up, +z front, +x wearer's LEFT.

Sources:
  electrodes  BITalino (r)evolution user manual §2.3 / Fig. 15: IN+/IN- on the collar bones, REF on the iliac crest
              (Einthoven lead I). B (DUT) and C (control) are both lead I, C 50 mm lower; REFs mirror-symmetric (v3.1 TC-05).
  lead colours PLUX manual Table 2: red = IN+, black = IN-, white = REF.
  earlobe     symmetric head model from the scan (head half-breadth 88 mm at y = 1.70 m).
writes system_layout.json
"""
import json, os, numpy as np
from vest_geom import off_layer, off_in, DEG, mirror_phi
from torso import Torso
T = Torso()
HERE = os.path.dirname(os.path.abspath(__file__))
PL = json.load(open(os.path.join(HERE, "placement.json")))

def phi_at_x(x, y, front=True):
    ph = np.linspace(0.0, 90.0, 1801) if x > 0 else np.linspace(-270.0, -180.0, 1801)
    if not front: ph = np.linspace(-90.0, 0.0, 1801) if x > 0 else np.linspace(-180.0, -90.0, 1801)
    P = T.point(np.full_like(ph, y), ph * DEG, 0.0); return float(ph[np.argmin(np.abs(P[:, 0] - x))])
def frame(phi, y, off):
    p = T.point(y, phi * DEG, off); h = 1e-4
    py = T.point(y + h, phi * DEG, off) - p; pt = T.point(y, phi * DEG + h, off) - p
    n = np.cross(py, pt); n /= np.linalg.norm(n); up = py - (py @ n) * n; up /= np.linalg.norm(up); right = np.cross(up, n)
    return dict(origin=p.tolist(), normal=n.tolist(), up=up.tolist(), right=right.tolist(), phi=phi, y=y)
def skin(phi, y, lift=0.0): return frame(phi, y, lift)
def vest_out(phi, y, extra=0.0): return frame(phi, y, float(off_layer(y, "outer")) + extra)

L = {}
# ---------------------------------------------------------------- skin contact
E = {}
for dev, y_cl, ref_side in (("B", 1.520, "R"), ("C", 1.470, "L")):
    E[f"{dev}_IN+"] = skin(phi_at_x(+0.085, y_cl), y_cl)          # left collar-bone region  (red)
    E[f"{dev}_IN-"] = skin(phi_at_x(-0.085, y_cl), y_cl)          # right collar-bone region (black)
    # REF on the lower rib cage (costal margin, the Holter 'RL' site): the PLUX iliac-crest site is > 30 cm from a chest
    # sensor, and the real electrode leads are 30 cm (HeartBIT ECG sensor, PLUX 3-lead cable SKU 810121413)
    E[f"{dev}_REF"] = skin(phi_at_x(+0.100 if ref_side == "L" else -0.100, 1.240), 1.240)
L["electrodes"] = E
L["electrode_note"] = "PLUX Ag/AgCl Ø24 mm (HeartBIT kit) or the CSV disposable electrodes; centres ≥ 50 mm apart"
L["earlobe_L"] = dict(origin=[0.080, 1.700, -0.010], normal=[1.0, 0.0, 0.0], up=[0, 1, 0], right=[0, 0, -1])

# ---------------------------------------------------------------- devices on the vest (pose = back face centre on the vest's outer surface)
# C sits on the left chest next to its electrodes (its ECG front-end is on the board, so its electrode leads must stay short
# and comparable to B's — otherwise TC-05 would compare lead lengths, not power paths). A goes outboard/lower.
L["A_heartbit"] = dict(vest_out(26.0, 1.282, 0.0012), size_mm=[69.4, 61.5, 13.5], pocket=[78, 72, 18], note="HeartBIT main unit (official casing)")
L["C_board"] = dict(vest_out(63.0, 1.380, 0.0012), size_mm=[126.5, 85.8, 18.0], pocket=[130, 88, 22], note="BITalino Board BLE + 523450 in printed case (incl. screw lugs)")
L["phone"] = dict(vest_out(mirror_phi(50.0), 1.165, 0.0012), size_mm=[78.0, 165.0, 9.0], pocket=[86, 172, 14], note="phone up to 165 x 78 x 9 mm")
L["tc_pouch"] = dict(vest_out(45.0, 1.150, 0.0012), size_mm=[40.0, 50.0, 18.0], pocket=[44, 54, 20], note="K-type plugs park here; meter plugs in to read")
L["chest_pod"] = PL["chest_pod"]
# inside the vest, on the lining (between lining and skin): HeartBIT ECG sensor for B, near the electrodes
L["ecg_box_B"] = dict(frame(phi_at_x(-0.040, 1.400), 1.400, 0.0060), size_mm=[15.0, 15.0, 10.0], note="HeartBIT ECG sensor on the sternum (right of the zip), inner mesh pocket")
# lead ports (eyelets through lining + shell, behind the pockets)
L["port_B"] = vest_out(mirror_phi(64.0), 1.345, 0.0)          # behind the pod pocket, at its centre-front edge
L["port_C"] = vest_out(84.0, 1.372, 0.0)          # behind C's pocket, at its centre-front edge (ECG socket side)
L["ppg_guide"] = vest_out(30.0, 1.548, 0.0)               # elastic loop on the left front yoke near the neckline

# ---------------------------------------------------------------- routes  (lists of (phi, y, offset-kind)) -> 3D polylines
def path(pts, kind="out", extra=0.0, n=18):
    out = []
    for (pa, ya), (pb, yb) in zip(pts[:-1], pts[1:]):
        for t in np.linspace(0, 1, n, endpoint=False):
            ph, y = pa + (pb - pa) * t, ya + (yb - ya) * t
            off = {"out": float(off_layer(y, "outer")) + extra, "skin": 0.0012 + extra, "lining": float(off_in(y)) - 0.002}[kind]
            out.append(T.point(y, ph * DEG, off))
    ph, y = pts[-1]
    off = {"out": float(off_layer(y, "outer")) + extra, "skin": 0.0012 + extra, "lining": float(off_in(y)) - 0.002}[kind]
    out.append(T.point(y, ph * DEG, off)); return np.array(out)
def plen(P): return float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1)))
R = {}
eb = L["ecg_box_B"]; ebp = (eb["phi"], eb["y"])
def ph(key): return SL_E[key]["phi"]
SL_E = E
# B: HeartBIT ECG sensor (sternum) -> electrodes (under the vest, on the skin); φ unwrapped across the centre front
R["B_lead_red_IN+"] = path([ebp, (75 - 360, 1.46), (E["B_IN+"]["phi"] - 360, 1.520)], "skin")
R["B_lead_black_IN-"] = path([ebp, (E["B_IN-"]["phi"], 1.520)], "skin")
R["B_lead_white_REF"] = path([ebp, (E["B_REF"]["phi"], 1.240)], "skin")
R["B_ecg_uce6_to_A2"] = path([ebp, (L["port_B"]["phi"], L["port_B"]["y"])], "lining")
# C: Board ECG block (left chest, socket facing the centre) -> port_C -> electrodes
pc = (L["port_C"]["phi"], L["port_C"]["y"])
R["C_lead_red_IN+"] = path([pc, (E["C_IN+"]["phi"], 1.470)], "skin")
R["C_lead_black_IN-"] = path([pc, (95, 1.42), (E["C_IN-"]["phi"] + 360, 1.470)], "skin")
R["C_lead_white_REF"] = path([pc, (E["C_REF"]["phi"], 1.240)], "skin")
# A: PulseSensor from the left outboard pocket over the front yoke to the left earlobe
pa = (26.0, 1.318)
yoke = path([pa, (24.0, 1.40), (30.0, 1.548), (14.0, 1.585)], "out", 0.003)
ear = np.array(L["earlobe_L"]["origin"]); neck0 = yoke[-1]
free = np.array([neck0 + (ear - neck0) * t + np.array([0.012, 0, 0]) * np.sin(np.pi * t) for t in np.linspace(0, 1, 16)])
R["A_ppg_cable"] = np.vstack([yoke, free[1:]])
# thermocouples: panel backsheet (TC1) and air-gap / vest surface under the panel (TC2) -> pouch on the left front, low
R["TC1_panel"] = path([(-90 + np.degrees(np.arcsin(0.10 / 0.19)), 1.43), (-40, 1.33), (-8, 1.20), (45, 1.165)], "out", 0.004)
R["TC2_airgap"] = path([(-90 + np.degrees(np.arcsin(0.04 / 0.19)), 1.42), (-40, 1.32), (-8, 1.195), (45, 1.158)], "out", 0.006)
L["routes"] = {k: v.tolist() for k, v in R.items()}
L["route_length_mm"] = {k: round(plen(v) * 1000) for k, v in R.items()}
json.dump(L, open(os.path.join(HERE, "system_layout.json"), "w"), indent=1)
if __name__ == "__main__":
    for k, v in L["route_length_mm"].items(): print(f"{k:22s} {v:5d} mm")
    for k, e in E.items(): print(k, np.round(e["origin"], 3))
