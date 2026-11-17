"""MEEP driver for a lumped (delta-gap) port on a PEC-sheet feed, on the TO
non-uniform grid of tomesh.py.  Units: 1 MEEP length = 1 mm, c = 1.

Port model (all positions are exact Yee-lattice points, see check_port()):
  * the gap is ONE computational cell along y, between the ground edge and the
    feed strip end, both PEC sheets in the plane z = zp;
  * excitation: Ey current line source across the gap (Norton source) in
    parallel with a lumped resistor R_src (default 50 ohm) made of a
    conductive one-cell block -> the antenna rings down in a few ns;
  * V  = (mean of Ey over the interior strip points in the gap) * d;
  * I  = discrete Ampere loop around the feed strip on the plane
         y = y_loop (half-integer, a few cells inside the feed strip), ONE
         CELL WIDER than the strip on every side: Hx on z = zp +- 3d/2
         (x = xa-d..xb+d) and Hz on x = xa - 3d/2, xb + 3d/2 (z = zp-d..zp+d).
         validation/diag_loop.py shows the tight loop (Hx at zp +- d/2) misses
         ~30 % of the strip current on a Yee PEC sheet, while loops grown by
         1 and 2 cells agree within 0.5 %.  This is the current INTO the
         antenna only (the resistor current stays inside the gap).
  * Z_ant = eta0 * V / I ;  P_acc = Re(V* I)  (MEEP flux convention, no 1/2).
Line integrals and surface fluxes are invariant under the TO map, so the
computational-grid values are the physical ones.
"""
import json, math, os, time
import numpy as np

C0 = 299792458.0
ETA0 = 376.730313668


def fm(f_hz):
    return f_hz * 1e-3 / C0


def _on_int(v, d, tol=1e-6):
    return abs(v / d - round(v / d)) < tol


def _on_half(v, d, tol=1e-6):
    return abs(v / d - 0.5 - round(v / d - 0.5)) < tol


def check_port(xa, xb, yg0, yg1, zp, yl, d):
    assert _on_int(xa, d) and _on_int(xb, d), ("strip edges must be integer lattice points", xa, xb)
    assert _on_int(yg0, d) and _on_int(yg1, d) and abs(yg1 - yg0 - d) < 1e-6, ("gap must be one cell", yg0, yg1)
    assert _on_int(zp, d), ("strip plane must be an integer lattice plane", zp)
    assert _on_half(yl, d), ("Ampere loop plane must be half-integer", yl)


def resistor_block(mp, mesh, port_c, R_ohm, s_zone):
    """One-cell conductive block in the gap: G' = n * sigma_eff' * d (MEEP units)."""
    from tomesh import to_factors
    xa, xb, yg0, yg1, zp, d = port_c
    n = int(round((xb - xa) / d)) + 1
    Rp = R_ohm / ETA0
    sig_eff = 1.0 / (Rp * n * d)
    f = to_factors(s_zone)
    sig_d = sig_eff / f[1]           # J = sigma_D * D = sigma_D * eps'_yy * E
    med = mp.Medium(epsilon_diag=mp.Vector3(*f), mu_diag=mp.Vector3(*f),
                    D_conductivity_diag=mp.Vector3(sig_d, sig_d, sig_d))
    ygc = 0.5 * (yg0 + yg1)
    return mp.Block(center=mp.Vector3(0.5 * (xa + xb), ygc, zp),
                    size=mp.Vector3(xb - xa + 0.5 * d, 0.5 * d, 0.5 * d), material=med)


