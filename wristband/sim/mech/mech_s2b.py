"""[S2b COPY of mech_v3f.py, 2026-11-15] the stage-2b design (v3/LEAD_NOTES.md 2d) is now the input: geom_v3f stage 2b (window seat +0.09,
laminate flush at 5.395 with a 0.20 STRUCTURAL bond, capsule top 0.50 / 4.6 mm, corner bumpers 0.33), rail stainless outside the antenna buffer
(GF-LCP inside it: reported as its own section), W1 / W2 chains with the precision tolerances of M-2 / M-4, CAD masses of stage 2b.
Writes mech_raw_s2b.json (mech_raw.json = stage 2a = 'before' stays).
SIM-14 / V3-G7 (mechanical, calculation part) for the 41 x 34 pod of stage 2a.
Geometry: v3/cad/src/geom_v3f.py (read-only import) with V3F_POD_L=41, V3F_POD_W=34, V3F_OPT=fpc=dwg,fold=1.9,joint=zif,raise=0.15
(v3/stage2a/stage2a.json). Methods copied (see copied/): Navier plate (baseline_calc navier), stage-1 window_plate_s1 rail / insert beams,
sim14_stack chain() (WC / RSS / MC). New here: a 1-D plate-strip FE across the short span (Hermite beams, distributed bead / bond
springs, rail and rib as springs from their post spans, rotational restraint), scaled to 2-D with the Navier/strip ratio.
All results are model output (E). Criteria and safety factor: MECH.md.
usage: python3 -B mech_v3f.py  -> mech_raw.json"""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
os.environ.update(V3F_POD_L="41", V3F_POD_W="34", V3F_OPT="fpc=dwg,fold=1.9,joint=zif,raise=0.15")
sys.path.insert(0, "/path/to/SolarVest_work/wristband/v3/cad/src")
import geom_v3f as G   # noqa: E402
Z = G.Z
assert G.TAG == "L41W34_fold1p9_fpcdwg_jointzif_raise0p15", G.TAG
assert G.S2B and abs(Z.win1 - 4.595) < 1e-9 and abs(Z.pv1 - 4.595) < 1e-9

SF = 1.5                         # safety factor on pressure / force (stated criterion, MECH.md)
P5 = 0.5                         # 5 bar in MPa
GL = dict(E=70e3, nu=0.22); SS = dict(E=193e3, nu=0.29, G=75e3); PC = dict(E=2.3e3, nu=0.37); TI = dict(E=105e3, nu=0.34)
LCP_E = G.RAIL_E_GPA * 1e3; EPOXY_E = 2.5e3
BEAD_E = 3.0                     # [E] elastic seal bead (silicone / MS class, Shore A ~50), MPa
H_PC = 100.0                     # [E] crush flow pressure of PC in an edge impact, MPa (yield 60-65, Vickers ~150)
R = {}


def Dp(E, nu, t): return E * t ** 3 / (12 * (1 - nu ** 2))


# --------------------------------------------------------------------------------- plate models
def navier(a, b, t, E, nu, q=1.0, patch=None, terms=119):
    """SS rectangular plate, centre deflection (mm) and max centre bending stress (MPa); q MPa over the plate or over a centred patch (c, d)"""
    D = Dp(E, nu, t); w = mx = my = 0.0
    c, d = patch if patch else (a, b)
    for m in range(1, terms + 1, 2):
        for n in range(1, terms + 1, 2):
            qmn = 16 * q / (math.pi ** 2 * m * n) * math.sin(m * math.pi * c / (2 * a)) * math.sin(n * math.pi * d / (2 * b))
            s = math.sin(m * math.pi / 2) * math.sin(n * math.pi / 2)
            qmn *= s                                       # patch centred at (a/2, b/2): sin(m pi x0 / a) sin(n pi y0 / b)
            k = (m * m / a ** 2 + n * n / b ** 2)
            wmn = qmn / (D * math.pi ** 4 * k ** 2)
            w += s * wmn; mx += s * D * math.pi ** 2 * (m * m / a ** 2 + nu * n * n / b ** 2) * wmn
            my += s * D * math.pi ** 2 * (nu * m * m / a ** 2 + n * n / b ** 2) * wmn
    return w, 6 * max(mx, my) / t ** 2


def f2d(a, L, t, E, nu):
    """2-D / strip ratio at the centre (SS): applied to the elastic part of the strip result"""
    return navier(a, L, t, E, nu, 1.0)[0] / (5 * 1.0 * L ** 4 / (384 * Dp(E, nu, t)))


