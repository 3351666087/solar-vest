"""Bench scene (not worn): the panel on the printed test stand + REF1 on the top long edge + thermocouple TC1 +
ND-mesh cover + the back pod (lid off) wired by W01. Used for TC-02 (I-V / reference-cell calibration), TC-03b
(ND mesh), TC-21 (fabric samples), TC-24 (blackout cover) and charger burn-in.

Frames: S = panel frame (X long axis, Y short axis, Z out of the glass, panel rear plane Z = 0);
        W = bench (mm, Z up, table top Z = 0). Exported in metres, glTF Y-up.
"""
import os, sys, json, numpy as np, trimesh
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, "..", "vest"))
import enclosures as E
from assembly import glb_as_mesh, colored, rgba, WS, HW
TILT_FROM_VERTICAL = 45.0                                    # stand label (0 = vertical, 90 = flat)
L2, W2 = E.L_P / 2, E.W_P / 2
def T(tx=0, ty=0, tz=0): M = np.eye(4); M[:3, 3] = (tx, ty, tz); return M
def Rz(a): return trimesh.transformations.rotation_matrix(np.radians(a), (0, 0, 1))
def Rx(a): return trimesh.transformations.rotation_matrix(np.radians(a), (1, 0, 0))
def stl(n): return trimesh.load(os.path.join(HERE, "parts", n + ".stl"))

PIV_S_X = L2 + 3.0 + 7.0                                     # pivot line in S: (±PIV_S_X, 0, 7.8)
PIV_W = np.array([0.0, 0.0, E.PIVOT_Z])
theta = 90.0 - TILT_FROM_VERTICAL                            # panel tilt from horizontal
S2W = T(*PIV_W) @ Rx(theta) @ T(0, 0, -7.8)                  # panel frame -> bench (rotation about the long axis)
def build():
    sc = trimesh.Scene(); idx = {}
    def add(m, name, group, M=None):
        m = m.copy()
        if M is not None: m.apply_transform(M)
        sc.add_geometry(m, node_name=name, geom_name=name); idx[name] = group
    M_PANEL_S = np.array([[0, -1, 0, 0], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]])
    pg = os.path.join(WS, "建模教程", "panel_6V6W_photo.glb")
    add(glb_as_mesh(pg, skip="glass"), "panel", "panel", S2W @ M_PANEL_S)
    add(glb_as_mesh(pg, only="glass"), "panel_glass", "panel", S2W @ M_PANEL_S)
    # cradles: cradle (Xc, Yc, Zc) -> S (L2 + 3 - Yc, Xc, Zc) at +X end, mirrored at -X end
    C_plus = np.array([[0, -1, 0, L2 + 3.0], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]])
    for side, Mc in (("+X", C_plus), ("-X", Rz(180) @ C_plus)):
        add(colored(stl("stand_cradle"), rgba("3b4048")), f"stand_cradle_{side}", "stand", S2W @ Mc)
        sx = 1 if side == "+X" else -1
        Mb = T(sx * (PIV_S_X + 3.0 + 3.0), 0, 0) @ Rz(90)                       # base upright just outside the cradle arm
        add(colored(stl("stand_base"), rgba("2c3138")), f"stand_base_{side}", "stand", Mb)
        for dz, nm in ((0.0, "pivot"), (-35.0, "lock")):                          # M4 bolts
            p = S2W @ np.array([sx * (L2 + 3.0 + 7.0), 0, 7.8 + dz, 1.0])
            b = trimesh.creation.cylinder(radius=2.0, height=24.0, sections=16); b.apply_transform(Rz(0) @ trimesh.transformations.rotation_matrix(np.pi / 2, (0, 1, 0)))
            b.apply_translation(p[:3] + np.array([sx * 6.0, 0, 0])); add(colored(b, rgba("b9bdc3")), f"bolt_{nm}_{side}", "stand")
    # REF1 clip moved to the top long edge (S Y = +W2): S' = T(0, W2) Rz(-90) T(L2, 0) S
    M_ref = T(0, W2, 0) @ Rz(-90) @ T(L2, 0, 0)
    add(colored(stl("ref1_holder"), rgba("3a3f46")), "ref1_holder", "sensors", S2W @ M_ref)
    cell = trimesh.creation.box((40, 30, 2.8)); cell.apply_translation((-L2 - 0.4 - 3 - 3 - 20.5, 0, E.D_P - 1.2 - 1.4))
    add(colored(cell, rgba("1b2a4a")), "ref1_cell", "sensors", S2W @ M_ref)
    tip = trimesh.creation.cylinder(radius=4.0, height=0.8); tip.apply_translation((-100.0, 0.0, 9.4)); add(colored(tip, rgba("b9bdc3")), "TC1_tip", "sensors", S2W)
    # ND-mesh cover (TC-03b) — sewn sleeve, shown as a thin translucent sheet over the glass
    cov = trimesh.creation.box((E.L_P + 2 * 3.6 + 4, E.W_P + 2 * 3.6 + 4, 0.6)); cov.apply_translation((0, 0, E.D_P + 2.6))
    add(colored(cov, rgba("505860", 90)), "cover_ND_mesh", "cover", S2W)
    # back pod on the table, lid off, W01 from the junction box
    M_pod = T(-60.0, -260.0, 2.0)
    add(colored(stl("back_pod_base"), rgba("e9e8e3")), "back_pod_base", "back_pod", M_pod)
    pm = glb_as_mesh(os.path.join(HW, "out", "pmbh", "fab", "pmbh.glb")); pm.apply_translation((-100, 100, E.Z_BRD)); add(pm, "PMB-H", "back_pod", M_pod)
    jb = (S2W @ np.array([-78.5, 0.0, -2.0, 1.0]))[:3]; j1 = (M_pod @ np.array([0.8, -7.5, 9.0, 1.0]))[:3]
    P = np.array([jb, jb + [0, 0, -30], [jb[0] - 20, -150, 8], [j1[0] - 40, j1[1], 9.0], j1])
    from harness import smooth
    from vest3d import tube
    add(colored(tube(smooth(P, 200), 2.5, 10), rgba("202224")), "W01_bench", "cables")
    # table
    tb = trimesh.creation.box((900, 650, 20)); tb.apply_translation((0, -60, -10)); add(colored(tb, rgba("9a8f7e")), "table", "table")
    # to glTF metres, Y-up
    G = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1.0]]) @ np.diag([0.001, 0.001, 0.001, 1])
    for name in list(sc.geometry): sc.geometry[name].apply_transform(G)
    return sc, idx
if __name__ == "__main__":
    sc, idx = build(); out = os.path.join(HERE, "out"); sc.export(os.path.join(out, "bench.glb"))
    json.dump(idx, open(os.path.join(out, "bench_index.json"), "w"), indent=0)
    print("bench nodes", len(idx), "MB", round(os.path.getsize(os.path.join(out, "bench.glb")) / 1e6, 1))
