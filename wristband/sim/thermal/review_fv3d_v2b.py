#!/usr/bin/env python3
"""Adversarial re-check of the V2-B heat claims: compact 3-D finite-volume steady conduction model.
Independent re-implementation (does NOT import sim13_fv3d.py); it reuses only the material / boundary data of
sim/thermal-mech/materials.py (read-only) and the SIM-13 tissue sub-model results (R_eff, occluded-patch T).
Step 1 validates the method on a simplified v1 stack against SIM-13 (sim/thermal-mech/out/sim13_results.md).
Step 2 runs the V2-B one-layer stack of redesign/REDESIGN_V2.md section 5.2 / 5.3.
Run: python3 -B fv3d_v2b.py   -> fv3d_v2b.json
Grid 0.5 mm in plan, <= 0.25 mm in Z. Units mm in geometry, SI in the solve."""
import sys, os, json, math, time
sys.dont_write_bytecode = True
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, '/path/to/SolarVest_work/wristband/sim/thermal-mech')
from materials import MAT, SOLAR, ENV, h_rad   # noqa

K = {m: (v[0], v[1]) for m, v in MAT.items()}
K.update({
 'ti':      (17.0, 17.0),     # Ti Gr2 16-22 W/mK handbook [E]
 'encap':   (0.25, 0.25),     # EVA / TPU / POE encapsulant 0.2-0.35 W/mK [E]
 'si':      (148.0, 148.0),   # silicon
 'flex':    (10.0, 0.25),     # 0.12 mm 2-layer FPC, ~30 % copper in plane [E]
 'parts':   (0.6, 0.45),      # 1.0 mm layer: ~50 % SMD bodies (1.0) + 50 % air [E] (v2b density 0.61)
 'air_cav': (0.036, 0.036),   # 0.75-1.75 mm cavity: 0.027 + radiation 6 W/m2K x ~1.5 mm [E]
 'steel':   (16.3, 16.3),
 'void':    (0.0, 0.0),
})
MATS = list(K); MID = {m: i for i, m in enumerate(MATS)}

def axis(breaks, dmax):
    b = sorted(set(round(x, 4) for x in breaks)); e = [b[0]]
    for a, c in zip(b[:-1], b[1:]):
        n = max(1, int(math.ceil((c - a) / dmax - 1e-9))); e += list(np.linspace(a, c, n + 1)[1:])
    return np.array(e)

