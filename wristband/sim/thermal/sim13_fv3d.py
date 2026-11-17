"""SIM-13  3-D finite-volume steady-state thermal model of the SolarBand in sun.

Geometry from mech/geom_v0.py (same numbers as the build123d enclosure v0), materials/BCs from materials.py.
Rectilinear non-uniform grid, cell-centred FV, orthotropic k (xy / z), Robin BCs:
  top (lens + frame rim)  : forced convection + linearised radiation to T_amb
  sides                   : forced convection + linearised radiation to T_amb
  bottom, in skin contact : contact conductance 1/R_c to T_skin
  bottom, not in contact  : air-gap conduction k_air/d(y) + radiation to T_skin (d from a 35 mm wrist cylinder)
Solar heat: lens bulk absorption, black print on the lens underside (everything except the cells), PV cells
(minus the electrical power when harvesting), frame rim. Board losses from the harvester / shunt path.

usage: python sim13_fv3d.py [--quick]      (results -> out/fv3d_*.json, png)
"""
import argparse, json, math, os, sys, time
import numpy as np
import scipy.sparse as sp

HERE = os.path.dirname(os.path.abspath(__file__))
WB = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(WB, "mech"))
sys.path.insert(0, os.path.join(WB, "envs", "pylib"))
import geom_v0 as G                                    # noqa: E402
from materials import MAT, SOLAR, PV, ENV, h_rad      # noqa: E402

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)
MATS = list(MAT.keys())
MID = {m: i for i, m in enumerate(MATS)}
VOID = -1


