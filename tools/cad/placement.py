"""Where everything sits on the vest (metres, body frame: y up, +z front, +x wearer's left).

writes placement.json used by the enclosure CAD (shoe standoffs + contoured feet) and the assembly.
"""
import json, numpy as np
from vest_geom import P3, off_layer, off_in, DEG, mirror_phi, Y_YOKE
from torso import Torso
T = Torso()

CARRIER_EXTRA = 0.0025       # 1000D carrier patch (1 mm) + 1.5 mm HDPE frame sheet in the back
WEB_T, HOOK_T = 0.0016, 0.0020
HOOK_STACK = 0.0077          # printed U-hook: 2.0 plate behind the webbing + 2.2 slot + 3.5 pad
PANEL_L, PANEL_W, PANEL_D = 0.2618, 0.171, 0.015
MIN_GAP = 0.018              # air gap panel back <-> vest at the closest point
Y_TOP = 1.500

def carrier_pt(phi, y):
    return T.point(np.asarray(y, float), np.asarray(phi, float) * DEG, off_layer(np.asarray(y, float), "outer") + CARRIER_EXTRA)
def surface_frame(phi, y, layer_off):
    p = T.point(y, phi * DEG, layer_off); h = 1e-4
    py = T.point(y + h, phi * DEG, layer_off) - p; pt = T.point(y, phi * DEG + h, layer_off) - p
    n = np.cross(py, pt); n /= np.linalg.norm(n)            # outward
    up = py - (py @ n) * n; up /= np.linalg.norm(up)
    right = np.cross(up, n)                                   # wearer's ... (see usage)
    return p, n, up, right

# ------------------------------------------------------------------ panel pose
phis = np.linspace(-170, -10, 801)
def back_point_at_x(x, y):
    P = carrier_pt(phis, np.full_like(phis, y)); return P[np.argmin(np.abs(P[:, 0] - x))]
yb = Y_TOP - PANEL_W; yc = 0.5 * (Y_TOP + yb)
grid_u = np.linspace(-PANEL_L / 2, PANEL_L / 2, 27); grid_v = np.linspace(yb, Y_TOP, 19)
S = np.array([[back_point_at_x(u, v) for u in grid_u] for v in grid_v])          # carrier surface under the panel
best = None
for a in np.radians(np.arange(-15, 15.01, 0.25)):
    d = S[..., 2] - (S[..., 1] - yc) * np.tan(a); z0 = d.min() - MIN_GAP / np.cos(a); g = (d - z0) * np.cos(a)
    corner = max(g[0, 0], g[0, -1], g[-1, 0], g[-1, -1])
    if best is None or corner < best[0]: best = (corner, a, z0, g)
_, ALPHA, Z0, GAP = best
n_out = np.array([0.0, np.sin(ALPHA), -np.cos(ALPHA)]); up = np.array([0.0, np.cos(ALPHA), np.sin(ALPHA)]); ex = np.array([1.0, 0, 0])
C_BACK = np.array([0.0, yc, Z0])                         # centre of the panel's back (frame rear) plane
def plane_to_body(u, v, w=0.0):
    """panel-plane coords (m): u along +x body, v along 'up', w along n_out (away from body)."""
    return C_BACK + u * ex + v * up + w * n_out
def gap_at(u, v):
    """distance from the panel back plane to the carrier surface, measured along -n_out."""
    p = plane_to_body(u, v); y = p[1]
    q = back_point_at_x(u, y); return float((q - p) @ (-n_out)), q

# panel local frame (panel_6v6w.py): x = short side (171), y = long side (261.8, junction box at +y), z = out of the glass
# -> panel +x = body 'up', panel +y = body +x (junction box on the wearer's LEFT), panel +z = n_out
R_panel = np.c_[up, ex, n_out]

