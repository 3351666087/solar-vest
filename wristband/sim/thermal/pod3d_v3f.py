#!/usr/bin/env python3
"""V3-G2 cases 1, 4, 5: the V3-F 41 x 34 pod (stage 2a) in the physics review's 3-D finite-volume model
(review_fv3d_v2b.py = unchanged copy of redesign/attack_physics/calc/fv3d_v2b.py, the model that gives V2-B's 41.17 C).
Same solver, boundary data and tissue boundary (SIM-13 tissue2d R_eff), so the V2-B comparison is model to model.
Geometry: v3/cad/src/geom_v3f.py values with V3F_POD_W=34, raise 0.15 (window half 5.305, PV half 4.65), BASELINE 8.
No cell in the pod (V3-F: cell in the root-A capsule). Plan simplified to boxes on a 0.5 mm grid (corner radii ignored).
Run: python3 -B pod3d_v3f.py > logs/pod3d.log   -> out/pod3d.json"""
import sys, os, json, time
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np
import review_fv3d_v2b as F                                                           # noqa: E402

F.K.update({'motor': (5.0, 5.0),            # ERM: steel can, magnet, coil, air inside, effective [E]
            'pet': (0.20, 0.20),            # front-light film + OCA [E]
            'lcd': (0.9, 0.9),              # memory-LCD: 2 x 0.25 glass + polarisers [E]
            'via_island': (60.0, 30.0),     # thermal-via island under TMP117 (review value) [E]
            'tmp': (1.0, 1.0), 'ic': (1.0, 1.0)})
F.MATS[:] = list(F.K); F.MID.clear(); F.MID.update({m: i for i, m in enumerate(F.MATS)})
SOLAR, TAU = F.SOLAR, F.TAU
TIS = F.TIS                                                                            # (R_eff, T_skin) per perfusion
L, W = 41.0, 34.0
U10 = (5.525, 25.55); U15 = (5.525, 22.55)
U10_S2A = U10        # pod frame = board frame + 1.5 (g1/place/work/pl_S2W34A3_B_s13.json, F side)
MOTOR_C = (20.0, 25.4)                            # cad motor_search chosen centre
ZB = [-0.80, 0, 0.25, 0.30, 0.35, 1.45, 2.15, 2.20, 2.35, 2.50, 2.60, 2.65, 2.77, 2.985, 3.15, 3.30, 3.35, 3.355, 3.40,
      3.555, 3.60, 3.805, 3.905, 3.85, 4.505]


