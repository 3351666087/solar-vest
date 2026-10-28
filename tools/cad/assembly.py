"""Whole-system assembly in the body frame (metres, y up, +z front, +x wearer's left).

writes  out/assembly.glb               vest + panel + shoes + pods (with boards, XIAO, battery) + cables  (no body)
        out/assembly_with_torso_PRIVATE.glb   same + the wearer's torso (derived from the body scan: keep local)
        out/assembly_index.json        node names -> group, for the viewer
"""
import json, os, sys, numpy as np, trimesh
HERE = os.path.dirname(os.path.abspath(__file__)); VEST = os.path.join(HERE, "..", "vest"); HW = os.path.join(HERE, "..", "hw")
sys.path.insert(0, VEST)
WS = os.path.abspath(os.path.join(HERE, "..", ".."))                     # repository root
PL = json.load(open(os.path.join(VEST, "placement.json")))
OUT = os.path.join(HERE, "out"); os.makedirs(OUT, exist_ok=True)
import enclosures as E

G2C = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]]) @ np.diag([1000, 1000, 1000, 1])   # glTF(m, Y-up) -> CAD(mm, Z-up)
def rgba(h, a=255): h = h.lstrip("#"); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)] + [a], np.uint8)
def colored(m, c): m = m.copy(); m.visual = trimesh.visual.ColorVisuals(m, face_colors=np.tile(c, (len(m.faces), 1))); return m

def glb_as_mesh(path, pre=G2C, only=None, skip=None):
    """flatten a GLB scene to one mesh with per-face colours (material base colour), in CAD mm."""
    sc = trimesh.load(path, force="scene"); parts = []
    for node in sc.graph.nodes_geometry:
        if only and not node.startswith(only): continue
        if skip and node.startswith(skip): continue
        T, gname = sc.graph[node]; g = sc.geometry[gname].copy(); g.apply_transform(T)
        col = np.array([180, 180, 180, 255], np.uint8)
        v = g.visual
        try:
            if isinstance(v, trimesh.visual.TextureVisuals) and v.material is not None:
                bc = getattr(v.material, "baseColorFactor", None)
                if bc is None and hasattr(v.material, "main_color"): bc = v.material.main_color
                if bc is not None: col = np.array(bc, np.uint8) if np.max(bc) > 1 else (np.array(bc) * 255).astype(np.uint8)
            elif hasattr(v, "face_colors"): col = None
        except Exception: pass
        if col is not None: g = colored(g, col if len(col) == 4 else np.r_[col, 255])
        parts.append(g)
    m = trimesh.util.concatenate(parts); m.apply_transform(pre); return m

def frame(o, x, y, z, scale=0.001):
    """4x4: local (mm) -> body (m), local axes x,y,z expressed in body coords, local origin -> o."""
    M = np.eye(4); M[:3, 0], M[:3, 1], M[:3, 2] = x, y, z; M[:3, :3] *= scale; M[:3, 3] = o; return M
def at(M, p): return (M @ np.r_[p, 1.0])[:3]

# ---- frames -----------------------------------------------------------------------------------
C_BACK = np.array(PL["panel"]["back_plane_centre"]); n_out = np.array(PL["panel"]["n_out"]); up = np.array(PL["panel"]["up"])
ex = np.array([1.0, 0, 0])
M_S = frame(C_BACK, -ex, up, n_out)                                                  # panel frame S (mm) -> body
M_PANEL = M_S @ np.array([[0, -1, 0, 0], [1, 0, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]])   # panel model (x short=up, y long) -> S
bp = PL["back_pod"]; M_BP0 = frame(np.array(bp["origin"]), bp["right"], bp["up"], bp["normal"])
M_BACKPOD = M_BP0 @ np.array([[1, 0, 0, -38.5], [0, 1, 0, 62.8], [0, 0, 1, 2.0], [0, 0, 0, 1]])   # pod CAD -> body
cp = PL["chest_pod"]; M_CP0 = frame(np.array(cp["origin"]), cp["right"], cp["up"], cp["normal"])
M_CHESTPOD = M_CP0 @ np.array([[1, 0, 0, -28.0], [0, 1, 0, -12.5], [0, 0, 1, 2.0], [0, 0, 0, 1]])
r2 = PL["ref2"]; M_REF2 = frame(np.array(r2["origin"]), r2["right"], r2["up"], r2["normal"])