class Model:
    def __init__(self, LX, LY, zbreaks, dxy=0.5, dz=0.25):
        self.xe = axis([0, LX], dxy); self.ye = axis([0, LY], dxy); self.ze = axis(zbreaks, dz)
        self.dx = np.diff(self.xe); self.dy = np.diff(self.ye); self.dzv = np.diff(self.ze)
        self.xc = 0.5 * (self.xe[1:] + self.xe[:-1]); self.yc = 0.5 * (self.ye[1:] + self.ye[:-1]); self.zc = 0.5 * (self.ze[1:] + self.ze[:-1])
        self.shape = (len(self.dx), len(self.dy), len(self.dzv))
        self.mat = np.full(self.shape, MID['void'], dtype=np.int16); self.q = np.zeros(self.shape)
    def box(self, m, x0, x1, y0, y1, z0, z1):
        ix = (self.xc > x0) & (self.xc < x1); iy = (self.yc > y0) & (self.yc < y1); iz = (self.zc > z0) & (self.zc < z1)
        self.mat[np.ix_(ix, iy, iz)] = MID[m]
        return np.ix_(ix, iy, iz)
    def heat(self, W, sel):
        vol = (self.dx[:, None, None] * self.dy[None, :, None] * self.dzv[None, None, :] * np.ones(self.shape))[sel]
        self.q[sel] += W * vol / vol.sum()
    def solve(self, bc):
        """bc: dict(T_amb, h_top, h_side, T_skin, R_c, R_tis, indent, z_ref_contact, yc, radius)
        boundary faces = any face between a solid cell and void / outside."""
        nx, ny, nz = self.shape; N = nx * ny * nz
        idx = np.arange(N).reshape(self.shape)
        kxy = np.array([K[m][0] for m in MATS])[self.mat]; kz = np.array([K[m][1] for m in MATS])[self.mat]
        solid = self.mat != MID['void']
        DX = self.dx[:, None, None] * np.ones(self.shape); DY = self.dy[None, :, None] * np.ones(self.shape); DZ = self.dzv[None, None, :] * np.ones(self.shape)
        rows, cols, vals = [], [], []; diag = np.zeros(N); rhs = (self.q).ravel().copy()
        self.bflux = []   # (label, cell index array, g array, Tref)
        def interior(ax, k, D, A):
            sl_a = [slice(None)] * 3; sl_b = [slice(None)] * 3; sl_a[ax] = slice(0, -1); sl_b[ax] = slice(1, None)
            a, b = tuple(sl_a), tuple(sl_b)
            both = solid[a] & solid[b]
            with np.errstate(divide='ignore', invalid='ignore'):
                g = np.where(both, A[a] * 1e-6 / ((D[a] / (2 * k[a]) + D[b] / (2 * k[b])) * 1e-3), 0.0)
            i = idx[a][both]; j = idx[b][both]; gg = g[both]
            rows.extend([i, j]); cols.extend([j, i]); vals.extend([-gg, -gg])
            np.add.at(diag, i, gg); np.add.at(diag, j, gg)
        interior(0, kxy, DX, DY * DZ); interior(1, kxy, DY, DX * DZ); interior(2, kz, DZ, DX * DY)
        # boundary faces
        Y3 = self.yc[None, :, None] * np.ones(self.shape)
        def bface(ax, side, k, D, A, kind):
            # side = -1: face on the low side of the cell; +1: high side
            sh = np.roll(solid, -side, axis=ax)
            edge = [slice(None)] * 3; edge[ax] = 0 if side < 0 else -1
            sh[tuple(edge)] = False
            face = solid & ~sh
            if not face.any(): return
            Rcell = D / (2 * np.where(k > 0, k, 1)) * 1e-3
            if kind == 'top': h = np.full(self.shape, bc['h_top']); Tr = bc['T_amb']
            elif kind == 'side':
                zf = self.zc[None, None, :] * np.ones(self.shape)
                # faces below the floor plane (cap side walls) see skin; above: ambient
                h = np.where(zf < 0, 1.0 / (2 * bc['R_c'] + bc['R_tis']), bc['h_side']); Tr = None
                g = np.where(face, A * 1e-6 / (Rcell + 1.0 / h), 0.0)
                for sel, T in ((face & (zf < 0), bc['T_skin']), (face & (zf >= 0), bc['T_amb'])):
                    i = idx[sel]; np.add.at(diag, i, g[sel]); np.add.at(rhs, i, g[sel] * T); self.bflux.append(('skin' if T == bc['T_skin'] else 'side', i, g[sel], T, None))
                return
            else:  # bottom: skin contact or air gap + radiation to skin
                zface = (self.ze[:-1])[None, None, :] * np.ones(self.shape)
                dyy = np.minimum(np.abs(Y3 - bc['yc']), bc['radius'] - 1e-6); sag = bc['radius'] - np.sqrt(bc['radius'] ** 2 - dyy ** 2)
                gap = np.maximum(0.0, zface - bc['z_low'] - bc['indent'] + sag)     # mm; z_low = lowest face (cap / mesa)
                hr = h_rad(SOLAR['eps_shell'], 37.0, SOLAR['eps_skin'])
                with np.errstate(divide='ignore'):
                    hgap = 0.027 / np.maximum(gap, 1e-9) * 1e3 + hr
                h = np.where(gap <= 1e-6, 1.0 / (bc['R_c'] + bc['R_tis']), 1.0 / (1.0 / hgap + bc['R_tis'])); Tr = bc['T_skin']
                self.contact = face & (gap <= 1e-6); self.botface = face
            g = np.where(face, A * 1e-6 / (Rcell + 1.0 / h), 0.0)
            i = idx[face]; np.add.at(diag, i, g[face]); np.add.at(rhs, i, g[face] * Tr)
            self.bflux.append((kind, i, g[face], Tr, (Rcell[face], A[face])))
        bface(2, +1, kz, DZ, DX * DY, 'top'); bface(2, -1, kz, DZ, DX * DY, 'bottom')
        for ax, k, D, A in ((0, kxy, DX, DY * DZ), (1, kxy, DY, DX * DZ)):
            bface(ax, -1, k, D, A, 'side'); bface(ax, +1, k, D, A, 'side')
        rows = np.concatenate(rows); cols = np.concatenate(cols); vals = np.concatenate(vals)
        s = solid.ravel(); diag[~s] = 1.0; rhs[~s] = bc['T_amb']
        A = sp.csr_matrix((np.concatenate([vals, diag]), (np.concatenate([rows, np.arange(N)]), np.concatenate([cols, np.arange(N)]))), shape=(N, N))
        try:
            sys.path.insert(0, '/path/to/SolarVest_work/wristband/envs/pylib'); import pyamg
            ml = pyamg.smoothed_aggregation_solver(A); T = ml.solve(rhs, tol=1e-10, accel='cg', maxiter=400)
        except Exception as e:
            T = spl.spsolve(A.tocsc(), rhs)
        self.T = T.reshape(self.shape); self.res = float(np.linalg.norm(A @ T - rhs) / np.linalg.norm(rhs))
        out = {}
        for kind, i, g, Tr, extra in self.bflux:
            out[kind] = out.get(kind, 0.0) + float((g * (T[i] - Tr)).sum())
        self.flux = out
        # skin-contact surface temperature (device face): T_face = T_cell - q * Rcell
        for kind, i, g, Tr, extra in self.bflux:
            if kind == 'bottom':
                Rcell, Aface = extra; qf = g * (T[i] - Tr) / (Aface * 1e-6); Tf = T[i] - qf * Rcell
                cm = self.contact.ravel()[i]
                self.skin = dict(contact_area_mm2=float(Aface[cm].sum()), skin_contact_max_C=float(Tf[cm].max()), skin_contact_mean_C=float((Tf[cm] * Aface[cm]).sum() / Aface[cm].sum()),
                                 noncontact_bottom_max_C=float(Tf[~cm].max()) if (~cm).any() else None,
                                 q_contact_W=float((g * (T[i] - Tr))[cm].sum()), q_noncontact_W=float((g * (T[i] - Tr))[~cm].sum()),
                                 q_contact_peak_Wm2=float(qf[cm].max()), q_contact_mean_Wm2=float((g * (T[i] - Tr))[cm].sum() / (Aface[cm].sum() * 1e-6)))
        return self
    def stat(self, m):
        sel = self.mat == MID[m]; return float(self.T[sel].max()), float(self.T[sel].mean())

