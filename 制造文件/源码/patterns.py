"""Sewing patterns from the flattened vest pieces: cut lines with per-edge seam allowance, notches, grain lines,
placement marks, seam-length check, 1:1 SVG / DXF, plotter PDF and tiled A4 PDF.

usage: python patterns.py <outdir>
"""
import json, os, sys, numpy as np
from shapely.geometry import Polygon, LineString, Point, MultiPolygon
from shapely.ops import unary_union
from vest_geom import *

OUT = sys.argv[1] if len(sys.argv) > 1 else "out"
os.makedirs(OUT, exist_ok=True)
SA = {"seam": 10.0, "zip": 12.0, "bound": 0.0}          # mm

PIECES = {   # name: (Chinese label, cut instruction, mirror partner)
    "YOKE_B":  ("后育克 Back yoke",            "面布 ×1，里布 ×1", None),
    "BACK_C":  ("中后片 Centre back",           "面布 ×1，里布 ×1", None),
    "BACK_SL": ("左侧后片 Side back L",         "面布 ×1，里布 ×1（与右片成对）", "BACK_SR"),
    "BACK_SR": ("右侧后片 Side back R",         "面布 ×1，里布 ×1", "BACK_SL"),
    "FRONT_L": ("左前片 Front L",               "面布 ×1，里布 ×1（与右片成对）", "FRONT_R"),
    "FRONT_R": ("右前片 Front R（胸前仓口袋）", "面布 ×1，里布 ×1", "FRONT_L"),
    "YOKE_FL": ("左前育克 Front yoke L",        "面布 ×1，里布 ×1", "YOKE_FR"),
    "YOKE_FR": ("右前育克 Front yoke R",        "面布 ×1，里布 ×1", "YOKE_FL"),
    "SIDE_L":  ("左侧片 Side L（弹力）",        "弹力网布 ×1，单层", "SIDE_R"),
    "SIDE_R":  ("右侧片 Side R（弹力）",        "弹力网布 ×1，单层", "SIDE_L"),
}

def classify(name, phi, y):
    """edge type of a boundary vertex from its (φ, y) parameters."""
    tol_p, tol_y = 0.6, 0.0012
    phl = np.where(phi < -90, mirror_phi(phi), phi)          # fold to the left half
    if abs(y - hem(phl)) < tol_y: return "hem", "bound"
    if abs(y - neckline(phl)) < tol_y: return "neck", "bound"
    if name.startswith(("FRONT", "YOKE_F")) and (abs(phi - 90) < tol_p or abs(phi + 270) < tol_p): return "cf", "zip"
    if name.startswith("YOKE_F") and abs(y - Y_YOKE_F) < tol_y: return "yoke_f", "seam"
    if name.startswith("FRONT") and abs(y - Y_YOKE_F) < tol_y: return "yoke_f", "seam"
    if abs(y - Y_YOKE) < tol_y and (name.startswith("BACK") or name == "YOKE_B"): return "yoke_b", "seam"
    if abs(phl - PHI_PRINCESS) < tol_p or abs(phl - (-180 - PHI_PRINCESS)) < tol_p: return "princess", "seam"
    if (abs(abs(phl) - PHI_SIDE) < tol_p) and y < Y_SPLIT + 0.01: return ("side_f" if phl > 0 else "side_b"), "seam"
    if abs(phl - 0) < tol_p and y > Y_SP - 0.004: return "shoulder", "seam"
    return "armhole", "bound"

def outline(pc):
    b = pc["bnd"]; uv = pc["uv"][b]
    if Polygon(uv).exterior.is_ccw is False: b = b[::-1]; uv = uv[::-1]
    kinds = [classify(pc["name"], pc["phi"][i], pc["y"][i]) for i in b]
    return b, uv, kinds

