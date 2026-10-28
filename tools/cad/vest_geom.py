"""Vest pieces on the parametric torso: outlines in (φ, y) parameter space, 3D meshes, ARAP flattening.

φ (deg) runs around the body: 90 = centre front (left front edge), 0 = wearer's left side, -90 = centre back,
-180 = wearer's right side, -270 = centre front (right front edge). This avoids a wrap-around at the right side.
Lengths: metres in 3D, millimetres in the flattened patterns.
"""
import numpy as np, triangle, igl
from shapely.geometry import Polygon, box, LineString, Point
from shapely.ops import unary_union
from scipy.interpolate import CubicSpline
from torso import Torso

T = Torso()
DEG = np.pi / 180

# ------------------------------------------------------------------ fit / layer stack
def off_in(y):
    """vest lining (inner face) distance from skin: 13 mm ease at chest/waist -> +8 cm girth, 5 mm on shoulders."""
    # upper chest kept at 10-11 mm so the ECG snap connectors on the collar bones (≈ 8 mm tall) are not crushed
    return np.interp(y, [1.00, 1.30, 1.45, 1.52, 1.56, 1.60], [0.013, 0.013, 0.011, 0.010, 0.006, 0.005])
LINING_T, SHELL_T = 0.0030, 0.0005        # 3 mm 3D spacer mesh lining, 500D Cordura shell
def off_layer(y, layer):
    return off_in(y) + {"lining": LINING_T / 2, "shell": LINING_T + SHELL_T / 2, "outer": LINING_T + SHELL_T}[layer]

def P3(phi_deg, y, layer="shell"):
    phi_deg = np.asarray(phi_deg, float); y = np.asarray(y, float)
    return T.point(y, phi_deg * DEG, off_layer(y, layer))

# ------------------------------------------------------------------ key heights (m, standing, incl. 1 cm sole)
Y_HEM_F, Y_HEM_B = 1.060, 1.040            # just above the belt line
Y_NECK_B = 1.582                            # 6 mm below C7 -> ~4.5 cm neck ease
Y_NECK_F = 1.505                            # scoop front neck, 2 cm below the suprasternal notch
Y_SP = 1.538                                # vest shoulder point, ~1.5 cm inside the acromion
Y_ARM_BOT = 1.360                           # armhole bottom, 4 cm below the axilla
PHI_SIDE = 12.0                             # stretch side panel spans ±12° around each side
Y_SPLIT = 1.455                             # above this the front/back meet at the shoulder seam (φ = 0)
Y_YOKE = 1.505                              # back yoke seam: just above the solar panel's top edge (1.50 m)
Y_YOKE_F = 1.465                            # front yoke seam (chest), keeps the shoulder curvature out of the front body
PHI_PRINCESS = -42.0                        # back princess seams at φ = -42° and -138°

def phi_at_x(x_target, y, front=True, layer="shell"):
    """φ on the front (0..90) or back (-90..0) where the surface has |x| = x_target at height y."""
    ph = np.linspace(0.0, 90.0, 901) if front else np.linspace(-90.0, 0.0, 901)
    X = P3(ph, np.full_like(ph, y), layer)[:, 0]
    i = np.argmin(np.abs(X - x_target)); return float(ph[i])

def armhole_curve(n=240):
    """closed armhole loop (left side) in (φ, y): SP -> front -> bottom -> back -> SP."""
    front = [(0.170, 1.480), (0.165, 1.430), (0.167, 1.395)]
    back = [(0.175, 1.395), (0.172, 1.430), (0.178, 1.480)]
    pts = [(0.0, Y_SP)] + [(phi_at_x(x, y, True), y) for x, y in front] + [(0.0, Y_ARM_BOT)] + \
          [(phi_at_x(x, y, False), y) for x, y in back] + [(0.0, Y_SP)]
    P = np.array(pts); s = np.r_[0, np.cumsum(np.hypot(np.diff(P[:, 0]) / 60, np.diff(P[:, 1]) / 0.15))]
    cs = CubicSpline(s, P, bc_type="periodic")
    return cs(np.linspace(0, s[-1], n, endpoint=False))

def neckline(phi):
    """y of the neckline at φ (left half, φ in [-90, 90])."""
    phi = np.asarray(phi, float)
    front = Y_NECK_F + (Y_NECK_B - Y_NECK_F) * np.cos(np.clip(phi, 0, 90) / 90 * np.pi / 2) ** 2
    return np.where(phi <= 0, Y_NECK_B, front)
