"""SIM-13 sub-model: effective thermal resistance of perfused wrist tissue under the band's contact strip.

2-D (Y-Z) steady Pennes bioheat equation  k lap(T) + w rho c (T_a - T) = 0  on y in [-40, 40] mm, depth 0..30 mm:
  contact strip |y| < 6.5 mm (SIM-13 contact width, 35 mm wrist radius, 1.2 mm indentation): uniform heat flux q
  exposed skin |y| > 6.5 mm: Robin h_env to T_env, chosen so that undisturbed skin is 34 C
  depth 30 mm: T = T_a.  k 0.37 W/mK (skin/fat average), rho c 4.0e6 J/m3K, T_a 36 C (wrist arterial, E).
By superposition T_strip = 34 C + q * R_eff, so the band model can use T_skin = 34 C and R_c + R_eff.
A 2-D strip (infinitely long along X) spreads less than the real 40 mm-long patch: R_eff is conservative.
"""
import json, math, os
import numpy as np
import scipy.sparse as sp
import scipy.sparse.linalg as spla

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")


def r_eff(omega, half=6.5e-3, k=0.37, rhoc=4.0e6, Ta=36.0, h_env=20.0, Ts0=34.0, q=500.0, ny=321, nz=121, Ly=40e-3, Lz=30e-3):
    m = math.sqrt(omega * rhoc / k)
    # undisturbed 1-D: surface flux out = k m (Ta - Ts0) coth-ish; choose T_env so that Ts0 holds far from the band
    q0 = k * m * (Ta - Ts0) / math.tanh(m * Lz) if m * Lz < 50 else k * m * (Ta - Ts0)
    T_env = Ts0 - q0 / h_env
    y = np.linspace(-Ly, Ly, ny); z = np.linspace(0, Lz, nz)
    dy, dz = y[1] - y[0], z[1] - z[0]
    N = ny * nz
    idx = lambda i, j: i * nz + j    # noqa: E731
    rows, cols, vals = [], [], []
    b = np.zeros(N)
    for i in range(ny):
        for j in range(nz):
            p = idx(i, j)
            if j == nz - 1:
                rows.append(p); cols.append(p); vals.append(1.0); b[p] = Ta; continue
            diag = omega * rhoc
            b[p] += omega * rhoc * Ta
            for (ii, jj, d) in ((i - 1, j, dy), (i + 1, j, dy), (i, j + 1, dz), (i, j - 1, dz)):
                if 0 <= ii < ny and 0 <= jj < nz:
                    w = k / (d * d)
                    if jj < 0:
                        continue
                    rows.append(p); cols.append(idx(ii, jj)); vals.append(-w); diag += w
            if j == 0:   # surface (half cell): flux BC -> ghost-free form, factor 2/dz
                if abs(y[i]) < half:
                    b[p] += 2 * q / dz
                else:
                    diag += 2 * h_env / dz
                    b[p] += 2 * h_env * T_env / dz
                # mirror the missing j-1 neighbour (symmetric ghost) by doubling the j+1 coupling
                w = k / (dz * dz)
                rows.append(p); cols.append(idx(i, 1)); vals.append(-w); diag += w
            if i in (0, ny - 1):   # far lateral edges: zero flux (mirror)
                w = k / (dy * dy)
                rows.append(p); cols.append(idx(1 if i == 0 else ny - 2, j)); vals.append(-w); diag += w
            rows.append(p); cols.append(p); vals.append(diag)
    A = sp.csr_matrix((vals, (rows, cols)), shape=(N, N))
    T = spla.spsolve(A, b).reshape(ny, nz)
    strip = np.abs(y) < half
    Ts_strip = T[strip, 0].mean()
    far = T[np.abs(y) > 30e-3, 0].mean()
    # reference: same model with q = 0 under the strip is not 34 C exactly (no evaporation there); use q -> 0 run
    return dict(omega=omega, m_per_m=m, R_1D=1 / (k * m), Ts_strip=Ts_strip, Ts_far=far, T_env=T_env, q=q), T, y, z


def main():
    res = {}
    for om in (1e-3, 3e-3, 6e-3):
        r1, _, _, _ = r_eff(om, q=500.0)
        r0, _, _, _ = r_eff(om, q=0.0)
        R = (r1["Ts_strip"] - r0["Ts_strip"]) / 500.0
        res[f"{om:g}"] = dict(R_eff_m2K_W=R, R_1D_m2K_W=r1["R_1D"], spreading_gain=r1["R_1D"] / R,
                              Ts_strip_q0=r0["Ts_strip"], Ts_far=r1["Ts_far"])
        print(f"omega={om:g}: R_eff={R:.5f} m2K/W  (1-D {r1['R_1D']:.5f}, gain {r1['R_1D']/R:.2f}), strip T at q=0 {r0['Ts_strip']:.2f} C")
    json.dump(res, open(os.path.join(OUT, "tissue2d.json"), "w"), indent=1)


if __name__ == "__main__":
    main()