def cut_polygon(uv, kinds):
    """piece polygon grown by the per-edge seam allowance (square corners between two sewn edges)."""
    poly = Polygon(uv); parts = [poly]
    n = len(uv)
    # group consecutive vertices of the same edge type into runs
    runs, start = [], 0
    for i in range(1, n + 1):
        if i == n or kinds[i % n][0] != kinds[start][0]:
            runs.append((start, i)); start = i
    if len(runs) > 1 and kinds[0][0] == kinds[-1][0]:          # merge the wrap-around run
        s0, e0 = runs.pop(0); s1, e1 = runs.pop(-1); runs.insert(0, (s1, e0 + n))
    for s, e in runs:
        sa = SA[kinds[s % n][1]]
        if sa <= 0: continue
        idx = [(k % n) for k in range(s - 1, e + 1)]           # include the corner vertices on both ends
        line = uv[idx]
        if len(line) < 2: continue
        # extend each end by sa along the end tangent only where the neighbour edge is also sewn
        prev_sa = SA[kinds[(s - 1) % n][1]]; next_sa = SA[kinds[e % n][1]]
        pts = list(line)
        if prev_sa > 0: t = line[0] - line[1]; pts.insert(0, line[0] + t / np.linalg.norm(t) * sa)
        if next_sa > 0: t = line[-1] - line[-2]; pts.append(line[-1] + t / np.linalg.norm(t) * sa)
        # outside of a CCW polygon is on the right -> negative single-sided buffer
        band = LineString(pts).buffer(-sa, single_sided=True, cap_style=2, join_style=2, mitre_limit=3.0)
        parts.append(band)
    cut = unary_union(parts)
    if isinstance(cut, MultiPolygon): cut = max(cut.geoms, key=lambda g: g.area)
    return Polygon(cut.exterior)

def mirror_piece(pc, new_name):
    q = dict(pc); q["name"] = new_name
    q["uv"] = np.c_[pc["uv"][:, 0].max() - pc["uv"][:, 0], pc["uv"][:, 1]]
    q["phi"] = mirror_phi(pc["phi"]); q["V3"] = pc["V3"] * np.array([-1.0, 1.0, 1.0]); q["F"] = pc["F"][:, ::-1].copy()
    q["bnd"] = pc["bnd"]; return q

def edge_length(uv, kinds, kind):
    n = len(uv); L = 0.0
    for i in range(n):
        if kinds[i][0] == kind and kinds[(i + 1) % n][0] == kind: L += np.linalg.norm(uv[(i + 1) % n] - uv[i])
    return L

# ---------------------------------------------------------------- notches & marks (3D-defined, mapped into each piece)
def nearest_bnd(pc, b, phi, y):
    d = ((pc["phi"][b] - phi) * R_SCALE) ** 2 + (pc["y"][b] - y) ** 2
    return int(np.argmin(d))
def map_point(pc, phi, y):
    """2D position of an interior parameter point (barycentric in the param triangulation)."""
    P = np.c_[pc["phi"] * R_SCALE, pc["y"]]; q = np.array([phi * R_SCALE, y])
    for f in pc["F"]:
        a, b, c = P[f]; v0, v1, v2 = b - a, c - a, q - a
        d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1
        den = d00 * d11 - d01 * d01
        if abs(den) < 1e-18: continue
        v = (d11 * d20 - d01 * d21) / den; w = (d00 * d21 - d01 * d20) / den; u = 1 - v - w
        if min(u, v, w) >= -1e-9: return u * pc["uv"][f[0]] + v * pc["uv"][f[1]] + w * pc["uv"][f[2]]
    return None

NOTCH_Y = [1.15, 1.30]                       # vertical seams: match points at these heights
def notch_specs(name):
    s = []
    for y in NOTCH_Y + [1.42]:
        for ph in (PHI_SIDE, -PHI_SIDE, -180 + PHI_SIDE, -180 - PHI_SIDE): s.append((ph, y, 1))
    for y in NOTCH_Y + [1.42]:
        for ph in (PHI_PRINCESS, -180 - PHI_PRINCESS): s.append((ph, y, 1))
    for ph in (-150, -120, -90, -60, -30): s.append((ph, Y_YOKE, 2 if ph == -90 else 1))   # yoke: CB double notch
    for ph in (20, 45, 70): s.append((ph, Y_YOKE_F, 1)); s.append((mirror_phi(ph), Y_YOKE_F, 1))
    y_sh = 0.5 * (Y_SP + Y_NECK_B); s += [(0, y_sh, 1), (-180, y_sh, 1)]
    s += [(phi_at_x(0.166, 1.43, True), 1.43, 1), (mirror_phi(phi_at_x(0.166, 1.43, True)), 1.43, 1)]            # front armhole: 1
    s += [(phi_at_x(0.172, 1.43, False), 1.43, 2), (mirror_phi(phi_at_x(0.172, 1.43, False)), 1.43, 2)]          # back armhole: 2
    s += [(-90, Y_NECK_B, 2), (-90, hem(-90), 2)]                                                                    # CB
    return s

def _rect_phi(pose_phi, y_c, w, h):
    r = float(T.r(y_c, pose_phi * DEG)) + float(off_in(y_c)); dphi = np.degrees(w / 2 / r)
    return [(pose_phi - dphi, y_c - h / 2), (pose_phi + dphi, y_c - h / 2), (pose_phi + dphi, y_c + h / 2), (pose_phi - dphi, y_c + h / 2)]
