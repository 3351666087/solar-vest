"""V3-G9 worn checks for V3-F: wrist model (the strap lane's elliptical wrist, q = 0.68, Ramanujan perimeter; source in
../ref/sources.md WRIST), cross-sections for 130 / 140 / 165 / 200 mm wrists, either-wrist pose, the highest point of every
item, capsule contact on a desk and in side sleep (roll sweep), wrist extension against the hand-end wall, button reach,
the head on the contacts while worn. Also exports the worn assembly (165 mm, left and right wrists) as STEP + GLB and renders.

usage: python3 -B worn_v3f.py         (V3F_POD_L=41 for the reserve)
"""
import json, math, os, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import geom_v3f as G                                       # noqa: E402
from shapely.geometry import Polygon, Point, LineString, box as sbox   # noqa: E402

OUT = G.OUT_DIR                                             # [G1] out/ for plain outlines, out/options/<TAG>/ for option runs
TAG = G.TAG
Z = G.Z
L = G.POD_L
TS = G.STRAP_T
CAPS, WING = G.CAPSULE, G.WING
R_FAR = G.CAPSULE["r_far"]   # [E] capsule far outer edge radius 1.0 mm (glass top 37.4 x 9.9 mm); one constant in geom_v3f [S1 C-18]
TOP_PV, TOP_WIN = Z.pv1, Z.win1
HW = G.POD_W / 2                      # [G1] half pod width: u = Y - HW (16.0 at 32 mm)
FAST = bool(os.environ.get("V3F_FAST"))   # [G1] option runs: numbers and plots only, no worn STEP / GLB / renders


# ----------------------------------------------------------------------------------------------- strap path (u > 0 = ulnar)
class Path:
    """strap centre line from the bar: straight free span, then the skin-offset ellipse to the volar midline (t = pi)"""
    def __init__(self, Cw):
        g = G.wrist_geo(Cw)
        self.g = g; self.a, self.b = g["a"], g["b"]
        self.P0 = np.array(g["P0"]); self.d = np.array(g["d"]); self.n = np.array(g["n"]); self.free = g["free"]
        t = np.linspace(g["t0"], math.pi, 6000)
        a, b = self.a, self.b
        nx, ny = np.sin(t) / a, np.cos(t) / b; nn = np.hypot(nx, ny); nx, ny = nx / nn, ny / nn
        cx, cy = a * np.sin(t) + TS / 2 * nx, b * np.cos(t) + TS / 2 * ny
        ds = np.hypot(np.diff(cx), np.diff(cy)); self.sc = np.r_[0.0, np.cumsum(ds)] + self.free
        self.cx, self.cy, self.nx, self.ny = cx, cy, nx, ny
        self.s_end = float(self.sc[-1])

    def at(self, s):
        """centre point and outward unit normal at arc length s"""
        if s <= self.free:
            return self.P0 + s * self.d, self.n
        i = min(np.searchsorted(self.sc, s), len(self.sc) - 1)
        return np.array([self.cx[i], self.cy[i]]), np.array([self.nx[i], self.ny[i]])

    def band(self, s0, s1, off0, off1, ds=0.25):
        """polygon of the strip between s0..s1 and offsets off0..off1 from the centre line (offset along the local normal)"""
        ss = np.arange(s0, s1 + 1e-9, ds)
        if ss[-1] < s1: ss = np.r_[ss, s1]
        lo, hi = [], []
        for s in ss:
            c, n = self.at(s); lo.append(c + off0 * n); hi.append(c + off1 * n)
        return Polygon(lo + hi[::-1]).buffer(0)

    def rigid(self, s0, s1, t, r_far=0.0):
        """rigid item whose inner face lies on the strap's inner face along the straight free span (continued straight past
        the tangent point if s1 > free); t = thickness; optional radius on the far outer edge"""
        P0, d, n = self.P0, self.d, self.n
        def pt(s, o): return P0 + s * d + o * n
        o0 = -TS / 2
        if r_far <= 0:
            return Polygon([pt(s0, o0), pt(s1, o0), pt(s1, o0 + t), pt(s0, o0 + t)])
        pts = [pt(s0, o0), pt(s1, o0), pt(s1, o0 + t - r_far)]
        for k in range(1, 12):
            a = math.radians(90.0 * k / 12)
            pts.append(pt(s1 - r_far + r_far * math.cos(a), o0 + t - r_far + r_far * math.sin(a)))
        pts += [pt(s1 - r_far, o0 + t), pt(s0, o0 + t)]
        return Polygon(pts)


def ellipse_poly(a, b, n=720):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return Polygon(np.c_[a * np.sin(t), b * np.cos(t)])


def mirror_u(p):
    return Polygon([(-x, y) for x, y in p.exterior.coords])


def pod_section(b):
    """pod outer cross-section in the wrist frame (u = Y - 16, v = b + Z): body, top step, lugs (from the CAD regions)"""
    win = Polygon([(-HW, b + 0.0), (-HW, b + TOP_WIN), (G.Y_WIN1 - HW, b + TOP_WIN), (G.Y_WIN1 - HW, b + TOP_PV),
                   (HW, b + TOP_PV), (HW, b + 0.0)])
    lugA = sbox(HW, b + 0.0, HW + G.BAR_OUT, b + Z.pv_seat)
    lugB = sbox(-HW - G.BAR_OUT, b + 0.0, -HW, b + Z.pv_seat)
    mesa = sbox(G.CAP["y0"] - HW, b + Z.mesa, G.CAP["y1"] - HW, b)
    return dict(body=win, lugA=lugA, lugB=lugB, mesa=mesa)