# --------------------------------------------------------------------------------- strip FE (unit width, y across the short span)
class Strip:
    def __init__(self): self.beams = []; self.bodies = []; self.springs = []

    def beam(self, name, y0, y1, EI, q=1.0, h=0.05):
        n = int(round((y1 - y0) / h)) + 1
        self.beams.append(dict(name=name, y=np.linspace(y0, y1, n), EI=EI, q=q)); return len(self.beams) - 1

    def body(self, name, y, kw=None, kt=0.0):
        """rigid support body: vertical spring kw to ground (None = fixed), rotational spring kt (N mm / rad per mm)"""
        self.bodies.append(dict(name=name, y=y, kw=kw, kt=kt)); return len(self.bodies) - 1

    def seat(self, bi, body, ya, yb, k_dist):
        """distributed vertical spring (N/mm per mm of strip, per mm of bearing width) between beam bi and a body over ya..yb"""
        self.springs.append((bi, body, ya, yb, k_dist))

    def solve(self, qscale=1.0):
        off = []; nd = 0
        for b in self.beams: off.append(nd); nd += 2 * len(b["y"])
        boff = nd; nd += 2 * len(self.bodies)
        K = np.zeros((nd, nd)); F = np.zeros(nd)
        for bi, b in enumerate(self.beams):
            y = b["y"]; o = off[bi]
            for e in range(len(y) - 1):
                L = y[e + 1] - y[e]; ym = 0.5 * (y[e] + y[e + 1]); EI = b["EI"](ym) if callable(b["EI"]) else b["EI"]
                k = EI / L ** 3 * np.array([[12, 6 * L, -12, 6 * L], [6 * L, 4 * L * L, -6 * L, 2 * L * L], [-12, -6 * L, 12, -6 * L], [6 * L, 2 * L * L, -6 * L, 4 * L * L]])
                q = b["q"] * qscale; f = q * np.array([L / 2, L * L / 12, L / 2, -L * L / 12])
                ix = [o + 2 * e, o + 2 * e + 1, o + 2 * e + 2, o + 2 * e + 3]
                K[np.ix_(ix, ix)] += k; F[ix] += f
        for (bi, bo, ya, yb, kd) in self.springs:
            y = self.beams[bi]["y"]; o = off[bi]; B = self.bodies[bo]; ob = boff + 2 * bo
            hh = y[1] - y[0]
            for i, yy in enumerate(y):
                if ya - 1e-9 <= yy <= yb + 1e-9:
                    trib = hh * (0.5 if (abs(yy - ya) < 1e-9 or abs(yy - yb) < 1e-9) else 1.0)
                    c = np.zeros(nd); c[o + 2 * i] = 1.0; c[ob] = -1.0; c[ob + 1] = -(yy - B["y"])
                    K += kd * trib * np.outer(c, c)
        fixed = []
        for j, B in enumerate(self.bodies):
            ob = boff + 2 * j
            if B["kw"] is None: fixed.append(ob)
            else: K[ob, ob] += B["kw"]
            K[ob + 1, ob + 1] += B["kt"] + 1e-6
        free = [i for i in range(nd) if i not in fixed]
        u = np.zeros(nd); u[free] = np.linalg.solve(K[np.ix_(free, free)], F[free])
        out = {}
        for bi, b in enumerate(self.beams):
            o = off[bi]; w = u[o:o + 2 * len(b["y"]):2]
            y = b["y"]; EI = np.array([b["EI"](v) if callable(b["EI"]) else b["EI"] for v in y])
            curv = np.gradient(np.gradient(w, y), y)
            out[b["name"]] = dict(y=y, w=w, M=EI * curv)      # w > 0 in the load direction (towards the parts)
        out["bodies"] = {B["name"]: (u[boff + 2 * j], u[boff + 2 * j + 1]) for j, B in enumerate(self.bodies)}
        return out


def composite_EI(layers):
    """layers bottom->top: (t, E, nu); plate moduli E/(1-nu^2); per unit width"""
    Ep = [E / (1 - nu ** 2) for (_, E, nu) in layers]; z = 0.0; zc = []; A = 0.0; S = 0.0
    for (t, _, _), e in zip(layers, Ep): zc.append(z + t / 2); A += e * t; S += e * t * (z + t / 2); z += t
    zn = S / A
    return sum(e * (t ** 3 / 12 + t * (c - zn) ** 2) for (t, _, _), e, c in zip(layers, Ep, zc))


def bead_k(E, w, t):
    """compression stiffness per mm of bearing width (N/mm per mm per mm): long strip bead, shape factor S = w / (2 t), Ec = E (1 + 2 S^2)"""
    S = w / (2 * t); return E * (1 + 2 * S * S) / t


# --------------------------------------------------------------------------------- shared rib (insert on posts) and rail
ins_h = Z.insert1 - Z.insert0; ins_b = G.INSERT["y1"] - G.INSERT["y0"]
pg_rib = max(np.diff(G.POST_X)); pg_rail = max(np.diff(G.RAIL_POST_X))
I_ins = ins_b * ins_h ** 3 / 12
k_rib = 384 * SS["E"] * I_ins / (5 * pg_rib ** 4)                 # N/mm per mm (peak sag between posts, uniform load)
beta = 0.196 + (0.229 - 0.196) * (ins_h / ins_b - 1.5) / 0.5       # torsion constant factor, b/t 1.5..2
J_ins = beta * ins_h * ins_b ** 3
kt_rib = 8 * SS["G"] * J_ins / pg_rib ** 2                         # N mm / rad per mm (twist between posts, posts fixed in twist)
rail_h = Z.win_seat - Z.rail0; rail_b = G.RAIL["y1"] - G.RAIL["y0"]
k_rail = 384 * LCP_E * (rail_b * rail_h ** 3 / 12) / (5 * pg_rail ** 4)
K_RAIL_LCP = k_rail; K_RAIL_SS = k_rail * SS["E"] / LCP_E          # [S2b M-2] stainless section (outside the antenna buffer) = the design
k_rail = K_RAIL_SS
post_F = None
R["supports"] = dict(rib_insert_mm=[ins_b, round(ins_h, 3)], rib_post_gap_mm=pg_rib, k_rib_N_per_mm2=round(k_rib, 1), kt_rib_Nmm_per_rad_mm=round(kt_rib, 0),
                     rail_mm=[round(rail_b, 2), round(rail_h, 3)], rail_post_gap_mm=pg_rail, k_rail_N_per_mm2=round(k_rail, 1),
                     note="E: peak sag between posts used as a uniform spring (conservative); insert height grows with the 0.15 raise (S2a)")

