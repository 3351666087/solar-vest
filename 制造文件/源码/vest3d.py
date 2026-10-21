"""3D model of the custom vest (GLB): every pattern piece as a 3.5 mm shell+lining solid, stretch side panels,
bias binding on the bound edges, CF zipper, carrier patch, webbing rows A/B/C, side adjusters, chest-pod pocket,
cable tunnels. Also exports the (private) torso surface for local preview only.

usage: python vest3d.py <outdir>
"""
import json, os, sys, numpy as np, trimesh
from shapely.geometry import box as sbox
from vest_geom import *
from patterns import classify
OUT = sys.argv[1] if len(sys.argv) > 1 else "out"; os.makedirs(OUT, exist_ok=True)
PL = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "placement.json")))

def rgba(h, a=255): h = h.lstrip("#"); return [int(h[i:i + 2], 16) for i in (0, 2, 4)] + [a]
COL = dict(shell=rgba("2f343b"), yoke=rgba("3d4a5c"), side=rgba("16181b"), lining=rgba("8c96a3"), binding=rgba("1d1f22"),
           webbing=rgba("101112"), carrier=rgba("262a30"), zip=rgba("0c0c0c"), puller=rgba("e86a1a"), pocket=rgba("5a6573"),
           tunnel=rgba("2a2e34"), body=rgba("d9a88a"), buckle=rgba("202020"))

def colored(m, c): m.visual = trimesh.visual.ColorVisuals(m, face_colors=np.tile(c, (len(m.faces), 1))); return m

def thick_piece(poly, t_in_layer="inner"):
    phi, y, F = mesh_piece(poly, max_edge=0.010)
    Vo = T.point(y, phi * DEG, off_in(y) + LINING_T + SHELL_T)
    Vi = T.point(y, phi * DEG, off_in(y))
    n = len(phi)
    # orient outward
    nn = np.cross(Vo[F[:, 1]] - Vo[F[:, 0]], Vo[F[:, 2]] - Vo[F[:, 0]]); c = Vo[F].mean(1)
    flip = np.einsum("ij,ij->i", nn, np.c_[c[:, 0], np.zeros(len(c)), c[:, 2]]) < 0; F = F.copy(); F[flip] = F[flip][:, ::-1]
    import igl
    b = igl.boundary_loop(F)
    side = []
    for i in range(len(b)):
        a, bb = b[i], b[(i + 1) % len(b)]
        side += [[a, bb, bb + n], [a, bb + n, a + n]]
    faces = np.vstack([F, F[:, ::-1] + n, np.array(side)])
    m = trimesh.Trimesh(np.vstack([Vo, Vi]), faces, process=True); trimesh.repair.fix_normals(m)
    return m, (phi, y, F, b)

def edge_runs(name, phi, y, b, want="bound"):
    kinds = [classify(name, phi[i], y[i]) for i in b]; runs, cur = [], []
    for i, k in zip(b, kinds):
        if k[1] == want: cur.append(i)
        elif cur: runs.append(cur); cur = []
    if cur:
        if runs and kinds[0][1] == want: runs[0] = cur + runs[0]
        else: runs.append(cur)
    return [r for r in runs if len(r) > 2]

def sweep_rect(path, w, h, normal_fn=None):
    """sweep a w x h rectangle along a 3D polyline; the 'h' axis follows the local surface normal."""
    path = np.asarray(path); verts, faces = [], []
    for i, p in enumerate(path):
        t = path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]; t /= np.linalg.norm(t) + 1e-12
        nrm = normal_fn(p) if normal_fn else np.array([p[0], 0, p[2]]) / (np.hypot(p[0], p[2]) + 1e-12)
        nrm = nrm - (nrm @ t) * t; nrm /= np.linalg.norm(nrm) + 1e-12; bnm = np.cross(t, nrm)
        for su, sv in ((-1, -1), (1, -1), (1, 1), (-1, 1)): verts.append(p + bnm * su * w / 2 + nrm * sv * h / 2)
    V = np.array(verts); m = len(path)
    for i in range(m - 1):
        for k in range(4):
            a, b2 = i * 4 + k, i * 4 + (k + 1) % 4; faces += [[a, b2, b2 + 4], [a, b2 + 4, a + 4]]
    faces += [[0, 2, 1], [0, 3, 2], [(m - 1) * 4, (m - 1) * 4 + 1, (m - 1) * 4 + 2], [(m - 1) * 4, (m - 1) * 4 + 2, (m - 1) * 4 + 3]]
    return trimesh.Trimesh(V, np.array(faces), process=True)

def tube(path, r, sections=10):
    path = np.asarray(path); ang = np.linspace(0, 2 * np.pi, sections, endpoint=False); verts, faces = [], []
    for i, p in enumerate(path):
        t = path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]; t /= np.linalg.norm(t) + 1e-12
        a = np.cross(t, [0, 1, 0]) if abs(t[1]) < 0.9 else np.cross(t, [1, 0, 0]); a /= np.linalg.norm(a); b = np.cross(t, a)
        for q in ang: verts.append(p + r * (np.cos(q) * a + np.sin(q) * b))
    V = np.array(verts); m = len(path); s = sections
    for i in range(m - 1):
        for k in range(s):
            a0, a1 = i * s + k, i * s + (k + 1) % s; faces += [[a0, a1, a1 + s], [a0, a1 + s, a0 + s]]
    return trimesh.Trimesh(V, np.array(faces), process=True)

