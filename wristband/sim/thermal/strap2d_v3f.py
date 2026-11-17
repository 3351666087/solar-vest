#!/usr/bin/env python3
"""V3-G2 cases 2 and 3: 2-D steady section along the strap (s = arc length from the bar, z = height) for the c-Si wing on
root B and the cell capsule on root A, over perfused tissue (2-D Pennes, k 0.37, rho c 4e6, arterial 37 C at 30 mm depth,
as the BASELINE 12 1-D bound). The device's inner face lies on the strap's inner face along the straight free span; the air
gap to the skin g(s) is computed from the worn geometry of v3/cad/src/geom_v3f.py (POD_W 34, wrist_geo, ellipse_dist).
Gap conductance 0.026/(g + 0.05 mm) + 6 W/m2K radiation (BASELINE bound), contact R_c 0.0025 where g = 0.
Top: h_conv + h_rad to air, sun normal to every top face (worst orientation: free span facing the sun).
Run: python3 -B strap2d_v3f.py > logs/strap2d.log  -> out/strap2d.json"""
import sys, os, json, math, time
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
os.environ['V3F_POD_W'] = '34'; os.environ['V3F_POD_L'] = '41'; os.environ['V3F_NO_OUT'] = '1'
os.environ['V3F_OPT'] = 'fpc=dwg,fold=1.9,joint=zif,raise=0.15'
sys.path.insert(0, '/path/to/SolarVest_work/wristband/v3/cad/src')
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spl
import geom_v3f as G                                                                 # noqa: E402
sys.path.insert(0, HERE)
from materials import h_rad                                                          # noqa: E402

K = {'tis': (0.37, 0.37), 'tpu': (0.20, 0.20), 'encap': (0.25, 0.25), 'si': (148.0, 148.0), 'glass': (1.0, 1.0), 'pc': (0.20, 0.20),
     'air': (0.036, 0.036), 'cell': (25.0, 0.60), 'band': (0.10, 0.10)}
DS, DZ = 0.1, 0.05                       # mm
S0, S1 = -12.0, 40.0
TS = G.STRAP_T


def gap_fn(Cw):
    g = G.wrist_geo(Cw); P0, d, n = np.array(g['P0']), np.array(g['d']), np.array(g['n'])
    a, b = g['a'], g['b']
    ss = np.arange(-2.5, g['free'] + 0.01, 0.25)
    gp = [max(0.0, G.ellipse_dist(P0 + s * d - TS / 2 * n, a, b, n=6000)) for s in ss]
    def f(s):
        if s >= g['free']: return 0.0
        return float(np.interp(s, ss, gp))
    return f, g


def build(Cw, item='wing', active=(2.0, 13.7), outer_light=None, a_cell=0.90, a_bg=0.90, a_light=0.30, a_strap=0.60,
          a_top=0.15, wing_s1=13.7, t_top=0.40, cap_t=4.5):
    """columns of layers (material, thickness) bottom-up per s, sun absorbed (W/m2 of plan, per column, and the layer index)"""
    gap, geo = gap_fn(Cw)
    s = np.arange(S0 + DS / 2, S1, DS); cols = []
    W = G.WING; C = G.CAPSULE
    if item == 'wing':
        pitch = (active[1] - active[0] - 0.6) / 4; cells = [(active[0] + 0.3 + i * pitch + 0.15, active[0] + 0.3 + i * pitch + 0.15 + pitch - 0.075) for i in range(4)]
    for x in s:
        if x < -2.5:
            cols.append(dict(kind='pod', g=gap(-2.5) if False else None, layers=[], q=0.0)); continue
        if x < 0.0:   # lug strip (PC 2.25 high) beside the pod wall
            cols.append(dict(kind='dev', g=gap(x), layers=[('pc', 2.25)], q=0.50, qi=0)); continue
        if item == 'wing' and W['s0'] <= x < wing_s1:
            incell = any(c0 <= x < c1 for c0, c1 in cells)
            a = a_cell if incell else a_bg
            if outer_light is not None and x >= outer_light: a = a_light
            cols.append(dict(kind='dev', g=gap(x), layers=[('tpu', 1.20), ('encap', 1.20), ('si' if incell else 'encap', 0.15), ('encap', 0.40)],
                             q=a * 0.96, qi=2)); continue
        if item == 'capsule' and C['s0'] <= x < C['s1']:
            side = x < C['s0'] + C['side'] or x >= C['s1'] - C['side']
            if side:
                cols.append(dict(kind='dev', g=gap(x), layers=[('pc', cap_t - t_top), ('glass', t_top)], q=a_top * 0.96 + 0.009, qi=1, qbot=True)); continue
            incell = C['s0'] + 0.95 <= x < C['s1'] - 0.95          # cell 10 mm along s inside the 0.5 side walls
            cols.append(dict(kind='dev', g=gap(x), layers=[('pc', 0.40), ('cell' if incell else 'air', 3.50), ('air', cap_t - t_top - 3.90), ('glass', t_top)],
                             q=a_top * 0.96 + 0.009, qi=3, qbot=True)); continue
        if x < 16.0: lay = [('tpu', 1.5)]
        elif x < 19.0: lay = [('tpu', 2.0)]
        else: lay = [('band', 1.5)]
        cols.append(dict(kind='dev', g=gap(x), layers=lay, q=a_strap, qi=0))
    return s, cols, geo