# --------------------------------------------------------------------------------- case 5 first (gaps feed cases 1, 2, 4)
def chain(name, terms, req, limit, rng):
    mean = sum(s * 0.5 * (lo + hi) for (_, s, (lo, hi)) in terms)
    t = [0.5 * (hi - lo) for (_, _, (lo, hi)) in terms]
    wc_t, rss_t = sum(t), math.sqrt(sum(x * x for x in t))
    x = np.zeros(200_000)
    for (_, s, (lo, hi)) in terms: x += s * rng.uniform(lo, hi, x.size)
    wc, rss = (mean - wc_t, mean - rss_t) if req == ">=" else (mean + wc_t, mean + rss_t)
    ok = (lambda v: v >= limit - 1e-9) if req == ">=" else (lambda v: v <= limit + 1e-9)
    pf = float((x < limit - 1e-12).mean()) if req == ">=" else float((x > limit + 1e-12).mean())
    return dict(name=name, req=f"{req} {limit:g}", mean=round(mean, 4), wc=round(wc, 4), rss=round(rss, 4), pass_wc=bool(ok(wc)), pass_rss=bool(ok(rss)),
                mc_fail=round(pf, 4), terms=[[l, s, round(lo, 4), round(hi, 4)] for (l, s, (lo, hi)) in terms])


def sym(n, t): return (n - t, n + t)


rng = np.random.default_rng(14)
sup_h = Z.panel0 - Z.pcb1                          # board top -> panel underside (legs + band), 1.15 with the raise
seat_h = Z.win_seat - Z.pcb1                       # board top -> window frame seat (rib insert top / rail top), 1.905
bond, frame_t = Z.frame0 - Z.win_seat, Z.frame1 - Z.frame0
FLAT = ("board local flatness between posts / legs", -1, sym(0, 0.03))
ST = {}
ST["W1_window_film_to_panel_gap"] = chain("W1 window: film (under the glass) -> panel front, air gap [S2b: seat +0.09, precision tolerances M-2]", [
    ("rail / rib-insert seat (precision +-0.02)", +1, sym(seat_h, 0.02)), ("bond line with spacer beads +-0.03", +1, sym(bond, 0.03)),
    ("frame +-0.02", +1, sym(frame_t, 0.02)), ("film + OCA +-0.02 (RFQ)", -1, sym(0.22, 0.02)), ("support legs + band (precision +-0.02)", -1, sym(sup_h, 0.02)),
    ("LS011B7DH03 0.745 +-0.11", -1, sym(0.745, 0.11)), FLAT], ">=", 0.0, rng)
ST["W2_ZIF_to_panel"] = chain("W2 J13 ZIF top -> panel underside [S2b M-4: legs +-0.02, FH34SRJ 1.0 as a maximum]", [
    ("support legs + band +-0.02", +1, sym(sup_h, 0.02)),
    ("FH34SRJ height 0.95-1.00 (1.0 as max, connector RFQ to confirm)", -1, (0.95, 1.0)),
    ("solder standoff 0.02-0.08", -1, (0.02, 0.08)), FLAT], ">=", 0.0, rng)
ST["W3_low_parts_to_support"] = chain("W3 low parts (<= 0.70 body + 0.05 solder, max) -> support band underside", [
    ("support legs, board -> band underside +-0.05", +1, sym(Z.sup0 - Z.pcb1, 0.05)),
    ("low-zone part + solder at its (raised) maximum", -1, (Z.parts_low - Z.pcb1,) * 2), FLAT], ">=", 0.0, rng)
zr = G.FPC_Z_RETURN - Z.pcb1
ST["W4_display_FPC_fold_Rin"] = chain("W4 display FPC fold inner radius (rule >= 0.45)", [
    ("half of: support legs + band +-0.05", +1, sym(sup_h / 2, 0.025)), ("half of: bottom Pol + TFT 0.365 +-0.05", +1, sym(0.365 / 2, 0.025)),
    ("half of: tape 0.05 +-0.01", -1, sym(zr / 2, 0.005)), ("half of: FPC 0.10 +-0.03", -1, sym(G.FPC["t"] / 2, 0.015)),
    ("half of: board flatness", -1, sym(0, 0.015))], ">=", G.FPC["r_in_min"], rng)


