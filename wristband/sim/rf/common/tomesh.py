"""Non-uniform FDTD mesh for MEEP by transformation optics (TO).

MEEP only has uniform Cartesian grids.  A separable, piecewise-linear coordinate
map x' = X(x), y' = Y(y), z' = Z(z) turns a non-uniform *physical* grid into the
uniform *computational* grid MEEP runs on.  Maxwell's equations keep their form
if the materials are replaced by (Ward & Pendry 1996; Pendry, Schurig & Smith 2006)

    eps'_ii = eps * s_i / (s_j s_k),   mu'_ii = mu * s_i / (s_j s_k)

with s_i = dx'_i/dx_i (computational cell / physical cell).  Conductivity enters
MEEP as D_conductivity = sigma/eps, which is invariant.  PEC stays PEC.  Line
integrals (E.dl, H.dl) and power flux through a surface are invariant, so port
voltages, currents and flux boxes measured on the computational grid are the
physical values.  Field values convert as E_i = s_i E'_i, H_i = s_i H'_i, and
physical coordinates follow from the inverse map.

Stability: with Courant number S (MEEP: dt = S * dx'), the scheme is stable if
S * sqrt(sx^2 + sy^2 + sz^2) <= 1 everywhere (same limit as a physical
non-uniform Yee grid, i.e. set by the smallest physical cell).

Units: 1 MEEP length unit = 1 mm (physical and computational).
"""
import math
import numpy as np


class AxisMap:
    """Piecewise-uniform physical grid on one axis.

    segs: list of (x_start, x_end, h_phys).  Segments must be contiguous and
    (x_end - x_start)/h_phys must be an integer.  dcomp: computational cell.
    The computational axis is centred on 0 (MEEP cell centred at the origin).
    """

    def __init__(self, segs, dcomp):
        self.dcomp = dcomp
        self.segs = []
        n_tot = 0
        for (a, b, h) in segs:
            n = (b - a) / h
            if abs(n - round(n)) > 1e-6:
                raise ValueError(f"segment {a}..{b} not a multiple of h={h}")
            self.segs.append((a, b, h, int(round(n))))
            n_tot += int(round(n))
        for (s1, s2) in zip(self.segs[:-1], self.segs[1:]):
            if abs(s1[1] - s2[0]) > 1e-9:
                raise ValueError("segments not contiguous")
        self.n = n_tot
        if self.n % 2:
            raise ValueError("total number of cells must be even (origin on a grid point)")
        self.L = self.n * dcomp
        # breakpoints
        xp = [self.segs[0][0]]
        xc = [-self.L / 2]
        for (a, b, h, n) in self.segs:
            xp.append(b)
            xc.append(xc[-1] + n * dcomp)
        self.xp = np.array(xp)
        self.xc = np.array(xc)
        self.s = np.array([dcomp / h for (_, _, h, _) in self.segs])

    # --- maps ------------------------------------------------------------
    def to_comp(self, x):
        return np.interp(x, self.xp, self.xc, left=np.nan, right=np.nan)

    def to_phys(self, xc):
        return np.interp(xc, self.xc, self.xp, left=np.nan, right=np.nan)

    def seg_index_phys(self, x):
        i = np.searchsorted(self.xp, x, side="right") - 1
        return np.clip(i, 0, len(self.segs) - 1)

    def seg_index_comp(self, xc):
        i = np.searchsorted(self.xc, xc, side="right") - 1
        return np.clip(i, 0, len(self.segs) - 1)

    def s_at_comp(self, xc):
        return self.s[self.seg_index_comp(xc)]

    def h_at_phys(self, x):
        return np.array([self.segs[i][2] for i in np.atleast_1d(self.seg_index_phys(x))])

    def overlapping(self, a, b):
        """indices of segments overlapping the physical interval (a, b)"""
        out = []
        for i, (sa, sb, h, n) in enumerate(self.segs):
            if min(b, sb) - max(a, sa) > 1e-12:
                out.append(i)
        return out

    def phys_grid(self):
        """physical coordinates of all integer grid points"""
        return self.to_phys(-self.L / 2 + self.dcomp * np.arange(self.n + 1))

    def is_on_grid(self, x, tol=1e-6):
        g = self.phys_grid()
        return np.min(np.abs(g - x)) < tol

    def describe(self):
        return [dict(x0=a, x1=b, h=h, n=n, s=self.dcomp / h) for (a, b, h, n) in self.segs]


class Mesh3:
    def __init__(self, mx, my, mz):
        assert abs(mx.dcomp - my.dcomp) < 1e-12 and abs(mx.dcomp - mz.dcomp) < 1e-12
        self.ax = (mx, my, mz)
        self.dcomp = mx.dcomp

    @property
    def ncells(self):
        return self.ax[0].n * self.ax[1].n * self.ax[2].n

    @property
    def size_comp(self):
        return tuple(a.L for a in self.ax)

    def smax(self):
        return math.sqrt(sum(float(np.max(a.s)) ** 2 for a in self.ax))

    def courant(self, margin=0.95):
        return min(0.5, margin / self.smax())

    def to_comp(self, p):
        return tuple(float(a.to_comp(v)) for a, v in zip(self.ax, p))

    def zones(self):
        """iterate over (ix, iy, iz) zone triples"""
        for i in range(len(self.ax[0].segs)):
            for j in range(len(self.ax[1].segs)):
                for k in range(len(self.ax[2].segs)):
                    yield (i, j, k)

    def zone_box_phys(self, ijk):
        return [(self.ax[d].segs[ijk[d]][0], self.ax[d].segs[ijk[d]][1]) for d in range(3)]

    def zone_s(self, ijk):
        return tuple(self.ax[d].s[ijk[d]] for d in range(3))


def to_factors(s):
    sx, sy, sz = s
    return (sx / (sy * sz), sy / (sx * sz), sz / (sx * sy))