def solve(s, cols, w=3e-3, T_air=35.0, h_conv=10.0, Gsun=1000.0, T_pod=42.0, worn=True, Ta=37.0):
    """FV: tissue block (ns x nzt, z < 0) + device block (ns x nzd, z from the device's inner face up)."""
    hr = h_rad(0.9, (T_air + 45.0) / 2.0 if Gsun > 0 else T_air + 5.0)
    h_top = h_conv + hr
    ns = len(s); zt = np.r_[np.arange(0, 3.0, 0.1), np.arange(3.0, 30.0001, 0.5)]; zt_c = 0.5 * (zt[1:] + zt[:-1]); dzt = np.diff(zt); nzt = len(dzt)
    nzd = int(round(4.8 / DZ))                                        # [S2b] room for the 4.6 mm capsule (empty rows are not solved)
    mat = np.full((ns, nzd), '', dtype=object); qv = np.zeros((ns, nzd))
    for i, c in enumerate(cols):
        if c['kind'] != 'dev': continue
        z0 = 0
        for j, (m_, t) in enumerate(c['layers']):
            n = int(round(t / DZ)); mat[i, z0:z0 + n] = m_
            if j == c['qi']:
                k_ = z0 if c.get('qbot') else z0 + n - 1               # print under the glass: bottom glass cell; else the layer's top cell
                qv[i, min(k_, nzd - 1)] += c['q'] * Gsun * DS * 1e-3   # W per m of depth
            z0 += n
    solid = mat != ''
    Nt = ns * nzt; Nd = ns * nzd; N = Nt + Nd
    it = lambda i, j: i * nzt + j                                         # noqa: E731  (j = 0 at the skin surface, downwards)
    idv = lambda i, j: Nt + i * nzd + j                                   # noqa: E731
    rows, colsA, vals = [], [], []; rhs = np.zeros(N); diag = np.zeros(N)
    def link(p, q, g):
        rows.extend([p, q]); colsA.extend([q, p]); vals.extend([-g, -g]); diag[p] += g; diag[q] += g
    kt = 0.37; wrc = (w * 4.0e6) if worn else 0.0
    dsm = DS * 1e-3
    for i in range(ns):
        for j in range(nzt):
            p = it(i, j); dz = dzt[j] * 1e-3
            if worn:
                diag[p] += wrc * dsm * dz; rhs[p] += wrc * dsm * dz * Ta
            if i + 1 < ns: link(p, it(i + 1, j), kt * dz / dsm)
            if j + 1 < nzt: link(p, it(i, j + 1), kt * dsm / (0.5 * (dzt[j] + dzt[j + 1]) * 1e-3))
            else:
                g = kt * dsm / (0.5 * dz); diag[p] += g; rhs[p] += g * Ta
    dzm = DZ * 1e-3
    for i in range(ns):
        c = cols[i]
        for j in range(nzd):
            if not solid[i, j]: continue
            p = idv(i, j); kx, kz = K[mat[i, j]]
            rhs[p] += qv[i, j]
            if i + 1 < ns and solid[i + 1, j]:
                k2 = K[mat[i + 1, j]][0]; link(p, idv(i + 1, j), dzm / (dsm / (2 * kx) + dsm / (2 * k2)))
            if j + 1 < nzd and solid[i, j + 1]:
                k2 = K[mat[i, j + 1]][1]; link(p, idv(i, j + 1), dsm / (dzm / (2 * kz) + dzm / (2 * k2)))
            elif j + 1 >= nzd or not solid[i, j + 1]:
                g = dsm / (dzm / (2 * kz) + 1.0 / h_top); diag[p] += g; rhs[p] += g * T_air
            if j == 0:   # inner face -> gap -> skin top tissue cell
                gm = c['g']
                Rg = 0.0025 if gm <= 1e-6 else 1.0 / (0.026 / ((gm + 0.05) * 1e-3) + 6.0)
                g = dsm / (dzm / (2 * kz) + Rg + dzt[0] * 1e-3 / (2 * kt))
                if worn: link(p, it(i, 0), g)
                else:
                    gb = dsm / (dzm / (2 * kz) + 1.0 / (h_conv + hr)); diag[p] += gb; rhs[p] += gb * T_air
    for i in range(ns):   # skin surface not covered by a device column: the pod floor (Robin to T_pod through a 1 mm gap)
        p = it(i, 0)
        if cols[i]['kind'] == 'pod' and worn:
            g = dsm / (1.0 / (0.026 / 1.05e-3 + 6.0) + dzt[0] * 1e-3 / (2 * kt)); diag[p] += g; rhs[p] += g * T_pod
    used = np.zeros(N, bool); used[:Nt] = True; used[Nt:] = solid.ravel()
    diag[~used] = 1.0
    A = sp.csr_matrix((np.r_[vals, diag], (np.r_[rows, np.arange(N)], np.r_[colsA, np.arange(N)])), shape=(N, N))
    T = spl.spsolve(A.tocsc(), rhs)
    Tt = T[:Nt].reshape(ns, nzt); Td = np.where(solid, T[Nt:].reshape(ns, nzd), np.nan)
    skin = Tt[:, 0] + (Tt[:, 0] - Tt[:, 1]) * 0.5 * dzt[0] / (0.5 * (dzt[0] + dzt[1]))     # surface extrapolation
    return dict(skin=skin, Td=Td, mat=mat)