def pv_chains(bead_tol, dz=0.0):
    ring = Z.pv_seat - Z.floor1 + dz
    p1 = chain("P1 PV laminate underside -> tallest part", [
        ("ring floor top -> PV seat 2.20 +-0.05" + (f" (+{dz:g} raise)" if dz else ""), +1, sym(ring, 0.05)),
        (f"lid bond line 0.20 +-{bead_tol:g}", +1, sym(Z.pv0 - Z.pv_seat, bead_tol)),
        ("carrier film 0.10 +-0.02", -1, sym(0.10, 0.02)), ("PCB 1.0 +-0.1 (JLC)", -1, sym(1.0, 0.1)),
        ("tallest part + solder 0.95-1.05", -1, (0.95, 1.05)), FLAT], ">=", 0.0, rng)
    p2 = chain("P2 PV laminate underside -> motor top (carrier cut away)", [
        ("ring floor top -> PV seat 2.20 +-0.05" + (f" (+{dz:g} raise)" if dz else ""), +1, sym(ring, 0.05)),
        (f"lid bond line 0.20 +-{bead_tol:g}", +1, sym(Z.pv0 - Z.pv_seat, bead_tol)),
        ("motor PSA 0.05 +-0.01", -1, sym(Z.psa, 0.01)), ("motor 2.0-2.2 (2.1 typ, 2.2 max class)", -1, (2.0, G.MOTOR["h_max"]))], ">=", 0.0, rng)
    p3 = chain("P3 rib PV seat below the ring PV seat -> bond line at the rib must stay >= 0", [
        ("ring floor top -> PV seat +-0.05", +1, sym(ring, 0.05)), ("bond line nominal", +1, sym(Z.pv0 - Z.pv_seat, 0.0)),
        ("carrier film +-0.02", -1, sym(0.10, 0.02)), ("PCB 1.0 +-0.1", -1, sym(1.0, 0.1)),
        ("stainless post 1.0 +-0.02 (board -> insert underside = PC shelf top)", -1, sym(Z.insert0 - Z.pcb1 + dz, 0.02))], ">=", 0.0, rng)
    return p1, p2, p3


ST["P1_PV_lam_to_parts"], ST["P2_PV_lam_to_motor"], ST["P3_rib_bondline"] = pv_chains(0.05)
R["stack"] = ST

# --------------------------------------------------------------------------------- case 1: PV laminate
y_rib_w0, y_rib_w1 = G.Y_LAM0, G.RIB["y1"]                     # laminate bearing on the rib shelf 20.55-21.0
y_ring0 = G.POD_W - G.WALL; y_lam1 = G.POD_W - G.LID_IN          # ring wall inner face 33.0, laminate edge 33.5
y_rib_c = 0.5 * (G.RIB["y0"] + G.RIB["y1"])
y_win0, y_win1 = G.LID_IN, G.Y_WIN1
lam_x = G.lam_outline().bounds; a_pv = (G.E3_BLOCK["x0"] + G.X_LID1) / 2 - (G.X_LAM0 + G.K_BLOCK_IN["x1"]) / 2
film_b = G.film_outline().bounds
fr_y = (film_b[1] - 0.1, film_b[3] + 0.1)                        # frame opening edges (film + 0.1)
EI_win = lambda t: (lambda y: composite_EI([(frame_t, SS["E"], SS["nu"]), (t, GL["E"], GL["nu"])]) if (y < fr_y[0] or y > fr_y[1]) else Dp(GL["E"], GL["nu"], t))
EPX = bead_k(EPOXY_E, 0.45, 0.20)
kt_ring_wall = PC["E"] / (1 - PC["nu"] ** 2) * G.WALL ** 3 / 12 / (Z.pv_seat - Z.floor1)   # ring wall as a cantilever under an end moment


def model(t_pv, t_win, support, qs=1.0, rigid=False):
    """combined strip: window glass (y 0.5-20.45) and PV laminate (y 20.55-33.5) sharing the rib body.
    support: 'bead' (elastic beads under the laminate), 'bond' (rigid epoxy, rotation restraint by rib torsion and ring wall), 'bond_pin' (rigid
    epoxy, no rotation credit). The window always: elastic bead on the ring, structural bond on the rail and the rib insert (BASELINE)."""
    s = Strip(); big = 1e9 if rigid else None
    wv = s.beam("window", y_win0, y_win1, EI_win(t_win)); pv = s.beam("pv", y_rib_w0, y_lam1, Dp(GL["E"], GL["nu"], t_pv))
    kt_r = kt_rib if support == "bond" else 0.0
    rib = s.body("rib", y_rib_c, kw=(big or k_rib), kt=kt_r)
    rail = s.body("rail", 0.5 * (G.RAIL["y0"] + G.RAIL["y1"]), kw=(big or k_rail), kt=0.0)
    ringw = s.body("ring_win", 0.5 * (y_win0 + G.WALL), kw=None, kt=0.0)
    ringp = s.body("ring_pv", 0.5 * (y_ring0 + y_lam1), kw=None, kt=(kt_ring_wall if support == "bond" else 0.0))
    kb_w = 1e9 if rigid else bead_k(BEAD_E, G.WALL - y_win0, bond)
    s.seat(wv, ringw, y_win0, G.WALL, kb_w)
    s.seat(wv, rail, G.RAIL["y0"], G.RAIL["y1"], 1e9 if rigid else EPX)
    s.seat(wv, rib, G.INSERT["y0"], y_win1, 1e9 if rigid else EPX)
    kp = 1e9 if rigid else (bead_k(BEAD_E, y_rib_w1 - y_rib_w0, 0.20) if support == "bead" else EPX)
    s.seat(pv, rib, y_rib_w0, y_rib_w1, kp)
    s.seat(pv, ringp, y_ring0, y_lam1, 1e9 if rigid else (bead_k(BEAD_E, y_lam1 - y_ring0, 0.20) if support == "bead" else EPX))
    return s.solve(qs)