def marks(name, layer="shell"):
    """placement marks (lines/rects/points in φ,y) per piece."""
    here = os.path.dirname(os.path.abspath(__file__))
    PLc = json.load(open(os.path.join(here, "placement.json"))); SL = json.load(open(os.path.join(here, "system_layout.json")))
    m = []
    if name in ("BACK_C",) and layer == "shell":
        for r, label in (("A", "织带 A（面板上支脚）/ row A"), ("B", "织带 B（面板下支脚）/ row B"), ("C", "织带 C（背部仓）/ row C")):
            y = PLc["webbing_rows_y"][r]
            m.append(("line", label, [(ph, y) for ph in np.linspace(-136, -44, 47)]))
            for ph in PLc["bar_tacks_phi"][r]: m.append(("tack", "", [(ph, y)]))
        m.append(("rect", "加强片 1000D carrier", [(-138, 1.20), (-42, 1.20), (-42, 1.505), (-138, 1.505)]))
    pockets = {"FRONT_R": [("chest_pod", "胸前仓口袋 B（P1）", [75, 125]), ("phone", "手机袋（P4）", None)],
               "FRONT_L": [("A_heartbit", "HeartBIT 袋 A（P2）", None), ("C_board", "Board 袋 C（P3）", None), ("tc_pouch", "热电偶插头袋（P5）", None)]}
    if name in pockets and layer == "shell":
        for key, label, size in pockets[name]:
            pose = SL[key] if key in SL else PLc[key]
            w, h = (size or pose["pocket"][:2]); phi = pose.get("phi"); y = pose.get("y")
            if phi is None: phi, y = mirror_phi(48.0), 1.378
            m.append(("rect", f"{label} {w:.0f}×{h:.0f}", _rect_phi(phi, y, w / 1000, h / 1000)))
    if name == "FRONT_R": m.append(("tack", "导线孔 B（铜扣眼 Ø7，面布+里布）", [(SL["port_B"]["phi"], SL["port_B"]["y"])]))
    if name == "FRONT_L": m.append(("tack", "导线孔 C（铜扣眼 Ø7，面布+里布）", [(SL["port_C"]["phi"], SL["port_C"]["y"])]))
    if name == "YOKE_FL" and layer == "shell": m.append(("tack", "PPG 线松紧环", [(SL["ppg_guide"]["phi"], SL["ppg_guide"]["y"])]))
    if name == "YOKE_B" and layer == "shell":
        m.append(("rect", "REF2 魔术贴毛面 50×40", _rect_phi(-8.0, 1.548, 0.050, 0.040)))
    if layer == "lining":
        if name == "FRONT_R":
            e = SL["ecg_box_B"]; m.append(("rect", "ECG 传感器内袋（网布 34×30，开口朝上）", _rect_phi(e["phi"], e["y"], 0.034, 0.030)))
        # elastic lead keepers every ~80 mm along the electrode leads that run under this piece
        for k, P in SL["routes"].items():
            if not k.startswith(("B_lead", "C_lead")): continue
            P = np.array(P); d = np.r_[0, np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))]
            for s_ in np.arange(0.06, d[-1] - 0.04, 0.08):
                q = P[np.argmin(np.abs(d - s_))]; ph = np.degrees(np.arctan2(q[2], q[0])); yq = q[1]
                if ph > 90 + 1e-6: ph -= 360
                if ph < -270: ph += 360
                m.append(("tack", "", [(ph, yq)]))
    return m