def pod(a_disp=0.60, a_print=0.15, mask=None, G=1000.0, q_chg=0.0, q_motor=0.0, island=True, a_rim=SOLAR['alpha_frame'],
        motor_mat='motor', ir_reject=0.0, motor_pad=0.0, a_win_ir=0.0, pv_raise=0.0, win_raise=0.0, u10=None, rail_ss=False):
    """pv_raise: [fix] PV laminate (and K / E3 block tops) raised; air gap under the laminate 0.15 -> 0.15 + pv_raise (LEAD f: up to 0.655 to the window top)"""
    """mask: absorptance of an opaque mask print on the whole window-glass underside (interim build; no display heat)"""
    # [S2b] win_raise: window seat raised (M-2): frame, film, glass, lip, rail top, insert top follow; the panel does not (air 0.155 + win_raise).
    # u10: TMP117 / island centre (T-5 island at (6.05, 25.55)). rail_ss: rail stainless outside the antenna buffer (X > 11.5, M-2).
    wr = win_raise; U10 = u10 or U10_S2A
    m = F.Model(L, W, sorted(set(ZB + [z + pv_raise for z in (2.65, 2.77, 2.985, 3.15, 3.35, 3.60, 3.85)] + [z + wr for z in (3.355, 3.555, 3.805, 3.905, 4.505)])))
    m.box('resin', 0, L, 0, W, 0, 3.85 + pv_raise)                                   # body, then carved
    m.box('air_cav', 1, L - 1, 1, W - 1, 0.25, 3.85 + pv_raise)                      # cavity
    m.box('resin', 14.5, 25.5, 12.0, 19.0, -0.80, 0)                      # PPG mesa 11 x 7, 0.80 proud
    m.box('ti', 1.5, 12.5, 8.7, 28.0, 0, 0.25); m.box('ti', 27.5, 39.5, 6.0, 28.0, 0, 0.25)   # E1 212, E2 264 mm2 (cad)
    m.box('psa', 1.5, L - 1.5, 1.5, W - 1.5, 0.25, 0.35)                  # carrier film
    m.box('pcb', 1.5, L - 1.5, 1.5, W - 1.5, 0.35, 1.45)                  # 1.0 mm 6-layer + tolerance
    m.box('parts', 1.5, L - 1.5, 1.5, 20.0, 1.45, 2.35)                   # low-part zone under the window half
    m.box('parts', 1.5, L - 1.5, 20.0, W - 1.5, 1.45, 2.50)               # general zone under the PV half
    # motor through the board cut-out (d 8.6), on the floor film with PSA
    m.box('air_cav', MOTOR_C[0] - 4.3, MOTOR_C[0] + 4.3, MOTOR_C[1] - 4.3, MOTOR_C[1] + 4.3, 0.25, 2.65 + pv_raise)
    mot = m.box(motor_mat, MOTOR_C[0] - 4.05, MOTOR_C[0] + 4.05, MOTOR_C[1] - 4.05, MOTOR_C[1] + 4.05, 0.30, 2.50)
    if motor_pad:   # [fix] insulating foam disc under the motor instead of PSA: motor raised by motor_pad on the floor film
        m.box('foam', MOTOR_C[0] - 4.05, MOTOR_C[0] + 4.05, MOTOR_C[1] - 4.05, MOTOR_C[1] + 4.05, 0.25, 0.30)
    m.box('psa', MOTOR_C[0] - 4.05, MOTOR_C[0] + 4.05, MOTOR_C[1] - 4.05, MOTOR_C[1] + 4.05, 0.25, 0.30)
    # panel support: 4 corner posts board -> frame, frame band 1.0 under the panel border
    for x, y in ((1.3, 5.7), (32.3, 5.7), (1.3, 18.7), (32.3, 18.7)):
        m.box('resin', x, x + 1.0, y, y + 1.0, 1.45, 2.50)
    m.box('resin', 1.3, 33.3, 5.7, 19.7, 2.50, 2.60); m.box('air_cav', 2.3, 32.3, 6.7, 18.7, 2.50, 2.60)
    m.box('lcd', 1.3, 33.3, 5.7, 19.7, 2.60, 3.30); disp = m.box('lcd', 1.3, 33.3, 5.7, 19.7, 3.30, 3.40)
    m.box('air', 1.0, 37.5, 1.0, 20.0, 3.40, 3.555 + wr)                  # 0.155 air gap over the panel (+ win_raise)
    m.box('resin', 1.1, 33.7, 5.0, 5.4, 2.50, 3.555 + wr)                 # antenna-side window rail (GF-LCP)
    if rail_ss: m.box('steel', 11.5, 33.7, 5.0, 5.4, 2.50, 3.555 + wr)   # [S2b M-2] stainless section outside the antenna buffer
    # window: stainless frame 0.25 under the glass, minus the film opening and the antenna corner (PC seat there)
    m.box('steel', 0.5, 37.5, 0.5, 20.45, 3.555 + wr, 3.805 + wr)
    m.box('resin', 0.5, 11.5, 0.5, 9.5, 3.555 + wr, 3.805 + wr)
    film = m.box('pet', 2.13, 33.6, 6.53, 18.87, 3.555 + wr, 3.805 + wr)
    m.box('glass', 0.5, 37.5, 0.5, 20.45, 3.805 + wr, 4.505 + wr)
    gl_bot = m.box('glass', 0.5, 37.5, 0.5, 20.45, 3.805 + wr, 3.905 + wr)
    m.box('resin', 0, 0.5, 0, 20.45, 3.555, 4.505 + wr); m.box('resin', 0, 37.5, 0, 0.5, 3.555, 4.505 + wr)   # PC lip
    # rib (PC shelf + stainless insert), six rib posts
    m.box('resin', 3.8, 37.0, 20.0, 21.0, 2.15, 3.355 + wr); m.box('steel', 3.8, 34.0, 20.0, 20.5, 2.60, 3.355 + wr)
    for x in (4.1, 10.0, 16.0, 22.0, 28.0, 33.0):
        m.box('resin', x - 0.5, x + 0.5, 19.8, 20.8, 1.45, 2.15)
    m.box('resin', 3.65, 37.5, 20.45, 20.55, 3.355 + wr, 3.85 + pv_raise)            # sealant joint between the glasses
    # PV laminate: flex 0.12 / encap 0.215 / Si 0.165 / encap 0.20 / glass 0.50 = 1.20 (RFQ max)
    X0, X1, Y0, Y1 = 3.65, 37.5, 20.55, 33.5
    m.box('flex', X0, X1, Y0, Y1, 2.65 + pv_raise, 2.77 + pv_raise); m.box('encap', X0, X1, Y0, Y1, 2.77 + pv_raise, 3.35 + pv_raise); m.box('glass', X0, X1, Y0, Y1, 3.35 + pv_raise, 3.85 + pv_raise)
    strips = []
    for i in range(4):
        y0 = 21.0 + i * 3.07; y1 = min(y0 + 2.80 + (0.04 if i == 3 else 0), 33.05)
        strips.append(m.box('si', 4.1, 31.8, y0, y1, 2.985 + pv_raise, 3.15 + pv_raise))
    a_si = 311.1
    # blocks: K corner (contacts) and the E3 block (Ti strip on top), PV-half lip
    kb = m.box('resin', 0.4, 3.65, 20.45, W, 1.45, 3.85 + pv_raise); e3 = m.box('resin', 37.5, L, 0, W, 2.85, 3.85 + pv_raise)
    m.box('ti', 38.0, 40.5, 2.0, 32.0, 3.60 + pv_raise, 3.85 + pv_raise); m.box('resin', X0, X1, 33.5, W, 2.65 + pv_raise, 3.85 + pv_raise)
    # charger U15 and TMP117 U10 (sky side of the board)
    chg = m.box('ic', U15[0] - 1.0, U15[0] + 1.0, U15[1] - 1.0, U15[1] + 1.0, 1.45, 2.20)
    if island:
        x0, x1, y0, y1 = U10[0] - 2.0, U10[0] + 2.0, U10[1] - 2.0, U10[1] + 2.0
        m.box('via_island', x0, x1, y0, y1, 0.35, 1.45); m.box('ti', x0, x1, y0, y1, 0.25, 0.35)   # filled contact to E1
        m.box('air_cav', x0, x1, y0, y1, 1.45, 2.50)
    tmp = m.box('tmp', U10[0] - 1.0, U10[0] + 1.0, U10[1] - 1.0, U10[1] + 1.0, 1.45, 2.20)
    # ------------------------------------------------------------------ absorbed sun
    Gm = G * 1e-6; tr = TAU * (1 - SOLAR['lens_abs'])
    a_wg = 37.0 * 19.95; a_film = (33.6 - 2.13) * (18.87 - 6.53); a_lam = (X1 - X0) * (Y1 - Y0)
    a_rimtot = L * W - a_wg - a_lam
    Q = {}
    Q['window_glass_bulk'] = Gm * a_wg * TAU * SOLAR['lens_abs']; m.heat(Q['window_glass_bulk'], m.box('glass', 0.5, 37.5, 0.5, 20.45, 3.905 + wr, 4.505 + wr))
    if mask is not None:
        Q['mask'] = Gm * a_wg * tr * mask * (1 - a_win_ir); m.heat(Q['mask'], gl_bot)
    else:
        Q['film'] = Gm * a_film * tr * 0.03; m.heat(Q['film'], film)
        Q['display'] = Gm * a_film * tr * 0.97 * a_disp * (1 - a_win_ir); m.heat(Q['display'], disp)
        Q['window_border_print'] = Gm * (a_wg - a_film) * tr * a_print
        m.heat(Q['window_border_print'], gl_bot)                          # print on the glass underside (spread over the glass bottom layer)
    Q['lam_glass_bulk'] = Gm * a_lam * TAU * SOLAR['lens_abs'] * 0.5 / 0.7
    m.heat(Q['lam_glass_bulk'], m.box('glass', X0, X1, Y0, Y1, 3.35 + pv_raise, 3.85 + pv_raise))
    Q['silicon'] = Gm * a_si * tr * (SOLAR['alpha_cell'] - ir_reject)
    for s in strips: m.heat(Q['silicon'] / 4, s)
    Q['lam_print'] = Gm * (a_lam - a_si) * tr * a_print; m.heat(Q['lam_print'], m.box('flex', X0, X1, Y0, Y1, 2.65 + pv_raise, 2.77 + pv_raise))
    Q['rim'] = Gm * a_rimtot * a_rim
    m.heat(Q['rim'] * 0.3, m.box('resin', 0.4, 3.65, 20.45, W, 3.60 + pv_raise, 3.85 + pv_raise)); m.heat(Q['rim'] * 0.7, m.box('ti', 38.0, 40.5, 2.0, 32.0, 3.60 + pv_raise, 3.85 + pv_raise))
    if q_chg: m.heat(q_chg, chg); Q['charger'] = q_chg
    if q_motor: m.heat(q_motor, mot); Q['motor'] = q_motor
    m.absorbed = sum(Q.values()); m.Q = Q; m.sel = dict(tmp=tmp, disp=disp, island=(U10[0] - 2.0, U10[0] + 2.0, U10[1] - 2.0, U10[1] + 2.0))
    return m