# ------------------------------------------------------------------------------------------- helpers
def in_rrect(x, y, x0, y0, L, W, R):
    """Vectorised point-in-rounded-rectangle (corner radius R)."""
    x1, y1 = x0 + L, y0 + W
    inside = (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
    cx = np.clip(x, x0 + R, x1 - R)
    cy = np.clip(y, y0 + R, y1 - R)
    return inside & ((x - cx) ** 2 + (y - cy) ** 2 <= R * R + 1e-12)


def in_rect(x, y, x0, y0, x1, y1):
    return (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)


def ctr(d, key="cx", ykey="cy"):
    return d[key] - d["L"] / 2, d[ykey] - d["W"] / 2


def make_axis(breaks, lo, hi, dmax_fn, merge=0.02):
    b = sorted(set([round(v, 4) for v in breaks if lo - 1e-9 <= v <= hi + 1e-9] + [lo, hi]))
    bb = [b[0]]
    for v in b[1:]:
        if v - bb[-1] > merge:
            bb.append(v)
    bb[-1] = hi
    edges = [bb[0]]
    for a, c in zip(bb[:-1], bb[1:]):
        dm = dmax_fn(0.5 * (a + c))
        n = max(1, int(math.ceil((c - a) / dm - 1e-9)))
        edges += list(np.linspace(a, c, n + 1)[1:])
    return np.array(edges)


# --------------------------------------------------------------------------------------------- model
DEFAULT = dict(
    G=SOLAR["G"], T_amb=ENV["T_amb"], T_skin=ENV["T_skin"], R_c=ENV["R_contact"], h_top=ENV["h_top"],
    h_side=ENV["h_side"], indent=ENV["indent"], alpha_frame=SOLAR["alpha_frame"], alpha_print=SOLAR["alpha_print"],
    alpha_cell=SOLAR["alpha_cell"], mode="shorted",       # 'shorted' (W-C / PV_INH / inhibit), 'harvest' (W-S MPP), 'open'
    t_cell=G.Z.t_cell,        # PV cell thickness (1.2 nominal, 1.5 max -> lens gap 0.21)
    p_win=0.25,               # PPG window protrusion above the shell inner face (SIM-14 result)
    window_mat="resin",       # rev b: one-piece moulded PC window insert (SIM-14 V0-PRODUCT-W); "glass" = ARCH glass window
    k_override={"gap_pad": (5.0, 5.0)},   # merged with case overrides; gap pad 5 W/mK (design E)
    cavity_fill=None,         # None or (material, region) to test a thermal filler between PCB and back shell
    tissue=None,              # reserved
    dmax=0.5, dfine=0.25,
    island=7.0,               # L1 copper island edge, mm            (design E; ARCH R-THERM-1 v0 was 6/5/0.4/3 W/mK)
    pedestal=6.0,             # 316L pedestal edge on the back of E1, mm
    pad_t=0.20,               # gap-pad thickness between pedestal and island, mm (pedestal top = F.Cu - pad_t)
    slot=True,                # 1.0 mm NPTH slot ring around the island keep-out, 4 x 1 mm bridges
    foam_hole=True,           # air pocket (no foam) in foam A above the island keep-out
    pennes=None,              # None or dict(omega=1/s, T_a=C): replace the fixed 34 C skin by 1-D perfused tissue
    tissue_R=None,            # m2K/W effective tissue resistance (2-D Pennes, sim13_tissue2d.py), in series with R_c
)


class Band:
    def __init__(self, **kw):
        self.p = dict(DEFAULT)
        ko = dict(DEFAULT["k_override"]); ko.update(kw.pop("k_override", {}))
        self.p.update(kw)
        self.p["k_override"] = ko
        if self.p["pennes"]:
            # 1-D Pennes tissue behind the contact: q = (T_s - T_a) k m, m = sqrt(omega rho c / k)  [skin/fat avg k 0.37]
            pe = self.p["pennes"]
            km = 0.37 * math.sqrt(pe["omega"] * 4.0e6 / 0.37)
            self.p["R_tissue"] = 1.0 / km
            self.p["T_skin"] = pe["T_a"]
        else:
            self.p["R_tissue"] = 0.0
        if self.p.get("tissue_R"):
            # 2-D perfused-tissue effective resistance from sim13_tissue2d.py (T_skin = occluded-patch reference)
            self.p["R_tissue"] = self.p["tissue_R"]
        self.z = G.Z
        self._grid()
        self._materials()

    # -------------------------------------------------------------------------------------- grid
    def _grid(self):
        p, z = self.p, self.z
        xb = [0, G.WALL, 40 - G.WALL, G.BOARD_X0, G.BOARD_X0 + G.BOARD_L, G.LENS_LIP, 40 - G.LENS_LIP,
              G.LENS_LIP + G.LENS_LEDGE, 40 - G.LENS_LIP - G.LENS_LEDGE, 3.7, 36.3]
        yb = [0, G.WALL, 32 - G.WALL, G.BOARD_Y0, G.BOARD_Y0 + G.BOARD_W, G.LENS_LIP, 32 - G.LENS_LIP,
              G.LENS_LIP + G.LENS_LEDGE, 32 - G.LENS_LIP - G.LENS_LEDGE]
        rects = [G.PV_BOARD, G.BATTERY] + G.PV_CELLS
        for r in rects:
            xb += [r["x0"], r["x0"] + r["L"]]
            yb += [r["y0"], r["y0"] + r["W"]]
        for c in (G.MESA, G.WINDOW, G.E1, G.E2):
            x0, y0 = ctr(c)
            xb += [x0, x0 + c["L"]]
            yb += [y0, y0 + c["W"]]
        tx, ty = G.TMP117_XY
        for s in (p["island"], p["island"] + 1.0, p["island"] + 3.0, p["pedestal"], 2.0, 2.4):
            xb += [tx - s / 2, tx + s / 2]
            yb += [ty - s / 2, ty + s / 2]
        for zz in G.TALL_ZONE + [G.IFA_KEEPOUT]:
            xb += [zz["x0"], zz["x1"]]
            yb += [zz["y0"], zz["y1"]]
        for (_, _, cx, cy, L, W, _) in G.PARTS:
            xb += [cx - L / 2, cx + L / 2]
            yb += [cy - W / 2, cy + W / 2]
        for q in G.PPG_PARTS:
            xb += [q["cx"] - q["L"] / 2, q["cx"] + q["L"] / 2]
            yb += [q["cy"] - q["W"] / 2, q["cy"] + q["W"] / 2]
        for (sx, sy) in G.STANDOFFS:
            xb += [sx - G.STANDOFF_D / 2, sx + G.STANDOFF_D / 2]
            yb += [sy - G.STANDOFF_D / 2, sy + G.STANDOFF_D / 2]
        wi = G.WINDOW_INSERT                                   # rev b: PPG window insert flange + legs
        xb += [G.WINDOW["cx"] - wi["flange_L"] / 2, G.WINDOW["cx"] + wi["flange_L"] / 2]
        yb += [G.WINDOW["cy"] - wi["flange_W"] / 2, G.WINDOW["cy"] + wi["flange_W"] / 2]
        for (lx, ly) in wi["legs"]:
            xb += [lx - wi["leg_d"] / 2, lx + wi["leg_d"] / 2]
            yb += [ly - wi["leg_d"] / 2, ly + wi["leg_d"] / 2]
        fine_x = (tx - 5, tx + 5)
        fine_y = (ty - 5, ty + 5)
        dm, df = p["dmax"], p["dfine"]
        self.xe = make_axis(xb, 0, 40, lambda v: df if fine_x[0] <= v <= fine_x[1] else dm)
        self.ye = make_axis(yb, 0, 32, lambda v: df if fine_y[0] <= v <= fine_y[1] else dm)
        zcell_top = z.z_pvb_top + z.joint_snbi + p["t_cell"]
        self.z_cell_top = zcell_top
        self.z_lens_bot = z.z_lens_bot
        self.z_top = z.z_top
        hs = sorted(set(round(G.HEIGHTS[k]["h"][1], 2) for k in [q[1] for q in G.PARTS] + [q["hkey"] for q in G.PPG_PARTS]))
        zb = [-G.MESA["h"], -G.TALL_POCKET, -G.ELECTRODE_PROUD, 0.0, z.t_backshell - G.TALL_POCKET,
              G.ELECTRODE_T - G.ELECTRODE_PROUD, z.z_shell_in, z.z_shell_in + p["p_win"], 0.9, z.z_fcu - p["pad_t"],
              z.z_fcu, z.z_fcu + 0.05, z.z_l6, z.z_batt_bot, z.z_batt_top, z.z_pvb_bot - 0.7, z.z_shell_in - 0.15,
              z.z_pvb_bot, z.z_pvb_top, z.z_pvb_top + z.joint_snbi, zcell_top, z.z_ledge - 0.6, z.z_ledge,
              self.z_lens_bot, self.z_top] + [z.z_fcu - h for h in hs]
        self.ze = make_axis(zb, -G.MESA["h"], self.z_top, lambda v: 0.5 if z.z_batt_bot < v < z.z_batt_top else 0.25)
        self.xc = 0.5 * (self.xe[1:] + self.xe[:-1]); self.dx = np.diff(self.xe)
        self.yc = 0.5 * (self.ye[1:] + self.ye[:-1]); self.dy = np.diff(self.ye)
        self.zc = 0.5 * (self.ze[1:] + self.ze[:-1]); self.dz = np.diff(self.ze)
        self.shape = (len(self.xc), len(self.yc), len(self.zc))

    # --------------------------------------------------------------------------------- materials
    def _materials(self):
        p, z = self.p, self.z
        X, Y, Zc = np.meshgrid(self.xc, self.yc, self.zc, indexing="ij")
        X2, Y2 = X[:, :, 0], Y[:, :, 0]
        M = np.full(self.shape, VOID, dtype=np.int16)

        def setm(mask3, name):
            M[mask3] = MID[name]

        def plan(mask2):
            return np.broadcast_to(mask2[:, :, None], self.shape)

        def zr(a, b):
            return (Zc >= a) & (Zc < b)

        case = in_rrect(X2, Y2, 0, 0, 40, 32, G.CASE_R)
        cav = in_rrect(X2, Y2, G.WALL, G.WALL, 40 - 2 * G.WALL, 32 - 2 * G.WALL, G.CAV_R)
        lens = in_rrect(X2, Y2, G.LENS_LIP, G.LENS_LIP, G.LENS["L"], G.LENS["W"], G.LENS["R"])
        ap = in_rrect(X2, Y2, G.LENS_LIP + G.LENS_LEDGE, G.LENS_LIP + G.LENS_LEDGE, G.APERTURE["L"], G.APERTURE["W"], G.APERTURE["R"])
        mx0, my0 = ctr(G.MESA); mesa = in_rrect(X2, Y2, mx0, my0, G.MESA["L"], G.MESA["W"], G.MESA["R"])
        wx0, wy0 = ctr(G.WINDOW); win = in_rrect(X2, Y2, wx0, wy0, G.WINDOW["L"], G.WINDOW["W"], G.WINDOW["R"])
        e1x, e1y = ctr(G.E1); e1 = in_rrect(X2, Y2, e1x, e1y, G.E1["L"], G.E1["W"], G.E1["R"])
        e2x, e2y = ctr(G.E2); e2 = in_rrect(X2, Y2, e2x, e2y, G.E2["L"], G.E2["W"], G.E2["R"])
        tall = np.zeros_like(case)
        for t in G.TALL_ZONE:
            tall |= in_rect(X2, Y2, t["x0"], t["y0"], t["x1"], t["y1"])
        tall &= cav
        lpk = np.zeros_like(case)
        for t in G.LOCAL_POCKETS:
            lpk |= in_rect(X2, Y2, t["x0"], t["y0"], t["x1"], t["y1"])
        tx, ty = G.TMP117_XY

        def sq(s, cx=tx, cy=ty):
            return in_rect(X2, Y2, cx - s / 2, cy - s / 2, cx + s / 2, cy + s / 2)

        ped, recess, pkg = sq(p["pedestal"]), sq(2.4), sq(2.0)
        island, ko = sq(p["island"]), sq(p["island"] + 1.0)
        slotring = sq(p["island"] + 3.0) & ~ko          # 1.0 mm NPTH slot (JLC minimum non-plated slot width)
        board = in_rrect(X2, Y2, G.BOARD_X0, G.BOARD_Y0, G.BOARD_L, G.BOARD_W, G.BOARD_R)
        batt = in_rect(X2, Y2, G.BATTERY["x0"], G.BATTERY["y0"], G.BATTERY["x0"] + G.BATTERY["L"], G.BATTERY["y0"] + G.BATTERY["W"])
        pvb = in_rect(X2, Y2, G.PV_BOARD["x0"], G.PV_BOARD["y0"], G.PV_BOARD["x0"] + G.PV_BOARD["L"], G.PV_BOARD["y0"] + G.PV_BOARD["W"])
        cells = np.zeros_like(case)
        for c in G.PV_CELLS:
            cells |= in_rect(X2, Y2, c["x0"], c["y0"], c["x0"] + c["L"], c["y0"] + c["W"])
        ribs = (in_rect(X2, Y2, G.WALL, G.PV_BOARD["y0"], 3.7, G.PV_BOARD["y0"] + G.PV_BOARD["W"]) |
                in_rect(X2, Y2, 36.3, G.PV_BOARD["y0"], 40 - G.WALL, G.PV_BOARD["y0"] + G.PV_BOARD["W"]))
        so = np.zeros_like(case)
        for (sx, sy) in G.STANDOFFS:
            so |= (X2 - sx) ** 2 + (Y2 - sy) ** 2 <= (G.STANDOFF_D / 2) ** 2
        self.masks = dict(case=case, cav=cav, lens=lens, ap=ap, mesa=mesa, win=win, e1=e1, e2=e2, tall=tall,
                          pkg=pkg, island=island, board=board, batt=batt, pvb=pvb, cells=cells)

        zs, zf, zl6 = z.z_shell_in, z.z_fcu, z.z_l6
        zbat0, zbat1 = z.z_batt_bot, z.z_batt_top
        zpv0, zpv1 = z.z_pvb_bot, z.z_pvb_top
        zc0, zc1 = zpv1 + z.joint_snbi, self.z_cell_top
        zlb, ztop = self.z_lens_bot, self.z_top
        ep = G.ELECTRODE_T - G.ELECTRODE_PROUD   # electrode back face (0.3)
        # below Z = 0
        setm(plan(mesa) & zr(-G.MESA["h"], 0), "resin")
        setm(plan(tall) & zr(-G.TALL_POCKET, 0), "resin")
        setm(plan(e1 | e2) & zr(-G.ELECTRODE_PROUD, 0), "steel316")
        # back shell plate and walls (whole height), cavity default air
        setm(plan(case) & zr(0, ztop), "resin")
        setm(plan(cav) & zr(zs, zlb), "air")
        setm(plan(tall) & zr(zs - G.TALL_POCKET, zs), "air")                     # pocket under tall zone
        setm(plan(tall) & zr(-G.TALL_POCKET, zs - G.TALL_POCKET), "resin")
        setm(plan(lpk) & zr(zs - 0.15, zs), "air")                                 # U7 local pocket (0.15)
        setm(plan(e1 | e2) & zr(0, ep), "steel316")
        setm(plan(win) & zr(-G.MESA["h"], zs + p["p_win"]), p["window_mat"])
        wi = G.WINDOW_INSERT                                   # rev b: flange on the shell inner face + 2 legs onto F.Cu
        flange = in_rrect(X2, Y2, G.WINDOW["cx"] - wi["flange_L"] / 2, G.WINDOW["cy"] - wi["flange_W"] / 2, wi["flange_L"],
                          wi["flange_W"], wi["flange_R"]) & ~win
        setm(plan(flange) & zr(zs, zs + p["p_win"]), "resin")
        legs = np.zeros_like(case)
        for (lx, ly) in wi["legs"]:
            legs |= (X2 - lx) ** 2 + (Y2 - ly) ** 2 <= (wi["leg_d"] / 2) ** 2
        setm(plan(legs) & zr(zs + p["p_win"], zf), "resin")
        setm(plan(so & cav) & zr(0, zf), "resin")
        setm(plan(so & cav & tall) & zr(zs - G.TALL_POCKET, zf), "resin")
        # E1 pedestal + gap pad + TMP117
        zpt = zf - p["pad_t"]
        setm(plan(ped) & zr(ep, zpt), "steel316")
        setm(plan(recess) & zr(0.9, zpt), "air")
        setm(plan(ped) & zr(zpt, zf), "gap_pad")
        # parts
        for (ref, hk, cx, cy, L, W, zone) in G.PARTS:
            h = G.HEIGHTS[hk]["h"][1]
            m = in_rect(X2, Y2, cx - L / 2, cy - W / 2, cx + L / 2, cy + W / 2)
            setm(plan(m) & zr(zf - h, zf), "ic")
        for q in G.PPG_PARTS:
            h = G.HEIGHTS[q["hkey"]]["h"][1]
            m = in_rect(X2, Y2, q["cx"] - q["L"] / 2, q["cy"] - q["W"] / 2, q["cx"] + q["L"] / 2, q["cy"] + q["W"] / 2)
            setm(plan(m) & zr(zf - h, zf), "ic")
        if p["cavity_fill"]:
            mat, region = p["cavity_fill"]
            reg = {"board": board, "batt": batt & board}[region]
            sel = plan(reg & ~win & ~ped) & zr(zs, zf) & (M == MID["air"])
            setm(sel, mat)
        # PCB
        setm(plan(board) & zr(zf, zl6), "pcb")
        setm(plan(ko) & zr(zf + 0.05, zl6), "pcb_ko")
        setm(plan(ko & ~island) & zr(zf, zf + 0.05), "pcb_ko")
        setm(plan(island) & zr(zf, zf + 0.05), "cu_island")
        if p["slot"]:
            setm(plan(slotring & board) & zr(zf, zl6), "slot_bridged")
        # battery on 0.15 mm PE-foam tape (cut-out over the TMP117 island); air swelling gap above it
        setm(plan(batt) & zr(zl6, zbat0), "pe_tape")
        if p["foam_hole"]:
            setm(plan(batt & sq(p["island"] + 3.0)) & zr(zl6, zbat0), "air")
        setm(plan(batt) & zr(zbat0, zbat1), "battery")
        setm(plan(ribs) & zr(zpv0 - 0.7, zpv0), "resin")
        setm(plan(pvb) & zr(zpv0, zpv1), "pv_board")
        setm(plan(cells) & zr(zpv1, zc0), "snbi_jnt")
        setm(plan(cells) & zr(zc0, zc1), "pv_cell")
        setm(plan(cav & ~ap) & zr(z.z_ledge - 0.6, z.z_ledge), "resin")             # lens ledge
        setm(plan(lens & ~ap) & zr(z.z_ledge, zlb), "psa")                          # lens PSA ring
        setm(plan(lens) & zr(zlb, ztop), "glass")
        M[~plan(case)] = VOID
        self.M = M
        self.zlev = dict(zc0=zc0, zc1=zc1, zlb=zlb, ztop=ztop, zbat0=zbat0, zbat1=zbat1, zf=zf, ep=ep)

    # ------------------------------------------------------------------------------------ assemble
    def _k(self):
        kxy = np.zeros(len(MATS)); kz = np.zeros(len(MATS)); rc = np.zeros(len(MATS))
        for i, m in enumerate(MATS):
            a = MAT[m]
            kk = self.p["k_override"].get(m, (a[0], a[1]))
            kxy[i], kz[i], rc[i] = kk[0], kk[1], a[2] * a[3]
        Mi = np.where(self.M >= 0, self.M, 0)
        return kxy[Mi], kz[Mi], rc[Mi]

    def sources(self, P_elec_cells, P_board):
        """Heat input [W] per cell. P_board: list of (x, y, W) point loads on the PCB F.Cu side."""
        p = self.p
        Gs = p["G"] * 1e-6          # W per mm2
        Q = np.zeros(self.shape)
        dA = np.outer(self.dx, self.dy)
        msk = self.masks
        lv = self.zlev
        k_lens = np.where((self.zc >= lv["zlb"]) & (self.zc < lv["ztop"]))[0]
        tl = (1 - SOLAR["lens_R_front"])
        T_lens = tl * (1 - SOLAR["lens_abs"]) * (1 - SOLAR["lens_R_back"])
        # lens bulk absorption, spread over the lens thickness
        for k in k_lens:
            Q[:, :, k] += np.where(msk["lens"], Gs * tl * SOLAR["lens_abs"] * dA * self.dz[k] / self.z.t_lens, 0)
        # black print on the lens underside except over the cells
        kb = k_lens[0]
        printed = msk["lens"] & ~msk["cells"]
        Q[:, :, kb] += np.where(printed, Gs * tl * (1 - SOLAR["lens_abs"]) * p["alpha_print"] * dA, 0)
        # PV cells: absorbed in the top cell layer, minus electrical extraction (uniform per area)
        kc = np.where((self.zc >= lv["zc0"]) & (self.zc < lv["zc1"]))[0][-1]
        A_cells = float((dA * msk["cells"]).sum())
        q_cell = Gs * T_lens * p["alpha_cell"] - P_elec_cells / A_cells
        Q[:, :, kc] += np.where(msk["cells"], q_cell * dA, 0)
        # frame rim (top surface outside the lens)
        kt = len(self.zc) - 1
        rim = msk["case"] & ~msk["lens"]
        Q[:, :, kt] += np.where(rim, Gs * p["alpha_frame"] * dA, 0)
        # board point loads (put in the PCB layer just above F.Cu)
        kp = np.where(self.zc > lv["zf"])[0][0]
        for (x, y, w) in P_board:
            i = int(np.searchsorted(self.xe, x) - 1); j = int(np.searchsorted(self.ye, y) - 1)
            Q[i, j, kp] += w
        self.A_cells = A_cells
        self.absorbed = dict(
            lens_bulk=float(sum(Q[:, :, k][msk["lens"]].sum() for k in k_lens[1:])) + float((np.where(msk["lens"], Gs * tl * SOLAR["lens_abs"] * dA * self.dz[kb] / self.z.t_lens, 0)).sum()),
            print=float((np.where(printed, Gs * tl * (1 - SOLAR["lens_abs"]) * p["alpha_print"] * dA, 0)).sum()),
            cells_abs=float(Gs * T_lens * p["alpha_cell"] * A_cells),
            rim=float((np.where(rim, Gs * p["alpha_frame"] * dA, 0)).sum()))
        return Q

    def assemble(self):
        p = self.p
        nx, ny, nz = self.shape
        N = nx * ny * nz
        idx = np.arange(N).reshape(self.shape)
        kxy, kz, rc = self._k()
        solid = self.M >= 0
        rows, cols, vals = [], [], []
        diag = np.zeros(self.shape)
        rhs = np.zeros(self.shape)
        DX = self.dx[:, None, None]; DY = self.dy[None, :, None]; DZ = self.dz[None, None, :]
        self.bc_faces = []      # (mask_array_of_faces, conductance array, T_ref, label)

        # interior conductances, three directions
        for ax in range(3):
            d = [DX, DY, DZ][ax]
            k = kxy if ax < 2 else kz
            sl_a = [slice(None)] * 3; sl_b = [slice(None)] * 3
            sl_a[ax] = slice(0, -1); sl_b[ax] = slice(1, None)
            sl_a, sl_b = tuple(sl_a), tuple(sl_b)
            dfull = np.broadcast_to(d, self.shape)
            area = [DY * DZ, DX * DZ, DX * DY][ax]
            area = np.broadcast_to(area, self.shape)
            Ra = dfull[sl_a] / (2 * k[sl_a]); Rb = dfull[sl_b] / (2 * k[sl_b])
            g = area[sl_a] / (Ra + Rb) * 1e-3        # W/K (mm units: A[mm2]/L[mm] * k -> *1e-3 m)
            both = solid[sl_a] & solid[sl_b]
            g = np.where(both, g, 0)
            ia, ib = idx[sl_a][both], idx[sl_b][both]
            gv = g[both]
            rows += [ia, ib]; cols += [ib, ia]; vals += [-gv, -gv]
            diag[sl_a] += g; diag[sl_b] += g
        # boundary faces: solid cell whose neighbour is void or outside
        Tamb, Tsk = p["T_amb"], p["T_skin"]
        hr_top = h_rad(SOLAR["eps_lens"]); hr_side = h_rad(SOLAR["eps_shell"])
        hr_skin = h_rad(SOLAR["eps_shell"], 37.0, SOLAR["eps_skin"])
        kair = MAT["air"][0] * 0.9          # conduction only for the external gap
        bc = {}
        for ax in range(3):
            for sgn in (-1, 1):
                nb = np.full(self.shape, False)
                sl_in = [slice(None)] * 3; sl_nb = [slice(None)] * 3
                if sgn == 1:
                    sl_in[ax] = slice(0, -1); sl_nb[ax] = slice(1, None)
                    edge = [slice(None)] * 3; edge[ax] = -1
                else:
                    sl_in[ax] = slice(1, None); sl_nb[ax] = slice(0, -1)
                    edge = [slice(None)] * 3; edge[ax] = 0
                nb[tuple(sl_in)] = ~solid[tuple(sl_nb)]
                nb[tuple(edge)] = True
                face = solid & nb
                if not face.any():
                    continue
                d = [DX, DY, DZ][ax]; k = kxy if ax < 2 else kz
                area = np.broadcast_to([DY * DZ, DX * DZ, DX * DY][ax], self.shape)
                Rcell = np.broadcast_to(d, self.shape) / (2 * k) * 1e-3   # m2K/W
                Zf = np.broadcast_to(self.zc[None, None, :], self.shape)
                Yf = np.broadcast_to(self.yc[None, :, None], self.shape)
                if ax == 2 and sgn == 1:
                    h = np.full(self.shape, p["h_top"] + hr_top); Tref = Tamb; lab = "top"
                    hh = h
                elif ax == 2 and sgn == -1:
                    zface = np.broadcast_to(self.ze[None, None, :-1], self.shape)
                    gap = np.vectorize(lambda yy, zz: G.wrist_gap(yy, zz, indent=p["indent"]))(Yf[face], zface[face])
                    hh = np.zeros(self.shape)
                    h_gap = 1.0 / (np.maximum(gap, 0.05) * 1e-3 / kair) + hr_skin
                    hc = np.where(gap <= 1e-6, 1.0 / (p["R_c"] + p["R_tissue"]), 1.0 / (1.0 / h_gap + p["R_tissue"]))
                    hh[face] = hc
                    cont = np.zeros(self.shape, bool); cont[face] = gap <= 1e-6
                    self.contact = cont
                    Tref = Tsk; lab = "bottom"
                else:
                    hh = np.where(Zf >= 0, p["h_side"] + hr_side, 1.0 / (1.0 / (1.0 / (0.3e-3 / kair) + hr_skin) + p["R_tissue"]))
                    Tref = None; lab = "side"
                g = np.where(face, area * 1e-6 / (Rcell + 1.0 / np.maximum(hh, 1e-9)), 0)
                if lab == "side":
                    Tr = np.where(Zf >= 0, Tamb, Tsk)
                else:
                    Tr = np.full(self.shape, Tref)
                diag += g
                rhs += g * Tr
                bc[(ax, sgn)] = (face, g, Tr, lab)
        self.bc = bc
        rows.append(idx[solid]); cols.append(idx[solid]); vals.append(diag[solid])
        # void cells: identity, T = T_amb
        rows.append(idx[~solid]); cols.append(idx[~solid]); vals.append(np.ones((~solid).sum()))
        rhs[~solid] = Tamb
        A = sp.csr_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(N, N))
        self.A, self.rhs_bc, self.idx, self.solid = A, rhs, idx, solid
        self.C = rc * np.broadcast_to(DX * DY * DZ, self.shape) * 1e-9          # J/K
        return A

    def solve(self, Q, x0=None):
        import pyamg
        b = (self.rhs_bc + np.where(self.solid, Q, 0)).ravel()
        if not hasattr(self, "_ml"):
            self._ml = pyamg.smoothed_aggregation_solver(self.A, symmetry="symmetric", max_coarse=500)
        res = []
        x = self._ml.solve(b, x0=x0, tol=1e-10, accel="cg", residuals=res, maxiter=400)
        self.last_res = (len(res), float(np.linalg.norm(b - self.A @ x) / np.linalg.norm(b)))
        return x.reshape(self.shape)

    # --------------------------------------------------------------------------------- run a case
    def run(self):
        p = self.p
        self.assemble()
        T = None
        Tcell = 55.0
        harvest = p["mode"] == "harvest"
        for it in range(8):
            tl = (1 - SOLAR["lens_R_front"]) * (1 - SOLAR["lens_abs"]) * (1 - SOLAR["lens_R_back"])
            irr = p["G"] / 1000.0 * tl
            if harvest:
                P_mpp = PV["P_stc"] * irr * (1 + PV["gamma_P"] * (Tcell - 25))
                I = P_mpp / PV["Vmp"]
                P_bat = PV["eta_harv"] * (P_mpp - I * I * PV["R_sh"]) - PV["P_load"]
                Ib = max(P_bat, 0) / PV["Vbat"]
                P_board = [(12.0, 9.0, (1 - PV["eta_harv"]) * (P_mpp - I * I * PV["R_sh"])),   # U1 + L1/L2
                           (8.0, 4.0, I * I * PV["R_sh"]),                                       # RSH1
                           (28.5, 10.0, PV["P_load"])]                                           # system load
                P_cell_out = P_mpp
                P_batt_heat = Ib * Ib * PV["R_cell_int"]
            elif p["mode"] == "shorted":
                Isc = PV["Isc_stc"] * irr * (1 + PV["alpha_Isc"] * (Tcell - 25))
                P_board = [(8.0, 4.0, Isc * Isc * PV["R_sh"]), (16.0, 4.0, Isc * Isc * PV["R_q1"]),
                           (28.5, 10.0, PV["P_load"])]
                P_cell_out = Isc * Isc * (PV["R_sh"] + PV["R_q1"] + PV["R_wire"])
                P_mpp = 0.0; P_batt_heat = 0.0; Ib = 0.0
            else:  # open circuit / battery full
                P_board = [(28.5, 10.0, PV["P_load"])]
                P_cell_out = 0.0; P_mpp = 0.0; P_batt_heat = 0.0; Ib = 0.0
            Q = self.sources(P_cell_out, P_board)
            if P_batt_heat > 0:
                mb = self.M == MID["battery"]
                Q[mb] += P_batt_heat * self.C[mb] / self.C[mb].sum()
            if p["mode"] == "harvest" or p["mode"] == "shorted":
                pass
            if not harvest:
                P_board_tot = sum(w for (_, _, w) in P_board)
            T = self.solve(Q, None if T is None else T.ravel())
            Tc_new = float(T[self.M == MID["pv_cell"]].mean())
            if abs(Tc_new - Tcell) < 0.02:
                Tcell = Tc_new
                break
            Tcell = Tc_new
        self.T, self.Q = T, Q
        self.elec = dict(P_mpp=P_mpp, P_cell_out=P_cell_out, P_board=sum(w for (_, _, w) in P_board),
                         P_batt_heat=P_batt_heat, I_bat=Ib,
                         P_stored=(PV["eta_harv"] * (P_mpp - (P_mpp / PV["Vmp"]) ** 2 * PV["R_sh"]) - PV["P_load"]) if harvest else 0.0)
        return self.report()

    # ------------------------------------------------------------------------------------- report
    def face_T(self, key):
        face, g, Tr, lab = self.bc[key]
        nx, ny, nz = self.shape
        kxy, kz, _ = self._k()
        ax = key[0]
        d = [self.dx[:, None, None], self.dy[None, :, None], self.dz[None, None, :]][ax]
        k = kxy if ax < 2 else kz
        Rcell = np.broadcast_to(d, self.shape) / (2 * k) * 1e-3
        # flux q = (T - Tr) * g / A ; Tface = T - q * Rcell
        area = np.broadcast_to([self.dy[None, :, None] * self.dz[None, None, :], self.dx[:, None, None] * self.dz[None, None, :],
                                self.dx[:, None, None] * self.dy[None, :, None]][ax], self.shape) * 1e-6
        q = np.where(face, (self.T - Tr) * g / area, 0)
        return np.where(face, self.T - q * Rcell, np.nan), q

    def report(self):
        T, M = self.T, self.M
        r = {}
        # energy balance
        Qin = float(self.Q[self.solid].sum())
        flows = {}
        for key, (face, g, Tr, lab) in self.bc.items():
            f = float(((self.T - Tr) * g)[face].sum())
            if lab == "side":
                Zf = np.broadcast_to(self.zc[None, None, :], self.shape)
                f_amb = float(((self.T - Tr) * g)[face & (Zf >= 0)].sum())
                flows["side_amb"] = flows.get("side_amb", 0) + f_amb
                flows["side_skin"] = flows.get("side_skin", 0) + f - f_amb
            else:
                flows[lab] = flows.get(lab, 0) + f
        r["heat_in_W"] = Qin
        r["heat_out_W"] = flows
        r["balance_err_W"] = Qin - sum(flows.values())
        r["absorbed_W"] = self.absorbed
        r["electrical"] = self.elec
        # bottom faces: skin-contact surface temperatures
        Tf, q = self.face_T((2, -1))
        cont = self.contact
        X = np.broadcast_to(self.xc[:, None, None], self.shape); Y = np.broadcast_to(self.yc[None, :, None], self.shape)
        e1m = np.broadcast_to(self.masks["e1"][:, :, None], self.shape)
        winm = np.broadcast_to(self.masks["win"][:, :, None], self.shape)
        mesam = np.broadcast_to(self.masks["mesa"][:, :, None], self.shape)
        r["skin_contact_max_C"] = float(np.nanmax(np.where(cont, Tf, np.nan)))
        r["skin_contact_mean_C"] = float(np.nanmean(np.where(cont, Tf, np.nan)))
        r["contact_area_mm2"] = float((np.broadcast_to(np.outer(self.dx, self.dy)[:, :, None], self.shape))[cont].sum())
        r["E1_face_mean_C"] = float(np.nanmean(np.where(cont & e1m, Tf, np.nan)))
        r["window_face_max_C"] = float(np.nanmax(np.where(cont & winm, Tf, np.nan)))
        r["noncontact_bottom_max_C"] = float(np.nanmax(np.where(~cont, Tf, np.nan)))
        r["skin_heat_flux_max_W_m2"] = float(np.nanmax(np.where(cont, q, np.nan)))
        # TMP117: package cells (U10) - the die sits on the exposed pad next to the island
        tx, ty = G.TMP117_XY
        pk = (np.broadcast_to(self.masks["pkg"][:, :, None], self.shape) & (M == MID["ic"]))
        zf = self.zlev["zf"]
        pk_top = pk & (np.broadcast_to(self.zc[None, None, :], self.shape) > zf - 0.3)
        r["TMP117_C"] = float(T[pk_top].mean())
        r["TMP117_error_vs_E1_face_K"] = r["TMP117_C"] - r["E1_face_mean_C"]
        r["island_C"] = float(T[M == MID["cu_island"]].mean())
        r["E1_face_max_C"] = float(np.nanmax(np.where(cont & e1m, Tf, np.nan)))
        pedm = np.broadcast_to((np.abs(X[:, :, :1] - tx) <= self.p["pedestal"] / 2) & (np.abs(Y[:, :, :1] - ty) <= self.p["pedestal"] / 2), self.shape)
        r["E1_face_under_pedestal_C"] = float(np.nanmean(np.where(cont & e1m & pedm, Tf, np.nan)))
        r["TMP117_error_vs_skin_contact_max_K"] = r["TMP117_C"] - r["skin_contact_max_C"]
        for ref in ("U6", "U9", "U1"):
            pr = [q for q in G.PARTS if q[0] == ref][0]
            mm = np.broadcast_to(((np.abs(X[:, :, :1] - pr[2]) <= pr[4] / 2) & (np.abs(Y[:, :, :1] - pr[3]) <= pr[5] / 2)), self.shape) & (M == MID["ic"])
            r[f"T_{ref}_C"] = float(T[mm].mean())
        bat = M == MID["battery"]
        r["battery_max_C"] = float(T[bat].max()); r["battery_mean_C"] = float(T[bat].mean())
        r["battery_min_C"] = float(T[bat].min())
        # NTC lead taped to the cell near the PCM / tab end (case X 4.5 end), mid-height, mid-width
        i = int(np.searchsorted(self.xc, G.BATTERY["x0"] + 1.5)); j = int(np.searchsorted(self.yc, G.BATTERY["y0"] + G.BATTERY["W"] / 2))
        kk = np.where(bat[i, j, :])[0]
        r["battery_NTC_C"] = float(T[i, j, kk].mean())
        r["pv_cell_max_C"] = float(T[M == MID["pv_cell"]].max()); r["pv_cell_mean_C"] = float(T[M == MID["pv_cell"]].mean())
        r["lens_top_max_C"] = float(T[:, :, -1][self.masks["lens"]].max())
        r["pcb_mean_C"] = float(T[M == MID["pcb"]].mean()); r["pcb_max_C"] = float(T[M == MID["pcb"]].max())
        ppg = M == MID["ic"]
        r["max_component_C"] = float(T[ppg].max())
        r["grid"] = list(self.shape); r["amg_iters_relres"] = list(self.last_res)
        r["params"] = {k: v for k, v in self.p.items() if k not in ("k_override",)}
        r["params"]["k_override"] = {k: list(v) for k, v in self.p["k_override"].items()}
        return r


