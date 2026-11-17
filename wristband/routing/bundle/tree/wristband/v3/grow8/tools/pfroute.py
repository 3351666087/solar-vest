"""[grow G-2] Whole-board negotiated-congestion router (PathFinder) on the plane-fanned board.
Python side: rasterise the dump of maze_finish.py (fixed copper, keep-outs, plates, connections), build one static rule mask per net
(the rule model of layout/tools/maze_rrr.py: JLC deck, net-class widths / clearances / vias, holes 0.20, edge / motor 0.30, antenna
pocket, B.Cu void over the plates, R-2 forbidden nets, dot keep-outs 2.0 mm, U10 island as fixed copper, L4 pour yields), then call the
compiled core src/libpf.so (pf.c) and write routes in maze_finish.py's apply format.

  venv-python pfroute.py DUMP.json ROUTES.json [PARAMS.json]
"""
import ctypes as C, json, math, os, sys, time
import numpy as np
from matplotlib.path import Path
from scipy.ndimage import distance_transform_edt as _edt

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(os.path.dirname(HERE), "src", "libpf.so")
SIG6 = ["F.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]
SIG8 = ["F.Cu", "In2.Cu", "In3.Cu", "In5.Cu", "In6.Cu", "B.Cu"]   # [grow8 P-5] In1 GND / In4 VDD_1V8 planes
SIG = SIG6
PLANE_LAYER = {6: {"GND": "In1.Cu"}, 8: {"GND": "In1.Cu", "VDD_1V8": "In4.Cu"}}
VIA_BIT, PVIA_BIT = 6, 7                                          # [grow8] mask bits (pf.c: 64 / 128); layers use bits 0..5
SOFT_POUR = "L4_VDD_1V8"
DEF = dict(grid=0.025, iters=60, reroute_all=1, pres0=0.3, pres_mult=1.2, hist_inc=2.0, hw=1.2, via_cost_mm=1.2, l4_cost=3.0,
           layer_cost=[1.0, 1.0, None, 1.0, 1.0], max_exp=3000000, conn_margin=3.0, net_margin=6.0, dyn_margin_grid=1.0,
           order="short", seed=1, tlim=3000.0, plane_nets=None, plane_fix=None, layer_cost8=[1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
           neck=0.0, neck_w=0.09, neck_clr=0.09, shield=None)
# [grow8 Q-2] neck: router radius (mm) around the net's own pad copper inside which every track of the net is 0.09 wide with 0.09
#   clearance (0 = off; evaluate.py passes the DRU radius - 0.1). [grow8 Q-3] shield: inner layers on which plate-forbidden nets may run
#   over the plates (8 layers: ["In2.Cu", "In3.Cu"], between the In1 GND and In4 VDD_1V8 planes); None = none (F.Cu only).
# plane_nets None -> ["GND"] on 6 layers, ["GND", "VDD_1V8"] on 8; plane_fix None -> on for 8 layers (zone-only plane ends count as on
# the plane; no plane via inside a NO_POUR area of that plane layer), off on 6 layers (engine behaviour unchanged)
BT_BINS = [0.095, 0.15, 0.2, 0.225, 0.25, 0.30]
BV_BINS = [0.25, 0.30, 0.325, 0.35]


class PF(C.Structure):
    _fields_ = [("NL", C.c_int32), ("NY", C.c_int32), ("NX", C.c_int32), ("NNET", C.c_int32),
                ("lab", C.c_void_p), ("mask", C.c_void_p), ("m_off", C.c_void_p), ("win", C.c_void_p),
                ("kT", C.c_void_p), ("kV", C.c_void_p), ("plane", C.c_void_p),
                ("At", C.c_void_p), ("Av", C.c_void_p), ("vhole", C.c_void_p),
                ("nKT", C.c_int32), ("nKV", C.c_int32), ("BT", C.c_void_p), ("BV", C.c_void_p),
                ("grid", C.c_float), ("margin", C.c_float), ("lc", C.c_float * 8), ("via_cost", C.c_float),
                ("NC", C.c_int32), ("c_net", C.c_void_p), ("c_ga", C.c_void_p), ("c_gb", C.c_void_p),
                ("NG", C.c_int32), ("g_off", C.c_void_p), ("g_cells", C.c_void_p), ("g_onplane", C.c_void_p), ("g_net", C.c_void_p),
                ("NORD", C.c_int32), ("order", C.c_void_p), ("nc_off", C.c_void_p), ("nc_list", C.c_void_p),
                ("max_iter", C.c_int32), ("reroute_all", C.c_int32),
                ("pres0", C.c_float), ("pres_mult", C.c_float), ("hist_inc", C.c_float), ("hw", C.c_float),
                ("max_exp", C.c_int64), ("conn_margin", C.c_float), ("tlim", C.c_float),
                ("out_status", C.c_void_p), ("it_stats", C.c_void_p), ("n_iter", C.c_void_p), ("final_over", C.c_void_p),
                ("nmask", C.c_void_p), ("kNeck", C.c_int32), ("AtNeck", C.c_float)]


def ptr(a):
    return a.ctypes.data_as(C.c_void_p)


def prep(D, prm):
    t0 = time.time()
    GRID = prm["grid"]; MARGIN = 1.3 * GRID
    xs = [p[0] for p in D["outline"]]; ys = [p[1] for p in D["outline"]]
    X0, Y0 = min(xs) - 0.2, min(ys) - 0.2
    NX = int((max(xs) - X0 + 0.2) / GRID) + 1; NY = int((max(ys) - Y0 + 0.2) / GRID) + 1
    gx = X0 + GRID * np.arange(NX); gy = Y0 + GRID * np.arange(NY)
    XX, YY = np.meshgrid(gx, gy)
    NL = len(SIG); L = {ln: i for i, ln in enumerate(SIG)}
    nets = sorted(D["rules"]); nid = {n: i + 1 for i, n in enumerate(nets)}; nid[""] = 0
    lab = np.zeros((NL, NY, NX), np.int16); holeN = np.zeros((NY, NX), np.int16)

    def cbox(x0, y0, x1, y1):
        return (max(0, int((x0 - X0) / GRID) - 1), min(NX, int((x1 - X0) / GRID) + 2), max(0, int((y0 - Y0) / GRID) - 1), min(NY, int((y1 - Y0) / GRID) + 2))

    vias_fixed = []
    items = sorted(D["items"], key=lambda it: 0 if (it["k"] == "poly" and not it["net"]) else 1)   # netless copper graphics (net ties) under the pads
    for it in items:
        if it["k"] == "poly" and it.get("zone") == SOFT_POUR:
            continue
        v = nid.get(it["net"], 0) or -1
        if it["k"] == "poly":
            pts = np.array(it["pts"]); i0, i1, j0, j1 = cbox(pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max())
            if i1 <= i0 or j1 <= j0:
                continue
            m = Path(pts).contains_points(np.c_[XX[j0:j1, i0:i1].ravel(), YY[j0:j1, i0:i1].ravel()], radius=1e-9).reshape(j1 - j0, i1 - i0)
            lab[L[it["layer"]], j0:j1, i0:i1][m] = v
        elif it["k"] == "seg":
            a, b, r = it["a"], it["b"], it["r"]
            i0, i1, j0, j1 = cbox(min(a[0], b[0]) - r, min(a[1], b[1]) - r, max(a[0], b[0]) + r, max(a[1], b[1]) + r)
            PX, PY = XX[j0:j1, i0:i1], YY[j0:j1, i0:i1]; dx, dy = b[0] - a[0], b[1] - a[1]; Ls = dx * dx + dy * dy
            t = np.zeros_like(PX) if Ls == 0 else np.clip(((PX - a[0]) * dx + (PY - a[1]) * dy) / Ls, 0, 1)
            lab[L[it["layer"]], j0:j1, i0:i1][np.hypot(PX - a[0] - t * dx, PY - a[1] - t * dy) <= r] = v
        else:
            c = it["c"]; r = it["r"]; rh = it.get("rh", r)
            i0, i1, j0, j1 = cbox(c[0] - r, c[1] - r, c[0] + r, c[1] + r)
            d = np.hypot(XX[j0:j1, i0:i1] - c[0], YY[j0:j1, i0:i1] - c[1])
            if it["k"] == "via":
                for li in range(NL):
                    lab[li, j0:j1, i0:i1][d <= r] = v
                vias_fixed.append((it["net"], c))
            holeN[j0:j1, i0:i1][d <= rh] = v
    hole = holeN != 0
    padN = np.zeros((NY, NX), np.int16)                         # [grow8 Q-2] pad copper (any layer) per net
    if prm["neck"] > 0:
        for pd in D.get("pads", []):
            if pd["net"] not in nid:
                continue
            for pg in pd["pts"]:
                pg = np.array(pg); i0, i1, j0, j1 = cbox(pg[:, 0].min(), pg[:, 1].min(), pg[:, 0].max(), pg[:, 1].max())
                if i1 <= i0 or j1 <= j0:
                    continue
                m = Path(pg).contains_points(np.c_[XX[j0:j1, i0:i1].ravel(), YY[j0:j1, i0:i1].ravel()], radius=1e-9).reshape(j1 - j0, i1 - i0)
                padN[j0:j1, i0:i1][m] = nid[pd["net"]]
    clr_lut = np.full(len(nets) + 3, 0.10, np.float32)       # index lab + 1 (netless copper: 0.10)
    for n, r in D["rules"].items():
        clr_lut[nid[n] + 1] = 0.10 if r["clr"] <= 0.10 else r["clr"]
    CLR_GROUPS = sorted(set(clr_lut.tolist()))
    pts = np.c_[XX.ravel(), YY.ravel()]
    inside = Path(D["outline"]).contains_points(pts).reshape(NY, NX)
    d_edge = _edt(inside) * GRID
    mc = D["motor"]; d_motor = np.hypot(XX - mc[0], YY - mc[1]) - mc[2]
    plate = np.zeros((NY, NX), bool)
    for pg in D["plates"]:
        plate |= Path(pg).contains_points(pts).reshape(NY, NX)
    trk_block = np.zeros((NL, NY, NX), bool); via_block = np.zeros((NY, NX), bool)
    for k in D["keep"]:
        if not k["pts"] or len(k["pts"]) < 3 or k["name"].endswith("_AREA") or "NOPOUR" in k["name"] or "NO_POUR" in k["name"]:
            continue
        m = Path(k["pts"]).contains_points(pts).reshape(NY, NX)
        if k["tracks"]:
            for ln in k["layers"]:
                if ln in L:
                    trk_block[L[ln]] |= m
        if k["vias"]:
            via_block |= m
    trk_block[L["B.Cu"]] |= plate
    for dc in D["dots"]:
        via_block |= np.hypot(XX - dc[0], YY - dc[1]) < 2.0
    noplane = {}                                                   # [grow8] NO_POUR areas on a plane net's plane layer
    for pn, pl_ln in PLANE_LAYER[D.get("nl", 6)].items():
        for k in D["keep"]:
            if k["pts"] and len(k["pts"]) >= 3 and ("NOPOUR" in k["name"] or "NO_POUR" in k["name"]) and pl_ln in k["layers"]:
                m = Path(k["pts"]).contains_points(pts).reshape(NY, NX)
                noplane[pn] = noplane.get(pn, np.zeros((NY, NX), bool)) | m
    edt = lambda m: np.full(m.shape, 1e9) if m.all() else _edt(m) * GRID
    d_trk = [edt(~trk_block[li]) for li in range(NL)]
    d_vblk = edt(~via_block); d_plate = edt(~plate)
    forb = set(D["forb"])
    shield = set(prm.get("shield") or [])
    t_static = time.time() - t0

    # ---------------------------------------------------------------- end floods -> groups
    def cell(p):
        return int(round((p[1] - Y0) / GRID)), int(round((p[0] - X0) / GRID))

    def flood(e, n):
        li_s = [L[l] for l in e["layers"] if l in L] or list(range(NL))
        j, i = cell(e["p"])
        res = [(li, j + dj, i + di) for li in li_s for dj in range(-3, 4) for di in range(-3, 4)
               if 0 <= j + dj < NY and 0 <= i + di < NX and lab[li, j + dj, i + di] == n]
        if not res:
            return [(li, j, i) for li in li_s]
        seen = set(res); st = list(res)
        while st and len(seen) < 40000:
            li, jj, ii = st.pop()
            for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (li, jj + dj, ii + di)
                if 0 <= q[1] < NY and 0 <= q[2] < NX and q not in seen and lab[q] == n:
                    seen.add(q); st.append(q)
            if hole[jj, ii]:
                for l2 in range(NL):
                    q = (l2, jj, ii)
                    if q not in seen and lab[q] == n:
                        seen.add(q); st.append(q)
        return list(seen)

    P2 = NY * NX
    groups = []                   # dict(net, cells set, onplane)
    owner = {}                    # node -> group index (by net)
    conns = []
    for pr in D["pairs"]:
        net = pr[0]["net"] or pr[1]["net"]
        if not net or net not in nid:
            continue
        n = nid[net]; gi = []
        for e in pr:
            cells = flood(e, n)
            nodes = {li * P2 + j * NX + i for li, j, i in cells}
            hit = {owner[v] for v in nodes if v in owner}
            hit = {g for g in hit if groups[g]["net"] == n and groups[g]["alive"]}
            if hit:
                g0 = min(hit)
                for g in hit - {g0}:
                    groups[g0]["cells"] |= groups[g]["cells"]; groups[g]["alive"] = False; groups[g]["fwd"] = g0; groups[g0]["pz"] |= groups[g]["pz"]
                groups[g0]["cells"] |= nodes
            else:
                groups.append(dict(net=n, cells=set(nodes), alive=True, fwd=None, pz=False)); g0 = len(groups) - 1
            for v in groups[g0]["cells"]:
                owner[v] = g0
            if e.get("pz") and prm["plane_fix"]:
                groups[g0]["pz"] = True
            gi.append(g0)
        conns.append([n, gi[0], gi[1], math.hypot(pr[0]["p"][0] - pr[1]["p"][0], pr[0]["p"][1] - pr[1]["p"][1]), net])

    def res_g(g):
        while groups[g]["fwd"] is not None:
            g = groups[g]["fwd"]
        return g
    for c in conns:
        c[1] = res_g(c[1]); c[2] = res_g(c[2])
    conns = [c for c in conns if c[1] != c[2]]
    alive = sorted({c[1] for c in conns} | {c[2] for c in conns}); gmap = {g: k for k, g in enumerate(alive)}
    plane_ids = {nid[n] for n in prm["plane_nets"] if n in nid}
    g_cells = []; g_off = [0]; g_onplane = []; g_net = []
    for g in alive:
        cs = sorted(groups[g]["cells"]); g_cells += cs; g_off.append(len(g_cells)); g_net.append(groups[g]["net"])
        g_onplane.append(int(groups[g]["net"] in plane_ids and (groups[g]["pz"] or any(hole[(v % P2) // NX, v % NX] for v in cs))))
    for c in conns:
        c[1] = gmap[c[1]]; c[2] = gmap[c[2]]

    # ---------------------------------------------------------------- per-net static masks
    NNET = len(nets)
    win = np.zeros((NNET + 1, 4), np.int32); m_off = np.zeros(NNET + 2, np.int64)
    kT = np.zeros(NNET + 1, np.int32); kV = np.zeros(NNET + 1, np.int32); plane = np.zeros(NNET + 1, np.int32)
    At = np.zeros(NNET + 1, np.float32); Av = np.zeros(NNET + 1, np.float32); vhole = np.zeros(NNET + 1, np.float32)
    masks = []; nmasks = []; neck_cells = 0
    NW, NC_ = prm["neck_w"], prm["neck_clr"]
    netconns = {}
    for k, c in enumerate(conns):
        netconns.setdefault(c[0], []).append(k)
    pad = int(prm["net_margin"] / GRID)
    off = 0
    for net in nets:
        n = nid[net]; ru = D["rules"][net]; w = ru["w"]; c_n = ru["clr"]; vd, vh = ru["via"]
        h = 0.05 if c_n <= 0.10 else c_n - 0.05        # halos: h_a + h_b >= max(c_a, c_b) for every class pair
        a_t = w / 2 + h; a_v = max(vd / 2 + h, vh + 0.15); vhole[n] = vh
        kT[n] = next((k for k, b in enumerate(BT_BINS) if b >= a_t - 1e-6), len(BT_BINS) - 1)
        kV[n] = next((k for k, b in enumerate(BV_BINS) if b >= a_v - 1e-6), len(BV_BINS) - 1)
        At[n] = max(a_t, BT_BINS[kT[n]]); Av[n] = max(a_v, BV_BINS[kV[n]])      # halo = checker radius: symmetric overlap test
        plane[n] = int(n in plane_ids)
        m_off[n] = off
        if n not in netconns:
            win[n] = (0, 0, 0, 0); continue
        cells = [v for k in netconns[n] for g in (conns[k][1], conns[k][2]) for v in g_cells[g_off[g]:g_off[g + 1]]]
        cs = np.array(cells, np.int64); jj = (cs % P2) // NX; ii = cs % NX
        if plane[n]:
            j0, j1, i0, i1 = 0, NY, 0, NX
        else:
            j0, j1, i0, i1 = max(0, jj.min() - pad), min(NY, jj.max() + pad + 1), max(0, ii.min() - pad), min(NX, ii.max() + pad + 1)
        win[n] = (j0, j1, i0, i1)
        sl = (slice(j0, j1), slice(i0, i1))
        lf = lab[:, sl[0], sl[1]].astype(np.int32)
        oF = (lf != 0) & (lf != n); cF = clr_lut[lf + 1]
        de = d_edge[sl]; dm = d_motor[sl]
        vA = (d_vblk[sl] >= vd / 2 + 0.04) & (de >= 0.30 + vd / 2 + MARGIN) & (dm >= 0.30 + vd / 2 + MARGIN)
        dho = edt(~(hole[sl] & (holeN[sl] != n)))           # hole to copper: other nets only (KiCad exempts the own net)
        dhoA = edt(~hole[sl])                                # hole to hole: every hole
        mb = np.zeros((j1 - j0, i1 - i0), np.uint8)
        dp = d_plate[sl]
        zone = None
        if prm["neck"] > 0:
            pm = padN[sl] == n
            if pm.any():
                zone = edt(~pm) <= prm["neck"]
                neck_cells += int(zone.sum())
        for li in range(NL):
            base = (d_trk[li][sl] >= w / 2 + 0.04) & (de >= 0.30 + w / 2 + MARGIN) & (dm >= 0.30 + w / 2 + MARGIN)
            fr = base & (dho >= w / 2 + 0.20 + MARGIN)
            dmin = None; dall = None
            for cg in CLR_GROUPS:                          # KiCad: clearance = max(own class, other class)
                og = oF[li] & (cF[li] == cg)
                if not og.any():
                    continue
                dg = edt(~og); cc = max(c_n, cg, 0.09)
                fr &= dg >= w / 2 + cc + MARGIN
                vA &= dg >= vd / 2 + cc + MARGIN
                dmin = dg if dmin is None else np.minimum(dmin, dg)
            if dmin is not None:
                vA &= dmin >= vh + 0.20 + MARGIN
            if net in forb and SIG[li] not in ("F.Cu", "B.Cu") and SIG[li] not in shield:   # [grow8] inner layers; Q-3 shielded layers open
                fr &= dp >= w / 2 + 0.04
            if zone is not None:                                 # [grow8 Q-2] neck: 0.09 track, 0.09 clearance to every other copper
                frn = (d_trk[li][sl] >= NW / 2 + 0.04) & (de >= 0.30 + NW / 2 + MARGIN) & (dm >= 0.30 + NW / 2 + MARGIN) & (dho >= NW / 2 + 0.20 + MARGIN)
                if dmin is not None:
                    frn &= dmin >= NW / 2 + NC_ + MARGIN
                if net in forb and SIG[li] not in ("F.Cu", "B.Cu") and SIG[li] not in shield:
                    frn &= dp >= NW / 2 + 0.04
                fr = np.where(zone, frn, fr)
            mb |= (fr.astype(np.uint8) << li)
        vA &= (dhoA >= vh + 0.20 + MARGIN) & (dho >= vd / 2 + 0.20 + MARGIN)
        if net in forb:
            vA &= dp >= vd / 2 + 0.04
        mb |= vA.astype(np.uint8) << VIA_BIT
        if plane[n]:
            pv = vA & ~hole[sl]
            if prm["plane_fix"] and net in noplane:
                pv &= ~noplane[net][sl]
            mb |= pv.astype(np.uint8) << PVIA_BIT
        for v in cells:                                        # own end copper is always passable
            li, r2 = divmod(v, P2); j, i = divmod(r2, NX)
            mb[j - j0, i - i0] |= 1 << li
        masks.append(mb.ravel()); off += mb.size
        nmasks.append(zone.astype(np.uint8).ravel() if zone is not None else np.zeros(mb.size, np.uint8))
    m_off[NNET + 1] = off
    mask = np.concatenate(masks) if masks else np.zeros(1, np.uint8)
    nmask = np.concatenate(nmasks) if nmasks else np.zeros(1, np.uint8)
    return dict(GRID=GRID, X0=X0, Y0=Y0, NX=NX, NY=NY, NL=NL, nets=nets, nid=nid, lab=lab, mask=mask, nmask=nmask, neck_cells=neck_cells, m_off=m_off, win=win, kT=kT, kV=kV,
                plane=plane, At=At, Av=Av, vhole=vhole, conns=conns, netconns=netconns, g_cells=np.array(g_cells, np.int32),
                g_off=np.array(g_off, np.int64), g_onplane=np.array(g_onplane, np.int32), g_net=np.array(g_net, np.int32),
                plate=plate, vias_fixed=vias_fixed, t_static=t_static, t_prep=time.time() - t0)


def order_nets(R, prm):
    nets_used = sorted(R["netconns"])
    L_ = {n: sum(R["conns"][k][3] for k in R["netconns"][n]) for n in nets_used}
    pol = prm["order"]
    if pol == "short":
        o = sorted(nets_used, key=lambda n: (L_[n], n))
    elif pol == "long":
        o = sorted(nets_used, key=lambda n: (-L_[n], n))
    elif pol == "pins":
        o = sorted(nets_used, key=lambda n: (-len(R["netconns"][n]), n))
    elif pol == "random":
        o = list(nets_used); np.random.RandomState(prm["seed"]).shuffle(o)
    elif isinstance(pol, list):                               # explicit net names first, the rest short-first
        first = [R["nid"][x] for x in pol if x in R["nid"] and R["nid"][x] in L_]
        o = first + sorted([n for n in nets_used if n not in first], key=lambda n: (L_[n], n))
    else:
        raise SystemExit("unknown order policy %r" % pol)
    if prm.get("seed") and pol != "random" and prm.get("order_jitter", 0) > 0:   # small seeded perturbation of the order
        rs = np.random.RandomState(prm["seed"]); key = np.arange(len(o)) + rs.normal(0, prm["order_jitter"], len(o))
        o = [o[k] for k in np.argsort(key, kind="stable")]
    return o


def run(R, prm):
    lib = C.CDLL(LIB)
    lib.pf_run.restype = C.c_int
    lib.pf_run.argtypes = [C.POINTER(PF), C.c_void_p, C.c_int64, C.c_void_p]
    o = order_nets(R, prm)
    NNET = len(R["nets"])
    nc_off = np.zeros(NNET + 2, np.int64); nc_list = []
    for n in range(1, NNET + 1):
        nc_off[n] = len(nc_list)
        ks = sorted(R["netconns"].get(n, []), key=lambda k: R["conns"][k][3])
        nc_list += ks
    nc_off[NNET + 1] = len(nc_list)
    nc_off[0] = 0
    # nc_off[n]..nc_off[n+1] must be the slice of net n: rebuild as cumulative
    cum = np.zeros(NNET + 2, np.int64); acc = 0
    for n in range(0, NNET + 1):
        cum[n] = acc; acc += len(R["netconns"].get(n, []))
    cum[NNET + 1] = acc
    nc_off = cum
    nc_list = np.array(nc_list, np.int32)
    conns = R["conns"]; NC = len(conns)
    c_net = np.array([c[0] for c in conns], np.int32); c_ga = np.array([c[1] for c in conns], np.int32); c_gb = np.array([c[2] for c in conns], np.int32)
    order = np.array(o, np.int32)
    if R["NL"] == 5:
        lc = list(prm["layer_cost"]); lc[2] = prm["l4_cost"] if lc[2] is None else lc[2]
    else:
        lc = list(prm["layer_cost8"])
    BT = np.array(BT_BINS, np.float32); BV = np.array(BV_BINS, np.float32)
    out_status = np.zeros(NC, np.int32); it_stats = np.zeros((prm["iters"], 6), np.float32)
    n_iter = np.zeros(1, np.int32); final_over = np.zeros(1, np.int32)
    lab = np.ascontiguousarray(R["lab"]); mask = np.ascontiguousarray(R["mask"]); win = np.ascontiguousarray(R["win"])
    nmask = np.ascontiguousarray(R["nmask"])
    p = PF(NL=R["NL"], NY=R["NY"], NX=R["NX"], NNET=NNET, lab=ptr(lab), mask=ptr(mask), m_off=ptr(R["m_off"]), win=ptr(win),
           kT=ptr(R["kT"]), kV=ptr(R["kV"]), plane=ptr(R["plane"]), At=ptr(R["At"]), Av=ptr(R["Av"]), vhole=ptr(R["vhole"]),
           nKT=len(BT_BINS), nKV=len(BV_BINS), BT=ptr(BT), BV=ptr(BV), grid=R["GRID"], margin=prm["dyn_margin_grid"] * R["GRID"],
           lc=(C.c_float * 8)(*(lc + [1.0] * (8 - len(lc)))), via_cost=prm["via_cost_mm"] / R["GRID"],
           NC=NC, c_net=ptr(c_net), c_ga=ptr(c_ga), c_gb=ptr(c_gb), NG=len(R["g_onplane"]), g_off=ptr(R["g_off"]), g_cells=ptr(R["g_cells"]),
           g_onplane=ptr(R["g_onplane"]), g_net=ptr(R["g_net"]), NORD=len(order), order=ptr(order), nc_off=ptr(nc_off), nc_list=ptr(nc_list),
           max_iter=prm["iters"], reroute_all=prm["reroute_all"], pres0=prm["pres0"], pres_mult=prm["pres_mult"], hist_inc=prm["hist_inc"],
           hw=prm["hw"], max_exp=prm["max_exp"], conn_margin=prm["conn_margin"], tlim=prm["tlim"],
           out_status=ptr(out_status), it_stats=ptr(it_stats), n_iter=ptr(n_iter), final_over=ptr(final_over),
           nmask=ptr(nmask) if prm["neck"] > 0 else None, kNeck=0, AtNeck=max(prm["neck_w"] / 2 + prm["neck_clr"] / 2, BT_BINS[0]))
    cap = 20_000_000
    path_out = np.zeros(cap, np.int32); path_off = np.zeros(2 * NC + 1, np.int64)
    t0 = time.time()
    rc = lib.pf_run(C.byref(p), ptr(path_out), cap, ptr(path_off))
    if rc != 0:
        raise SystemExit("path buffer overflow")
    t_route = time.time() - t0
    return dict(status=out_status, it_stats=it_stats[:n_iter[0]], final_over=int(final_over[0]), path_out=path_out, path_off=path_off,
                t_route=t_route, order=o)


def to_routes(R, O, D):
    GRID, X0, Y0, NX, NY = R["GRID"], R["X0"], R["Y0"], R["NX"], R["NY"]; P2 = NX * NY
    xy = lambda c2: (round(X0 + GRID * (c2 % NX), 4), round(Y0 + GRID * (c2 // NX), 4))
    routes = {}
    nmask = R.get("nmask"); neckw = R.get("neck_w", 0.09); nstat = {}

    def nb(n, c2):                                             # [grow8 Q-2] node in the net's neck zone (same rule as pf.c)
        if nmask is None or not R.get("neck_on"):
            return 0
        j, i = divmod(c2, NX); w_ = R["win"][n]
        if j < w_[0] or j >= w_[1] or i < w_[2] or i >= w_[3]:
            return 0
        return int(nmask[R["m_off"][n] + (j - w_[0]) * (w_[3] - w_[2]) + (i - w_[2])])
    for k, c in enumerate(R["conns"]):
        net = c[4]; ru = D["rules"][net]; w = ru["w"]; vd, vh = ru["via"]; n_ = c[0]
        r = routes.setdefault(net, dict(net=net, segs=[], vias=[], _v=set()))
        for pp in range(2):
            a, b = O["path_off"][2 * k + pp], O["path_off"][2 * k + pp + 1]
            nodes = O["path_out"][a:b].tolist()
            pv = bool(nodes) and nodes[-1] == -1
            if pv:
                nodes = nodes[:-1]
            if not nodes:
                continue
            run = [nodes[0]]
            def flush(run):
                if len(run) < 2:
                    return
                fl = [nb(n_, v % P2) for v in run]                  # step narrow iff either end node is in the neck zone
                st = [fl[q] | fl[q + 1] for q in range(len(run) - 1)]
                q0 = 0
                for q in range(1, len(st) + 1):
                    if q == len(st) or st[q] != st[q0]:
                        flush1(run[q0:q + 1], neckw if st[q0] else w)
                        q0 = q

            def flush1(run, ww):
                if ww < w:
                    nstat[net] = nstat.get(net, 0) + sum(math.dist(xy(a % P2), xy(b % P2)) for a, b in zip(run, run[1:]))
                pl = [xy(v % P2) for v in run]
                simp = [pl[0]]
                for q in range(1, len(pl) - 1):
                    A, B, Cc = simp[-1], pl[q], pl[q + 1]
                    if abs((B[0] - A[0]) * (Cc[1] - A[1]) - (B[1] - A[1]) * (Cc[0] - A[0])) > 1e-9:
                        simp.append(B)
                simp.append(pl[-1])
                for A, B in zip(simp, simp[1:]):
                    r["segs"].append(dict(layer=SIG[run[0] // P2], a=A, b=B, w=ww))
            for v in nodes[1:]:
                if v // P2 != run[-1] // P2:
                    flush(run); cc = xy(v % P2)
                    if cc not in r["_v"]:
                        r["_v"].add(cc); r["vias"].append(dict(c=cc, d=vd, h=vh))
                    run = [v]
                else:
                    run.append(v)
            flush(run)
            if pv:
                cc = xy(nodes[-1] % P2)
                if cc not in r["_v"]:
                    r["_v"].add(cc); r["vias"].append(dict(c=cc, d=vd, h=vh))
    out = []
    for r in routes.values():
        r.pop("_v")
        if r["segs"] or r["vias"]:
            out.append(r)
    R["neck_mm"] = {k: round(v, 2) for k, v in sorted(nstat.items())}
    return out


def main(dumpf, outf, prmf=None):
    global SIG
    prm = dict(DEF)
    if prmf:
        prm.update(json.load(open(prmf)) if isinstance(prmf, str) else prmf)
    t0 = time.time()
    D = json.load(open(dumpf))
    nl = D.get("nl", 6); SIG = list(D.get("sig", SIG6))
    if prm.get("plane_nets") is None:
        prm["plane_nets"] = sorted(PLANE_LAYER[nl])
    if prm.get("plane_fix") is None:
        prm["plane_fix"] = nl == 8
    R = prep(D, prm)
    R["neck_on"] = prm["neck"] > 0; R["neck_w"] = prm["neck_w"]
    O = run(R, prm)
    routes = to_routes(R, O, D)
    st = O["status"]
    nvia = sum(len(r["vias"]) for r in routes); tl = sum(math.dist(s["a"], s["b"]) for r in routes for s in r["segs"])
    stats = dict(cells=int(R["NL"] * R["NX"] * R["NY"]), grid_mm=R["GRID"], nx=R["NX"], ny=R["NY"], layers=R["NL"], connections=len(R["conns"]),
                 nets=len(R["netconns"]), routed=int((st == 1).sum()), joined_elsewhere=int((st == 2).sum()), unrouted=int((st == 0).sum()),
                 dropped=int((st == 3).sum()), iterations=len(O["it_stats"]), final_overused_nodes=O["final_over"],
                 per_iteration=[dict(overused=int(s[0]), failed=int(s[1]), t=round(float(s[2]), 2), nets=int(s[3]), exp_M=round(float(s[4]), 2),
                                     pres=round(float(s[5]), 3)) for s in O["it_stats"]],
                 new_vias=nvia, new_track_mm=round(tl, 1), t_static_s=round(R["t_static"], 1), t_prep_s=round(R["t_prep"], 1),
                 t_route_s=round(O["t_route"], 1), t_total_s=round(time.time() - t0, 1), params=prm,
                 neck_cells=R["neck_cells"], neck_mm=R.get("neck_mm", {}), neck_mm_total=round(sum(R.get("neck_mm", {}).values()), 1))
    failed = [dict(net=c[4], len=round(c[3], 2), status=int(st[k])) for k, c in enumerate(R["conns"]) if st[k] in (0, 3)]
    json.dump(dict(routes=routes, removed=[], failed=failed, stats=stats), open(outf, "w"), indent=0)
    print("pfroute: conns %d routed %d joined %d unrouted %d dropped %d | iters %d over(final) %d | prep %.1f s route %.1f s" % (
        stats["connections"], stats["routed"], stats["joined_elsewhere"], stats["unrouted"], stats["dropped"], stats["iterations"],
        stats["final_overused_nodes"], R["t_prep"], O["t_route"]), flush=True)
    return stats


if __name__ == "__main__":
    main(*sys.argv[1:4])