# ---------------------------------------------------------------- accessory pieces (rectangles): pockets, inner pocket, panel cover
def rect_piece(w, h, sa=10.0, corner_cut=0.0):
    uv = np.array([[0, 0], [w, 0], [w, h], [0, h]], float)
    kinds = [("seam", "seam")] * 4
    cut = Polygon(uv).buffer(sa, join_style=2)
    if corner_cut > 0:
        for cx, cy in ((0, 0), (w, 0), (w, h), (0, h)):
            sx, sy = (-1 if cx == 0 else 1), (-1 if cy == 0 else 1)
            cut = cut.difference(Polygon([(cx - sx * 0.01, cy - sy * 0.01), (cx + sx * (sa + 1), cy - sy * 0.01),
                                          (cx + sx * (sa + 1), cy + sy * (sa + 1)), (cx - sx * 0.01, cy + sy * (sa + 1))]).buffer(0)) \
                if False else cut
        inner = [(corner_cut, 0), (w - corner_cut, 0), (w - corner_cut, corner_cut), (w, corner_cut), (w, h - corner_cut), (w - corner_cut, h - corner_cut),
                 (w - corner_cut, h), (corner_cut, h), (corner_cut, h - corner_cut), (0, h - corner_cut), (0, corner_cut), (corner_cut, corner_cut)]
        uv = np.array(inner, float); kinds = [("seam", "seam")] * len(uv)
        cut = Polygon(uv).buffer(sa, join_style=2)
    notches = []
    for (a, b) in ((uv[i], uv[(i + 1) % len(uv)]) for i in range(len(uv))):
        L_ = np.linalg.norm(b - a)
        if L_ < 40: continue
        t = (b - a) / L_; nrm = np.array([t[1], -t[0]]); m_ = (a + b) / 2
        notches.append([(m_ + nrm * sa).tolist(), (m_ + nrm * sa - nrm * (sa + 6)).tolist()])
    return dict(uv=uv, kinds=kinds, cut=np.array(cut.exterior.coords), notches=notches, marks=[], stretch=None, area_m2=float(cut.area) / 1e6)

EXTRAS = {   # name: (w, h, corner_cut, label, cut instruction)
    "P1_FRONT": (75 + 2 * 24, 125 + 24, 24, "P1 胸前仓口袋（B）袋面+风琴边", "500D ×1（四角剪口后折成立体袋）"),
    "P1_FLAP": (79, 45, 0, "P1 袋盖", "500D ×2（正反合缝）+ 魔术贴 75×20"),
    "P2_FRONT": (78 + 2 * 18, 72 + 18, 18, "P2 HeartBIT 袋（A）袋面+风琴边", "500D ×1"),
    "P2_FLAP": (82, 40, 0, "P2 袋盖", "500D ×2 + 魔术贴"),
    "P3_FRONT": (130 + 2 * 22, 88 + 22, 22, "P3 Board 袋（C）袋面+风琴边", "500D ×1"),
    "P3_FLAP": (134, 45, 0, "P3 袋盖", "500D ×2 + 魔术贴"),
    "P4_FRONT": (86 + 2 * 14, 172 + 14, 14, "P4 手机袋 袋面+风琴边", "500D ×1"),
    "P4_FLAP": (90, 45, 0, "P4 袋盖", "500D ×2 + 魔术贴"),
    "P5_FRONT": (44 + 2 * 20, 54 + 20, 20, "P5 热电偶插头袋", "500D ×1"),
    "P5_FLAP": (48, 35, 0, "P5 袋盖", "500D ×2 + 魔术贴"),
    "P6_INNER": (34, 30, 0, "P6 ECG 传感器内袋（里布侧）", "弹力网布 ×1，三边车缝，开口朝上"),
    "COVER": (261.8 + 2 * 3.6 + 2 * 25, 171.0 + 2 * 3.6 + 2 * 25, 25, "面板遮挡罩（TC-24 遮光 / TC-03b ND 网 / TC-21 面料）", "每种面料各 ×1；四角车成盒角，边缘穿 3 mm 松紧绳"),
}
def build_extras():
    res = {}
    for k, (w, h, cc, label, cutinfo) in EXTRAS.items():
        res[k] = rect_piece(w, h, 15.0 if k == "COVER" else 10.0, cc)
        PIECES[k] = (label, cutinfo, None)
    return res