HTOP = lambda f=1.0: ENV['h_top'] * f + h_rad(SOLAR['eps_lens'], 50.0)
HSIDE = lambda f=1.0: ENV['h_side'] * f + h_rad(SOLAR['eps_shell'], 42.0)
TAU = (1 - SOLAR['lens_R_front'])

def bc(T_amb=35.0, T_skin=34.0, R_c=ENV['R_contact'], R_tis=0.0, indent=1.2, z_low=-0.6, hf=1.0, yc=16.0):
    return dict(T_amb=T_amb, h_top=HTOP(hf), h_side=HSIDE(hf), T_skin=T_skin, R_c=R_c, R_tis=R_tis, indent=indent, z_low=z_low, yc=yc, radius=35.0)

# ------------------------------------------------------------------------------------------------ v1 (validation)
def v1(alpha_print=0.95, harvest=False, G=1000.0):
    # Z from the back-shell outer face (0) up; mesa 0.6 below. Nominal CAD stack (mech/README: 10.32 nominal)
    z = dict(shell=0.70, clr=0.10, parts=1.00, pcb=0.80, foam=0.15, batt=3.50, gap=0.56, pvb=0.60, jnt=0.05, cell=1.20, air=0.51, lens=0.55)
    zs = [-0.6, 0]; 
    for k in z: zs.append(zs[-1] + z[k])
    zb = dict(zip(['mesa0', 'z0'] + list(z), zs))
    m = Model(40, 32, zs)
    top = zs[-1]
    m.box('resin', 0, 40, 0, 32, 0, top)                                   # body filled with PC, then carved
    m.box('air', 1.2, 38.8, 1.2, 30.8, z['shell'], zb['air'])              # cavity up to the lens underside
    m.box('resin', 14.5, 25.5, 12.5, 19.5, -0.6, 0)                        # mesa 11 x 7
    z0 = z['shell'] + z['clr']
    m.box('parts', 1.5, 38.5, 1.5, 30.5, z0, z0 + z['parts']); z0 += z['parts']
    m.box('pcb', 1.5, 38.5, 1.5, 30.5, z0, z0 + z['pcb']); z0 += z['pcb']
    m.box('pe_tape', 4.5, 35.5, 14.5, 27.0, z0, z0 + z['foam']); z0 += z['foam']
    m.box('battery', 4.5, 35.5, 14.5, 27.0, z0, z0 + z['batt']); zbt = z0 + z['batt']
    zp = zbt + z['gap']
    m.box('pv_board', 2.7, 37.3, 6.5, 30.5, zp, zp + z['pvb']); zp += z['pvb']
    m.box('snbi_jnt', 3.2, 36.8, 7.0, 30.0, zp, zp + z['jnt']); zp += z['jnt']
    cells = m.box('pv_cell', 3.2, 36.8, 7.0, 30.0, zp, zp + z['cell']); zp += z['cell']
    m.box('steel316', 4.0, 12.0, 11.5, 20.5, 0, 0.6); m.box('steel316', 28.0, 36.0, 11.5, 20.5, 0, 0.6)   # E1, E2 8 x 9 in the shell
    lens = m.box('glass', 0.8, 39.2, 0.8, 31.2, top - z['lens'], top)
    a_lens = 1157.0; a_cells = 33.6 * 23.0; a_print = a_lens - a_cells; a_rim = 1249 - a_lens
    Gm = G * 1e-6
    q_bulk = Gm * a_lens * TAU * SOLAR['lens_abs']
    tr = TAU * (1 - SOLAR['lens_abs'])
    q_print = Gm * a_print * tr * alpha_print; q_cells = Gm * a_cells * tr * SOLAR['alpha_cell']; q_rim = Gm * a_rim * SOLAR['alpha_frame']
    if harvest: q_cells -= 0.109
    m.heat(q_bulk, lens); m.heat(q_cells, cells)
    pr = m.box('glass', 0.8, 39.2, 0.8, 31.2, top - z['lens'], top - z['lens'] + 0.14)       # print on the lens underside (bottom lens cells)
    m.heat(q_print, pr); m.heat(q_rim, m.box('resin', 0, 40, 0, 32, top - 0.3, top) if False else pr)
    m.absorbed = q_bulk + q_print + q_cells + q_rim
    return m