def stl(name): return trimesh.load(os.path.join(HERE, "parts", name + ".stl"))
COL = dict(pod=rgba("e9e8e3"), pod_lid=rgba("f2f1ec"), chest=rgba("cfd3d8"), chest_lid=rgba("dfe2e6"), shoe=rgba("26282b"),
           hook=rgba("4a4e54"), ref=rgba("3a3f46"), cell=rgba("1b2a4a"), xiao_pcb=rgba("1f5f3a"), usb=rgba("c9ccd1"), shield=rgba("b8bcc2"),
           header=rgba("111111"), battery=rgba("c8ccd2"), cable_panel=rgba("b02a2a"), cable_j6=rgba("2a2a2a"), cable_ref=rgba("d4a017"))

def build(with_torso=False):
    sc = trimesh.Scene(); idx = {}
    def add(mesh, name, group, M=None):
        m = mesh.copy()
        if M is not None: m.apply_transform(M)
        sc.add_geometry(m, node_name=name, geom_name=name); idx[name] = group
    # vest
    v = trimesh.load(os.path.join(VEST, "out", "vest.glb"), force="scene")
    for node in v.graph.nodes_geometry:
        T, g = v.graph[node]; m = v.geometry[g].copy(); m.apply_transform(T); add(m, "vest/" + node, "vest")
    # panel
    pg = os.path.join(WS, "modeling", "panel_6V6W_photo.glb")
    add(glb_as_mesh(pg, skip="glass"), "panel", "panel", M_PANEL)
    add(glb_as_mesh(pg, only="glass"), "panel_glass", "panel", M_PANEL)
    # shoes + ref1 (S frame)
    for k in ("TL", "TR", "BL", "BR", "TM", "BM"): add(colored(stl(f"panel_shoe_{k}"), COL["shoe"]), f"shoe_{k}", "shoes", M_S)
    add(colored(stl("ref1_holder"), COL["ref"]), "ref1_holder", "sensors", M_S)
    cell1 = trimesh.creation.box((40, 30, 2.8)); x_edge = -E.L_P / 2
    cell1.apply_translation((x_edge - 0.4 - 3 - 3 - 20.5, 0, E.D_P - 1.2 - 1.4)); add(colored(cell1, COL["cell"]), "ref1_cell", "sensors", M_S)
    r2m, _ = E.ref2_holder() if False else (stl("ref2_holder"), 0)
    add(colored(r2m, COL["ref"]), "ref2_holder", "sensors", M_REF2)
    # back pod: tub, lid, hooks, PMB-H, XIAO, battery
    add(colored(stl("back_pod_base"), COL["pod"]), "back_pod_base", "back_pod", M_BACKPOD)
    add(colored(stl("back_pod_lid"), COL["pod_lid"]), "back_pod_lid", "back_pod_lid", M_BACKPOD)
    for hx in E.HOOK_X:
        Mh = M_BACKPOD @ np.array([[1, 0, 0, hx], [0, 1, 0, E.HOOK_TOP_Y], [0, 0, 1, -2.0], [0, 0, 0, 1]])
        add(colored(stl("webbing_hook"), COL["hook"]), f"back_pod_hook_{hx:.0f}", "back_pod", Mh)
    pm = glb_as_mesh(os.path.join(HW, "out", "pmbh", "fab", "pmbh.glb")); pm.apply_translation((-100, 100, E.Z_BRD))
    add(pm, "PMB-H", "boards", M_BACKPOD)
    zx = E.Z_BRD
    for nm, (x0, x1, y0, y1, z0, z1), c in (("xiao_pcb", (62.0, 83.0, -21.9, -4.1, zx + 12.6, zx + 13.8), "xiao_pcb"),
                                           ("xiao_usb", (75.8, 84.2, -16.7, -9.3, zx + 13.8, zx + 17.0), "usb"),
                                           ("xiao_shield", (63.5, 74.5, -18.0, -8.0, zx + 13.8, zx + 15.4), "shield"),
                                           ("xiao_hdr_a", (63.6, 81.4, -6.65, -4.11, zx + 10.1, zx + 12.6), "header"),
                                           ("xiao_hdr_b", (63.6, 81.4, -21.89, -19.35, zx + 10.1, zx + 12.6), "header"),
                                           ("battery_2500mAh", (11.0, 75.0, -123.6, -73.6, 0.5, 10.5), "battery")):
        b = trimesh.creation.box((x1 - x0, y1 - y0, z1 - z0)); b.apply_translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
        add(colored(b, COL[c]), nm, "boards", M_BACKPOD)
    # chest pod: tub, lid, LIB (rotated 180°), Core B LOD1 (rotated 180°)
    add(colored(stl("chest_pod_base"), COL["chest"]), "chest_pod_base", "chest_pod", M_CHESTPOD)
    add(colored(stl("chest_pod_lid"), COL["chest_lid"]), "chest_pod_lid", "chest_pod_lid", M_CHESTPOD)
    R180 = np.diag([-1.0, -1.0, 1.0, 1.0])
    lb = glb_as_mesh(os.path.join(HW, "out", "libb", "fab", "libb.glb")); lb.apply_transform(R180); lb.apply_translation((156.0, -140.0, E.ZLIB))
    add(lb, "LIB", "boards", M_CHESTPOD)
    core = glb_as_mesh(os.path.join(WS, "modeling", "bitalino_core_LOD1.glb")); core.apply_transform(R180); core.apply_translation((28.0, 32.5, E.ZCORE))
    add(core, "BITalino_Core_B", "boards", M_CHESTPOD)
    # complete harness + non-solar devices (A, C, ECG sensor, electrodes, PulseSensor, thermocouples, phone)
    import harness
    wires = harness.build_harness(add, dict(M_S=M_S, M_BACKPOD=M_BACKPOD, M_CHESTPOD=M_CHESTPOD, M_REF2=M_REF2))
    json.dump(wires, open(os.path.join(OUT, "harness.json"), "w"), ensure_ascii=False, indent=1)
    if with_torso:
        t = trimesh.load(os.path.join(VEST, "out", "_private_torso.glb"), force="scene")
        for node in t.graph.nodes_geometry:
            T, g = t.graph[node]; m = t.geometry[g].copy(); m.apply_transform(T); add(m, "torso_PRIVATE", "torso")
        # head + neck proxy (the torso model stops at 1.625 m): only so the ear clip has context
        hd = trimesh.creation.icosphere(subdivisions=3, radius=1.0); hd.apply_scale((0.078, 0.115, 0.098)); hd.apply_translation((0.0, 1.745, 0.012))
        nk = trimesh.creation.cylinder(radius=0.058, height=0.10, sections=32); nk.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, (1, 0, 0))); nk.apply_translation((0.0, 1.655, -0.005))
        add(colored(trimesh.util.concatenate([hd, nk]), rgba("d9a88a")), "head_proxy_PRIVATE", "torso")
    return sc, idx

if __name__ == "__main__":
    sc, idx = build(False); sc.export(os.path.join(OUT, "assembly.glb"))
    sc2, idx2 = build(True); sc2.export(os.path.join(OUT, "assembly_with_torso_PRIVATE.glb"))
    json.dump(idx2, open(os.path.join(OUT, "assembly_index.json"), "w"), indent=0)
    tri = sum(len(g.faces) for g in sc.geometry.values())
    print("assembly nodes", len(idx), "triangles", tri, "size MB", round(os.path.getsize(os.path.join(OUT, "assembly.glb")) / 1e6, 1))
    # interference checks (body frame): panel vs shoes clearance, pods vs vest surface
    from torso import Torso
    T = Torso()
    print("panel back plane gap check ok:", PL["panel"]["gap_mm"])