# ------------------------------------------------------------------ shoes (6): 4 corner cradles + 2 edge bumpers
SHOES = []
INSET_U, INSET_V = 0.018, 0.020
specs = [("TL", -1, +1, "corner_top"), ("TR", +1, +1, "corner_top"), ("BL", -1, -1, "corner_bottom"), ("BR", +1, -1, "corner_bottom"),
         ("MT", 0, +1, "edge_top"), ("MB", 0, -1, "edge_bottom")]
for name, su, sv, kind in specs:
    u_c = su * (PANEL_L / 2 - INSET_U); v_c = sv * (PANEL_W / 2 - INSET_V)
    # sample the carrier surface under a 44 x 44 mm foot, in foot-local (s along u, t along v) coords, w = gap
    ss = np.linspace(-0.022, 0.022, 9); tt = np.linspace(-0.022, 0.022, 9)
    G = np.array([[gap_at(u_c + s, v_c + t)[0] for s in ss] for t in tt])
    Sg, Tg = np.meshgrid(ss, tt)
    A = np.c_[np.ones(Sg.size), Sg.ravel(), Tg.ravel(), Sg.ravel() ** 2]
    coef, *_ = np.linalg.lstsq(A, G.ravel(), rcond=None)
    rms = float(np.sqrt(np.mean((A @ coef - G.ravel()) ** 2)))
    g0, q = gap_at(u_c, v_c)
    SHOES.append(dict(name=name, kind=kind, u=u_c, v=v_c, gap_center_mm=g0 * 1000,
                      gap_min_mm=float(G.min() * 1000), gap_max_mm=float(G.max() * 1000),
                      fit_mm=dict(h0=coef[0] * 1000, a=coef[1], b=coef[2], c=coef[3] / 1000, rms=rms * 1000),
                      contact_point=q.tolist(), webbing_row="A" if sv > 0 else "B"))

# ------------------------------------------------------------------ webbing rows on the carrier (y, φ range)
ROWS = {"A": 1.485, "B": 1.345, "C": 1.265}
# move the row heights so they sit under the shoe feet centres
for s in SHOES:
    if s["name"] in ("TL", "TR", "MT"): ROWS["A"] = float(plane_to_body(0, s["v"])[1])
    if s["name"] in ("BL", "BR", "MB"): ROWS["B"] = float(plane_to_body(0, s["v"])[1])

# bar tacks (body x, m): each hook sits between two tacks with ~3 mm play each side
TACKS = {"A": [-0.128, -0.098, -0.017, 0.017, 0.098, 0.128], "B": [-0.128, -0.098, -0.017, 0.017, 0.098, 0.128],
         "C": [-0.128, -0.042, 0.0, 0.042, 0.128]}
def phi_back_at_x(x, y):
    ph = np.linspace(-170, -10, 1601); P = carrier_pt(ph, np.full_like(ph, y)); return float(ph[np.argmin(np.abs(P[:, 0] - x))])

# ------------------------------------------------------------------ pods
def pod_pose(phi, y, layer_off, back_off):
    p, n, upv, right = surface_frame(phi, y, layer_off)
    return dict(origin=(p + n * back_off).tolist(), normal=n.tolist(), up=upv.tolist(), right=right.tolist())
BACK_POD = pod_pose(-90.0, 1.205, float(off_layer(1.205, "outer") + CARRIER_EXTRA), HOOK_STACK)
# the pod's two hooks have their bridge 15 mm below the pod's top edge -> webbing row C centre 13 mm below that
ROWS["C"] = round(1.205 + 0.1316 / 2 - 0.015 - 0.013, 4)
BACK_POD.update(size_mm=[101.0, 131.6, 28.5], hangs_on="C")
CHEST_POD = pod_pose(mirror_phi(48.0), 1.378, float(off_layer(1.378, "outer")), 0.0012)
CHEST_POD.update(size_mm=[67.3, 110.5, 19.6], pocket="FRONT_R")