def hem(phi):
    return 0.5 * (Y_HEM_F + Y_HEM_B) + 0.5 * (Y_HEM_F - Y_HEM_B) * np.sin(np.asarray(phi, float) * DEG)

def mirror_phi(phi): return -180.0 - np.asarray(phi)        # wearer's left <-> right

def band_polygon():
    ph = np.linspace(-270, 90, 721)
    phl = np.where(ph < -90, mirror_phi(ph), ph)              # evaluate the left-half functions symmetrically
    lo = np.c_[ph, hem(phl)]; hi = np.c_[ph, neckline(phl)][::-1]
    return Polygon(np.vstack([lo, hi]))

def piece_polygons():
    band = band_polygon()
    armL = Polygon(armhole_curve()); armR = Polygon(np.c_[mirror_phi(armhole_curve()[:, 0]), armhole_curve()[:, 1]])
    body = band.difference(armL).difference(armR)
    lo, hi = 0.9, 1.7
    zones = {
        "FRONT_L": unary_union([box(PHI_SIDE, lo, 90, Y_SPLIT), box(0, Y_SPLIT, 90, Y_YOKE_F)]),
        "YOKE_FL": box(0, Y_YOKE_F, 90, hi),
        "SIDE_L": box(-PHI_SIDE, lo, PHI_SIDE, Y_SPLIT),
        "YOKE_B": box(-180, Y_YOKE, 0, hi),
        "BACK_C": box(-180 - PHI_PRINCESS, lo, PHI_PRINCESS, Y_YOKE),
        "BACK_SL": unary_union([box(PHI_PRINCESS, lo, -PHI_SIDE, Y_SPLIT), box(PHI_PRINCESS, Y_SPLIT, 0, Y_YOKE)]),
        "BACK_SR": unary_union([box(-180 + PHI_SIDE, lo, -180 - PHI_PRINCESS, Y_SPLIT), box(-180, Y_SPLIT, -180 - PHI_PRINCESS, Y_YOKE)]),
        "SIDE_R": box(-180 - PHI_SIDE, lo, -180 + PHI_SIDE, Y_SPLIT),
        "FRONT_R": unary_union([box(-270, lo, -180 - PHI_SIDE, Y_SPLIT), box(-270, Y_SPLIT, -180, Y_YOKE_F)]),
        "YOKE_FR": box(-270, Y_YOKE_F, -180, hi),
    }
    out = {}
    for k, z in zones.items():
        g = body.intersection(z)
        if g.geom_type == "MultiPolygon": g = max(g.geoms, key=lambda q: q.area)
        out[k] = g
    return out, armL, armR

# ------------------------------------------------------------------ meshing + flattening
R_SCALE = 0.19 * DEG          # φ degrees -> metres-ish so the param-space triangulation is near-isotropic
def mesh_piece(poly, max_edge=0.008):
    ext = np.array(poly.exterior.coords)[:-1]
    # resample the boundary so no edge exceeds max_edge (in scaled param units)
    pts = []
    for a, b in zip(ext, np.roll(ext, -1, 0)):
        da = np.hypot((b[0] - a[0]) * R_SCALE, b[1] - a[1]); n = max(1, int(np.ceil(da / max_edge)))
        for t in np.arange(n) / n: pts.append(a + (b - a) * t)
    pts = np.array(pts); S = np.c_[pts[:, 0] * R_SCALE, pts[:, 1]]
    segs = np.c_[np.arange(len(S)), (np.arange(len(S)) + 1) % len(S)]
    tri = triangle.triangulate({"vertices": S, "segments": segs}, f"pq30a{max_edge**2 * 0.45:.8f}")
    UV = tri["vertices"]; F = tri["triangles"].astype(np.int64)
    phi, y = UV[:, 0] / R_SCALE, UV[:, 1]
    return phi, y, F