def v2b_rev1():
    """V2-B revision 1 reference (copy of redesign/v2_rev1_checks.py v2b_rev1 with its defaults): must give 41.17 C at 3e-3."""
    fl, film, parts, pcb, cell_t, gap = 0.35, 0.10, 1.00, 0.80, 2.10, 0.30
    strip_x, y_first, board_y1, cell_y0, cell_x = (3.7, 31.4), 6.0, 19.5, 19.9, (5.0, 35.0)
    lid = (0.12, 0.15, 0.165, 0.20, 0.50)
    z_cell0 = fl + 0.15 + 0.10; z_cell1 = z_cell0 + cell_t; z_lid0 = z_cell1 + gap
    zl = [z_lid0]
    for t in lid: zl.append(zl[-1] + t)
    zs = [-0.75, 0, 0.25, fl, fl + film, fl + film + pcb, fl + film + pcb + parts, fl + 0.15, z_cell0, z_cell1] + zl
    m = F.Model(40, 32, zs)
    m.box('resin', 0, 40, 0, 32, 0, z_lid0); m.box('air_cav', 1.0, 39.0, 1.0, 31.0, fl, z_lid0)
    m.box('resin', 14.5, 25.5, 11.5, 18.5, -0.75, 0)
    m.box('ti', 1.5, 14.0, 4.0, 22.5, 0, 0.25); m.box('ti', 26.0, 39.0, 2.0, 24.5, 0, 0.25)
    m.box('psa', 1.5, 38.5, 1.5, board_y1, fl, fl + film); m.box('pcb', 1.5, 38.5, 1.5, board_y1, fl + film, fl + film + pcb)
    m.box('parts', 2.0, 38.0, 2.0, board_y1 - 0.5, fl + film + pcb, fl + film + pcb + parts)
    m.box('steel', cell_x[0] - 0.3, cell_x[1] + 0.3, cell_y0, 29.9, fl, fl + 0.15); m.box('psa', cell_x[0], cell_x[1], cell_y0, 29.9, fl + 0.15, z_cell0)
    m.box('battery', cell_x[0], cell_x[1], cell_y0, 29.9, z_cell0, z_cell1); m.box('air', cell_x[0], cell_x[1], cell_y0, 29.9, z_cell1, z_lid0)
    yp = min(9.0, board_y1 - 4.0)
    m.box('resin', 12, 14, yp, yp + 2, fl + film + pcb, z_lid0); m.box('resin', 26, 28, yp, yp + 2, fl + film + pcb, z_lid0)
    m.box('flex', 0, 40, 0, 32, zl[0], zl[1]); m.box('encap', 0, 40, 0, 32, zl[1], zl[4]); m.box('glass', 0, 40, 0, 32, zl[4], zl[5])
    strips = [m.box('si', strip_x[0], strip_x[1], y_first + i * 5.6, y_first + i * 5.6 + 5.2, zl[2], zl[3]) for i in range(4)]
    a_lid = 1249.0; a_si = 4 * (strip_x[1] - strip_x[0]) * 5.2; Gm = 1e-3; tr = TAU * (1 - SOLAR['lens_abs'])
    q_bulk = Gm * a_lid * TAU * SOLAR['lens_abs']; q_si = Gm * a_si * tr * SOLAR['alpha_cell']; q_print = Gm * (a_lid - a_si) * tr * 0.15
    for s in strips: m.heat(q_si / 4, s)
    m.heat(q_print, m.box('flex', 0, 40, 0, 32, zl[0], zl[1])); m.heat(q_bulk, m.box('glass', 0, 40, 0, 32, zl[4], zl[5]))
    m.absorbed = q_bulk + q_si + q_print
    return m