# ------------------------------------------------------------------ cable routes (surface polylines, metres)
def surf_path(pts_phi_y, layer="outer", extra=0.004):
    out = []
    for (pa, ya), (pb, yb_) in zip(pts_phi_y[:-1], pts_phi_y[1:]):
        for t in np.linspace(0, 1, 25, endpoint=False):
            ph, y = pa + (pb - pa) * t, ya + (yb_ - ya) * t
            out.append(T.point(y, ph * DEG, off_layer(y, layer) + extra))
    ph, y = pts_phi_y[-1]; out.append(T.point(y, ph * DEG, off_layer(y, layer) + extra))
    return np.array(out)
def length(P): return float(np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1)))
jb = plane_to_body(+0.0785, 0.0, -0.004)                     # junction box exit, under the panel
pod_o = np.array(BACK_POD["origin"])
CABLES = {}
# panel lead: from the junction box straight down behind the panel, then along the carrier to the pod's left wall
p1 = surf_path([(-90 + np.degrees(np.arcsin(0.072 / 0.19)), 1.42), (-90 + np.degrees(np.arcsin(0.062 / 0.19)), 1.28)], "outer", 0.006)
CABLES["panel"] = np.vstack([jb, p1]).tolist()
CABLES["J6_back_to_chest"] = surf_path([(-90 - 22, 1.215), (-150, 1.235), (-180, 1.255), (mirror_phi(20), 1.30), (mirror_phi(40), 1.33)], "outer", 0.003).tolist()
CABLES["ref1"] = surf_path([(-90 + np.degrees(np.arcsin(0.145 / 0.19)), 1.43), (-90 + np.degrees(np.arcsin(0.065 / 0.19)), 1.28)], "outer", 0.006).tolist()
CABLES["ref2"] = surf_path([(-8, 1.548), (-30, 1.50), (-55, 1.40), (-90 + np.degrees(np.arcsin(0.06 / 0.19)), 1.28)], "outer", 0.004).tolist()
CABLE_LEN = {k: round(length(np.array(v)) * 1000) for k, v in CABLES.items()}

REF2_POSE = pod_pose(-8.0, 1.548, float(off_layer(1.548, "outer")), 0.001)
REF1_POSE = dict(origin=plane_to_body(+(PANEL_L / 2 + 0.020), 0.0, PANEL_D).tolist(), normal=n_out.tolist(), up=up.tolist())

out = dict(
    note="metres, body frame: y up (floor 0, 1 cm sole), +z front, +x = wearer's left",
    panel=dict(size_mm=[PANEL_L * 1000, PANEL_W * 1000, PANEL_D * 1000], top_y=Y_TOP, tilt_deg=float(np.degrees(ALPHA)),
               back_plane_centre=C_BACK.tolist(), R_panel_to_body=R_panel.tolist(), n_out=n_out.tolist(), up=up.tolist(),
               gap_mm=dict(min=float(GAP.min() * 1000), max=float(GAP.max() * 1000),
                           corners=[float(GAP[0, 0] * 1000), float(GAP[0, -1] * 1000), float(GAP[-1, 0] * 1000), float(GAP[-1, -1] * 1000)])),
    shoes=SHOES, webbing_rows_y=ROWS, bar_tacks_x=TACKS,
    bar_tacks_phi={r: [phi_back_at_x(x, ROWS[r]) for x in xs] for r, xs in TACKS.items()}, back_pod=BACK_POD, chest_pod=CHEST_POD, ref1=REF1_POSE, ref2=REF2_POSE,
    cables=CABLES, cable_length_mm=CABLE_LEN,
)
json.dump(out, open("placement.json", "w"), indent=1)
if __name__ == "__main__":
    print(f"panel tilt {np.degrees(ALPHA):+.2f}°, gap min {GAP.min()*1000:.1f} max {GAP.max()*1000:.1f} mm")
    for s in SHOES: print(f"  {s['name']}: gap centre {s['gap_center_mm']:.1f} mm (foot {s['gap_min_mm']:.1f}-{s['gap_max_mm']:.1f}), fit rms {s['fit_mm']['rms']:.2f} mm, c={s['fit_mm']['c']:.5f}/mm")
    print("rows", {k: round(v, 3) for k, v in ROWS.items()}, "cables mm", CABLE_LEN)