def build():
    polys, armL, armR = piece_polygons()
    scene = trimesh.Scene(); meta = {}
    for k, poly in polys.items():
        m, (phi, y, F, b) = thick_piece(poly)
        col = COL["side"] if k.startswith("SIDE") else COL["yoke"] if k.startswith("YOKE") else COL["shell"]
        scene.add_geometry(colored(m, col), node_name=f"vest_{k}", geom_name=f"vest_{k}")
        # binding on the bound edges (neck / armholes / hem): 6 x 4 mm bead centred on the edge
        for j, run in enumerate(edge_runs(k, phi, y, b)):
            P = T.point(y[run], phi[run] * DEG, off_in(y[run]) + (LINING_T + SHELL_T) / 2)
            if len(P) > 3: scene.add_geometry(colored(tube(P, 0.0028), COL["binding"]), node_name=f"binding_{k}_{j}")
        meta[k] = dict(tris=int(len(m.faces)))
    # carrier patch on the centre back (1000D, 1 mm proud)
    cp = polys["BACK_C"].intersection(sbox(-140, 1.20, -40, Y_YOKE))
    phi, y, F = mesh_piece(cp, 0.012); V = T.point(y, phi * DEG, off_layer(y, "outer") + 0.0010)
    scene.add_geometry(colored(trimesh.Trimesh(V, F), COL["carrier"]), node_name="carrier_patch")
    # webbing rows A/B/C, 25 x 1.6 mm, across the carrier
    for r, yr in PL["webbing_rows_y"].items():
        ph = np.linspace(-136, -44, 60); P = T.point(np.full_like(ph, yr), ph * DEG, off_layer(yr, "outer") + 0.0025 + 0.0008)
        scene.add_geometry(colored(sweep_rect(P, 0.025, 0.0016), COL["webbing"]), node_name=f"webbing_row_{r}")
        for x in PL["bar_tacks_x"][r]:                                                                  # bar tacks
            pt = P[np.argmin(np.abs(P[:, 0] - x))]
            scene.add_geometry(colored(trimesh.creation.box((0.004, 0.024, 0.0022), trimesh.transformations.translation_matrix(pt)), rgba("8a8f96")), node_name=f"tack_{r}_{x:+.3f}")
    # CF zipper: tape + teeth along both front edges, puller at the top
    for side_phi in (90.0 - 0.3, -270.0 + 0.3):
        yy = np.linspace(hem(90) + 0.004, Y_NECK_F - 0.004, 80)
        P = T.point(yy, np.full_like(yy, side_phi * DEG), off_in(yy) + LINING_T + SHELL_T + 0.0008)
        scene.add_geometry(colored(sweep_rect(P, 0.006, 0.0022), COL["zip"]), node_name=f"zip_{'L' if side_phi > 0 else 'R'}")
    top = T.point(Y_NECK_F - 0.012, 90 * DEG, off_in(Y_NECK_F) + 0.006)
    scene.add_geometry(colored(trimesh.creation.box((0.010, 0.030, 0.004), trimesh.transformations.translation_matrix(top + [0, -0.012, 0])), COL["puller"]), node_name="zip_puller")
    # side adjusters: 20 mm webbing across each stretch panel + ladder lock
    for sgn, base in ((1, 0.0), (-1, -180.0)):
        for yr in (1.15, 1.30):
            ph = np.linspace(base - 16, base + 16, 30); P = T.point(np.full_like(ph, yr), ph * DEG, off_layer(yr, "outer") + 0.001)
            scene.add_geometry(colored(sweep_rect(P, 0.020, 0.0015), COL["webbing"]), node_name=f"adjuster_{'L' if sgn > 0 else 'R'}_{yr}")
            lk = T.point(yr, (base + 9 * (1 if sgn > 0 else -1)) * DEG, off_layer(yr, "outer") + 0.003)
            scene.add_geometry(colored(trimesh.creation.box((0.010, 0.024, 0.004), trimesh.transformations.translation_matrix(lk)), COL["buckle"]), node_name=f"ladderlock_{'L' if sgn > 0 else 'R'}_{yr}")
    # chest-pod bellows pocket (pod 67 x 111 x 20 -> pocket 75 x 125 x 24) + flap
    cpd = PL["chest_pod"]; o, n, upv, rt = (np.array(cpd[k]) for k in ("origin", "normal", "up", "right"))
    Rm = np.eye(4); Rm[:3, :3] = np.c_[rt, upv, n]; Rm[:3, 3] = o + n * 0.012
    pocket = trimesh.creation.box((0.075, 0.125, 0.024)); pocket.apply_transform(Rm)
    scene.add_geometry(colored(pocket, COL["pocket"]), node_name="pocket_chest_pod")
    flap = trimesh.creation.box((0.079, 0.040, 0.003)); Fm = Rm.copy(); Fm[:3, 3] = o + n * 0.0255 + upv * 0.050
    flap.apply_transform(Fm); scene.add_geometry(colored(flap, COL["yoke"]), node_name="pocket_flap")
    # ---- system pockets: A (HeartBIT, left chest), C (Board, left lower), phone (right lower), thermocouple pouch
    SL = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "system_layout.json")))
    def pocket_box(pose, w, h, d, name, flap=True):
        o, n, u, r = (np.array(pose[k]) for k in ("origin", "normal", "up", "right"))
        M = np.eye(4); M[:3, :3] = np.c_[r, u, n]; M[:3, 3] = o + n * (d / 2)
        b = trimesh.creation.box((w, h, d)); b.apply_transform(M)
        scene.add_geometry(colored(b, COL["pocket"]), node_name=f"pocket_{name}")
        if flap:
            f = trimesh.creation.box((w + 0.004, 0.035, 0.003)); Mf = M.copy(); Mf[:3, 3] = o + n * (d + 0.0015) + u * (h / 2 - 0.0175)
            f.apply_transform(Mf); scene.add_geometry(colored(f, COL["yoke"]), node_name=f"pocket_{name}_flap")
    for key, nm in (("A_heartbit", "A_heartbit"), ("C_board", "C_board"), ("phone", "phone"), ("tc_pouch", "tc_pouch")):
        w, h, d = (v / 1000 for v in SL[key]["pocket"]); pocket_box(SL[key], w, h, d, nm)
    # lead ports: brass eyelets through shell + lining behind the pockets
    for key in ("port_B", "port_C"):
        o, n = np.array(SL[key]["origin"]), np.array(SL[key]["normal"])
        ring = trimesh.creation.annulus(r_min=0.0035, r_max=0.0060, height=0.0015)
        z = np.array([0, 0, 1.0]); ax = np.cross(z, n); M = np.eye(4)
        if np.linalg.norm(ax) > 1e-9: M[:3, :3] = trimesh.transformations.rotation_matrix(np.arccos(np.clip(z @ n, -1, 1)), ax)[:3, :3]
        M[:3, 3] = o + n * 0.0008; ring.apply_transform(M); scene.add_geometry(colored(ring, rgba("b8954a")), node_name=f"eyelet_{key}")
    # elastic guide loop for the PPG cable on the left front yoke
    g = SL["ppg_guide"]; o, n, u, r = (np.array(g[k]) for k in ("origin", "normal", "up", "right"))
    M = np.eye(4); M[:3, :3] = np.c_[r, u, n]; M[:3, 3] = o + n * 0.003
    lp = trimesh.creation.box((0.010, 0.020, 0.004)); lp.apply_transform(M); scene.add_geometry(colored(lp, COL["webbing"]), node_name="ppg_guide_loop")
    # inner mesh pocket for the HeartBIT ECG sensor (B), on the lining's skin side
    e = SL["ecg_box_B"]; o, n, u, r = (np.array(e[k]) for k in ("origin", "normal", "up", "right"))
    M = np.eye(4); M[:3, :3] = np.c_[r, u, n]; M[:3, 3] = o + n * 0.001
    ip = trimesh.creation.box((0.030, 0.034, 0.002)); ip.apply_transform(M); scene.add_geometry(colored(ip, rgba("6f7782")), node_name="inner_pocket_ecg_B")
    # cable tunnels (sewn channels, shown as flat 30 mm strips) under each cable
    for k, P in PL["cables"].items():
        if k == "panel": P = P[1:]
        P = np.array(P)
        if len(P) > 3: scene.add_geometry(colored(sweep_rect(P, 0.030, 0.0012), COL["tunnel"]), node_name=f"tunnel_{k}")
    return scene, meta

def body_mesh():
    """private: torso surface from the photogrammetry-derived model, for local fit preview only."""
    ys = np.linspace(0.92, 1.625, 140); ts = np.linspace(-np.pi, np.pi, 120, endpoint=False)
    Yg, Tg = np.meshgrid(ys, ts, indexing="ij"); V = T.point(Yg.ravel(), Tg.ravel(), 0.0)
    F = []
    for i in range(len(ys) - 1):
        for j in range(len(ts)):
            a, b, c, d = i * len(ts) + j, i * len(ts) + (j + 1) % len(ts), (i + 1) * len(ts) + j, (i + 1) * len(ts) + (j + 1) % len(ts)
            F += [[a, c, b], [b, c, d]]
    return colored(trimesh.Trimesh(V, np.array(F)), COL["body"])

if __name__ == "__main__":
    sc, meta = build()
    sc.export(os.path.join(OUT, "vest.glb"))
    body_mesh().export(os.path.join(OUT, "_private_torso.glb"))
    print("vest.glb", meta)
