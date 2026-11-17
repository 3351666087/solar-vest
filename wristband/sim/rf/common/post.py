"""Post-processing: port impedance from the Yee samples, far field by the
surface-equivalence principle on the six faces of the flux box (physical
coordinates and fields recovered from the TO grid)."""
import math
import numpy as np

C0 = 299792458.0
ETA0 = 376.730313668


def port_Z(D):
    """D: dict-like from the npz written by fdtd.run_port_sim.
    Returns f, Z_ant (ohm), V', I_ant' (MEEP units), P_acc' = Re(V* I)."""
    xa, xb, yg0, yg1, zp, yl, d = D["port_comp"]
    f = D["freqs_hz"]
    ey = D["Ey"]
    n = ey.shape[1]
    V = (ey[:, 1:-1].mean(axis=1) if n > 2 else ey.mean(axis=1)) * d
    # loop normal +y, one cell wider than the strip: +z on the left, +x on top, -z on the right, -x on the bottom
    I = d * (D["Hz_l"].sum(axis=1) + D["Hx_top"].sum(axis=1) - D["Hz_r"].sum(axis=1) - D["Hx_bot"].sum(axis=1))
    # H lives half a time step after E on the Yee grid; MEEP's DFT time-stamps both at the
    # E step.  Re-referencing H (hence I) by exp(-i w dt/2) closes the vacuum energy balance
    # P_flux / P_acc to 0.98-1.02 over 8-13 GHz (validation/), vs 0.92-1.04 uncorrected.
    dt = float(D["dt_meep"]) if "dt_meep" in D else 0.5 * d
    I = I * np.exp(-1j * 2 * np.pi * f * 1e-3 / 299792458.0 * dt / 2)
    Z = ETA0 * V / I
    if np.median(Z.real) < 0:      # loop orientation vs. current direction into the antenna
        I = -I; Z = -Z
    P = np.real(np.conj(V) * I)
    # MEEP phasors use the physics convention exp(-i w t) (DFT kernel exp(+i w t)), in which
    # an inductor is Z = -i w L.  scikit-rf, the Murata S2P files and every circuit formula in
    # chain.py / rfnet.py use the engineering convention exp(+j w t) (inductor +j w L).
    # Return the engineering-convention impedance.  Evidence: the DC-shorted IFA must be
    # inductive below its first resonance; the raw MEEP value at 2.0 GHz is 10 - 118j.
    Z = np.conj(Z)
    return f, Z, V, I, P


def s11(Z, z0=50.0):
    return (Z - z0) / (Z + z0)


# ------------------------------------------------------------------ far field
def load_faces(D, mesh, fi):
    """Return list of (points (N,3) physical mm, J (N,3), M (N,3), dA (N,))."""
    out = []
    mx, my, mz = mesh.ax
    for ax in range(3):
        for side in (0, 1):
            k = f"face{ax}{side}"
            if k + "_x" not in D:
                continue
            xc, yc, zc, w = D[k + "_x"], D[k + "_y"], D[k + "_z"], D[k + "_w"]
            Xc, Yc, Zc = np.meshgrid(np.atleast_1d(xc), np.atleast_1d(yc), np.atleast_1d(zc), indexing="ij")
            W = np.asarray(w).reshape(Xc.shape)
            sx = mx.s_at_comp(Xc); sy = my.s_at_comp(Yc); sz = mz.s_at_comp(Zc)
            # at zone boundaries the interpolated field is ambiguous; use mean s of the two sides
            def s_mean(axis_map, c):
                lo = axis_map.s_at_comp(c - 1e-7); hi = axis_map.s_at_comp(c + 1e-7)
                return 0.5 * (lo + hi)
            sx = s_mean(mx, Xc); sy = s_mean(my, Yc); sz = s_mean(mz, Zc)
            P = np.stack([mx.to_phys(Xc), my.to_phys(Yc), mz.to_phys(Zc)], -1).reshape(-1, 3)
            S = np.stack([sx, sy, sz], -1).reshape(-1, 3)
            E = np.stack([np.asarray(D[k + "_E" + c][fi]).reshape(Xc.shape) for c in "xyz"], -1).reshape(-1, 3) * S
            H = np.stack([np.asarray(D[k + "_H" + c][fi]).reshape(Xc.shape) for c in "xyz"], -1).reshape(-1, 3) * S
            # physical area: comp weight / (s_t1 * s_t2)
            st = [S[:, i] for i in range(3) if i != ax]
            dA = W.reshape(-1) / (st[0] * st[1])
            n = np.zeros(3); n[ax] = 1.0 if side == 1 else -1.0
            J = np.cross(n, H)
            M = -np.cross(n, E)
            out.append((P, J, M, dA))
    return out


def far_field(faces, f_hz, ntheta=37, nphi=72, chunk=20000):
    """Radiation intensity U(theta, phi) in MEEP power units per steradian.
    e^{-i w t} convention (MEEP): radiation vectors use exp(-i k r.r')."""
    k = 2 * math.pi * f_hz * 1e-3 / C0           # rad/mm
    th = np.linspace(0, math.pi, ntheta); ph = np.linspace(0, 2 * math.pi, nphi, endpoint=False)
    TH, PH = np.meshgrid(th, ph, indexing="ij")
    rh = np.stack([np.sin(TH) * np.cos(PH), np.sin(TH) * np.sin(PH), np.cos(TH)], -1).reshape(-1, 3)
    thv = np.stack([np.cos(TH) * np.cos(PH), np.cos(TH) * np.sin(PH), -np.sin(TH)], -1).reshape(-1, 3)
    phv = np.stack([-np.sin(PH), np.cos(PH), np.zeros_like(PH)], -1).reshape(-1, 3)
    N = np.zeros((rh.shape[0], 3), complex); L = np.zeros((rh.shape[0], 3), complex)
    for (P, J, M, dA) in faces:
        for s in range(0, P.shape[0], chunk):
            ph_ = np.exp(-1j * k * (rh @ P[s:s + chunk].T))          # (ndir, n)
            N += ph_ @ (J[s:s + chunk] * dA[s:s + chunk, None])
            L += ph_ @ (M[s:s + chunk] * dA[s:s + chunk, None])
    Nt = np.sum(N * thv, 1); Np = np.sum(N * phv, 1)
    Lt = np.sum(L * thv, 1); Lp = np.sum(L * phv, 1)
    eta = 1.0   # MEEP units
    U = k ** 2 / (32 * math.pi ** 2 * eta) * (np.abs(Lp + eta * Nt) ** 2 + np.abs(Lt - eta * Np) ** 2)
    U = U.reshape(TH.shape)
    Uth = (k ** 2 / (32 * math.pi ** 2)) * np.abs(Lp + Nt) ** 2
    Uph = (k ** 2 / (32 * math.pi ** 2)) * np.abs(Lt - Np) ** 2
    dth = th[1] - th[0]; dph = ph[1] - ph[0]
    w = np.sin(TH) * dth * dph
    w[0, :] *= 0.5; w[-1, :] *= 0.5
    Prad = float(np.sum(U * w))
    return dict(theta=th, phi=ph, U=U, Uth=Uth.reshape(TH.shape), Uph=Uph.reshape(TH.shape), Prad=Prad)