def run_port_sim(mp, mesh, geometry, port, out_npz, *, f_lo=2.0e9, f_hi=2.9e9, nf_port=181,
                 f_src=2.45e9, fwidth_hz=3.0e9, R_src=50.0, flux_freqs_hz=None, ff_freqs_hz=None,
                 flux_box=None, flux_regions=None, flux_parts_diag=False, pml_cells=16, decay_by=1e-5, tmax_ns=15.0, extra_meta=None,
                 monitor_pt=None, eps_averaging=False, log=print):
    """port: dict(x0, x1, y_gap0, y_gap1, z, y_loop) in physical mm."""
    t_start = time.time()
    d = mesh.dcomp
    mx, my, mz = mesh.ax
    cell = mp.Vector3(*mesh.size_comp)
    courant = mesh.courant()
    xa, xb = float(mx.to_comp(port["x0"])), float(mx.to_comp(port["x1"]))
    yg0, yg1 = float(my.to_comp(port["y_gap0"])), float(my.to_comp(port["y_gap1"]))
    zp = float(mz.to_comp(port["z"]))
    yl = float(my.to_comp(port["y_loop"]))
    check_port(xa, xb, yg0, yg1, zp, yl, d)
    ygc = 0.5 * (yg0 + yg1)
    xc = 0.5 * (xa + xb)
    # zone scale factors at the gap
    s_zone = tuple(float(a.s_at_comp(v)) for a, v in zip(mesh.ax, (xc, ygc, zp)))
    geo = list(geometry)
    if R_src:
        geo.append(resistor_block(mp, mesh, (xa, xb, yg0, yg1, zp, d), R_src, s_zone))
    src = [mp.Source(mp.GaussianSource(fm(f_src), fwidth=fm(fwidth_hz)), component=mp.Ey,
                     center=mp.Vector3(xc, ygc, zp), size=mp.Vector3(xb - xa, 0, 0))]
    sim = mp.Simulation(cell_size=cell, resolution=1.0 / d, geometry=geo, sources=src,
                        boundary_layers=[mp.PML(pml_cells * d)], eps_averaging=eps_averaging, Courant=courant,
                        force_complex_fields=False)
    freqs = np.linspace(fm(f_lo), fm(f_hi), nf_port)
    V3 = mp.Vector3
    mon = dict(
        Ey=sim.add_dft_fields([mp.Ey], freqs, center=V3(xc, ygc, zp), size=V3(xb - xa, 0, 0), yee_grid=True),
        Hx_top=sim.add_dft_fields([mp.Hx], freqs, center=V3(xc, yl, zp + 1.5 * d), size=V3(xb - xa + 2 * d, 0, 0), yee_grid=True),
        Hx_bot=sim.add_dft_fields([mp.Hx], freqs, center=V3(xc, yl, zp - 1.5 * d), size=V3(xb - xa + 2 * d, 0, 0), yee_grid=True),
        Hz_l=sim.add_dft_fields([mp.Hz], freqs, center=V3(xa - 1.5 * d, yl, zp), size=V3(0, 0, 2 * d), yee_grid=True),
        Hz_r=sim.add_dft_fields([mp.Hz], freqs, center=V3(xb + 1.5 * d, yl, zp), size=V3(0, 0, 2 * d), yee_grid=True),
    )
    flux = None; faces = []
    if flux_box is not None:
        lo = [float(a.to_comp(v)) for a, v in zip(mesh.ax, flux_box[0])]
        hi = [float(a.to_comp(v)) for a, v in zip(mesh.ax, flux_box[1])]
        assert not any(np.isnan(lo + hi)), "flux box outside the mesh"
        ctr = [(a + b) / 2 for a, b in zip(lo, hi)]; sz = [b - a for a, b in zip(lo, hi)]
        regs = []
        for ax in range(3):
            for side, wgt in ((0, -1), (1, +1)):
                c = list(ctr); s = list(sz)
                c[ax] = (lo, hi)[side][ax]; s[ax] = 0
                regs.append(mp.FluxRegion(center=V3(*c), size=V3(*s), weight=wgt))
        ffr = np.array([fm(f) for f in flux_freqs_hz])
        flux = sim.add_flux(ffr, *regs)
        if ff_freqs_hz is not None:
            fff = np.array([fm(f) for f in ff_freqs_hz])
            comps = [mp.Ex, mp.Ey, mp.Ez, mp.Hx, mp.Hy, mp.Hz]
            for ax in range(3):
                for side in (0, 1):
                    c = list(ctr); s = list(sz)
                    c[ax] = (lo, hi)[side][ax]; s[ax] = 0
                    faces.append((ax, side, sim.add_dft_fields(comps, fff, center=V3(*c), size=V3(*s),
                                                               yee_grid=False)))
    if flux_regions is not None:
        # gate 3a: explicit list of planar regions (lo, hi, axis, weight) in physical mm (mesh_v2b.flux_regions)
        regs = []
        for (rlo, rhi, ax, wgt) in flux_regions:
            lo = [float(a.to_comp(v)) for a, v in zip(mesh.ax, rlo)]
            hi = [float(a.to_comp(v)) for a, v in zip(mesh.ax, rhi)]
            assert not any(np.isnan(lo + hi)), ("flux region outside the mesh", rlo, rhi)
            c = [(a + b) / 2 for a, b in zip(lo, hi)]; sz = [b - a for a, b in zip(lo, hi)]
            sz[ax] = 0
            regs.append(mp.FluxRegion(center=V3(*c), size=V3(*sz), weight=wgt))
        ffr = np.array([fm(f) for f in flux_freqs_hz])
        flux = sim.add_flux(ffr, *regs)
        flux_parts = [sim.add_flux(ffr, r) for r in regs] if flux_parts_diag else []
    else:
        flux_parts = []
    sim.init_sim()
    t_init = time.time() - t_start
    log(f"cells {mesh.ncells/1e6:.2f} M  courant {courant:.3f}  dt {courant*d/C0*1e-3*1e12:.4f} ps  "
        f"init {t_init:.0f} s  s_gap {s_zone}")
    if monitor_pt is None:
        mpt = V3(xc, ygc, zp)
    else:
        mpt = V3(*[float(a.to_comp(v)) for a, v in zip(mesh.ax, monitor_pt)])
    tmax = tmax_ns * 1e-9 * C0 * 1e3
    decay = mp.stop_when_fields_decayed(fm(1e9) ** -1 * 0.5, mp.Ey, mpt, decay_by)   # check every 0.5 ns

    def stop(s):
        return decay(s) or s.meep_time() > tmax
    tick = [time.time()]

    stop_files = [os.path.join(os.path.dirname(os.path.abspath(out_npz)), "STOP_ALL"),
                  os.path.abspath(out_npz).replace(".npz", ".STOP")]

    def progress(s):
        for sf in stop_files:              # processes from other shells cannot be signalled: stop-file abort
            if os.path.exists(sf):
                log(f"stop file {sf} found: aborting at t = {s.meep_time()/C0/1e3*1e9:.2f} ns")
                raise SystemExit(3)
        if time.time() - tick[0] > 120:
            tick[0] = time.time()
            log(f"  t = {s.meep_time()/C0/1e3*1e9:.2f} ns  wall {time.time()-t_start:.0f} s")
    sim.run(mp.at_every(fm(1e9) ** -1 * 0.05, progress), until_after_sources=stop)
    t_run = time.time() - t_start
    out = dict(freqs_hz=np.array([f * C0 / 1e-3 for f in freqs]), t_run_s=t_run,
               t_sim_ns=sim.meep_time() / C0 / 1e3 * 1e9)
    nf = len(freqs)
    get = lambda o, c: np.array([np.atleast_1d(np.squeeze(sim.get_dft_array(o, c, i))) for i in range(nf)])
    out["Ey"] = get(mon["Ey"], mp.Ey)
    out["Hx_top"] = get(mon["Hx_top"], mp.Hx)
    out["Hx_bot"] = get(mon["Hx_bot"], mp.Hx)
    out["Hz_l"] = get(mon["Hz_l"], mp.Hz)
    out["Hz_r"] = get(mon["Hz_r"], mp.Hz)
    n = int(round((xb - xa) / d)) + 1
    assert out["Ey"].shape[1] == n and out["Hx_top"].shape[1] == n + 2 and out["Hz_l"].shape[1] == 3, \
        (out["Ey"].shape, out["Hx_top"].shape, out["Hz_l"].shape, n)
    out["port_comp"] = np.array([xa, xb, yg0, yg1, zp, yl, d])
    out["dt_meep"] = courant * d
    out["R_src"] = R_src
    if flux is not None:
        out["flux_freqs_hz"] = np.array(flux_freqs_hz)
        out["P_flux"] = np.array(mp.get_fluxes(flux))
        if flux_box is not None:
            out["flux_box"] = np.array(flux_box)
        if flux_parts:
            out["P_flux_parts"] = np.array([mp.get_fluxes(fp) for fp in flux_parts])
    for (ax, side, obj) in faces:
        key = f"face{ax}{side}"
        md = sim.get_array_metadata(dft_cell=obj)
        out[key + "_x"], out[key + "_y"], out[key + "_z"], out[key + "_w"] = [np.array(a) for a in md]
        for cname, comp in zip(["Ex", "Ey", "Ez", "Hx", "Hy", "Hz"], [mp.Ex, mp.Ey, mp.Ez, mp.Hx, mp.Hy, mp.Hz]):
            out[key + "_" + cname] = np.array([sim.get_dft_array(obj, comp, k) for k in range(len(ff_freqs_hz))])
        out["ff_freqs_hz"] = np.array(ff_freqs_hz)
    np.savez_compressed(out_npz, **out)
    if extra_meta is not None:
        extra_meta = dict(extra_meta, eps_averaging=eps_averaging, t_run_s=t_run, t_sim_ns=out["t_sim_ns"], t_init_s=t_init)
        with open(out_npz.replace(".npz", "_meta.json"), "w") as fh:
            json.dump(extra_meta, fh, indent=1, default=str)
    log(f"done: wall {t_run:.0f} s, simulated {out['t_sim_ns']:.2f} ns")
    return out