def plate_result(t_pv, t_win, support):
    """deflection per bar (mm) at the worst point over what lies below, with the 2-D correction on the elastic part"""
    full = model(t_pv, t_win, support, 0.1); rig = model(t_pv, t_win, support, 0.1, rigid=True)
    out = {}
    # PV: over the parts / motor (y 21.0 .. board edge)
    Lp = (y_ring0 + y_lam1) / 2 - (y_rib_w0 + y_rib_w1) / 2
    fp = f2d(a_pv, Lp, t_pv, **GL)
    y = full["pv"]["y"]; m = (y >= y_rib_w1) & (y <= G.BOARD["y1"])
    wc = fp * rig["pv"]["w"] + (full["pv"]["w"] - rig["pv"]["w"])
    i = int(np.argmax(np.where(m, wc, -1))); out["pv"] = dict(w_per_bar=float(wc[i]), y_at=float(y[i]), f2d=round(fp, 3), span_mm=[round(a_pv, 2), round(Lp, 3)],
                                                             support_part_per_bar=float((full["pv"]["w"] - rig["pv"]["w"])[i]),
                                                             sigma_MPa_per_bar=float(fp * np.max(np.abs(full["pv"]["M"])) * 6 / t_pv ** 2),
                                                             w_profile=[[round(float(a), 2), round(float(b), 5)] for a, b in zip(y[::10], wc[::10])])
    a_w = G.E3_BLOCK["x0"] - G.WALL; Lw = y_rib_c - 0.5 * (G.RAIL["y0"] + G.RAIL["y1"])
    fw = f2d(a_w, Lw, t_win, **GL)
    y = full["window"]["y"]; m = (y >= G.PANEL["y0"]) & (y <= G.PANEL["y1"])
    wc = fw * rig["window"]["w"] + (full["window"]["w"] - rig["window"]["w"])
    i = int(np.argmax(np.where(m, wc, -1)))
    out["window"] = dict(w_per_bar=float(wc[i]), y_at=float(y[i]), f2d=round(fw, 3), span_mm=[round(a_w, 2), round(Lw, 3)],
                         support_part_per_bar=float((full["window"]["w"] - rig["window"]["w"])[i]),
                         sigma_MPa_per_bar=float(fw * np.max(np.abs(full["window"]["M"])) * 6 / t_win ** 2),
                         rib_sag_per_bar=float(full["bodies"]["rib"][0]), rail_sag_per_bar=float(full["bodies"]["rail"][0]))
    out["pv"]["rib_sag_per_bar"] = float(full["bodies"]["rib"][0])
    return out


gap_mm = dict(pv=Z.pv0 - Z.parts_gen, window=Z.film0 - (Z.panel0 + G.PANEL_NOM["t"] + G.PANEL_NOM["t_tol"]))
GAPS = dict(pv=dict(max_material=gap_mm["pv"], wc=ST["P1_PV_lam_to_parts"]["wc"], rss=ST["P1_PV_lam_to_parts"]["rss"]),
            window=dict(max_material=gap_mm["window"], wc=ST["W1_window_film_to_panel_gap"]["wc"], rss=ST["W1_window_film_to_panel_gap"]["rss"]))


def verdict(pc_mm, pc_wc):
    a = pc_mm >= SF * 5.0; b = pc_wc >= 5.0
    return "PASS" if (a and b) else ("PARTIAL" if (a or b) else "FAIL")


# check against the stage-2a calc basis (28.7 x 12.6 SS, 0.15 gap: 4.15 bar)
R["check_navier_28p7x12p6"] = round(0.15 / navier(28.7, 12.6, 0.50, **GL, q=0.1)[0], 2)
C1 = {}
for sup in ("bead", "bond_pin", "bond"):
    for t in (0.50, 0.55, 0.60):
        r = plate_result(t, 0.70, sup)["pv"]; w = r["w_per_bar"]
        pc = {k: (round(v / w, 2) if v > 0 else 0.0) for k, v in GAPS["pv"].items()}
        C1[f"{sup} t{t:.2f}"] = dict(w_mm_per_bar=round(w, 5), support_part_mm_per_bar=round(r["support_part_per_bar"], 5), contact_bar=pc,
                                     sigma_5bar_MPa=round(r["sigma_MPa_per_bar"] * 5, 0), pv_half_mm=round(Z.pod_pv + (t - 0.50), 3),
                                     verdict=verdict(pc["max_material"], pc["wc"]), f2d=r["f2d"], span=r["span_mm"],
                                     seat_raise_needed_mm=round(max(0.0, SF * 5 * w - GAPS["pv"]["max_material"], 5 * w - GAPS["pv"]["wc"]), 3))
R["case1_pv"] = C1
# chosen fix: bonded (no rotation credit), each glass, with the seat raise needed; then re-run the stack with that raise
FIX1 = {}
for t in (0.50, 0.55, 0.60):
    c = C1[f"bond_pin t{t:.2f}"]; w = c["w_mm_per_bar"]
    dz = math.ceil(max(SF * 5 * w - GAPS["pv"]["max_material"], 5 * w - GAPS["pv"]["wc"]) * 100 + 1e-6) / 100
    p1, p2, p3 = pv_chains(0.05, dz)
    w = c["w_mm_per_bar"]
    FIX1[f"t{t:.2f}"] = dict(seat_raise_mm=dz, pv_half_mm=round(Z.pod_pv + (t - 0.50) + dz, 3), within_window_half=Z.pod_pv + (t - 0.50) + dz <= Z.pod_win + 1e-9,
                             contact_bar_max_material=round((GAPS["pv"]["max_material"] + dz) / w, 2), contact_bar_wc=round(p1["wc"] / w, 2), P1_wc=p1["wc"], P2_wc=p2["wc"],
                             P3_wc=p3["wc"], mass_g=round((t - 0.50) * a_pv * 12.95 * 2.5e-3, 3))
R["case1_fix_bonded_seat_raise"] = FIX1

