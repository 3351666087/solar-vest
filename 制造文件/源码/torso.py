"""Symmetric parametric torso of the wearer, built from the photogrammetry reconstruction.

Coordinates: metres, y up (floor = 0, includes ~1 cm shoe sole), +z = front, +x = wearer's LEFT.
  0.90-1.32 m  : 'BV' bare-torso mesh (shirt removed by the earlier inference) — each horizontal contour is
                 ray-sampled around the body axis, then made left/right symmetric.
  1.32-1.62 m  : the scan merges the arms into the shoulders and is twisted ~20°, so it is not usable there.
                 These levels are a superellipse family whose widths/depths come from the scan's sagittal
                 profile (back/front depth at x≈0) and stature-scaled anthropometry (ANSUR II male, 185 cm):
                 acromion 1.52, cervicale (C7) 1.588, suprasternale 1.527, axilla 1.40.
The torso is r(y, θ) around the vertical axis x = 0, θ measured from +x toward +z (θ=90° front, -90° back).
"""
import json, os, numpy as np
from scipy.interpolate import PchipInterpolator
HERE = os.path.dirname(os.path.abspath(__file__))
NT = 360
THETA = np.linspace(-np.pi, np.pi, NT, endpoint=False)

def _ray_sample(contour_xz, n=NT):
    """r(θ) of a closed contour around the origin (x=0, z=0) by ray casting."""
    from shapely.geometry import Polygon, LineString
    poly = Polygon(contour_xz).buffer(0)
    r = np.empty(n)
    for i, t in enumerate(THETA):
        far = LineString([(0, 0), (np.cos(t) * 1.0, np.sin(t) * 1.0)])
        hit = poly.exterior.intersection(far)
        pts = [hit] if hit.geom_type == "Point" else list(getattr(hit, "geoms", []))
        r[i] = max(np.hypot(p.x, p.y) for p in pts) if pts else np.nan
    return r

def _symmetrize(r):
    """mirror x -> -x  ==  θ -> π - θ"""
    idx = [np.argmin(np.abs(((np.pi - t + np.pi) % (2 * np.pi)) - np.pi - THETA)) for t in THETA]
    return 0.5 * (r + r[idx])

def _superellipse(a, zf, zb, n):
    """r(θ) of a superellipse with half-width a, front depth zf (+z), back depth zb (-z)."""
    c, s = np.cos(THETA), np.sin(THETA)
    b = np.where(s >= 0, zf, zb)
    return (np.abs(c / a) ** n + np.abs(s / b) ** n) ** (-1.0 / n)