def stats(s, r, rng, cell_mat=('si', 'cell')):
    sel = (s >= rng[0]) & (s < rng[1])
    out = dict(skin_max_C=round(float(np.nanmax(r['skin'][sel])), 2), s_at_max=round(float(s[sel][np.nanargmax(r['skin'][sel])]), 1))
    mk = np.isin(r['mat'], cell_mat) & sel[:, None]
    if mk.any(): out['cell_max_C'] = round(float(np.nanmax(r['Td'][mk])), 2); out['cell_mean_C'] = round(float(np.nanmean(r['Td'][mk])), 2)
    out['device_top_max_C'] = round(float(np.nanmax(r['Td'][sel])), 2)
    return out


R = {}; t0 = time.time()


def case(tag, item, Cw=165.0, bkw=None, skw=None, rng=None):
    s, cols, geo = build(Cw, item, **(bkw or {}))
    r = solve(s, cols, **(skw or {}))
    if rng is None: rng = (2.0, 13.7) if item == 'wing' else (2.0, 13.9)
    st = stats(s, r, rng)
    # per sub-cell skin maxima (wing)
    if item == 'wing':
        a0, a1 = (bkw or {}).get('active', (2.0, 13.7)); pitch = (a1 - a0 - 0.6) / 4
        st['sub_cell_skin_max_C'] = [round(float(np.max(r['skin'][(s >= a0 + 0.3 + i * pitch) & (s < a0 + 0.3 + (i + 1) * pitch)])), 2) for i in range(4)]
        st['sub_cell_mean_gap_mm'] = [round(float(np.mean([c['g'] for x, c in zip(s, cols) if a0 + 0.3 + i * pitch <= x < a0 + 0.3 + (i + 1) * pitch])), 2) for i in range(4)]
    st['strap_far_skin_C'] = round(float(r['skin'][-1]), 2); st['free_span_mm'] = round(geo['free'], 2)
    R[tag] = st
    print('%-70s %s  (%.0f s)' % (tag, json.dumps(st), time.time() - t0), flush=True)
    return st


