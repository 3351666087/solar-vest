"""2-D electrostatics (finite differences, node potentials, cell permittivities) for cross-sections of the lid edge.
Returns Maxwell capacitances per unit length between Dirichlet conductors. Units: mm for geometry, F/m for results."""
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spl

EPS0 = 8.854e-12


class Grid:
    def __init__(self, x0, x1, z0, z1, h):
        self.h = h
        self.x = np.arange(x0, x1 + h / 2, h); self.z = np.arange(z0, z1 + h / 2, h)
        self.nx, self.nz = len(self.x), len(self.z)
        self.eps = np.ones((self.nx - 1, self.nz - 1))          # per cell
        self.cond = np.zeros((self.nx, self.nz), int)            # 0 = free node, k > 0 = conductor k

    def box_eps(self, xa, xb, za, zb, er):
        xc = (self.x[:-1] + self.x[1:]) / 2; zc = (self.z[:-1] + self.z[1:]) / 2
        self.eps[np.ix_((xc > xa) & (xc < xb), (zc > za) & (zc < zb))] = er

    def box_cond(self, xa, xb, za, zb, k):
        e = self.h * 1e-6
        self.cond[np.ix_((self.x >= xa - e) & (self.x <= xb + e), (self.z >= za - e) & (self.z <= zb + e))] = k

    def mask_cond(self, fn, k):
        X, Z = np.meshgrid(self.x, self.z, indexing="ij")
        self.cond[fn(X, Z)] = k

    def operator(self):
        nx, nz = self.nx, self.nz
        idx = np.arange(nx * nz).reshape(nx, nz)
        ep = np.pad(self.eps, 1, mode="edge")                     # padded cells: ep[i+1, j+1] = eps[i, j]
        # edge permittivities: horizontal edge between (i,j)-(i+1,j) borders cells (i,j-1) and (i,j)
        ex = 0.5 * (ep[1:-1, 0:-1] + ep[1:-1, 1:])                # shape (nx-1, nz)
        ez = 0.5 * (ep[0:-1, 1:-1] + ep[1:, 1:-1])                # shape (nx, nz-1)
        # boundary edges carry half a cell
        ex[:, 0] *= 0.5; ex[:, -1] *= 0.5; ez[0, :] *= 0.5; ez[-1, :] *= 0.5
        rows, cols, vals = [], [], []
        a, b = idx[:-1, :].ravel(), idx[1:, :].ravel(); w = ex.ravel()
        rows += [a, b, a, b]; cols += [b, a, a, b]; vals += [-w, -w, w, w]
        a, b = idx[:, :-1].ravel(), idx[:, 1:].ravel(); w = ez.ravel()
        rows += [a, b, a, b]; cols += [b, a, a, b]; vals += [-w, -w, w, w]
        return sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(nx * nz, nx * nz))

    def solve(self, volts):
        """volts: {k: V}. Returns phi and {k: charge per unit length in F/m x V} (charge on each conductor)."""
        L = self.operator()
        c = self.cond.ravel(); free = c == 0
        phi = np.zeros(c.size)
        for k, v in volts.items(): phi[c == k] = v
        A = L[free][:, free]; rhs = -L[free][:, ~free] @ phi[~free]
        phi[free] = spl.spsolve(A.tocsc(), rhs)
        q = L @ phi
        Q = {k: float(q[c == k].sum()) * EPS0 for k in volts}
        return phi.reshape(self.nx, self.nz), Q