# --------------------------------------------------------------------------------- case 2: window glass 0.70 on its rigid bond (+0.80 for the record)
C2 = {}
for t in (0.70, 0.80):
    r = plate_result(0.50, t, "bond_pin")["window"]; w = r["w_per_bar"]
    pc = {k: (round(v / w, 2) if v > 0 else 0.0) for k, v in GAPS["window"].items()}
    C2[f"t{t:.2f}"] = dict(w_mm_per_bar=round(w, 5), y_at=round(r["y_at"], 2), support_part_mm_per_bar=round(r["support_part_per_bar"], 5),
                           rail_sag_mm_5bar=round(r["rail_sag_per_bar"] * 5, 4), rib_sag_mm_5bar=round(r["rib_sag_per_bar"] * 5, 4),
                           contact_bar=pc, sigma_5bar_MPa=round(r["sigma_MPa_per_bar"] * 5, 0), f2d=r["f2d"], span=r["span"] if "span" in r else r["span_mm"],
                           verdict=verdict(pc["max_material"], pc["wc"]),
                           seat_raise_needed_mm=round(max(0.0, SF * 5 * w - GAPS["window"]["max_material"], 5 * w - GAPS["window"]["wc"]), 3))
R["case2_window"] = C2
# [S2b] the antenna-buffer section of the rail (X < 11.5) stays GF-LCP (metal rule): same strip with the LCP rail stiffness (conservative: mid-span strip)
k_rail = K_RAIL_LCP
_r = plate_result(0.50, 0.70, "bond_pin")["window"]; _w = _r["w_per_bar"]
_pc = {k: (round(v / _w, 2) if v > 0 else 0.0) for k, v in GAPS["window"].items()}
R["case2_window_LCP_section"] = dict(w_mm_per_bar=round(_w, 5), rail_sag_mm_5bar=round(_r["rail_sag_per_bar"] * 5, 4), contact_bar=_pc, verdict=verdict(_pc["max_material"], _pc["wc"]),
                                     note="GF-LCP rail inside the 5 mm antenna buffer (X 1.1-11.5), evaluated with the mid-span strip (E, conservative)")
for _pg in (2.0, 3.0):
    k_rail = K_RAIL_LCP * (pg_rail / _pg) ** 4
    _w = plate_result(0.50, 0.70, "bond_pin")["window"]["w_per_bar"]
    R["case2_window_LCP_section"][f"posts_{_pg:g}mm"] = {k: (round(v / _w, 2) if v > 0 else 0.0) for k, v in GAPS["window"].items()}
k_rail = K_RAIL_SS
# smallest fix for the window: stiffer rail (stainless core, same section) + precision tolerances on the W1 chain + the seat raise still needed
_k_rail0 = k_rail
W1T = [("rail / rib-insert seat (precision +-0.02)", +1, sym(seat_h, 0.02)), ("bond line with spacer beads +-0.03", +1, sym(bond, 0.03)),
       ("frame +-0.02", +1, sym(frame_t, 0.02)), ("film + OCA +-0.02 (RFQ)", -1, sym(0.22, 0.02)), ("support legs + band (precision +-0.02)", -1, sym(sup_h, 0.02)),
       ("LS011B7DH03 0.745 +-0.11", -1, sym(0.745, 0.11)), FLAT]
w1t = chain("W1 with precision tolerances", W1T, ">=", 0.0, rng)
WF = {}
for lab, kr in (("rail LCP as built", _k_rail0), ("rail stainless core 0.4 x 0.855", _k_rail0 * SS["E"] / LCP_E)):
    k_rail = kr
    for t in (0.70, 0.80):
        w = plate_result(0.50, t, "bond_pin")["window"]["w_per_bar"]
        for tl, wc0 in (("baseline tolerances", ST["W1_window_film_to_panel_gap"]["wc"]), ("precision tolerances", w1t["wc"])):
            dz = math.ceil(max(SF * 5 * w - GAPS["window"]["max_material"], 5 * w - wc0) * 100 + 1e-6) / 100
            WF[f"{lab} | t{t:.2f} | {tl}"] = dict(w_mm_per_bar=round(w, 5), W1_wc=wc0, seat_raise_mm=max(dz, 0.0), window_half_mm=round(Z.pod_win + (t - 0.70) + max(dz, 0.0), 3))
k_rail = _k_rail0
R["case2_fix"] = dict(W1_precision=w1t, variants=WF)
z2 = chain("W2 with precision support legs and the ZIF 1.0 as a maximum", [("support legs + band +-0.02", +1, sym(sup_h, 0.02)),
          ("FH34SRJ height 0.95-1.00 (1.0 as max, to be confirmed)", -1, (0.95, 1.0)), ("solder standoff 0.02-0.08", -1, (0.02, 0.08)), FLAT], ">=", 0.0, rng)
R["case5_fix_W2"] = dict(precision=z2, raise_needed_mm_baseline_tol=round(-ST["W2_ZIF_to_panel"]["wc"], 3))
R["case2_check_stage1_SS_36x14p6"] = round(0.10 / navier(36.0, 14.6, 0.70, **GL, q=0.1)[0], 2)