if __name__ == '__main__':
    W3 = dict(w=3e-3)
    # ---- case 2: wing as designed, per wrist and perfusion
    for Cw in (140.0, 165.0, 200.0):
        for w in (1e-3, 3e-3, 6e-3):
            case(f'C2 wing as designed {Cw:.0f} mm w{w:g}', 'wing', Cw, skw=dict(w=w))
    case('C2 wing as designed 165 mm w3e-3 wind x0.6 (h 6)', 'wing', 165.0, skw=dict(w=3e-3, h_conv=6.0))
    case('C2 reference: no wing (strap root a 0.6) 165 mm w3e-3', 'wing', 165.0, bkw=dict(wing_s1=2.0), skw=W3)
    case('C2 reference: no wing, strap a 0.30, 165 mm w3e-3', 'wing', 165.0, bkw=dict(wing_s1=2.0, a_strap=0.30), skw=W3)
    # mitigations: (a) active wing ends at s_end (wing body ends there, plain strap beyond); (b) light outer zone a 0.3 from s_end
    for se in (10.0, 9.0, 8.0):
        for Cw in (140.0, 165.0, 200.0):
            case(f'C2 mit-a wing to s {se:g} {Cw:.0f} mm w3e-3', 'wing', Cw, bkw=dict(active=(2.0, se), wing_s1=se), skw=W3, rng=(2.0, 13.7))
            case(f'C2 mit-b light outer zone from s {se:g} {Cw:.0f} mm w3e-3', 'wing', Cw, bkw=dict(active=(2.0, se), outer_light=se), skw=W3, rng=(2.0, 13.7))
    for se in (10.0, 8.0):
        case(f'C2 mit-a wing to s {se:g} 165 mm w1e-3', 'wing', 165.0, bkw=dict(active=(2.0, se), wing_s1=se), skw=dict(w=1e-3), rng=(2.0, 13.7))
        case(f'C2 mit-b light outer zone from s {se:g} 165 mm w1e-3', 'wing', 165.0, bkw=dict(active=(2.0, se), outer_light=se), skw=dict(w=1e-3), rng=(2.0, 13.7))
    # light strap with each mitigation (strap a 0.30)
    for se in (10.0, 8.0):
        case(f'C2 mit-a wing to s {se:g} + strap a 0.30, 165 mm w3e-3', 'wing', 165.0, bkw=dict(active=(2.0, se), wing_s1=se, a_strap=0.30), skw=W3, rng=(2.0, 13.7))
        case(f'C2 mit-b light zone from s {se:g} + strap a 0.30, 165 mm w3e-3', 'wing', 165.0, bkw=dict(active=(2.0, se), outer_light=se, a_strap=0.30), skw=W3, rng=(2.0, 13.7))
    # ---- case 3: capsule (root A), glass top with white print
    for a in (0.15, 0.30):
        for hc in (5.0, 10.0, 20.0):
            for Cw in (140.0, 165.0, 200.0):
                case(f'C3 capsule a {a:.2f} h {hc:g} {Cw:.0f} mm w3e-3', 'capsule', Cw, bkw=dict(a_top=a), skw=dict(w=3e-3, h_conv=hc))
        case(f'C3 capsule a {a:.2f} h 5 165 mm w1e-3', 'capsule', 165.0, bkw=dict(a_top=a), skw=dict(w=1e-3, h_conv=5.0))
        case(f'C3 capsule a {a:.2f} h 5 165 mm w6e-3', 'capsule', 165.0, bkw=dict(a_top=a), skw=dict(w=6e-3, h_conv=5.0))
    # cold: worn (perfusion 1e-3 and 5e-4, vasoconstriction), wind h 20 / 30; with sun 500 W/m2 and without; off the wrist
    for Ta in (-10.0, -20.0):
        for w in (1e-3, 5e-4):
            for hc in (20.0, 30.0):
                for Gs in (0.0, 500.0):
                    case(f'C3 cold worn air {Ta:g} w{w:g} h {hc:g} sun {Gs:g}', 'capsule', 165.0, bkw=dict(a_top=0.15),
                         skw=dict(w=w, h_conv=hc, T_air=Ta, Gsun=Gs, T_pod=Ta + 0.5 * (34 - Ta)))
        for Gs in (0.0, 500.0):
            case(f'C3 cold off-wrist air {Ta:g} h 20 sun {Gs:g}', 'capsule', 165.0, bkw=dict(a_top=0.15), skw=dict(worn=False, h_conv=20.0, T_air=Ta, Gsun=Gs))
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    json.dump(R, open(os.path.join(HERE, 'out', 'strap2d.json'), 'w'), indent=1)
    print('wrote out/strap2d.json', flush=True)