def build():
    D = json.load(open(os.path.join(HERE, "body_data.json")))
    import trimesh
    BV = np.array(D["BV"]).reshape(-1, 3); BF = np.array(D["BF"]).reshape(-1, 3)
    body = trimesh.Trimesh(BV, BF, process=False)
    levels, R = [], []
    for y in np.arange(0.90, 1.325, 0.01):
        s = body.section(plane_origin=[0, y, 0], plane_normal=[0, 1, 0])
        if s is None: continue
        best = max(s.discrete, key=lambda e: np.ptp(e[:, 0]) * np.ptp(e[:, 2]))
        r = _ray_sample(best[:, [0, 2]])
        if np.isnan(r).any(): continue
        levels.append(y); R.append(_symmetrize(r))
    R = np.array(R)
    # superellipse fit of the top BV level, so the upper family starts exactly where the mesh ends
    r_top = R[-1]
    a0 = r_top[np.argmin(np.abs(THETA))]; zf0 = r_top[np.argmin(np.abs(THETA - np.pi / 2))]; zb0 = r_top[np.argmin(np.abs(THETA + np.pi / 2))]
    best_n = min(np.arange(1.6, 4.0, 0.05), key=lambda n: np.mean((_superellipse(a0, zf0, zb0, n) - r_top) ** 2))
    resid = r_top - _superellipse(a0, zf0, zb0, best_n)
    #            y      a       zf     zb     n     residual weight
    UP = [(1.320, a0,     zf0,   zb0,   best_n, 1.0),
          (1.360, 0.194,  0.146, 0.185, 2.30, 0.7),
          (1.400, 0.193,  0.138, 0.183, 2.40, 0.4),   # axilla
          (1.440, 0.196,  0.126, 0.178, 2.50, 0.2),
          (1.480, 0.200,  0.110, 0.168, 2.60, 0.0),
          (1.500, 0.202,  0.100, 0.164, 2.60, 0.0),
          (1.520, 0.200,  0.088, 0.157, 2.40, 0.0),   # acromion (shoulder point)
          (1.540, 0.170,  0.072, 0.145, 2.20, 0.0),
          (1.560, 0.125,  0.060, 0.129, 2.10, 0.0),
          (1.575, 0.095,  0.054, 0.113, 2.00, 0.0),
          (1.588, 0.078,  0.051, 0.099, 2.00, 0.0),   # cervicale / side neck point
          (1.605, 0.066,  0.050, 0.086, 2.00, 0.0),
          (1.625, 0.062,  0.050, 0.080, 2.00, 0.0)]
    U = np.array(UP)
    fine = np.arange(1.3225, 1.6251, 0.0025)
    par = {k: PchipInterpolator(U[:, 0], U[:, i]) for i, k in enumerate(["a", "zf", "zb", "n", "w"], 1)}
    for y in fine:
        R = np.vstack([R, _superellipse(par["a"](y), par["zf"](y), par["zb"](y), par["n"](y)) + par["w"](y) * resid])
        levels.append(y)
    Y = np.array(levels)
    # resample onto a uniform 2.5 mm grid and smooth along y (σ = 6 mm) so the mesh/parametric joint at
    # 1.32 m and the photogrammetry ripples do not show up as creases in the vest
    from scipy.ndimage import gaussian_filter1d
    Yu = np.arange(Y[0], Y[-1] + 1e-9, 0.0025)
    Ru = np.vstack([PchipInterpolator(Y, R[:, j])(Yu) for j in range(R.shape[1])]).T
    Ru = gaussian_filter1d(Ru, sigma=6.0 / 2.5, axis=0, mode="nearest")
    Y, R = Yu, Ru
    np.savez(os.path.join(HERE, "torso.npz"), Y=Y, R=R, THETA=THETA)
    return Y, R

class Torso:
    """r(y, θ) with smooth interpolation; point(y, θ) -> xyz (m)."""
    def __init__(self):
        p = os.path.join(HERE, "torso.npz")
        if not os.path.exists(p): build()
        d = np.load(p); self.Y, self.R = d["Y"], d["R"]
        Rw = np.hstack([self.R, self.R[:, :1]]); Tw = np.append(THETA, np.pi)
        from scipy.interpolate import RectBivariateSpline
        self.spl = RectBivariateSpline(self.Y, Tw, Rw, kx=3, ky=3, s=0)
    def r(self, y, t):
        t = (np.asarray(t) + np.pi) % (2 * np.pi) - np.pi
        return self.spl(y, t, grid=False)
    def point(self, y, t, off=0.0):
        """surface point offset `off` metres along the true 3D outward normal."""
        y = np.asarray(y, float); t = np.asarray(t, float)
        r = self.r(y, t)
        P = np.stack([r * np.cos(t), y, r * np.sin(t)], -1)
        if np.isscalar(off) and off == 0: return P
        h = 1e-4
        Py = np.stack([self.r(y + h, t) * np.cos(t), y + h, self.r(y + h, t) * np.sin(t)], -1) - P
        Pt = np.stack([self.r(y, t + h) * np.cos(t + h), y, self.r(y, t + h) * np.sin(t + h)], -1) - P
        n = np.cross(Py, Pt); n /= np.linalg.norm(n, axis=-1, keepdims=True)   # outward
        return P + n * np.asarray(off)[..., None]
    def girth(self, y, off=0.0):
        t = np.linspace(-np.pi, np.pi, 721)
        P = self.point(np.full_like(t, y), t, off)
        return np.sum(np.linalg.norm(np.diff(P, axis=0), axis=1))

if __name__ == "__main__":
    Y, R = build(); T = Torso()
    for y in (0.95, 1.05, 1.15, 1.25, 1.32, 1.40, 1.48, 1.52, 1.56, 1.59):
        print(f"y={y:.2f}  girth {T.girth(y)*100:6.1f} cm   half-width {T.r(y, 0)*100:5.1f}  front {T.r(y, np.pi/2)*100:5.1f}  back {T.r(y, -np.pi/2)*100:5.1f}")