# ---------------------------------------------------------------- build everything
def build_all(layer):
    polys, _, _ = piece_polygons()
    pcs = {}
    for k in ("YOKE_B", "BACK_C", "BACK_SL", "FRONT_L", "YOKE_FL", "SIDE_L"):
        pcs[k] = build_piece(k, polys[k], layer if not k.startswith("SIDE") else "lining")
    pcs["BACK_SR"] = mirror_piece(pcs["BACK_SL"], "BACK_SR"); pcs["FRONT_R"] = mirror_piece(pcs["FRONT_L"], "FRONT_R")
    pcs["YOKE_FR"] = mirror_piece(pcs["YOKE_FL"], "YOKE_FR"); pcs["SIDE_R"] = mirror_piece(pcs["SIDE_L"], "SIDE_R")
    res = {}
    for k, pc in pcs.items():
        b, uv, kinds = outline(pc)
        if k.endswith("R") and k in ("BACK_SR", "FRONT_R", "YOKE_FR", "SIDE_R"):
            pass
        cut = cut_polygon(uv, kinds)
        notches = []
        for ph, y, cnt in notch_specs(k):
            if not (min(pc["phi"]) - 1 <= ph <= max(pc["phi"]) + 1): continue
            i = nearest_bnd(pc, b, ph, y)
            if abs(pc["phi"][b[i]] - ph) * R_SCALE > 0.006 or abs(pc["y"][b[i]] - y) > 0.006: continue
            if kinds[i][1] == "bound" and not (ph == -90): continue
            p = uv[i]; t = uv[(i + 1) % len(uv)] - uv[i - 1]; t /= np.linalg.norm(t); nrm = np.array([t[1], -t[0]])
            sa = SA[kinds[i][1]]
            for j in range(cnt):
                q = p + t * (j - (cnt - 1) / 2) * 3.0
                notches.append([(q + nrm * sa).tolist(), (q + nrm * sa - nrm * (sa + 6)).tolist()])
        mk = []
        for kind, label, pts in marks(k, layer):
            P2 = [map_point(pc, ph, y) for ph, y in pts]
            P2 = [p.tolist() for p in P2 if p is not None]
            if P2: mk.append((kind, label, P2))
        res[k] = dict(uv=uv, kinds=kinds, cut=np.array(cut.exterior.coords), notches=notches, marks=mk,
                      stretch=(float(pc["s_max"].max()), float(pc["s_min"].min())) if "s_max" in pc else None,
                      area_m2=float(cut.area) / 1e6)
    return res, pcs

def seam_report(res):
    pairs = [("FRONT_L", "SIDE_L", "side_f"), ("BACK_SL", "SIDE_L", "side_b"), ("BACK_C", "BACK_SL", "princess"),
             ("YOKE_B", "BACK_C", "yoke_b"), ("YOKE_FL", "FRONT_L", "yoke_f"), ("YOKE_FL", "YOKE_B", "shoulder")]
    out = []
    for a, b, kind in pairs:
        la = edge_length(res[a]["uv"], res[a]["kinds"], kind); lb = edge_length(res[b]["uv"], res[b]["kinds"], kind)
        if kind == "yoke_b":   # yoke spans centre + both side backs
            lb = sum(edge_length(res[p]["uv"], res[p]["kinds"], kind) for p in ("BACK_C", "BACK_SL", "BACK_SR"))
        if kind == "shoulder": lb = lb / 2                       # yoke back has both shoulders
        if kind == "princess": la = la / 2                       # centre back has both princess seams
        out.append((a, b, kind, la, lb))
    return out

# ---------------------------------------------------------------- writers
COL = {"cut": "#000", "sew": "#1565c0", "notch": "#000", "grain": "#2e7d32", "mark": "#c62828", "text": "#000"}
def layout(res, width=1450.0, gap=25.0):
    """shelf packing on a fabric width (mm). returns {piece: (dx, dy)}."""
    order = sorted(res, key=lambda k: -(np.ptp(res[k]["cut"][:, 1])))
    x = y = shelf_h = 0.0; pos = {}
    for k in order:
        c = res[k]["cut"]; w, h = np.ptp(c[:, 0]), np.ptp(c[:, 1])
        if x + w > width: x = 0.0; y += shelf_h + gap; shelf_h = 0.0
        pos[k] = (x - c[:, 0].min(), y - c[:, 1].min()); x += w + gap; shelf_h = max(shelf_h, h)
    return pos, y + shelf_h

