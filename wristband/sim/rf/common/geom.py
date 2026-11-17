"""Physical-scene primitives -> MEEP geometry on a TO-stretched grid.

All physical coordinates in mm.  See tomesh.py for the transformation.
Precedence: background (per zone) < dielectric primitives (list order) < PEC.
"""
import math
from dataclasses import dataclass, field
import numpy as np
from shapely.geometry import Polygon, MultiPolygon, box as sbox, GeometryCollection
from shapely.ops import unary_union

from tomesh import to_factors

C0 = 299792458.0
EPS0 = 8.8541878128e-12
F0_HZ = 2.44e9                         # material reference frequency
A_M = 1e-3                             # MEEP length unit = 1 mm
OMEGA_MEEP = 2 * math.pi * F0_HZ * A_M / C0


@dataclass(frozen=True)
class Mat:
    name: str
    eps: float = 1.0
    sigma: float = 0.0          # S/m (physical); converted to MEEP D-conductivity
    tand: float = 0.0           # alternative: loss tangent at F0
    pec: bool = False

    def sigma_d(self):
        """MEEP D_conductivity (units c/a): sigma/(eps0*eps) * a/c, or omega*tand."""
        s = 0.0
        if self.sigma:
            s += self.sigma / (EPS0 * self.eps) * A_M / C0
        if self.tand:
            s += OMEGA_MEEP * self.tand
        return s


AIR = Mat("air", 1.0)
PEC = Mat("pec", pec=True)


@dataclass
class Box:
    lo: tuple
    hi: tuple
    mat: Mat
    tag: str = ""


@dataclass
class PolyZ:
    """prism along z: shapely polygon (x,y) between z0 and z1 (z0==z1: PEC sheet)"""
    poly: object
    z0: float
    z1: float
    mat: Mat
    tag: str = ""


@dataclass
class IfacePlane:
    """horizontal interface layer at z between mat_lo (below) and mat_hi (above), over poly"""
    poly: object
    z: float
    mat_lo: Mat
    mat_hi: Mat
    tag: str = ""
    mat: Mat = field(default_factory=lambda: Mat("iface"))


@dataclass
class EllCylX:
    """elliptic cylinder along x: (y-yc)^2/a^2 + (z-zc)^2/b^2 <= 1, x0<x<x1"""
    yc: float
    zc: float
    a: float
    b: float
    x0: float
    x1: float
    mat: Mat
    nseg: int = 96          # 96-gon: max chord sagitta 0.015 mm on a 28 mm semi-axis
    tag: str = ""


@dataclass
class PolyX:
    """prism along x: shapely polygon in (y, z) between x0 and x1 (dielectric only)"""
    poly: object
    x0: float
    x1: float
    mat: Mat
    tag: str = ""


def _polys(g):
    if g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, (MultiPolygon, GeometryCollection)):
        out = []
        for q in g.geoms:
            out += _polys(q)
        return out
    return []