# ------------------------------------------------------------------------------------------- plots
def plots(b, tag):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    T, M = b.T, b.M
    Tm = np.where(M >= 0, T, np.nan)
    fig, axs = plt.subplots(2, 2, figsize=(13, 8.5))
    j = int(np.searchsorted(b.yc, G.TMP117_XY[1]))
    ax = axs[0, 0]
    im = ax.pcolormesh(b.xe, b.ze, Tm[:, j, :].T, cmap="inferno", shading="flat")
    ax.set_title(f"XZ section at Y={b.yc[j]:.2f} mm (through E1/TMP117)"); ax.set_xlabel("X mm"); ax.set_ylabel("Z mm")
    ax.set_aspect(1.5); fig.colorbar(im, ax=ax, label="°C")
    i = int(np.searchsorted(b.xc, 20.0))
    ax = axs[0, 1]
    im = ax.pcolormesh(b.ye, b.ze, Tm[i, :, :].T, cmap="inferno", shading="flat")
    ax.set_title(f"YZ section at X={b.xc[i]:.2f} mm (through PPG mesa)"); ax.set_xlabel("Y mm"); ax.set_ylabel("Z mm")
    ax.set_aspect(1.5); fig.colorbar(im, ax=ax, label="°C")
    Tf, q = b.face_T((2, -1))
    # lowest solid face temperature per column
    Tbot = np.full(Tf.shape[:2], np.nan)
    for ii in range(Tf.shape[0]):
        for jj in range(Tf.shape[1]):
            col = Tf[ii, jj, :]
            w = np.where(~np.isnan(col))[0]
            if len(w):
                Tbot[ii, jj] = col[w[0]]
    ax = axs[1, 0]
    im = ax.pcolormesh(b.xe, b.ye, Tbot.T, cmap="inferno", shading="flat")
    cont2 = b.contact.any(axis=2)
    ax.contour(b.xc, b.yc, cont2.T.astype(float), levels=[0.5], colors="cyan", linewidths=0.8)
    ax.set_title("Skin-side surface temperature (cyan = skin contact)"); ax.set_aspect("equal"); fig.colorbar(im, ax=ax, label="°C")
    ax = axs[1, 1]
    kb = np.where((b.zc > b.zlev["zbat0"]) & (b.zc < b.zlev["zbat1"]))[0]
    k = kb[len(kb) // 2]
    im = ax.pcolormesh(b.xe, b.ye, Tm[:, :, k].T, cmap="inferno", shading="flat")
    ax.set_title(f"XY plane Z={b.zc[k]:.2f} (battery mid-plane)"); ax.set_aspect("equal"); fig.colorbar(im, ax=ax, label="°C")
    fig.suptitle(f"SIM-13 3-D FV, case '{tag}'")
    fig.tight_layout()
    fn = os.path.join(OUT, f"fv3d_{tag}.png")
    fig.savefig(fn, dpi=110); plt.close(fig)
    return fn


CASES = {
    # tag: overrides (all on top of DEFAULT = recommended v0 design, 1000 W/m2 normal, 35 C, 0.5 m/s, skin 34 C)
    "WS_harvest":        dict(mode="harvest"),
    "WC_shorted":        dict(mode="shorted"),
    "open_batt_full":    dict(mode="open"),
    "WC_Rc_0.001":       dict(mode="shorted", R_c=0.001),
    "WC_Rc_0.004":       dict(mode="shorted", R_c=0.004),
    "WC_h_x0.6":         dict(mode="shorted", h_top=ENV["h_top"] * 0.6, h_side=ENV["h_side"] * 0.6),
    "WC_h_x1.5":         dict(mode="shorted", h_top=ENV["h_top"] * 1.5, h_side=ENV["h_side"] * 1.5),
    "WC_black_frame":    dict(mode="shorted", alpha_frame=0.9),
    "WC_white_print":    dict(mode="shorted", alpha_print=0.25),
    "WC_skin_36":        dict(mode="shorted", T_skin=36.0),
    "WC_indent_0.8":     dict(mode="shorted", indent=0.8),
    "WC_indent_1.6":     dict(mode="shorted", indent=1.6),
    "WC_cells_max_1.5":  dict(mode="shorted", t_cell=1.5),
    "WC_batt_kz0.3":     dict(mode="shorted", k_override={"battery": (20.0, 0.3)}),
    "WC_pcb_kz0.35":     dict(mode="shorted", k_override={"pcb": (40.0, 0.35)}),
    "WC_pcb_kz3":        dict(mode="shorted", k_override={"pcb": (40.0, 3.0)}),
    "WC_air_k0.027":     dict(mode="shorted", k_override={"air": (0.027, 0.027)}),
    "WC_cavityfill":     dict(mode="shorted", cavity_fill=("gap_pad", "batt")),
    "WC_glass_window":   dict(mode="shorted", window_mat="glass"),
    "WC_TMP_archv0":     dict(mode="shorted", island=6.0, pedestal=5.0, pad_t=0.4, slot=False, foam_hole=False,
                              k_override={"gap_pad": (3.0, 3.0)}),
    "WC_pennes_w1e-3":   dict(mode="shorted", pennes=dict(omega=1e-3, T_a=36.0)),
    "WC_pennes_w3e-3":   dict(mode="shorted", pennes=dict(omega=3e-3, T_a=36.0)),
    "WC_tissue2d_w1e-3": dict(mode="shorted", tissue_R=0.01533, T_skin=35.18),
    "WC_tissue2d_w3e-3": dict(mode="shorted", tissue_R=0.01102, T_skin=35.47),
    "WC_tissue2d_w6e-3": dict(mode="shorted", tissue_R=0.00856, T_skin=35.61),
    "WS_tissue2d_w3e-3": dict(mode="harvest", tissue_R=0.01102, T_skin=35.47),
    "WC_tissue2d_w3e-3_whiteprint": dict(mode="shorted", tissue_R=0.01102, T_skin=35.47, alpha_print=0.25),
    "WC_whiteprint_cavityfill": dict(mode="shorted", alpha_print=0.25, cavity_fill=("gap_pad", "batt")),
    "indoor_25C":        dict(mode="open", G=0.0, T_amb=25.0, T_skin=33.0),
    "shade_35C":         dict(mode="open", G=0.0, T_amb=35.0, T_skin=34.0),
    "WS_500Wm2":         dict(mode="harvest", G=500.0),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--cases", default="")
    ap.add_argument("--gridstudy", action="store_true")
    a = ap.parse_args()
    results = {}
    sel = [c for c in a.cases.split(",") if c] or (["WS_harvest", "WC_shorted"] if a.quick else list(CASES))
    for tag in sel:
        t0 = time.time()
        b = Band(**CASES[tag])
        r = b.run()
        r["runtime_s"] = round(time.time() - t0, 1)
        results[tag] = r
        if tag in ("WS_harvest", "WC_shorted", "WC_cavityfill", "WC_tissue2d_w3e-3"):
            r["plot"] = plots(b, tag)
        print(f"{tag:18s} grid={r['grid']} skin_max={r['skin_contact_max_C']:.2f} E1={r['E1_face_mean_C']:.2f} "
              f"TMP117={r['TMP117_C']:.2f} err={r['TMP117_error_vs_E1_face_K']:+.3f} bat_max={r['battery_max_C']:.2f} "
              f"NTC={r['battery_NTC_C']:.2f} pv={r['pv_cell_max_C']:.2f} bal={r['balance_err_W']:.2e} t={r['runtime_s']}s", flush=True)
    if a.gridstudy:
        for dm, df in ((1.0, 0.5), (0.5, 0.25), (0.35, 0.18)):
            b = Band(mode="shorted", dmax=dm, dfine=df)
            r = b.run()
            results[f"grid_{dm}_{df}"] = r
            print(f"grid {dm}/{df} {r['grid']} skin_max={r['skin_contact_max_C']:.3f} bat_max={r['battery_max_C']:.3f} "
                  f"TMP117 err={r['TMP117_error_vs_E1_face_K']:+.4f} pv={r['pv_cell_max_C']:.3f}", flush=True)
    fn = os.path.join(OUT, "fv3d_results.json" if not a.cases else f"fv3d_results_{'_'.join(sel)[:60]}.json")
    if a.gridstudy:
        fn = os.path.join(OUT, "fv3d_gridstudy.json")
    json.dump(results, open(fn, "w"), indent=1, default=float)
    print("wrote", fn)


if __name__ == "__main__":
    main()