def piece_svg(k, r, dx, dy, H, title):
    f = lambda p: f"{p[0] + dx:.2f},{H - (p[1] + dy):.2f}"          # flip v (pattern up = page up)
    s = [f'<g id="{k}">']
    s.append(f'<polygon points="{" ".join(f(p) for p in r["cut"])}" fill="#fff" stroke="{COL["cut"]}" stroke-width="0.6"/>')
    s.append(f'<polygon points="{" ".join(f(p) for p in r["uv"])}" fill="none" stroke="{COL["sew"]}" stroke-width="0.35" stroke-dasharray="4,2"/>')
    for a, b in r["notches"]: s.append(f'<line x1="{a[0]+dx:.2f}" y1="{H-(a[1]+dy):.2f}" x2="{b[0]+dx:.2f}" y2="{H-(b[1]+dy):.2f}" stroke="#000" stroke-width="0.6"/>')
    for kind, label, P in r["marks"]:
        if kind == "line": s.append(f'<polyline points="{" ".join(f(p) for p in P)}" fill="none" stroke="{COL["mark"]}" stroke-width="0.4" stroke-dasharray="6,3"/>')
        elif kind == "rect": s.append(f'<polygon points="{" ".join(f(p) for p in P)}" fill="none" stroke="{COL["mark"]}" stroke-width="0.5"/>')
        elif kind == "tack": s.append(f'<circle cx="{P[0][0]+dx:.2f}" cy="{H-(P[0][1]+dy):.2f}" r="2.5" fill="none" stroke="{COL["mark"]}" stroke-width="0.5"/>')
        if label and P: s.append(f'<text x="{P[0][0]+dx+3:.1f}" y="{H-(P[0][1]+dy)-2:.1f}" font-size="6" fill="{COL["mark"]}">{label}</text>')
    c = r["uv"]; cx, cy = c[:, 0].mean(), c[:, 1].mean(); h = np.ptp(c[:, 1])
    s.append(f'<line x1="{cx+dx:.1f}" y1="{H-(cy+dy-h*0.3):.1f}" x2="{cx+dx:.1f}" y2="{H-(cy+dy+h*0.3):.1f}" stroke="{COL["grain"]}" stroke-width="0.6" marker-start="url(#a)" marker-end="url(#a)"/>')
    name, cutinfo, _ = PIECES[k]
    s.append(f'<text x="{cx+dx+4:.1f}" y="{H-(cy+dy):.1f}" font-size="9" font-weight="bold">{name}</text>')
    s.append(f'<text x="{cx+dx+4:.1f}" y="{H-(cy+dy)+11:.1f}" font-size="6.5">{cutinfo} · {title}</text>')
    s.append(f'<text x="{cx+dx+4:.1f}" y="{H-(cy+dy)+20:.1f}" font-size="5.5" fill="#555">布纹线 ↕ 与布边平行 · 缝份已含（虚线=净缝线）· 包边处无缝份</text>')
    s.append("</g>"); return "\n".join(s)

def write_svg(res, path, title):
    pos, H = layout(res); W = 1450 + 60; H += 120
    body = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" height="{H}mm" viewBox="0 0 {W} {H}" font-family="Helvetica, PingFang SC, sans-serif">',
            '<defs><marker id="a" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="5" markerHeight="5" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#2e7d32"/></marker></defs>',
            f'<rect x="0" y="0" width="{W}" height="{H}" fill="#fff"/>',
            f'<text x="10" y="18" font-size="12" font-weight="bold">太阳能背心纸样 · {title} · 1:1（单位 mm）</text>',
            '<rect x="10" y="26" width="100" height="100" fill="none" stroke="#000" stroke-width="0.5"/><text x="14" y="78" font-size="7">校验方块 100 × 100 mm</text>']
    for k in res: body.append(piece_svg(k, res[k], pos[k][0] + 130, pos[k][1] + 30, H, title))
    body.append("</svg>")
    open(path, "w").write("\n".join(body)); return W, H

def write_dxf(res, path):
    import ezdxf
    doc = ezdxf.new("R2010", setup=True); doc.units = ezdxf.units.MM
    for n, c in (("CUT", 7), ("SEW", 5), ("NOTCH", 7), ("GRAIN", 3), ("MARK", 1), ("TEXT", 7)): doc.layers.add(n, color=c)
    msp = doc.modelspace(); pos, _ = layout(res)
    for k, r in res.items():
        dx, dy = pos[k]
        msp.add_lwpolyline([(p[0] + dx, p[1] + dy) for p in r["cut"]], close=True, dxfattribs={"layer": "CUT"})
        msp.add_lwpolyline([(p[0] + dx, p[1] + dy) for p in r["uv"]], close=True, dxfattribs={"layer": "SEW"})
        for a, b in r["notches"]: msp.add_line((a[0] + dx, a[1] + dy), (b[0] + dx, b[1] + dy), dxfattribs={"layer": "NOTCH"})
        for kind, label, P in r["marks"]:
            if kind in ("line", "rect"): msp.add_lwpolyline([(p[0] + dx, p[1] + dy) for p in P], close=(kind == "rect"), dxfattribs={"layer": "MARK"})
            else: msp.add_circle((P[0][0] + dx, P[0][1] + dy), 2.5, dxfattribs={"layer": "MARK"})
        c = r["uv"]; cx, cy, h = c[:, 0].mean(), c[:, 1].mean(), np.ptp(c[:, 1])
        msp.add_line((cx + dx, cy + dy - h * 0.3), (cx + dx, cy + dy + h * 0.3), dxfattribs={"layer": "GRAIN"})
        msp.add_text(k, height=8, dxfattribs={"layer": "TEXT"}).set_placement((cx + dx + 4, cy + dy))
    doc.saveas(path)