def flatten(V3, F):
    """LSCM initial guess -> ARAP (as-rigid-as-possible) parametrisation, in mm. Returns UV and per-face stretch."""
    bnd = igl.boundary_loop(F)
    i0 = bnd[0]; i1 = bnd[np.argmax(np.linalg.norm(V3[bnd] - V3[i0], axis=1))]
    d = np.linalg.norm(V3[i1] - V3[i0])
    uv0, _ = igl.lscm(V3, F, np.array([i0, i1], np.int64), np.array([[0.0, 0.0], [d, 0.0]]))
    data = igl.ARAPData(); data.max_iter = 200; data.with_dynamics = True     # dynamic regularisation instead of pinned vertices (libigl tutorial 503)
    igl.arap_precomputation(np.ascontiguousarray(V3), np.ascontiguousarray(F), 2, np.zeros(0, np.int32), data)
    uv = igl.arap_solve(np.zeros((0, 2)), data, uv0)
    # per-face singular values of the 3D->2D map
    s1, s2 = [], []
    for f in F:
        a, b, c = V3[f]; e1, e2 = b - a, c - a
        n1 = e1 / np.linalg.norm(e1); n2 = np.cross(np.cross(e1, e2), e1); n2 /= np.linalg.norm(n2)
        X = np.array([[e1 @ n1, e2 @ n1], [e1 @ n2, e2 @ n2]])
        U = np.array([uv[f[1]] - uv[f[0]], uv[f[2]] - uv[f[0]]]).T
        sv = np.linalg.svd(U @ np.linalg.inv(X), compute_uv=False); s1.append(sv[0]); s2.append(sv[1])
    return uv * 1000.0, np.array(s1), np.array(s2)

def orient(uv, V3, F):
    """rotate/flip the flat piece so 3D 'up' (+y) is +v (grain line vertical) and the pattern faces the right side."""
    # gradient of the 3D height over the flat piece = grain direction
    A = np.c_[uv, np.ones(len(uv))]; g, *_ = np.linalg.lstsq(A, V3[:, 1], rcond=None)
    ang = np.arctan2(g[1], g[0]); c, s = np.cos(np.pi / 2 - ang), np.sin(np.pi / 2 - ang)
    uv = uv @ np.array([[c, s], [-s, c]])
    # right side up: the outward normal of the 3D piece must map to +z of the flat triangle orientation
    f = F[0]; p, q = uv[f[1]] - uv[f[0]], uv[f[2]] - uv[f[0]]; e = p[0] * q[1] - p[1] * q[0]
    n3 = np.cross(V3[f[1]] - V3[f[0]], V3[f[2]] - V3[f[0]])
    centroid = V3[f].mean(0); outward = np.array([centroid[0], 0, centroid[2]])
    if (e > 0) != (n3 @ outward > 0): uv[:, 0] *= -1
    return uv - uv.min(0)

def build_piece(name, poly, layer):
    phi, y, F = mesh_piece(poly)
    V3 = P3(phi, y, layer)
    # keep triangles consistently oriented (outward normal)
    n = np.cross(V3[F[:, 1]] - V3[F[:, 0]], V3[F[:, 2]] - V3[F[:, 0]])
    c = V3[F].mean(1); outward = np.c_[c[:, 0], np.zeros(len(c)), c[:, 2]]
    flip = np.einsum("ij,ij->i", n, outward) < 0
    F[flip] = F[flip][:, ::-1]
    uv, s1, s2 = flatten(V3, F)
    uv = orient(uv, V3, F)
    return dict(name=name, layer=layer, phi=phi, y=y, V3=V3, F=F, uv=uv, s_max=s1, s_min=s2,
                bnd=igl.boundary_loop(F))

if __name__ == "__main__":
    polys, aL, aR = piece_polygons()
    for k, p in polys.items(): print(k, p.geom_type, "param area", round(p.area, 3), "bounds", np.round(p.bounds, 3))
    print("armhole φ range", np.round([np.array(aL.exterior.coords)[:, 0].min(), np.array(aL.exterior.coords)[:, 0].max()], 1))
    for k in ("YOKE_B", "BACK_C", "BACK_SL", "FRONT_L", "YOKE_FL", "SIDE_L"):
        pc = build_piece(k, polys[k], "shell")
        A = pc["s_max"] * pc["s_min"]
        print(f"{k}: {len(pc['F'])} tris  flat size {pc['uv'].max(0).round(0)} mm  stretch max {pc['s_max'].max():.3f} min {pc['s_min'].min():.3f}  area ratio p5/p95 {np.percentile(A,5):.3f}/{np.percentile(A,95):.3f}")