class GeometryBuilder:
    def __init__(self, mesh, mp, zone_planes=True):
        self.zone_planes = zone_planes
        self.mesh = mesh
        self.mp = mp
        self._cache = {}
        self.stats = dict(background=0, dielectric=0, pec=0)

    # ------------------------------------------------------------------
    def medium(self, mat, s):
        if mat.pec:
            return self.mp.metal
        key = (mat, tuple(round(v, 9) for v in s))
        if key in self._cache:
            return self._cache[key]
        f = to_factors(s)
        sd = mat.sigma_d()
        kw = dict(epsilon_diag=self.mp.Vector3(*(mat.eps * v for v in f)),
                  mu_diag=self.mp.Vector3(*f))
        if sd > 0:
            kw["D_conductivity_diag"] = self.mp.Vector3(sd, sd, sd)
        m = self.mp.Medium(**kw)
        self._cache[key] = m
        return m

    def _block_comp(self, lo_c, hi_c, med):
        mp = self.mp
        c = mp.Vector3(*[float(a + b) / 2 for a, b in zip(lo_c, hi_c)])
        sz = mp.Vector3(*[float(b - a) for a, b in zip(lo_c, hi_c)])
        return mp.Block(center=c, size=sz, material=med)

    # ------------------------------------------------------------------
    def background(self, mat=AIR):
        objs = []
        M = self.mesh
        for ijk in M.zones():
            bx = M.zone_box_phys(ijk)
            lo = [M.ax[d].to_comp(bx[d][0]) for d in range(3)]
            hi = [M.ax[d].to_comp(bx[d][1]) for d in range(3)]
            objs.append(self._block_comp(lo, hi, self.medium(mat, M.zone_s(ijk))))
        self.stats["background"] += len(objs)
        if self.zone_planes:
            objs += self.zone_boundary_planes(mat)
        return objs

    def zone_boundary_planes(self, mat=AIR):
        """Grid points lying exactly on a zone boundary plane (normal = axis a) are shared by
        two zones.  With eps_averaging off MEEP would give them the material of whichever
        block comes last.  The non-uniform-Yee-consistent value is the arithmetic mean of
        the tangential eps' (Ey, Ez on an x-plane: dual-cell length averaging) and the
        harmonic mean of the normal mu' (Hx on an x-plane).  These one-plane blocks set
        exactly that for the background material (validation/: restores the far-field
        directivity of the TO grid to the uniform-grid value)."""
        M = self.mesh
        d = M.dcomp
        out = []
        nz = [len(M.ax[a].segs) for a in range(3)]
        for a in range(3):
            b, c = [q for q in range(3) if q != a]
            for i in range(nz[a] - 1):
                xb = float(M.ax[a].xc[i + 1])          # comp coordinate of the boundary plane
                for j in range(nz[b]):
                    for k in range(nz[c]):
                        ijk_l = [0, 0, 0]; ijk_l[a] = i; ijk_l[b] = j; ijk_l[c] = k
                        ijk_r = list(ijk_l); ijk_r[a] = i + 1
                        sl, sr = M.zone_s(tuple(ijk_l)), M.zone_s(tuple(ijk_r))
                        fl, fr = to_factors(sl), to_factors(sr)
                        eps = [mat.eps * 0.5 * (fl[q] + fr[q]) for q in range(3)]
                        mu = [0.5 * (fl[q] + fr[q]) for q in range(3)]
                        mu[a] = 2.0 / (1.0 / fl[a] + 1.0 / fr[a])
                        eps[a] = mat.eps * 2.0 / (1.0 / fl[a] + 1.0 / fr[a])
                        med = self.mp.Medium(epsilon_diag=self.mp.Vector3(*eps), mu_diag=self.mp.Vector3(*mu))
                        lo = [0.0] * 3; hi = [0.0] * 3
                        lo[a], hi[a] = xb - 0.49 * d, xb + 0.49 * d
                        sb, sc = M.ax[b].segs[j], M.ax[c].segs[k]
                        lo[b], hi[b] = float(M.ax[b].to_comp(sb[0])), float(M.ax[b].to_comp(sb[1]))
                        lo[c], hi[c] = float(M.ax[c].to_comp(sc[0])), float(M.ax[c].to_comp(sc[1]))
                        out.append(self._block_comp(lo, hi, med))
        self.stats["zone_planes"] = len(out)
        return out

    def interface_plane(self, poly, z, mat_lo, mat_hi, tag=""):
        """One-plane layer at a horizontal dielectric interface z (a grid plane) over the
        polygon: tangential eps = arithmetic mean of the two media (what subpixel averaging
        gives for Ex, Ey on a planar interface), conductivities averaged the same way."""
        M = self.mesh
        d = M.dcomp
        zc = float(M.ax[2].to_comp(z))
        out = []
        minx, miny, maxx, maxy = poly.bounds
        for i in M.ax[0].overlapping(minx, maxx):
            for j in M.ax[1].overlapping(miny, maxy):
                k_lo = int(M.ax[2].seg_index_phys(z - 1e-7)); k_hi = int(M.ax[2].seg_index_phys(z + 1e-7))
                zr = sbox(M.ax[0].segs[i][0], M.ax[1].segs[j][0], M.ax[0].segs[i][1], M.ax[1].segs[j][1])
                for q in _polys(poly.intersection(zr)):
                    qc = self._map_poly(q, (0, 1))
                    fl = to_factors(M.zone_s((i, j, k_lo))); fh = to_factors(M.zone_s((i, j, k_hi)))
                    # tangential (x, y): half dual cell in each medium -> arithmetic mean of eps'
                    et = [0.5 * (mat_lo.eps * fl[q] + mat_hi.eps * fh[q]) for q in range(2)]
                    st = [0.5 * (mat_lo.eps * mat_lo.sigma_d() * fl[q] + mat_hi.eps * mat_hi.sigma_d() * fh[q]) for q in range(2)]
                    ez = 0.5 * (mat_lo.eps * fl[2] + mat_hi.eps * fh[2])          # unused (no Ez on the plane)
                    muz = 2.0 / (1.0 / fl[2] + 1.0 / fh[2])                     # Hz on the plane: normal -> harmonic
                    kw = dict(epsilon_diag=self.mp.Vector3(et[0], et[1], ez),
                              mu_diag=self.mp.Vector3(0.5 * (fl[0] + fh[0]), 0.5 * (fl[1] + fh[1]), muz))
                    if max(st) > 0:
                        kw["D_conductivity_diag"] = self.mp.Vector3(st[0] / et[0], st[1] / et[1], st[0] / et[0])
                    out.append(self._prism(qc, 2, zc - 0.49 * d, zc + 0.49 * d, self.mp.Medium(**kw)))
        self.stats["interface_planes"] = self.stats.get("interface_planes", 0) + len(out)
        return out

    def box(self, b: Box):
        M = self.mesh
        d = M.dcomp
        if b.mat.pec:
            lo, hi = [], []
            for k in range(3):
                a, c = M.ax[k].to_comp(b.lo[k]), M.ax[k].to_comp(b.hi[k])
                if abs(c - a) < 1e-9:      # zero-thickness sheet
                    lo.append(a - 0.49 * d); hi.append(a + 0.49 * d)
                else:
                    lo.append(a - 0.02 * d); hi.append(c + 0.02 * d)
            self.stats["pec"] += 1
            return [self._block_comp(lo, hi, self.mp.metal)]
        out = []
        ranges = [M.ax[k].overlapping(b.lo[k], b.hi[k]) for k in range(3)]
        for i in ranges[0]:
            for j in ranges[1]:
                for kk in ranges[2]:
                    ijk = (i, j, kk)
                    zb = M.zone_box_phys(ijk)
                    lo = [max(b.lo[q], zb[q][0]) for q in range(3)]
                    hi = [min(b.hi[q], zb[q][1]) for q in range(3)]
                    lo_c = [M.ax[q].to_comp(lo[q]) for q in range(3)]
                    hi_c = [M.ax[q].to_comp(hi[q]) for q in range(3)]
                    out.append(self._block_comp(lo_c, hi_c, self.medium(b.mat, M.zone_s(ijk))))
        self.stats["dielectric"] += len(out)
        return out

    def _prism(self, poly_c, axis, a0, a1, med):
        """poly_c: shapely polygon in the two comp coords perpendicular to axis
        (for axis z: (x',y'); for axis x: (y',z')).  Prism from a0 to a1."""
        mp = self.mp
        xs, ys = poly_c.exterior.coords.xy
        pts = [(float(a), float(b)) for a, b in list(zip(xs, ys))[:-1]]
        a0, a1 = float(a0), float(a1)
        if axis == 2:
            verts = [mp.Vector3(p[0], p[1], a0) for p in pts]
            ax = mp.Vector3(0, 0, 1)
        elif axis == 0:
            verts = [mp.Vector3(a0, p[0], p[1]) for p in pts]
            ax = mp.Vector3(1, 0, 0)
        else:
            raise NotImplementedError
        return mp.Prism(vertices=verts, height=a1 - a0, axis=ax, material=med)

    def _map_poly(self, poly, axes):
        """map a shapely polygon (physical) lying inside a single zone in the two
        given axes to computational coords (affine per axis)."""
        A, B = self.mesh.ax[axes[0]], self.mesh.ax[axes[1]]
        xs, ys = poly.exterior.coords.xy
        xc = A.to_comp(np.array(xs)); yc = B.to_comp(np.array(ys))
        return Polygon(list(zip(xc, yc)))

    def polyz(self, p: PolyZ):
        M = self.mesh
        d = M.dcomp
        out = []
        if p.mat.pec:
            # assumes the polygon lies within one x- and one y-zone (true for the antenna)
            for q in _polys(p.poly):
                qc = self._map_poly(q, (0, 1)).buffer(0.02 * d, join_style=2)
                z0c, z1c = M.ax[2].to_comp(p.z0), M.ax[2].to_comp(p.z1)
                if abs(z1c - z0c) < 1e-9:
                    z0c, z1c = z0c - 0.49 * d, z0c + 0.49 * d
                else:
                    z0c, z1c = z0c - 0.02 * d, z1c + 0.02 * d
                for qq in _polys(qc):
                    out.append(self._prism(qq, 2, z0c, z1c, self.mp.metal))
            self.stats["pec"] += len(out)
            return out
        minx, miny, maxx, maxy = p.poly.bounds
        for i in M.ax[0].overlapping(minx, maxx):
            for j in M.ax[1].overlapping(miny, maxy):
                zr = sbox(M.ax[0].segs[i][0], M.ax[1].segs[j][0], M.ax[0].segs[i][1], M.ax[1].segs[j][1])
                inter = p.poly.intersection(zr)
                for q in _polys(inter):
                    qc = self._map_poly(q, (0, 1))
                    for kk in M.ax[2].overlapping(p.z0, p.z1):
                        z0 = max(p.z0, M.ax[2].segs[kk][0]); z1 = min(p.z1, M.ax[2].segs[kk][1])
                        med = self.medium(p.mat, M.zone_s((i, j, kk)))
                        out.append(self._prism(qc, 2, M.ax[2].to_comp(z0), M.ax[2].to_comp(z1), med))
        self.stats["dielectric"] += len(out)
        return out

    def ellcylx(self, e: EllCylX):
        t = np.linspace(0, 2 * math.pi, e.nseg, endpoint=False)
        ell = Polygon(list(zip(e.yc + e.a * np.cos(t), e.zc + e.b * np.sin(t))))
        return self.polyx(PolyX(ell, e.x0, e.x1, e.mat, e.tag))

    def polyx(self, e: PolyX):
        M = self.mesh
        ell = e.poly
        miny, minz, maxy, maxz = ell.bounds
        out = []
        for j in M.ax[1].overlapping(miny, maxy):
            for kk in M.ax[2].overlapping(minz, maxz):
                zr = sbox(M.ax[1].segs[j][0], M.ax[2].segs[kk][0], M.ax[1].segs[j][1], M.ax[2].segs[kk][1])
                inter = ell.intersection(zr)
                for q in _polys(inter):
                    qc = self._map_poly(q, (1, 2))
                    for i in M.ax[0].overlapping(e.x0, e.x1):
                        x0 = max(e.x0, M.ax[0].segs[i][0]); x1 = min(e.x1, M.ax[0].segs[i][1])
                        med = self.medium(e.mat, M.zone_s((i, j, kk)))
                        out.append(self._prism(qc, 0, M.ax[0].to_comp(x0), M.ax[0].to_comp(x1), med))
        self.stats["dielectric"] += len(out)
        return out

    def build(self, prims, background=AIR):
        objs = self.background(background)
        diel = [p for p in prims if not p.mat.pec]
        pec = [p for p in prims if p.mat.pec]
        for p in diel + pec:
            if isinstance(p, Box):
                objs += self.box(p)
            elif isinstance(p, PolyZ):
                objs += self.polyz(p)
            elif isinstance(p, EllCylX):
                objs += self.ellcylx(p)
            elif isinstance(p, PolyX):
                objs += self.polyx(p)
            elif isinstance(p, IfacePlane):
                objs += self.interface_plane(p.poly, p.z, p.mat_lo, p.mat_hi, p.tag)
            else:
                raise TypeError(p)
        return objs