def bcx(w='w3e-3', T_amb=35.0, hf=1.0, T_skin=None, task=False):
    if task:
        return F.bc(T_amb=T_amb, hf=hf, z_low=-0.80, yc=17.0)
    Rt, Ts = TIS[w]
    return F.bc(T_amb=T_amb, T_skin=Ts if T_skin is None else T_skin, R_tis=Rt, hf=hf, z_low=-0.80, yc=17.0)


R = {}; t0 = time.time()


def run(tag, m, b):
    m.solve(b)
    r = dict(absorbed_W=round(m.absorbed, 4), skin_max_C=round(m.skin['skin_contact_max_C'], 2), skin_mean_C=round(m.skin['skin_contact_mean_C'], 2),
             contact_mm2=round(m.skin['contact_area_mm2'], 0), noncontact_bottom_max_C=round(m.skin['noncontact_bottom_max_C'], 2),
             residual=m.res, balance_err_W=round(m.absorbed - sum(m.flux.values()), 5))
    for mat in ('glass', 'si', 'lcd', 'motor', 'ic', 'battery'):
        if (m.mat == F.MID[mat]).any():
            r[mat + '_max_C'] = round(m.stat(mat)[0], 2)
    if hasattr(m, 'sel'):
        r['Q_W'] = {k: round(v, 4) for k, v in m.Q.items()}
        T_tmp = float(m.T[m.sel['tmp']].mean())
        x0, x1, y0, y1 = m.sel['island']
        ix = (m.xc > x0) & (m.xc < x1); iy = (m.yc > y0) & (m.yc < y1); iz = int(np.argmin(abs(m.zc - 0.0625)))
        T_pl = float(m.T[np.ix_(ix, iy, [iz])].mean())
        r.update(TMP117_C=round(T_tmp, 2), plate_under_island_C=round(T_pl, 2), tmp_err_vs_plate_K=round(T_tmp - T_pl, 2),
                 tmp_err_vs_skin_max_K=round(T_tmp - r['skin_max_C'], 2))
    R[tag] = r
    print('%-62s abs %.3f W | skin max %.2f mean %.2f | glass %s | si %s | lcd %s | TMP err %s | %.0f s' % (
        tag, r['absorbed_W'], r['skin_max_C'], r['skin_mean_C'], r.get('glass_max_C'), r.get('si_max_C'), r.get('lcd_max_C'),
        r.get('tmp_err_vs_plate_K'), time.time() - t0), flush=True)
    return r