def write_pdfs(res, outdir, title, tag):
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light")); FONT = "STSong-Light"
    from reportlab.pdfgen.canvas import Canvas as _C
    _ds = _C.drawString
    def _drawString(self, x, y, text, *a, **k): return _ds(self, x, y, text.replace(" · ", "，").replace("·", "，"), *a, **k)
    _C.drawString = _drawString                                   # STSong has no U+00B7
    def draw(c, k, r, dx, dy):
        P = lambda p: ((p[0] + dx) * mm, (p[1] + dy) * mm)
        c.setLineWidth(0.6); c.setStrokeColorRGB(0, 0, 0)
        path = c.beginPath(); pts = [P(p) for p in r["cut"]]; path.moveTo(*pts[0])
        for q in pts[1:]: path.lineTo(*q)
        path.close(); c.drawPath(path)
        c.setDash(4, 2); c.setStrokeColorRGB(0.08, 0.4, 0.75); c.setLineWidth(0.4)
        path = c.beginPath(); pts = [P(p) for p in r["uv"]]; path.moveTo(*pts[0])
        for q in pts[1:]: path.lineTo(*q)
        path.close(); c.drawPath(path); c.setDash()
        c.setStrokeColorRGB(0, 0, 0); c.setLineWidth(0.7)
        for a, b in r["notches"]: c.line(*P(a), *P(b))
        c.setStrokeColorRGB(0.78, 0.16, 0.16); c.setLineWidth(0.5)
        for kind, label, Q in r["marks"]:
            if kind in ("line", "rect"):
                pts = [P(p) for p in Q]
                for i in range(len(pts) - 1 + (kind == "rect")): c.line(*pts[i], *pts[(i + 1) % len(pts)])
            else: c.circle(*P(Q[0]), 2.5 * mm)
            if label: c.setFont(FONT, 7); c.setFillColorRGB(0.78, 0.16, 0.16); c.drawString(P(Q[0])[0] + 3 * mm, P(Q[0])[1] + 2 * mm, label)
        uv = r["uv"]; cx, cy, h = uv[:, 0].mean(), uv[:, 1].mean(), np.ptp(uv[:, 1])
        c.setStrokeColorRGB(0.18, 0.49, 0.2); c.setLineWidth(0.8); c.line(*P((cx, cy - h * 0.3)), *P((cx, cy + h * 0.3)))
        for s in (-1, 1):
            tip = P((cx, cy + s * h * 0.3)); c.line(tip[0], tip[1], tip[0] - 2 * mm, tip[1] - s * 4 * mm); c.line(tip[0], tip[1], tip[0] + 2 * mm, tip[1] - s * 4 * mm)
        name, cutinfo, _ = PIECES[k]
        c.setFillColorRGB(0, 0, 0); c.setFont(FONT, 12); c.drawString(*P((cx + 5, cy + 4)), name)
        c.setFont(FONT, 8); c.drawString(*P((cx + 5, cy - 4)), f"{cutinfo} · {title}")
        c.drawString(*P((cx + 5, cy - 10)), "布纹线与布边平行 · 实线=裁剪线 · 蓝虚线=净缝线 · 包边处无缝份")
    def test_square(c, x, y):
        c.setStrokeColorRGB(0, 0, 0); c.setLineWidth(0.5); c.rect(x * mm, y * mm, 50 * mm, 50 * mm)
        c.setFont(FONT, 7); c.drawString((x + 2) * mm, (y + 22) * mm, "校验 50 × 50 mm（打印时选'实际大小'）")
    # 1) plotter: one page per piece, page = piece + 30 mm margin
    c = canvas.Canvas(os.path.join(outdir, f"纸样_{tag}_绘图仪1比1.pdf"))
    for k, r in res.items():
        cut = r["cut"]; w, h = np.ptp(cut[:, 0]) + 60, np.ptp(cut[:, 1]) + 90
        c.setPageSize((w * mm, h * mm)); draw(c, k, r, 30 - cut[:, 0].min(), 60 - cut[:, 1].min()); test_square(c, 5, 5); c.showPage()
    c.save()
    # 2) tiled A4 (portrait 210 x 297, printable 190 x 277, 10 mm overlap), page grid letters + numbers
    c = canvas.Canvas(os.path.join(outdir, f"纸样_{tag}_A4拼贴.pdf"))
    from reportlab.lib.pagesizes import A4
    PW, PH, M, OV = 210, 297, 10, 10
    step_x, step_y = PW - 2 * M - OV, PH - 2 * M - OV
    for k, r in res.items():
        cut = r["cut"]; w, h = np.ptp(cut[:, 0]) + 20, np.ptp(cut[:, 1]) + 20
        nx, ny = int(np.ceil(w / step_x)), int(np.ceil(h / step_y))
        ox, oy = 10 - cut[:, 0].min(), 10 - cut[:, 1].min()
        for j in range(ny):
            for i in range(nx):
                c.setPageSize(A4); c.saveState()
                p = c.beginPath(); p.rect(M * mm, M * mm, (PW - 2 * M) * mm, (PH - 2 * M) * mm); c.clipPath(p, stroke=0)
                draw(c, k, r, M + ox - i * step_x, M + oy - j * step_y); c.restoreState()
                c.setStrokeColorRGB(0.6, 0.6, 0.6); c.setLineWidth(0.3); c.setDash(2, 2)
                c.rect(M * mm, M * mm, (PW - 2 * M) * mm, (PH - 2 * M) * mm)
                c.line((PW - M - OV) * mm, M * mm, (PW - M - OV) * mm, (PH - M) * mm); c.line(M * mm, (PH - M - OV) * mm, (PW - M) * mm, (PH - M - OV) * mm)
                c.setDash(); c.setFont(FONT, 8); c.setFillColorRGB(0.3, 0.3, 0.3)
                c.drawString(M * mm, (PH - 7) * mm, f"{PIECES[k][0]}  第 {chr(65 + j)}{i + 1} 页 / 共 {nx}×{ny}  · 灰虚线内 10 mm 为重叠区，对齐后粘贴 · {title}")
                if i == 0 and j == 0: test_square(c, M + 5, M + 5)
                c.showPage()
    c.save()