def items_for(Cw, side="both"):
    """all worn cross-section items (u > 0 = ulnar side carries root A and the capsule; u < 0 = radial, root B and the wing)"""
    p = Path(Cw); a, b = p.a, p.b
    it = {}
    ps = pod_section(b); it.update({"pod_" + k: v for k, v in ps.items()})
    it["rootA_hinge"] = p.band(0.0, CAPS["s0"], -TS / 2, TS / 2)
    it["capsule"] = p.rigid(CAPS["s0"], CAPS["s1"], CAPS["t"], R_FAR)
    it["rootA_end"] = p.band(CAPS["s1"], G.ROOT_END_S, -TS / 2, TS / 2)
    it["rootA_QR"] = p.band(G.QR["s0"], G.QR["s1"], -TS / 2, -TS / 2 + G.QR["t"])
    it["band_A"] = p.band(G.QR["s1"], p.s_end, -TS / 2, TS / 2)
    it["rootB_hinge"] = mirror_u(p.band(0.0, WING["s0"], -TS / 2, TS / 2))
    it["wing"] = mirror_u(p.rigid(WING["s0"], WING["s1"], WING["t"]))
    it["rootB_end"] = mirror_u(p.band(WING["s1"], G.ROOT_END_S, -TS / 2, TS / 2))
    it["rootB_QR"] = mirror_u(p.band(G.QR["s0"], G.QR["s1"], -TS / 2, -TS / 2 + G.QR["t"]))
    it["band_B"] = mirror_u(p.band(G.QR["s1"], p.s_end, -TS / 2, TS / 2))
    # buckle at the volar midline, on the band's outer face
    it["buckle"] = sbox(-G.BUCKLE["l"] / 2, -b - G.BUCKLE["t"], G.BUCKLE["l"] / 2, -b)     # 2.5 mm over the skin incl. the band
    return p, it