# ------------------------------------------------------------------------------------------------ V2-B
def v2b(alpha_print=0.25, harvest=False, G=1000.0, cell_t=2.10, gap=0.30, lid=(0.12, 0.15, 0.165, 0.20, 0.50), wall=1.0,
        posts=True, shim='steel', floor_ti=True, ir_reject=0.0):
    """Z = 0 at the floor's skin face; the optical cap (11 x 7) stands 0.75 proud below it.
    Plan (case frame, mm): board strip Y 1.5..19.5 (37 x 18), cell 10 x 30 at Y 19.9..29.9, X 5..35."""
    fl, film, pcb, parts = 0.35, 0.10, 0.80, 1.00
    z_cell0 = fl + 0.15 + 0.10; z_cell1 = z_cell0 + cell_t; z_lid0 = z_cell1 + gap
    zl = [z_lid0]
    for t in lid: zl.append(zl[-1] + t)
    zs = [-0.75, 0, 0.25, fl, fl + film, fl + film + pcb, fl + film + pcb + parts, fl + 0.15, z_cell0, z_cell1] + zl
    m = Model(40, 32, zs)
    top = zl[-1]
    m.box('resin', 0, 40, 0, 32, 0, z_lid0)                                 # walls + floor web
    m.box('air_cav', wall, 40 - wall, wall, 32 - wall, fl, z_lid0)          # dry-side cavity
    m.box('resin', 14.5, 25.5, 11.5, 18.5, -0.75, 0)                        # optical cap 11 x 7, centre 1 mm off the case centre-line (REDESIGN 5.3)
    if floor_ti:                                                            # Ti plates 0.25 in the 0.35 web, left and right of the cap
        m.box('ti', 1.5, 14.0, 4.0, 22.5, 0, 0.25); m.box('ti', 26.0, 39.0, 2.0, 24.5, 0, 0.25)
    m.box('psa', 1.5, 38.5, 1.5, 19.5, fl, fl + film)                       # bond film under the whole board
    m.box('pcb', 1.5, 38.5, 1.5, 19.5, fl + film, fl + film + pcb)
    m.box('parts', 2.0, 38.0, 2.0, 19.0, fl + film + pcb, fl + film + pcb + parts)
    m.box(shim if shim else 'air_cav', 4.7, 35.3, 19.9, 29.9, fl, fl + 0.15)
    m.box('psa', 5, 35, 19.9, 29.9, fl + 0.15, z_cell0)
    m.box('battery', 5, 35, 19.9, 29.9, z_cell0, z_cell1)
    m.box('air', 5, 35, 19.9, 29.9, z_cell1, z_lid0)                        # swelling gap: thin air film (0.030)
    if posts:                                                               # two PC support posts board -> lid, 2 x 2 mm
        m.box('resin', 12, 14, 9, 11, fl + film + pcb, z_lid0); m.box('resin', 26, 28, 9, 11, fl + film + pcb, z_lid0)
    # lid: FPC backsheet / encapsulant / silicon strips / encapsulant / glass (whole 40 x 32)
    m.box('flex', 0, 40, 0, 32, zl[0], zl[1]); m.box('encap', 0, 40, 0, 32, zl[1], zl[4]); m.box('glass', 0, 40, 0, 32, zl[4], zl[5])
    strips = []
    for i in range(4):
        y0 = 5.0 + i * 5.6
        strips.append(m.box('si', 3.7, 36.3, y0, y0 + 5.2, zl[2], zl[3]))
    a_lid = 1249.0; a_si = 4 * 32.6 * 5.2; a_print = a_lid - a_si; Gm = G * 1e-6
    q_bulk = Gm * a_lid * TAU * SOLAR['lens_abs']; tr = TAU * (1 - SOLAR['lens_abs'])
    q_si = Gm * a_si * tr * (SOLAR['alpha_cell'] - ir_reject); q_print = Gm * a_print * tr * alpha_print
    if harvest: q_si -= 0.105
    for s in strips: m.heat(q_si / 4, s)
    m.heat(q_print, m.box('flex', 0, 40, 0, 32, zl[0], zl[1])); 
    for s in strips: pass
    m.heat(q_bulk, m.box('glass', 0, 40, 0, 32, zl[4], zl[5]))
    m.absorbed = q_bulk + q_si + q_print; m.z_lid0 = z_lid0; m.top = top
    return m