if __name__ == "__main__":
    summary = {}
    for layer, title in (("shell", "面布 500D Cordura"), ("lining", "里布 3D 网眼")):
        res, pcs = build_all(layer)
        tag = {"shell": "面布", "lining": "里布"}[layer]
        if layer == "lining":
            res = {k: v for k, v in res.items() if not k.startswith("SIDE")}       # side panels are single-layer
        write_svg(res, os.path.join(OUT, f"纸样_{tag}_排料1比1.svg"), title)
        write_dxf(res, os.path.join(OUT, f"纸样_{tag}.dxf"))
        write_pdfs(res, OUT, title, tag)
        summary[layer] = {k: dict(area_m2=round(v["area_m2"], 4), stretch_max=v["stretch"][0] if v["stretch"] else None,
                                  stretch_min=v["stretch"][1] if v["stretch"] else None,
                                  size_mm=[round(float(np.ptp(v["cut"][:, 0]))), round(float(np.ptp(v["cut"][:, 1])))],
                                  bound_edge_mm=round(sum(np.linalg.norm(v["uv"][(i + 1) % len(v["uv"])] - v["uv"][i]) for i in range(len(v["uv"]))
                                                          if v["kinds"][i][1] == "bound" and v["kinds"][(i + 1) % len(v["uv"])][1] == "bound")))
                          for k, v in res.items()}
        if layer == "shell":
            summary["seams"] = [dict(a=a, b=b, seam=kind, len_a_mm=round(la, 1), len_b_mm=round(lb, 1), diff_mm=round(la - lb, 1))
                                for a, b, kind, la, lb in seam_report(res)]
            np.save(os.path.join(OUT, "_shell_pieces.npy"), {k: dict(V3=v["V3"], F=v["F"], phi=v["phi"], y=v["y"]) for k, v in pcs.items()}, allow_pickle=True)
    ex = build_extras(); title = "附件：口袋 / 内袋 / 面板遮挡罩"
    write_svg(ex, os.path.join(OUT, "纸样_附件_排料1比1.svg"), title); write_dxf(ex, os.path.join(OUT, "纸样_附件.dxf")); write_pdfs(ex, OUT, title, "附件")
    summary["extras"] = {k: dict(size_mm=[round(float(np.ptp(v["cut"][:, 0]))), round(float(np.ptp(v["cut"][:, 1])))], area_m2=round(v["area_m2"], 4)) for k, v in ex.items()}
    json.dump(summary, open(os.path.join(OUT, "pattern_summary.json"), "w"), ensure_ascii=False, indent=1)
    for s in summary["seams"]: print(f"seam {s['seam']:9s} {s['a']:8s}{s['len_a_mm']:7.1f}  vs {s['b']:8s}{s['len_b_mm']:7.1f}   diff {s['diff_mm']:+.1f} mm")
    for k, v in summary["shell"].items(): print(k, v)