def thickness_above_skin(poly, a, b):
    """max over the item's outline of the signed distance to the skin ellipse (+ outside)"""
    pts = np.asarray(poly.exterior.coords)
    return max(G.ellipse_dist(q, a, b, n=4000) for q in pts[::max(1, len(pts) // 60)])


def worn_numbers(Cw):
    p, it = items_for(Cw); a, b = p.a, p.b
    P0, d, n = p.P0, p.d, p.n
    def pt(s, o): return P0 + s * d + o * n
    o0 = -TS / 2
    res = dict(wrist_mm=Cw, a=round(a, 3), b=round(b, 3), free_span_mm=round(p.free, 2), tilt_deg=round(p.g["tilt"], 1))
    for nm, s0, s1, t in (("capsule", CAPS["s0"], CAPS["s1"], CAPS["t"]), ("wing", WING["s0"], WING["s1"], WING["t"])):
        far_out = pt(s1, o0 + t); far_in = pt(s1, o0)
        near_out = pt(s0, o0 + t)
        res[nm] = dict(
            thickness_above_skin_far_end_box_mm=round(G.ellipse_dist(far_out, a, b), 2),            # BASELINE item_on_free_span method
            thickness_above_skin_far_end_cad_mm=round(max(G.ellipse_dist(q, a, b) for q in np.asarray(
                p.rigid(s0, s1, t, R_FAR if nm == "capsule" else 0.0).exterior.coords) if np.dot(np.asarray(q) - P0, d) >= s1 - 2.5), 2),
            inner_face_gap_far_end_mm=round(G.ellipse_dist(far_in, a, b), 3),
            inner_face_gap_at_min_s1_free_minus_0p3_mm=round(G.ellipse_dist(pt(min(s1, p.free - 0.3), o0), a, b), 3),
            overhang_past_tangent_mm=round(max(0.0, s1 - p.free), 2),
            outer_top_below_pod_PV_top_mm=round((b + TOP_PV) - near_out[1], 2),
            outer_top_below_pod_window_top_mm=round((b + TOP_WIN) - near_out[1], 2),
            max_height_above_floor_plane_mm=round(max(q[1] for q in np.asarray(p.rigid(s0, s1, t).exterior.coords)) - b, 2))
    # every item: (1) max height above the floor plane (v - b), (2) max distance from the skin (prominence)
    tab = {}
    for nm, poly in it.items():
        if nm == "pod_mesa":
            continue
        crd = np.asarray(poly.exterior.coords)
        tab[nm] = dict(max_height_above_floor_plane_mm=round(float(crd[:, 1].max() - b), 2),
                       max_distance_from_skin_mm=round(thickness_above_skin(poly, a, b), 2))
    res["items"] = tab
    res["convention_thickness_above_skin_mm"] = {
        "pod window half (mesa pressed in)": round(TOP_WIN, 2), "pod PV half": round(TOP_PV, 2), "E3 rim / K corner": round(Z.rim_top, 2),
        "capsule (far end)": res["capsule"]["thickness_above_skin_far_end_box_mm"], "wing root (far end)": res["wing"]["thickness_above_skin_far_end_box_mm"],
        "textile band": TS, "quick release": G.QR["t"], "buckle (volar)": G.BUCKLE["t"]}
    if G.BUMPER:   # [S2b M-5] the corner bumpers stand G.BUMPER (0.34 after the mini-ECO) above the flat top (four R6 corners only)
        res["convention_thickness_above_skin_mm"]["pod corner bumpers (four R6 corners) [S2b M-5]"] = round(Z.win1 + G.BUMPER, 3)
    return res


# ----------------------------------------------------------------------------------------------- desk and side-sleep roll sweep
def roll_sweep(Cw, step=1.0):
    """rotate the strapped wrist cross-section by phi (deg) about the wrist centre: phi = 0 dorsal up (volar side on the desk),
    +90 ulnar side down (side sleep on the ulnar edge, writing posture), -90 radial side down, 180 dorsal down (palm up).
    The support plane touches the lowest point; report which item touches first and how far it stands out of the skin."""
    p, it = items_for(Cw); a, b = p.a, p.b
    skin = ellipse_poly(a, b, 1440)
    names = [k for k in it if k != "pod_mesa"] + ["skin"]
    pts = {k: np.asarray(it[k].exterior.coords) for k in it if k != "pod_mesa"}
    pts["skin"] = np.asarray(skin.exterior.coords)
    rows = []
    for phi in np.arange(-180.0, 180.0 + 1e-9, step):
        f = math.radians(phi)
        # down direction after the roll: (sin phi, -cos phi) in (u, v); height of a point above the support = -u sin phi + v cos phi + const
        proj = {k: -P[:, 0] * math.sin(f) + P[:, 1] * math.cos(f) for k, P in pts.items()}
        lows = {k: float(np.min(v)) for k, v in proj.items()}
        first = min(lows, key=lows.get)
        rows.append(dict(phi=float(phi), first=first, stand_out_of_skin_mm=round(lows["skin"] - lows[first], 2)))
    # summary: angular ranges per first-contact item
    ranges = []
    cur = None
    for r in rows:
        if cur is None or r["first"] != cur["item"]:
            cur = dict(item=r["first"], phi0=r["phi"], phi1=r["phi"], max_stand_out_mm=r["stand_out_of_skin_mm"]); ranges.append(cur)
        else:
            cur["phi1"] = r["phi"]; cur["max_stand_out_mm"] = max(cur["max_stand_out_mm"], r["stand_out_of_skin_mm"])
    key = {f"phi {k:+d}": next(r for r in rows if abs(r["phi"] - k) < 1e-6) for k in (0, 45, 60, 75, 90, 105, 120, -45, -60, -75, -90, -105, -120, 180)}
    return dict(wrist_mm=Cw, ranges=ranges, key_angles=key, rows=rows)


# ----------------------------------------------------------------------------------------------- wrist extension (sagittal)
def extension_angle(g, h, d):
    """hand dorsum rotating about an axis at depth d below the dorsal skin line, at the joint line; the pod's distal top
    corner at height h above the skin and g mm proximal of the joint line. Returns the extension angle (deg) at which the
    dorsal line of the hand reaches the corner: g sin(th) + (h + d) cos(th) = d."""
    A, B = g, h + d
    R = math.hypot(A, B); ph = math.atan2(A, B)
    if d / R > 1:
        return 0.0
    return math.degrees(ph + math.acos(d / R))


def wrist_extension():
    out = dict(model="2-D sagittal: forearm dorsal skin flat (the floor plane), hand dorsum a straight line through the joint line, "
                     "rotating about an axis at depth d below the dorsal skin (capitate head; depth not found in a source: d = 12 / 16 / 20 mm E); "
                     "pod distal top corner at height h above the skin and g mm proximal of the joint line; soft tissue not modelled (E)",
               functional_extension_deg=40, functional_source="J Hand Surg Am 16(3) 1991 functional-ROM study (search summary, ref key RYU91): most tasks within 40 deg extension",
               cases=[])
    ends = {"left wrist: hand-end wall (E3 rim, top 3.85; window glass corner 4.30 at 2.5 mm proximal)": [(0.0, Z.rim_top), (G.SETBACK, TOP_WIN)],
            "right wrist: elbow-end wall turned to the hand (window lip / glass 4.30 at the end; K block 3.85)": [(0.0, TOP_WIN)]}
    for lab, corners in ends.items():
        for d in (12.0, 16.0, 20.0):
            for g in (0.0, 5.0, 10.0, 15.0, 20.0):
                th40 = min(extension_angle(g + dx, h, d) for dx, h in corners)
                th41 = min(extension_angle(g + dx - 0.5, h, d) for dx, h in corners)      # 41 mm pod, centred placement
                thL = min(extension_angle(g + dx - (L - 40.0) / 2, h, d) for dx, h in corners)   # [G1] this pod length, centred placement
                out["cases"].append(dict(end=lab, axis_depth_mm=d, gap_pod_end_to_joint_line_mm=g, contact_deg_40mm=round(th40, 1),
                                         contact_deg_41mm_centred=round(th41, 1), contact_deg_this_pod_centred=round(thL, 1)))
    return out


# ----------------------------------------------------------------------------------------------- button and head
def button_reach():
    mb = G.MEMBRANE; sw = G.SW1
    zc = Z.pcb1 + sw["act_z_mid"]
    res = dict(membrane_window_Y=(mb["y0"], mb["y1"]), membrane_Z_above_skin=(mb["z0"], mb["z1"]), actuator_centre_above_skin_mm=round(zc, 2),
               e3_wrap_bottom_above_skin_mm=G.E3_WRAP["z0"], gap_membrane_top_to_E3_wrap_mm=round(G.E3_WRAP["z0"] - mb["z1"], 2),
               travel_mm=0.2, force_N=round(0.220 * 9.81, 2), source="PTS840 GK: 220 gf, travel 0.2 +0.2/-0.1 [DS PTS840 B-34]")
    # finger model: fingertip pad as a sphere of radius R; pressing the membrane centre on a vertical face at height zc above
    # a flat skin plane needs the sphere to approach from above at angle alpha with sin(alpha) >= 1 - zc / R (pad not into the skin)
    fr = {}
    for R in (5.0, 7.0, 9.0):
        s = 1 - zc / R
        alpha = math.degrees(math.asin(max(-1.0, min(1.0, s))))
        fr[f"R {R:g} mm"] = dict(min_approach_angle_from_horizontal_deg=round(alpha, 1),
                                 horizontal_share_of_press_force=round(math.cos(math.radians(alpha)), 2))
    res["fingertip_approach"] = fr
    res["left_wrist"] = "button faces the hand (distal); corridor to the hand dorsum = the pod-to-joint gap g; the hand covers it only in extension (see wrist_extension)"
    res["right_wrist"] = "button faces the elbow (proximal): the forearm skin continues flat; nothing covers it; E3 then sits at the elbow end too"
    res["roots"] = "both roots leave the long walls (Y), the button is on the end wall (X): no strap item in front of it on either wrist"
    return res


def head_check(Cw):
    p, it = items_for(Cw); a, b = p.a, p.b
    hd = G.HEAD
    # head cross-section (u, v) at the K corner: Y 20.6..35.6 -> u 4.6..19.6, Z 3.85..10.85
    head = sbox(hd["y0"] - HW, b + Z.rim_top, hd["y1"] - HW, b + Z.rim_top + hd["h"])
    out = dict(wrist_mm=Cw, footprint_case=(hd["x0"], hd["x1"], hd["y0"], hd["y1"]), height_mm=hd["h"])
    for k in ("capsule", "rootA_hinge", "rootA_end", "pod_lugA"):
        out[f"clearance to {k}"] = round(head.distance(it[k]), 2)
    out["clearance to skin"] = round(head.distance(ellipse_poly(a, b, 1440)), 2)
    # [S1 C-12] head lane housing: seat face from y 21.0; the 1.0 x 0.6 mm rebate on the window side passes over the window glass
    reb_w, reb_h = hd["rebate"]
    out["window glass step"] = (f"seat face from Y {hd['seat_y0']} (glass edge Y {G.Y_WIN1}, step {Z.win1 - Z.rim_top:.3f} mm): flat on the K block and laminate "
                                f"(Z {Z.rim_top}); the rebate ({reb_w} x {reb_h} mm) clears the glass by {Z.rim_top + reb_h - Z.win1:.3f} mm")
    out["rebate_clearance_mm"] = round(Z.rim_top + reb_h - Z.win1, 3)
    out["left wrist cable"] = "K corner at the elbow end: the head body and its USB-C cable point toward +x, i.e. toward the hand over the pod top"
    out["right wrist cable"] = "K corner at the hand end: head body and cable point toward the elbow over the pod top"
    return out


# ----------------------------------------------------------------------------------------------- plots
COL = {"pod_body": "0.15", "pod_lugA": "0.25", "pod_lugB": "0.25", "pod_mesa": "#7fb7e6", "capsule": "#f0f0f0", "wing": "#1f2a6b",
       "rootA_hinge": "#6a6a6a", "rootB_hinge": "#6a6a6a", "rootA_end": "#6a6a6a", "rootB_end": "#6a6a6a", "rootA_QR": "#b07030",
       "rootB_QR": "#b07030", "band_A": "#3c6e8f", "band_B": "#3c6e8f", "buckle": "#c9a227"}


def plot_sections(results):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MP
    fig, axs = plt.subplots(2, 2, figsize=(16, 13))
    for ax, Cw in zip(axs.ravel(), G.WRISTS):
        p, it = items_for(Cw); a, b = p.a, p.b
        ax.add_patch(MP(np.asarray(ellipse_poly(a, b).exterior.coords), closed=True, fc="#f3d7c4", ec="#b07a5a", lw=1))
        for nm, poly in it.items():
            ax.add_patch(MP(np.asarray(poly.exterior.coords), closed=True, fc=COL.get(nm, "0.6"), ec="k", lw=0.5, alpha=0.95))
        r = results["wrists"][str(int(Cw))]
        ax.set_xlim(-a - 6, a + 6); ax.set_ylim(-b - 6, b + 10); ax.set_aspect("equal"); ax.grid(alpha=0.25)
        ax.axhline(b + TOP_WIN, color="r", lw=0.6, ls=":"); ax.axhline(b + TOP_PV, color="m", lw=0.6, ls=":")
        cp = r["capsule"]; wg = r["wing"]
        ax.set_title(f"{Cw:.0f} mm wrist (a {a:.1f}, b {b:.1f} mm), free span {r['free_span_mm']} mm, tilt {r['tilt_deg']} deg\n"
                     f"capsule {cp['thickness_above_skin_far_end_box_mm']} mm above the skin at its far end, inner gap {cp['inner_face_gap_far_end_mm']}, "
                     f"overhang {cp['overhang_past_tangent_mm']}; wing {wg['thickness_above_skin_far_end_box_mm']} mm", fontsize=9)
        ax.text(-a - 5, b + 8.5, "radial (root B, wing)", fontsize=8); ax.text(a - 12, b + 8.5, "ulnar (root A, capsule)", fontsize=8)
        ax.set_xlabel("u mm (ulnar +)"); ax.set_ylabel("v mm (dorsal +)")
    fig.suptitle(f"V3-F {TAG} worn cross-sections (strap-lane ellipse q 0.68; pod floor tangent to the dorsal vertex, mesa pressed in). "
                 f"Identical on the left and right wrists (band turned 180 deg). Red dotted: window top 4.30; magenta: PV top 3.85", fontsize=10)
    fig.tight_layout(rect=(0, 0, 1, 0.97)); fig.savefig(os.path.join(OUT, f"worn_sections_{TAG}.png"), dpi=110); plt.close(fig)


def plot_roll(rolls):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MP
    fig = plt.figure(figsize=(17, 11))
    cols = {"capsule": "#d62728", "wing": "#1f77b4", "pod_body": "k", "buckle": "#c9a227", "band_A": "#2ca02c", "band_B": "#2ca02c",
            "skin": "#f3a07a", "pod_lugA": "0.4", "pod_lugB": "0.4", "rootA_end": "0.6", "rootB_end": "0.6", "rootA_QR": "#b07030", "rootB_QR": "#b07030"}
    ax = fig.add_subplot(2, 1, 1)
    for i, (Cw, R) in enumerate(rolls.items()):
        for rg in R["ranges"]:
            ax.barh(i, rg["phi1"] - rg["phi0"] + 1, left=rg["phi0"] - 0.5, color=cols.get(rg["item"], "0.8"), edgecolor="none")
            if rg["phi1"] - rg["phi0"] > 8:
                ax.text((rg["phi0"] + rg["phi1"]) / 2, i, f"{rg['item']}\n{rg['max_stand_out_mm']}", ha="center", va="center", fontsize=6.5, color="w" if rg["item"] in ("pod_body", "wing", "capsule") else "k")
    ax.set_yticks(range(len(rolls))); ax.set_yticklabels([f"{c} mm" for c in rolls]); ax.set_xlim(-180, 180)
    ax.set_xlabel("roll angle phi, deg: 0 = dorsal up (volar side on the support), +90 = ulnar side down (side sleep / writing), -90 = radial side down, 180 = palm up")
    ax.set_title(f"V3-F {TAG}: first item to touch a flat support when the strapped wrist rolls (number = how far it stands out of the skin, mm)", fontsize=10)
    for k, phi in enumerate((90, 60, -90)):
        a2 = fig.add_subplot(2, 3, 4 + k)
        p, it = items_for(165.0); a, b = p.a, p.b
        f = math.radians(phi)
        def rot(P): P = np.asarray(P); return np.c_[P[:, 0] * math.cos(f) + P[:, 1] * math.sin(f), -P[:, 0] * math.sin(f) + P[:, 1] * math.cos(f)]
        allp = [rot(ellipse_poly(a, b).exterior.coords)] + [rot(pp.exterior.coords) for nm, pp in it.items()]
        ymin = min(P[:, 1].min() for P in allp)
        a2.add_patch(MP(allp[0], closed=True, fc="#f3d7c4", ec="#b07a5a"))
        for (nm, pp), P in zip(it.items(), allp[1:]):
            a2.add_patch(MP(P, closed=True, fc=COL.get(nm, "0.6"), ec="k", lw=0.5))
        a2.axhline(ymin, color="k", lw=2)
        a2.set_xlim(-45, 45); a2.set_ylim(ymin - 3, ymin + 60); a2.set_aspect("equal"); a2.grid(alpha=0.2)
        a2.set_title(f"165 mm wrist, phi {phi:+d} deg", fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, f"worn_roll_contact_{TAG}.png"), dpi=110); plt.close(fig)


def plot_extension(ext):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 2, figsize=(16, 6.5))
    ax = axs[0]
    g, d, h = 10.0, 16.0, Z.rim_top
    th = extension_angle(g, h, d)
    ax.fill_between([-L - g, -g], [0, 0], [-8, -8], color="#f3d7c4")
    ax.add_patch(__import__("matplotlib.patches", fromlist=["Rectangle"]).Rectangle((-L - g, 0), L, h, fc="0.2"))
    for t_, ls in ((0.0, ":"), (40.0, "--"), (th, "-")):
        f = math.radians(t_)
        P = np.array([-d * math.sin(f), -d + d * math.cos(f)]); u = np.array([math.cos(f), math.sin(f)])
        Q = P + 60 * u
        ax.plot([P[0], Q[0]], [P[1], Q[1]], ls, color="#b07a5a", lw=2, label=f"hand dorsum at {t_:.0f} deg")
    ax.plot([0], [-d], "ko"); ax.text(1, -d, "axis (capitate head, depth d)", fontsize=8)
    ax.set_xlim(-L - g - 3, 45); ax.set_ylim(-d - 3, 40); ax.set_aspect("equal"); ax.grid(alpha=0.3); ax.legend(fontsize=8)
    ax.set_title(f"left wrist, pod end {g:g} mm proximal of the joint line, d {d:g} mm: hand touches the E3 rim at {th:.0f} deg", fontsize=10)
    ax.set_xlabel("x mm (0 = joint line)"); ax.set_ylabel("height above the forearm skin, mm")
    ax = axs[1]
    for lab, mk in ((list({c["end"] for c in ext["cases"]})[0], "o"), (list({c["end"] for c in ext["cases"]})[1], "s")):
        for d_ in (12.0, 16.0, 20.0):
            cs = [c for c in ext["cases"] if c["end"] == lab and c["axis_depth_mm"] == d_]
            ax.plot([c["gap_pod_end_to_joint_line_mm"] for c in cs], [c["contact_deg_40mm"] for c in cs], mk + "-",
                    label=f"{'left' if lab.startswith('left') else 'right'} wrist, d {d_:g}")
    ax.axhline(40, color="r", ls="--", lw=1); ax.text(0.3, 41, "functional extension 40 deg (J Hand Surg 1991)", color="r", fontsize=8)
    ax.set_xlabel("gap from the pod's distal end to the joint line, mm (one finger width above the wrist bone is about 15-20 mm)")
    ax.set_ylabel("extension at first contact, deg"); ax.grid(alpha=0.3); ax.legend(fontsize=7, ncol=2)
    ax.set_title("wrist extension at which the hand dorsum meets the pod", fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(OUT, f"worn_wrist_extension_{TAG}.png"), dpi=110); plt.close(fig)


# ----------------------------------------------------------------------------------------------- 3-D worn assembly
def _yz_prism(poly_so, x0, x1):
    """polygon in the local (s, o) plane -> solid along X from x0 to x1 (local frame: Y = s, Z = o)"""
    from build123d import Wire, Face, Vector, extrude, Pos
    pts = [Vector(0, sv, ov) for sv, ov in list(poly_so.exterior.coords)[:-1]]
    f = Face(Wire.make_polygon(pts, close=True))
    return Pos(x0, 0, 0) * extrude(f, x1 - x0, dir=(1, 0, 0))


def _local_box(x0, x1, s0, s1, o0, o1):
    return _yz_prism(sbox(s0, o0, s1, o1), x0, x1)


def capsule_parts(p):
    """capsule on root A in its local frame (x along the forearm, s along the strap, o = 0 at the strap's inner face),
    returned in the worn frame of the LEFT wrist: shell (PC), glass top, cell (GEB301030 class, end of life 3.5 mm), PCM end"""
    from build123d import Pos, Rot
    c = CAPS; x0 = c["x0"]; s0, s1, t = c["s0"], c["s1"], c["t"]
    outer = Polygon([(s0, 0), (s1, 0), (s1, t - R_FAR)] + [(s1 - R_FAR + R_FAR * math.cos(math.radians(9 * k)), t - R_FAR + R_FAR * math.sin(math.radians(9 * k)))
                                                         for k in range(1, 10)] + [(s1 - R_FAR, t), (s0, t)])
    side, bot, top = c["side"], c["wall"], c["top"]
    cav = sbox(s0 + side, bot, s1 - side, t - top)
    g_s1 = s1 - R_FAR - 0.5
    shell = _yz_prism(outer, x0, x0 + c["L"]) - _local_box(x0 + side, x0 + c["L"] - side, s0 + side, s1 - side, bot, t - top) \
        - _local_box(x0 + side, x0 + c["L"] - side, s0 + side, g_s1, t - top, t + 0.01)
    glass = _local_box(x0 + side, x0 + c["L"] - side, s0 + side, g_s1, t - top, t)
    cl, cw = c["cell"]
    xc0 = x0 + side + c["pcm_len"] + c["tabs"]
    scen = (s0 + s1) / 2
    cell = _local_box(xc0, xc0 + cl, scen - cw / 2, scen + cw / 2, bot, bot + c["cell_t"])
    pcm = _local_box(x0 + side + 0.1, x0 + side + c["pcm_len"] - 0.1, s0 + side + 0.3, s1 - side - 0.3, bot, bot + 1.25)
    tabs = _local_box(x0 + side + c["pcm_len"], xc0, scen - 2.5, scen + 2.5, bot + 1.10, bot + 1.25)
    tilt = p.g["tilt"]
    o0 = -TS / 2
    T = lambda sol: Pos(0, p.P0[0], p.P0[1]) * (Rot(-tilt, 0, 0) * (Pos(0, 0, o0) * sol))   # noqa: E731
    return {"capsule_shell_pc": T(shell), "capsule_glass_top": T(glass), "capsule_cell": T(cell), "capsule_pcm": T(pcm),
            "capsule_tab_joints": T(tabs)}


def wing_parts(p):
    """wing on root B (radial): TPU/FKM core 1.20 + laminate 1.75 with 4 sub-cells 2.7 x 31 mm, built on the ulnar side and
    mirrored by a 180 deg turn about the vertical axis through the pod centre (then x maps to POD_L - x, symmetric)"""
    from build123d import Pos, Rot
    w = WING; x0 = w["x0"]; s0, s1 = w["s0"], w["s1"]
    core = _local_box(x0, x0 + w["L"], s0, s1, 0, w["core"])
    lam = _local_box(x0, x0 + w["L"], s0, s1, w["core"], w["t"])
    ax0 = (L - w["cell_x"]) / 2
    pitch = (s1 - s0 - 0.6) / w["cells"]
    cells = [_local_box(ax0, ax0 + w["cell_x"], s0 + 0.3 + i * pitch + 0.15, s0 + 0.3 + i * pitch + 0.15 + w["cell_s"], w["t"] - 0.55, w["t"] - 0.385)
             for i in range(w["cells"])]
    for cc in cells:
        lam = lam - cc
    tilt = p.g["tilt"]; o0 = -TS / 2
    T = lambda sol: Pos(L, 0, 0) * (Rot(0, 0, 180) * (Pos(0, p.P0[0], p.P0[1]) * (Rot(-tilt, 0, 0) * (Pos(0, 0, o0) * sol))))   # noqa: E731
    out = {"wing_core_tpu": T(core), "wing_laminate": T(lam)}
    for i, cc in enumerate(cells):
        out[f"wing_cell_{i + 1}"] = T(cc)
    return out


def worn_assembly(Cw=165.0, wrist="left"):
    """worn assembly in the world frame of a LEFT arm (x toward the hand, y toward the ulnar side, z dorsal; wrist ellipse
    centred at y = z = 0). The right-wrist assembly is the same assembly turned 180 deg about the vertical axis through
    (POD_L / 2, 0): the band is turned on the right wrist and the right arm's ulnar side is -y."""
    import model_v3f as MV
    from build123d import Wire, Face, Vector, extrude, Pos, Rot
    P = MV.build()
    p, it = items_for(Cw); a, b = p.a, p.b
    parts = {}
    for nm, s_ in P.items():
        if nm == "parts_envelope":
            continue
        parts["pod/" + nm] = Pos(0, -HW, b) * s_
    def xprism(poly, x0, x1):
        pts = [Vector(0, u, v) for u, v in list(poly.exterior.coords)[:-1]]
        f = Face(Wire.make_polygon(pts, close=True))
        return Pos(x0, 0, 0) * extrude(f, x1 - x0, dir=(1, 0, 0))
    cx = L / 2
    spans = {"rootA_hinge": (G.LUG["x0"], G.LUG["x1"]), "rootB_hinge": (G.LUG["x0"], G.LUG["x1"]), "rootA_end": (cx - 17.5, cx + 17.5),
             "rootB_end": (cx - 17.5, cx + 17.5), "rootA_QR": (cx - 12.0, cx + 12.0), "rootB_QR": (cx - 12.0, cx + 12.0),
             "band_A": (cx - G.BAND["w"] / 2, cx + G.BAND["w"] / 2), "band_B": (cx - G.BAND["w"] / 2, cx + G.BAND["w"] / 2),
             "buckle": (cx - G.BUCKLE["w"] / 2, cx + G.BUCKLE["w"] / 2)}
    for nm, (x0, x1) in spans.items():
        parts["strap/" + nm] = xprism(it[nm], x0, x1)
    for nm, s_ in capsule_parts(p).items():
        parts["strap/" + nm] = s_
    for nm, s_ in wing_parts(p).items():
        parts["strap/" + nm] = s_
    parts["wrist_skin"] = xprism(ellipse_poly(a, b, 360), -35.0, L + 12.0)
    if wrist == "right":
        parts = {k: Pos(L, 0, 0) * (Rot(0, 0, 180) * v) for k, v in parts.items()}
    return parts


def main():
    t0 = time.time()
    res = dict(pod_L=G.POD_L, pod_W=G.POD_W, tag=G.TAG, wrist_model="ellipse q 0.68 (Coll. Antropol. 2014 via the strap lane), perimeter Ramanujan II, strap 1.5 mm, bar 2.5 mm "
                                           "outside the wall at 1.0 mm, floor tangent to the dorsal vertex (mesa pressed in)", wrists={})
    for Cw in G.WRISTS:
        res["wrists"][str(int(Cw))] = worn_numbers(Cw)
    res["baseline_section9"] = dict(capsule_thickness_above_skin={"140": 4.50, "165": 4.51, "200": 4.55, "130": 4.50},
                                    capsule_outer_top_below_pod_top={"140": 2.78, "165": 2.05, "200": 1.37},
                                    capsule_inner_face_gap_far_end={"140": 0.00, "165": 0.03, "200": 0.07, "130": 0.002},
                                    capsule_overhang={"130": 0.23}, wing_above_skin={"140": 2.95, "165": 2.97, "200": 3.01},
                                    free_span={"130": 13.7, "140": 14.0, "165": 14.7, "200": 15.7}, tilt={"130": 66, "140": 61, "165": 51, "200": 42})
    rolls = {int(Cw): roll_sweep(Cw) for Cw in G.WRISTS}
    res["roll_contact"] = {str(k): dict(ranges=v["ranges"], key_angles=v["key_angles"]) for k, v in rolls.items()}
    res["wrist_extension"] = wrist_extension()
    res["button"] = button_reach()
    res["head"] = {str(int(Cw)): head_check(Cw) for Cw in G.WRISTS}
    res["either_wrist"] = dict(
        mapping="left: x = X, u = Y - 16; right: band turned 180 deg about the vertical: x = POD_L - X, u = Y - 16 (u toward the ulnar side)",
        wing="root B (Y = 0) radial on both wrists", capsule="root A (Y = 32) ulnar on both wrists",
        E3={"left": "hand end", "right": "elbow end"}, button={"left": "hand-end wall, faces the hand", "right": "faces the elbow"},
        contacts={"left": "elbow end, ulnar corner", "right": "hand end, ulnar corner"},
        buckle="volar midline on both wrists (symmetric band); operated by the other hand from either side",
        cross_section="identical on both wrists (symmetric ellipse): every height and fit number holds for both")
    json.dump(res, open(os.path.join(OUT, f"worn_checks_{TAG}.json"), "w"), indent=1, default=str)
    plot_sections(res); plot_roll(rolls); plot_extension(res["wrist_extension"])
    print(f"numbers + plots {time.time() - t0:.1f}s", flush=True)
    if FAST:
        print("V3F_FAST: worn STEP / GLB / renders skipped"); return
    # 3-D worn assemblies (165 mm, both wrists): STEP + GLB + renders
    from build123d import Compound, Color, export_step, export_gltf
    import model_v3f as MV, zrender
    for wrist in ("left", "right"):
        parts = worn_assembly(165.0, wrist)
        cols = {}
        for nm, s in parts.items():
            base = nm.split("/")[-1]
            c = MV.COLORS.get(base) or {"capsule_shell_pc": (0.96, 0.96, 0.96, 1), "capsule_glass_top": (0.85, 0.92, 0.98, 0.6),
                                        "capsule_cell": (0.75, 0.75, 0.70, 1), "capsule_pcm": (0.1, 0.45, 0.2, 1), "capsule_tab_joints": (0.8, 0.8, 0.8, 1),
                                        "wing_core_tpu": (0.25, 0.25, 0.28, 1), "wing_laminate": (0.85, 0.9, 0.95, 0.5),
                                        "wing_cell_1": (0.08, 0.10, 0.32, 1), "wing_cell_2": (0.08, 0.10, 0.32, 1), "wing_cell_3": (0.08, 0.10, 0.32, 1),
                                        "wing_cell_4": (0.08, 0.10, 0.32, 1), "buckle": (0.8, 0.65, 0.15, 1),
                                        "wrist_skin": (0.95, 0.80, 0.70, 0.35), "band_A": (0.24, 0.43, 0.56, 1), "band_B": (0.24, 0.43, 0.56, 1),
                                        "rootA_QR": (0.69, 0.44, 0.19, 1), "rootB_QR": (0.69, 0.44, 0.19, 1)}.get(base, (0.40, 0.40, 0.42, 1))
            cols[nm] = list(c)
            s.label = nm.replace("/", "_"); s.color = Color(*c)
        if wrist == "left":
            asm = Compound(label=f"SolarBand_V3F_{TAG}_worn_165mm_left", children=list(parts.values()))
            export_step(asm, os.path.join(OUT, f"V3F_{TAG}_worn_165_left.step"))
            export_gltf(asm, os.path.join(OUT, f"V3F_{TAG}_worn_165_left.glb"), binary=True, linear_deflection=0.02, angular_deflection=0.3)
        L_ = []
        for nm, s in parts.items():
            m = MV.to_tm(s, tol=0.02)
            base = nm.split("/")[-1]
            c = list(cols[nm])
            if base == "wrist_skin":
                c = [0.95, 0.80, 0.70, 0.30]
            if base in ("window_glass", "pv_glass", "pv_encapsulant", "frontlight_film"):
                c[3] = 0.3
            L_.append((nm, np.asarray(m.vertices), np.asarray(m.faces), c))
        zrender.render(L_, os.path.join(OUT, f"render_worn_165_{wrist}_{TAG}.png"), 28, -62 if wrist == "left" else -62, size=(1500, 1100),
                       title=f"V3-F {TAG} worn on a 165 mm {wrist} wrist (x toward the hand): wing radial, capsule ulnar"
                             + ("; E3 and button at the hand end" if wrist == "left" else "; band turned 180 deg: E3 and button at the elbow end, contacts at the hand end"))
        zrender.render(L_, os.path.join(OUT, f"render_worn_165_{wrist}_end_{TAG}.png"), 8, 0, size=(1400, 1000),
                       title=f"V3-F {TAG} worn, 165 mm {wrist} wrist, view along the forearm from the hand")
        zrender.render(L_, os.path.join(OUT, f"render_worn_165_{wrist}_ulnar_{TAG}.png"), 25, 118 if wrist == "left" else -118, size=(1500, 1100),
                       title=f"V3-F {TAG} worn, 165 mm {wrist} wrist, seen from the ulnar side: capsule (white, glass top) on root A")
    print(f"done {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