if __name__ == '__main__':
    # reference: V2-B revision 1 in the same model (REDESIGN 5.7: 41.17 at 3e-3)
    run('REF V2-B rev1, print 0.15, w3e-3 (review 41.17)', v2b_rev1(), F.bc(T_skin=TIS['w3e-3'][1], R_tis=TIS['w3e-3'][0], z_low=-0.75, yc=15.0))
    # case 1: pod in full sun, W-C, 1000 W/m2, 35 C air
    for a in (0.45, 0.60, 0.75):
        for w in ('w1e-3', 'w3e-3', 'w6e-3'):
            run(f'C1 disp {a:.2f} print 0.15 {w}', pod(a_disp=a), bcx(w))
    for a in (0.60, 0.75):
        run(f'C1 disp {a:.2f} print 0.15 w3e-3 wind x0.6', pod(a_disp=a), bcx('w3e-3', hf=0.6))
        run(f'C1 disp {a:.2f} print 0.15 w1e-3 wind x0.6', pod(a_disp=a), bcx('w1e-3', hf=0.6))
    run('C1 disp 0.75 print 0.25 w3e-3', pod(a_disp=0.75, a_print=0.25), bcx('w3e-3'))
    run('C1 disp 0.75 print 0.60 (dark prints) w3e-3', pod(a_disp=0.75, a_print=0.60), bcx('w3e-3'))
    run('C1 disp 0.75 print 0.60 w1e-3 wind x0.6 (all worst)', pod(a_disp=0.75, a_print=0.60), bcx('w1e-3', hf=0.6))
    run('C1 disp 0.60 task BC (skin 34 fixed)', pod(a_disp=0.60), bcx(task=True))
    # interim build: masked window
    for w in ('w1e-3', 'w3e-3', 'w6e-3'):
        run(f'C1m mask 0.60 {w}', pod(mask=0.60), bcx(w))
    run('C1m mask 0.60 w3e-3 wind x0.6', pod(mask=0.60), bcx('w3e-3', hf=0.6))
    run('C1m mask 0.60 w1e-3 wind x0.6', pod(mask=0.60), bcx('w1e-3', hf=0.6))
    # fixes: FIX-P = PV laminate raised 0.655 mm to the window top (air under the laminate 0.15 -> 0.805; LEAD f, no new
    # maximum thickness) + IR-cut (hot-mirror) coating on the window glass removing 40 % of the display's absorbed heat [E]
    FIXP = dict(pv_raise=0.655, a_win_ir=0.40)
    for a in (0.45, 0.60, 0.75):
        for w in ('w1e-3', 'w3e-3', 'w6e-3'):
            run(f'FIXP C1 disp {a:.2f} print 0.15 {w}', pod(a_disp=a, **FIXP), bcx(w))
    for a in (0.60, 0.75):
        run(f'FIXP C1 disp {a:.2f} print 0.15 w3e-3 wind x0.6', pod(a_disp=a, **FIXP), bcx('w3e-3', hf=0.6))
        run(f'FIXP C1 disp {a:.2f} print 0.15 w1e-3 wind x0.6', pod(a_disp=a, **FIXP), bcx('w1e-3', hf=0.6))
    run('FIXP C1 disp 0.75 print 0.25 w3e-3', pod(a_disp=0.75, a_print=0.25, **FIXP), bcx('w3e-3'))
    run('FIXP C1 disp 0.75 print 0.60 w3e-3', pod(a_disp=0.75, a_print=0.60, **FIXP), bcx('w3e-3'))
    run('FIXP+SiIR C1 disp 0.75 print 0.15 w1e-3 wind x0.6', pod(a_disp=0.75, ir_reject=0.17, **FIXP), bcx('w1e-3', hf=0.6))
    for mk in (0.60, 0.35):
        for w in ('w1e-3', 'w3e-3'):
            run(f'FIXP C1m mask {mk:.2f} {w}', pod(mask=mk, **FIXP), bcx(w))
        run(f'FIXP C1m mask {mk:.2f} w3e-3 wind x0.6', pod(mask=mk, **FIXP), bcx('w3e-3', hf=0.6))
    run('raise only C1m mask 0.35 w3e-3', pod(mask=0.35, pv_raise=0.655), bcx('w3e-3'))
    run('raise only C1m mask 0.35 w1e-3 wind x0.6', pod(mask=0.35, pv_raise=0.655), bcx('w1e-3', hf=0.6))
    # case 4: charging heat (BQ25170 U15) and the skin-hot motor event (0.11 W, steady = upper bound of 257 s)
    for q in (0.022, 0.050, 0.070):
        run(f'C4 indoor 25 C still air, no sun, charge {q * 1e3:.0f} mW', pod(G=0.0, q_chg=q), bcx('w3e-3', T_amb=25.0, hf=0.4, T_skin=33.0))
    run('C4 indoor 25 C still air, no sun, no charge', pod(G=0.0), bcx('w3e-3', T_amb=25.0, hf=0.4, T_skin=33.0))
    for q in (0.0, 0.070):
        run(f'C4 sunny window 800 W/m2 30 C still air disp 0.75, charge {q * 1e3:.0f} mW', pod(a_disp=0.75, G=800.0, q_chg=q), bcx('w3e-3', T_amb=30.0, hf=0.4))
    run('C4 sun disp 0.75 w3e-3 + charge 70 mW', pod(a_disp=0.75, q_chg=0.070), bcx('w3e-3'))
    run('C4 motor 0.11 W steady, sun disp 0.75 w3e-3', pod(a_disp=0.75, q_motor=0.11), bcx('w3e-3'))
    run('C4 motor 0.11 W steady, sun disp 0.75 w1e-3 wind x0.6', pod(a_disp=0.75, q_motor=0.11), bcx('w1e-3', hf=0.6))
    run('FIXP C4 motor 0.11 W steady, sun disp 0.75 w3e-3', pod(a_disp=0.75, q_motor=0.11, **FIXP), bcx('w3e-3'))
    run('FIXP C4 motor 25 % duty (27.5 mW mean) steady, sun disp 0.75 w3e-3', pod(a_disp=0.75, q_motor=0.0275, **FIXP), bcx('w3e-3'))
    run('FIXP C4 motor 25 % duty steady, sun disp 0.75 w1e-3 wind x0.6', pod(a_disp=0.75, q_motor=0.0275, **FIXP), bcx('w1e-3', hf=0.6))
    run('FIXP C4 sun disp 0.75 w3e-3 + charge 70 mW', pod(a_disp=0.75, q_chg=0.070, **FIXP), bcx('w3e-3'))
    run('FIXP C5 TMP task BC disp 0.60', pod(a_disp=0.60, **FIXP), bcx(task=True))
    run('FIXP C5 TMP w3e-3 disp 0.75', pod(a_disp=0.75, **FIXP), bcx('w3e-3'))
    run('C5 TMP indoor charge 70 mW (charger 3 mm from U10)', pod(G=0.0, q_chg=0.070), bcx('w3e-3', T_amb=25.0, hf=0.4, T_skin=33.0))
    # case 5: TMP117 coupling (island in every run; extra boundary sets)
    run('C5 TMP task BC disp 0.60', pod(a_disp=0.60), bcx(task=True))
    run('C5 TMP task BC disp 0.75 print 0.60', pod(a_disp=0.75, a_print=0.60), bcx(task=True))
    run('C5 TMP no island, task BC disp 0.60', pod(a_disp=0.60, island=False), bcx(task=True))
    run('C5 TMP indoor 25 C no sun', pod(G=0.0), bcx('w3e-3', T_amb=25.0, hf=0.4, T_skin=33.0))
    os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
    json.dump(R, open(os.path.join(HERE, 'out', 'pod3d.json'), 'w'), indent=1)
    print('wrote out/pod3d.json', flush=True)