def report(m, tag, b):
    m.solve(b)
    r = dict(tag=tag, grid=list(m.shape), absorbed_W=round(m.absorbed, 3), residual=m.res, flux={k: round(v, 4) for k, v in m.flux.items()})
    r.update({k: (round(v, 2) if v is not None else None) for k, v in m.skin.items()})
    for mat, nm in (('battery', 'battery'), ('pv_cell', 'pv'), ('si', 'pv'), ('glass', 'lens'), ('pcb', 'pcb')):
        if (m.mat == MID[mat]).any():
            mx, mn = m.stat(mat); r[nm + '_max_C'] = round(mx, 2); r[nm + '_mean_C'] = round(mn, 2)
    r['balance_err_W'] = round(m.absorbed - sum(m.flux.values()), 6)
    return r

TIS = {'w1e-3': (0.01533, 35.18), 'w3e-3': (0.01102, 35.47), 'w6e-3': (0.00856, 35.61)}   # SIM-13 tissue2d.json

if __name__ == '__main__':
    R = {}; t0 = time.time()
    def run(tag, m, b):
        R[tag] = report(m, tag, b); r = R[tag]
        print('%-44s abs %.3f | skin max %.2f mean %.2f (A %.0f mm2) | to skin %.3f W (contact %.3f) | cell max %s | pv max %s | lens max %s | pcb mean %s | t %.0fs' % (
            tag, r['absorbed_W'], r['skin_contact_max_C'], r['skin_contact_mean_C'], r['contact_area_mm2'], r['flux'].get('bottom', 0) + r['flux'].get('skin', 0), r['q_contact_W'],
            r.get('battery_max_C'), r.get('pv_max_C'), r.get('lens_max_C'), r.get('pcb_mean_C'), time.time() - t0), flush=True)
    # ---- validation on v1 against SIM-13
    run('v1 WC black, task BC [SIM-13: skin 36.27, batt 49.06, pv 61.42, skin W 0.310]', v1(), bc())
    run('v1 WS black, task BC [SIM-13: 36.05, 47.42, 58.11, 0.282]', v1(harvest=True), bc())
    run('v1 WC white, task BC [SIM-13: 35.90, 46.74, 57.35, 0.257]', v1(alpha_print=0.25), bc())
    run('v1 WC black, tissue w3e-3 [SIM-13: 41.75, 51.45, 62.88, 0.254]', v1(), bc(T_skin=35.47, R_tis=0.01102))
    run('v1 WC white, tissue w3e-3 [SIM-13: 40.67, 48.86, 58.65, 0.209]', v1(alpha_print=0.25), bc(T_skin=35.47, R_tis=0.01102))
    run('v1 WC black, tissue w1e-3 [SIM-13: 42.54]', v1(), bc(T_skin=35.18, R_tis=0.01533))
    # ---- V2-B
    B = dict(z_low=-0.75, yc=15.0)
    run('V2-B WC white, task BC', v2b(), bc(**B))
    run('V2-B WC black, task BC', v2b(alpha_print=0.95), bc(**B))
    run('V2-B WS white, task BC', v2b(harvest=True), bc(**B))
    for w, (Rt, Ts) in TIS.items():
        run('V2-B WC white, tissue ' + w, v2b(), bc(T_skin=Ts, R_tis=Rt, **B))
    run('V2-B WC black, tissue w3e-3', v2b(alpha_print=0.95), bc(T_skin=35.47, R_tis=0.01102, **B))
    run('V2-B WS white, tissue w3e-3', v2b(harvest=True), bc(T_skin=35.47, R_tis=0.01102, **B))
    run('V2-B WC white, tissue w3e-3, max-material (cell 2.5, gap 0.2)', v2b(cell_t=2.5, gap=0.2), bc(T_skin=35.47, R_tis=0.01102, **B))
    run('V2-B WC white, tissue w3e-3, no posts', v2b(posts=False), bc(T_skin=35.47, R_tis=0.01102, **B))
    run('V2-B WC white, tissue w3e-3, convection x0.6', v2b(), bc(T_skin=35.47, R_tis=0.01102, hf=0.6, **B))
    run('V2-B WC white, tissue w3e-3, indent 0.8', v2b(), bc(T_skin=35.47, R_tis=0.01102, indent=0.8, **B))
    run('V2-B WC white, tissue w3e-3, IR-reject coating (-0.19 x 0.9 on Si)', v2b(ir_reject=0.17), bc(T_skin=35.47, R_tis=0.01102, **B))
    run('V2-B WC white, tissue w3e-3, 750 W/m2', v2b(G=750.0), bc(T_skin=35.47, R_tis=0.01102, **B))
    run('V2-B WC white, tissue w3e-3, 30 C air', v2b(), bc(T_amb=30.0, T_skin=35.47, R_tis=0.01102, **B))
    run('v1 WS black, tissue w3e-3 [SIM-13: 41.10, 49.67, 59.50, 0.230]', v1(harvest=True), bc(T_skin=35.47, R_tis=0.01102))
    run('V2-B WS white, tissue w1e-3', v2b(harvest=True), bc(T_skin=35.18, R_tis=0.01533, **B))
    run('V2-B WC white + IR-reject, tissue w1e-3', v2b(ir_reject=0.17), bc(T_skin=35.18, R_tis=0.01533, **B))
    run('V2-B WC white, tissue w3e-3, lid gap +0.5 mm (cell gap 0.8)', v2b(gap=0.8), bc(T_skin=35.47, R_tis=0.01102, **B))
    run('V2-B WC white, tissue w3e-3, print alpha 0.15', v2b(alpha_print=0.15), bc(T_skin=35.47, R_tis=0.01102, **B))
    run('V2-B WC white, tissue w3e-3, 25 C air', v2b(), bc(T_amb=25.0, T_skin=35.47, R_tis=0.01102, **B))
    run('V2-B WC white, tissue w3e-3, 500 W/m2', v2b(G=500.0), bc(T_skin=35.47, R_tis=0.01102, **B))
    run('V2-B WS white, task BC, 45 C-inhibit map point 30 C air', v2b(harvest=True), bc(T_amb=30.0, T_skin=33.5, **B))
    json.dump(R, open(os.path.join(HERE, 'fv3d_v2b.json'), 'w'), indent=1)
    print('wrote fv3d_v2b.json')