# --------------------------------------------------------------------------------- case 3: capsule top 0.40 strengthened glass
ca, cb, ct, cg = G.CAPSULE["L"] - 1.0, G.CAPSULE["w"] - 2 * G.CAPSULE["side"], G.CAPSULE["top"], G.CAPSULE["gap"]
C3 = {}
for lab, patch in (("spread", None), ("thumb_15mm", (min(15 * math.sqrt(math.pi) / 2, ca), min(15 * math.sqrt(math.pi) / 2, cb))),
                   ("probe_5mm", (5 * math.sqrt(math.pi) / 2,) * 2)):
    area = ca * cb if patch is None else patch[0] * patch[1]
    w, s = navier(ca, cb, ct, **GL, q=30.0 / area, patch=patch, terms=199)
    C3[lab] = dict(patch_mm=[round(v, 2) for v in (patch or (ca, cb))], w_30N_mm=round(w, 4), sigma_30N_MPa=round(s, 0),
                   force_to_touch_cell_N=round(30 * cg / w, 1), verdict="PASS" if 30 * cg / w >= SF * 30 else "FAIL")
w1, s1 = navier(ca, cb, ct, **GL, q=0.1)
C3["5bar"] = dict(contact_bar_SS=round(cg / w1, 2), sigma_5bar_MPa=round(s1 * 5, 0), verdict="PASS" if cg / w1 >= SF * 5 else "FAIL",
                  t_needed_for_SF_mm=round(ct * (SF * 5 / (cg / w1)) ** (1 / 3), 3))
w1b = navier(ca, cb, 0.50, **GL, q=0.1)[0]
C3["5bar_fix_t0.50"] = dict(contact_bar_SS=round(cg / w1b, 2), probe_force_to_touch_N=round(30 * cg / navier(ca, cb, 0.50, **GL, q=30.0 / C3["probe_5mm"]["patch_mm"][0] ** 2, patch=tuple(C3["probe_5mm"]["patch_mm"]), terms=199)[0], 1),
                            capsule_t_mm=G.CAPSULE["t"] + 0.10)
R["case3_capsule"] = dict(span_mm=[ca, cb], **C3)

# --------------------------------------------------------------------------------- case 4: floor film over the motor cut-out; button membrane
rc = G.MOTOR["cut_d"] / 2; rm = G.MOTOR["d"] / 2; F_m = P5 * math.pi * rc ** 2
C4 = dict(force_on_motor_N_5bar=round(F_m, 1))
Dpc = Dp(PC["E"], PC["nu"], Z.floor1); Dti = Dp(TI["E"], TI["nu"], Z.floor1)
C4["film_unsupported_clamped_mm"] = round(P5 * rc ** 4 / (64 * Dpc), 3)
for lab, ann in (("centred", rc - rm), ("eccentric_worst", 2 * (rc - G.MOTOR["d_max"] / 2))):
    Lb = ann; qline = F_m / (2 * math.pi * (rm + Lb / 2))     # annulus between the motor edge and the board / carrier edge, as a guided strip
    wb = qline * Lb ** 3 / (12 * Dpc) + qline * Lb / (5 / 6 * PC["E"] / (2 * (1 + PC["nu"])) * Z.floor1)
    sb = 6 * qline * Lb / 2 / Z.floor1 ** 2
    C4[f"motor_as_boss_{lab}"] = dict(annulus_mm=round(Lb, 3), motor_rise_mm_5bar=round(wb, 4), film_stress_MPa=round(sb, 1))
C4["Ti_disc_0p25_clamped_mm"] = round(P5 * rc ** 4 / (64 * Dti), 3); C4["Ti_disc_0p25_SS_mm"] = round(P5 * rc ** 4 * (5 + TI["nu"]) / (64 * (1 + TI["nu"]) * Dti), 3)
mem = G.MEMBRANE; A_mem = (mem["y1"] - mem["y0"]) * (mem["z1"] - mem["z0"])
C4["membrane"] = dict(window_mm=[round(mem["y1"] - mem["y0"], 2), round(mem["z1"] - mem["z0"], 2)], force_5bar_N=round(P5 * A_mem, 2), PTS840_operating_N=2.2,
                      switch_held_pressed=P5 * A_mem > 2.2, bar_at_actuation=round(2.2 / A_mem * 10, 2))
R["case4_floor_membrane"] = C4

# --------------------------------------------------------------------------------- case 6: 1 m drop, edge / corner crush of the PC lip before the glass edge
g = 9.81; m_pod = 10.49e-3; m_worn = 20.67e-3                                     # [S2b] CAD masses, stage 2b [mass json: pod 10.49, worn line 20.67]


def crush_depth(E_Nmm, theta, L=None, Rc=None):
    """PC lip crush depth (mm) to absorb E_Nmm: straight edge of length L, or a plan corner of radius Rc (chord 2 sqrt(2 Rc d))"""
    k = math.sin(2 * theta) / H_PC
    if L: return math.sqrt(E_Nmm * k / L)
    lo, hi = 1e-4, 5.0
    for _ in range(80):
        d = 0.5 * (lo + hi); V = (2 * math.sqrt(2 * Rc * d)) * d * d / 1.67   # approx. volume of a crushed rounded 90 deg edge (paraboloid factor)
        lo, hi = (d, hi) if V / k < E_Nmm else (lo, d)
    return d


C6 = {}
M_CAPS = 2.75e-3 + 0.093e-3 + 0.010e-3                                         # [S2b] capsule + glass 0.40 -> 0.50 (+0.093 g) + shell (+0.01 g), CAD
for lab, m in (("capsule_only_2p75g", M_CAPS), ("pod_only", m_pod), ("whole_band", m_worn)):
    E = m * g * 1.0 * 1e3                                                          # N mm
    rows = {}
    for th in (30, 45, 60, 75):
        t_ = math.radians(th)
        rows[f"{th}deg"] = dict(window_edge_line_mm=round(crush_depth(E, t_, L=41 - 2 * G.CASE_R), 3), window_corner_R6_mm=round(crush_depth(E, t_, Rc=G.CASE_R), 3),
                                window_glass_edge_clear_mm=round(G.LID_IN * math.sin(t_), 3),
                                capsule_corner_R1_mm=round(crush_depth(E, t_, Rc=1.0), 3), capsule_glass_edge_clear_mm=round(1.0 * math.sin(t_), 3))
    C6[lab] = dict(energy_J=round(E / 1e3, 3), by_angle=rows)
need = 0.0
for th in (30, 45, 60, 75):
    t_ = math.radians(th); need = max(need, crush_depth(m_pod * g * 1e3, t_, Rc=G.CASE_R) / math.sin(t_))
C6["window_setback_needed_mm_pod_only"] = round(need, 2)
C6["corner_bumper_proud_needed_mm_pod_only"] = round(max((crush_depth(m_pod * g * 1e3, math.radians(th), Rc=G.CASE_R) - G.LID_IN * math.sin(math.radians(th))) / math.cos(math.radians(th)) for th in (30, 45, 60, 75)), 2)
C6["S2b_bumper_mm"] = G.BUMPER
C6["S2b_R6_corner_margin_mm_pod_only"] = {f"{th}deg": round(G.LID_IN * math.sin(math.radians(th)) + G.BUMPER * math.cos(math.radians(th)) - crush_depth(m_pod * g * 1e3, math.radians(th), Rc=G.CASE_R), 3)
                                           for th in (30, 45, 60, 75)}
C6["S2b_R6_corner_margin_mm_whole_band"] = {f"{th}deg": round(G.LID_IN * math.sin(math.radians(th)) + G.BUMPER * math.cos(math.radians(th)) - crush_depth(m_worn * g * 1e3, math.radians(th), Rc=G.CASE_R), 3)
                                             for th in (30, 45, 60, 75)}
R["case6_drop"] = C6

# --------------------------------------------------------------------------------- case 7: root-A flex at the bar hinge
WR = json.load(open("/path/to/SolarVest_work/wristband/v3/cad/out/options/L41W34_fold1p9_fpcdwg_jointzif_raise0p15/worn_checks_L41W34_fold1p9_fpcdwg_jointzif_raise0p15.json"))["wrists"]
tilts = {k: v["tilt_deg"] for k, v in WR.items()}
Lh = G.CAPSULE["s0"]; tilt_mid = 0.5 * (max(tilts.values()) + min(tilts.values())); dstat = 0.5 * (max(tilts.values()) - min(tilts.values()))
t_cu, e_cu = 0.018, 0.010                                                        # [E] Cu 18 um; Cu centre to the flex's own neutral axis (PI 25 / adh / Cu / cover)
eps = lambda dth_deg: (e_cu + t_cu / 2) * math.radians(dth_deg) / Lh
C7 = dict(hinge_len_mm=Lh, tilts_deg=tilts, moulded_angle_deg=round(tilt_mid, 1),
          static_R_mm={k: round(Lh / math.radians(v), 2) for k, v in tilts.items()}, fit_offset_deg=round(dstat, 1),
          R_fit_offset_mm=round(Lh / math.radians(dstat), 2), wear_cycle_deg=10.0, R_wear_cycle_mm=round(Lh / math.radians(10.0), 2),
          IPC2223_dynamic_1layer_min_R_mm=round(100 * 0.07, 2), IPC2223_static_1layer_min_R_mm=round(6 * 0.07, 2),
          cu_strain_amplitude_wear_pct=round(eps(10.0) * 100, 3), cu_strain_fit_pct=round(eps(dstat) * 100, 3),
          cu_strain_full_bend_from_flat_pct=round(eps(max(tilts.values())) * 100, 3), RA_cu_limit_1e5_pct=0.30,
          note="E: the 0.07 mm PI/Cu flex is ~60x stiffer in tension than the 1.2 mm TPU around it, so it bends about its own neutral axis wherever it sits in the TPU")
C7["verdict"] = "PASS" if (C7["R_wear_cycle_mm"] >= C7["IPC2223_dynamic_1layer_min_R_mm"] and C7["cu_strain_amplitude_wear_pct"] <= 0.30) else "FAIL"
R["case7_flex_hinge"] = C7

R["inputs"] = dict(tag=G.TAG, Z={k: getattr(Z, k) for k in ("floor1", "pcb1", "parts_gen", "parts_low", "pv_seat", "pv0", "pv1", "sup0", "panel0", "film0", "win0", "win1",
                                                              "win_seat", "frame0", "frame1", "insert0", "insert1", "rail0")},
                   pod_pv=Z.pod_pv, pod_win=Z.pod_win, gaps=GAPS, SF=SF, bead_E_MPa=BEAD_E, k_bead_pv=round(bead_k(BEAD_E, 0.45, 0.20), 1), k_epoxy=round(EPX, 0),
                   kt_ring_wall=round(kt_ring_wall, 1), frame_opening_y=fr_y, a_pv=a_pv)
json.dump(R, open(os.path.join(HERE, "mech_raw_s2b.json"), "w"), indent=1, default=float)
for k, v in R.items():
    if k in ("inputs",): continue
    print("==", k); print(json.dumps(v, default=float)[:3000])
