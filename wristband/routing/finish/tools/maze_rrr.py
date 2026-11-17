"""[S2e, LEAD_NOTES 2l N-2 / N-3] Rip-up-and-reroute maze finisher (venv python; called as `maze_finish.py rrr DUMP.json ROUTES.json`).

Same rules as maze_finish.route (JLC deck, R-2, R-5, antenna pocket, edge / motor 0.30), plus:
  * five signal layers F, L3, L4, L5, B (N-3: L4 carries signals; its VDD_1V8 pour is not an obstacle, it is refilled around the
    new tracks; the plane-net router copper of GND / VDD_1V8 is never ripped). L4 steps cost LAYER_COST.
  * router copper (everything not on the fan-out board, not locked) is "soft": a path may cross it at a cost; the crossed segments are
    ripped with their whole connected router component, and the component's terminals (its touch points on fixed copper) are queued
    again. Negotiated congestion: the cost of a soft cell rises with the rip count of the blocking net and with a history raster of
    contested cells (PathFinder style), so the nets settle instead of ping-ponging.
Output: {"routes": [...], "removed": [uuids of board items to delete], "failed": [...]} for `maze_finish.py apply`.
"""
import heapq, json, math, os, time
from collections import deque

import numpy as np
from matplotlib.path import Path
from scipy.ndimage import distance_transform_edt as _edt

GRID = float(os.environ.get("MAZE_GRID", "0.025"))
MARGIN = 1.3 * GRID
SIG = ["F.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]
L4 = 2
LAYER_COST = [1.0, 1.0, float(os.environ.get("MAZE_L4_COST", "3.0")), 1.0, 1.0]
SOFT_POUR = "L4_VDD_1V8"
NORIP = {"GND", "VDD_1V8"}
RIP_PEN = float(os.environ.get("MAZE_RIP_PEN", "3.0"))        # per soft cell (grid units), x (1 + rips of the blocking net)
HIST_W = float(os.environ.get("MAZE_HIST_W", "2.0"))
MAXTRY = int(os.environ.get("MAZE_MAXTRY", "6"))
TLIM = float(os.environ.get("MAZE_TLIM", "3000"))             # s
EXP = int(os.environ.get("MAZE_EXP", "1500000"))
HW = float(os.environ.get("MAZE_HW", "2.0"))           # weighted A*
WIN = float(os.environ.get("MAZE_WIN", "8.0"))


def edt(mask_free):
    """distance (mm) from each cell to the nearest False cell of mask_free (inf when there is none)"""
    if mask_free.all():
        return np.full(mask_free.shape, 1e9)
    return _edt(mask_free) * GRID


def segdist(a, b, p):
    ax, ay = a; bx, by = b; dx, dy = bx - ax, by - ay; Ls = dx * dx + dy * dy
    t = 0.0 if Ls == 0 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / Ls))
    return math.hypot(p[0] - ax - t * dx, p[1] - ay - t * dy)


def segseg(a, b, c, d):
    return min(segdist(a, b, c), segdist(a, b, d), segdist(c, d, a), segdist(c, d, b))


def plane_goal_net(net):
    return net == "GND"


def route(dumpf, out):
    t_start = time.time()
    D = json.load(open(dumpf))
    xs = [p[0] for p in D["outline"]]; ys = [p[1] for p in D["outline"]]
    X0, Y0 = min(xs) - 0.2, min(ys) - 0.2
    NX = int((max(xs) - X0 + 0.2) / GRID) + 1; NY = int((max(ys) - Y0 + 0.2) / GRID) + 1
    gx = X0 + GRID * np.arange(NX); gy = Y0 + GRID * np.arange(NY)
    XX, YY = np.meshgrid(gx, gy)
    NL = len(SIG); L = {ln: i for i, ln in enumerate(SIG)}
    nets = sorted(D["rules"]); nid = {n: i + 1 for i, n in enumerate(nets)}; nid[""] = 0
    clr_of = np.zeros(len(nets) + 2);
    for n, r in D["rules"].items():
        clr_of[nid[n]] = r["clr"]
    hi_lut = np.zeros(len(nets) + 3, bool)              # index = lab + 1 (lab -1 = netless copper)
    for n, r in D["rules"].items():
        hi_lut[nid[n] + 1] = r["clr"] >= 0.15
    labF = np.zeros((NL, NY, NX), np.int32); labR = np.zeros((NL, NY, NX), np.int32)
    holeF = np.zeros((NY, NX), bool); holeR = np.zeros((NY, NX), bool)

    def cbox(x0, y0, x1, y1):
        i0 = max(0, int((x0 - X0) / GRID) - 1); i1 = min(NX, int((x1 - X0) / GRID) + 2)
        j0 = max(0, int((y0 - Y0) / GRID) - 1); j1 = min(NY, int((y1 - Y0) / GRID) + 2)
        return i0, i1, j0, j1

    def cell(p):
        return int(round((p[1] - Y0) / GRID)), int(round((p[0] - X0) / GRID))

    # ---------------------------------------------------------------- items
    IT = []                                             # dict(k, v (net id), net, layers [idx], geometry, bb, rm, id, alive)
    for it in D["items"]:
        if it["k"] == "poly" and it.get("zone") == SOFT_POUR:
            continue                                    # N-3: the L4 pour yields to tracks (refilled after apply)
        v = nid.get(it["net"], 0) or -1
        e = dict(k=it["k"], v=v, net=it["net"], rm=bool(it.get("rm")), id=it.get("id"), alive=True)
        if it["k"] == "poly":
            pts = np.array(it["pts"]); e.update(layers=[L[it["layer"]]], pts=pts, bb=(pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max()))
        elif it["k"] == "seg":
            a, b, r = it["a"], it["b"], it["r"]
            e.update(layers=[L[it["layer"]]], a=tuple(a), b=tuple(b), r=r, bb=(min(a[0], b[0]) - r, min(a[1], b[1]) - r, max(a[0], b[0]) + r, max(a[1], b[1]) + r))
        elif it["k"] == "via":
            c, r = it["c"], it["r"]
            e.update(layers=list(range(NL)), c=tuple(c), r=r, rh=it["rh"], bb=(c[0] - r, c[1] - r, c[0] + r, c[1] + r))
        elif it["k"] == "hole":
            c, r = it["c"], it["r"]
            e.update(layers=[], c=tuple(c), r=r, rh=r, bb=(c[0] - r, c[1] - r, c[0] + r, c[1] + r), rm=False)
        IT.append(e)

    def paint(e, val=None):
        lab = labR if e["rm"] else labF; hol = holeR if e["rm"] else holeF
        v = e["v"] if val is None else val
        if e["k"] == "poly":
            pts = e["pts"]; i0, i1, j0, j1 = cbox(*e["bb"])
            if i1 <= i0 or j1 <= j0:
                return
            sub = np.c_[XX[j0:j1, i0:i1].ravel(), YY[j0:j1, i0:i1].ravel()]
            m = Path(pts).contains_points(sub, radius=1e-9).reshape(j1 - j0, i1 - i0)
            lab[e["layers"][0], j0:j1, i0:i1][m] = v
        elif e["k"] == "seg":
            a, b, r = e["a"], e["b"], e["r"]; i0, i1, j0, j1 = cbox(*e["bb"])
            PX, PY = XX[j0:j1, i0:i1], YY[j0:j1, i0:i1]
            dx, dy = b[0] - a[0], b[1] - a[1]; Ls = dx * dx + dy * dy
            t = np.zeros_like(PX) if Ls == 0 else np.clip(((PX - a[0]) * dx + (PY - a[1]) * dy) / Ls, 0, 1)
            m = np.hypot(PX - a[0] - t * dx, PY - a[1] - t * dy) <= r
            lab[e["layers"][0], j0:j1, i0:i1][m] = v
        else:
            c = e["c"]; i0, i1, j0, j1 = cbox(*e["bb"])
            d = np.hypot(XX[j0:j1, i0:i1] - c[0], YY[j0:j1, i0:i1] - c[1])
            if e["k"] == "via":
                for li in range(NL):
                    lab[li, j0:j1, i0:i1][d <= e["r"]] = v
            if val is None or val != 0:
                hol[j0:j1, i0:i1] |= d <= e["rh"]

    if os.environ.get("MAZE_DIAG_SOFT"):           # diagnosis only: which copper walls the pairs in
        kinds = os.environ["MAZE_DIAG_SOFT"].split(",")
        for e in IT:
            if e["k"] in ("seg", "via") and ("all" in kinds or e["net"] not in NORIP):
                e["rm"] = True
            if "pads" in kinds and e["k"] == "poly":
                e["rm"] = True
    for e in IT:
        paint(e)
    BB = np.array([e["bb"] for e in IT])

    def repaint_R(bb):
        i0, i1, j0, j1 = cbox(*bb)
        labR[:, j0:j1, i0:i1] = 0; holeR[j0:j1, i0:i1] = False
        labF[:, j0:j1, i0:i1] = 0; holeF[j0:j1, i0:i1] = False
        hit = np.nonzero((BB[:, 0] <= bb[2] + 0.1) & (BB[:, 2] >= bb[0] - 0.1) & (BB[:, 1] <= bb[3] + 0.1) & (BB[:, 3] >= bb[1] - 0.1))[0]
        for k in hit:
            if IT[k]["alive"]:
                paint(IT[k])

    def add_item(e):
        nonlocal BB
        IT.append(e); BB = np.vstack([BB, np.array(e["bb"])[None, :]]); paint(e)
        journal.append(("add", len(IT) - 1))
        return len(IT) - 1

    # ---------------------------------------------------------------- static masks
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
    d_trk = [edt(~trk_block[li]) for li in range(NL)]
    d_vblk = edt(~via_block)
    d_plate = edt(~plate)
    forb = set(D["forb"])
    hist = np.zeros((NY, NX), np.float32)
    ripcnt = {}
    removed = set()                                     # uuids of board items ripped
    failed = []

    # ---------------------------------------------------------------- connectivity of router copper
    def comp_of(k0):
        n = IT[k0]["v"]
        cand = [k for k in range(len(IT)) if IT[k]["rm"] and IT[k]["alive"] and IT[k]["v"] == n and IT[k]["k"] in ("seg", "via")]
        seen = {k0}; dq = deque([k0])
        while dq:
            a = IT[dq.popleft()]
            for k in cand:
                if k in seen:
                    continue
                b = IT[k]
                if a["k"] == "seg" and b["k"] == "seg":
                    ok = a["layers"][0] == b["layers"][0] and segseg(a["a"], a["b"], b["a"], b["b"]) <= max(a["r"], b["r"]) + 1e-3
                elif a["k"] == "via" and b["k"] == "via":
                    ok = math.hypot(a["c"][0] - b["c"][0], a["c"][1] - b["c"][1]) <= a["r"] + b["r"]
                else:
                    s_, v_ = (a, b) if a["k"] == "seg" else (b, a)
                    ok = segdist(s_["a"], s_["b"], v_["c"]) <= v_["r"] + 1e-3
                if ok and not on_fixed(a, b, n):
                    seen.add(k); dq.append(k)
        return sorted(seen)

    def on_fixed(a, b, n):
        """True when the contact point of router items a, b lies on fixed copper of their net (a pad or fan-out copper):
        the component stops there, so a rip takes only the run between two terminals"""
        if a["k"] == "via" and b["k"] == "via":
            p = ((a["c"][0] + b["c"][0]) / 2, (a["c"][1] + b["c"][1]) / 2); lays = range(NL)
        elif a["k"] == "via" or b["k"] == "via":
            v_ = a if a["k"] == "via" else b; p = v_["c"]; lays = range(NL)
        else:
            cands = [(math.hypot(p[0] - q[0], p[1] - q[1]), p) for p in (a["a"], a["b"]) for q in (b["a"], b["b"])]
            p = min(cands)[1]; lays = a["layers"]
        j, i = cell(p)
        return any((labF[li, max(0, j - 1):j + 2, max(0, i - 1):i + 2] == n).any() for li in lays)

    def terminals(comp, n):
        """touch points of the component on fixed copper of its own net (checked after the component is removed)"""
        res = []
        for k in comp:
            e = IT[k]
            pl = [(e["a"], e["layers"]), (e["b"], e["layers"])] if e["k"] == "seg" else [(e["c"], list(range(NL)))]
            for p, lays in pl:
                j, i = cell(p)
                if not (0 <= j < NY and 0 <= i < NX):
                    continue
                hit = [li for li in lays if (labF[li, max(0, j - 1):j + 2, max(0, i - 1):i + 2] == n).any() or
                       (labR[li, max(0, j - 1):j + 2, max(0, i - 1):i + 2] == n).any()]
                for li in hit:                                # one terminal per layer: a ripped via leaves one island per layer
                    res.append(dict(p=p, layers=[SIG[li]], net=nets[n - 1], kind="TERM"))
        out = []
        for t in res:
            if all(t["layers"] != u["layers"] or math.hypot(t["p"][0] - u["p"][0], t["p"][1] - u["p"][1]) > 0.05 for u in out):
                out.append(t)
        return out

    journal = []

    def rollback(mark):
        bb = [1e9, 1e9, -1e9, -1e9]
        while len(journal) > mark:
            kind, x = journal.pop()
            ks = [x] if kind == "add" else x
            for k in ks:
                e = IT[k]; e["alive"] = (kind == "rip")
                if kind == "rip" and e["id"] and e["id"] != "new":
                    removed.discard(e["id"])
                b = e["bb"]; bb = [min(bb[0], b[0]), min(bb[1], b[1]), max(bb[2], b[2]), max(bb[3], b[3])]
        if bb[0] < 1e9:
            repaint_R(bb)

    def rip_set(ks):
        """[S2e] partial rip: only the blocking router segments / vias go; the cut ends left on the board are the terminals"""
        if os.environ.get("MAZE_RIP_RUN"):
            out_ = []
            for k in ks:
                if IT[k]["alive"]:
                    out_ += rip(k)
            return out_
        journal.append(("rip", list(ks)))
        bb = [1e9, 1e9, -1e9, -1e9]; bynet = {}
        for k in ks:
            e = IT[k]; e["alive"] = False
            if e["id"] and e["id"] != "new":
                removed.add(e["id"])
            b = e["bb"]; bb = [min(bb[0], b[0]), min(bb[1], b[1]), max(bb[2], b[2]), max(bb[3], b[3])]
            bynet.setdefault(e["v"], []).append(k)
        repaint_R(bb)
        res = []
        for n, kk in bynet.items():
            T = terminals(kk, n)
            ripcnt[n] = ripcnt.get(n, 0) + 1
            res += [[T[0], t] for t in T[1:]]
        return res

    def rip(k0):
        comp = comp_of(k0)
        journal.append(("rip", comp))
        n = IT[k0]["v"]; bb = [1e9, 1e9, -1e9, -1e9]
        for k in comp:
            e = IT[k]; e["alive"] = False
            if e["id"] and not e["id"].startswith("new"):
                removed.add(e["id"])
            b = e["bb"]; bb = [min(bb[0], b[0]), min(bb[1], b[1]), max(bb[2], b[2]), max(bb[3], b[3])]
        repaint_R(bb)
        T = terminals(comp, n)
        ripcnt[n] = ripcnt.get(n, 0) + 1
        return [[T[0], t] for t in T[1:]] if len(T) > 1 else []

    # ---------------------------------------------------------------- one pair
    def own(li, j, i, n):
        return labF[li, j, i] == n or (labF[li, j, i] == 0 and labR[li, j, i] == n)

    def own_cells(e, n, lab=None):
        li_s = [L[l] for l in e["layers"] if l in L] or list(range(NL))
        j, i = cell(e["p"])
        res = [(li, j + dj, i + di) for li in li_s for dj in range(-3, 4) for di in range(-3, 4)
               if 0 <= j + dj < NY and 0 <= i + di < NX and own(li, j + dj, i + di, n)]
        if not res:
            return None
        seen = set(res); st = list(res)
        while st and len(seen) < 40000:
            li, jj, ii = st.pop()
            for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                q = (li, jj + dj, ii + di)
                if 0 <= q[1] < NY and 0 <= q[2] < NX and q not in seen and own(q[0], q[1], q[2], n):
                    seen.add(q); st.append(q)
            if holeF[jj, ii] or holeR[jj, ii]:
                for l2 in range(NL):
                    q = (l2, jj, ii)
                    if q not in seen and own(q[0], q[1], q[2], n):
                        seen.add(q); st.append(q)
        return list(seen)

    nb = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0), (-1, -1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (1, 1, 1.414)]

    def route_pair(pr, allow_rip=True):
        net = pr[0]["net"] or pr[1]["net"]
        if not net or net not in nid:
            return "no net", None
        n = nid[net]; ru = D["rules"][net]; w = ru["w"]; c_n = ru["clr"]; vd, vh = ru["via"]
        S = own_cells(pr[0], n); T = own_cells(pr[1], n)
        pm = float(os.environ.get("MAZE_TERM_PM", "1.0")) if pr[0]["kind"] == "TERM" else 1.0       # a reconnect of a ripped run rips others only at a higher price
        if S is None and pr[0]["kind"] in ("PCB_TRACK", "PCB_VIA", "TERM"):
            return "end ripped", None
        if T is None and pr[1]["kind"] in ("PCB_TRACK", "PCB_VIA", "TERM"):
            return "end ripped", None
        if S is None:
            j, i = cell(pr[0]["p"]); S = [(L[l], j, i) for l in pr[0]["layers"] if l in L]
        if T is None:
            j, i = cell(pr[1]["p"]); T = [(L[l], j, i) for l in pr[1]["layers"] if l in L]
        Ss = set(S); T = set(T) - Ss
        if not T or not S:
            return "ends already joined", None
        span = int((WIN if tries_now[0] > 1 else min(WIN, 4.0)) / GRID); pad = int(1.0 / GRID)
        ea, eb = cell(pr[0]["p"]), cell(pr[1]["p"])      # [S2e] window from the two end points, not from the whole copper islands
        jmin = max(0, min(ea[0], eb[0]) - span); jmax = min(NY, max(ea[0], eb[0]) + span)
        imin = max(0, min(ea[1], eb[1]) - span); imax = min(NX, max(ea[1], eb[1]) + span)
        inw = lambda c: jmin + 1 <= c[1] < jmax - 1 and imin + 1 <= c[2] < imax - 1
        Sw = {c for c in Ss if inw(c)}; Tw = {c for c in T if inw(c)}
        if not Sw or not Tw:
            return "no path (end outside window)", None
        Ss, T = Sw, Tw
        allc = list(Ss) + list(T)
        wj0, wj1, wi0, wi1 = max(0, jmin - pad), min(NY, jmax + pad), max(0, imin - pad), min(NX, imax + pad)
        sl = (slice(wj0, wj1), slice(wi0, wi1))
        lf = labF[:, sl[0], sl[1]]; lr = labR[:, sl[0], sl[1]]
        oF = (lf != 0) & (lf != n); oR = (lr != 0) & (lr != n)
        hF = oF & hi_lut[lf + 1]; hR = oR & hi_lut[lr + 1]
        hoF = holeF[sl]; hoA = hoF | holeR[sl]
        de = d_edge[sl]; dm = d_motor[sl]
        shp = (NL, wj1 - wj0, wi1 - wi0)
        freeH = np.ones(shp, bool); freeA = np.ones(shp, bool)
        vbase = (d_vblk[sl] >= vd / 2 + 0.04) & (de >= 0.30 + vd / 2 + MARGIN) & (dm >= 0.30 + vd / 2 + MARGIN)
        vH = vbase.copy(); vA = vbase.copy()
        dhoF = edt(~hoF); dhoA = edt(~hoA)
        for li in range(NL):
            base = (d_trk[li][sl] >= w / 2 + 0.04) & (de >= 0.30 + w / 2 + MARGIN) & (dm >= 0.30 + w / 2 + MARGIN)
            for (lo_, hi_, fr, vv, dho) in (((oF[li] & ~hF[li]), hF[li], freeH, vH, dhoF), (((oF[li] | oR[li]) & ~(hF[li] | hR[li])), hF[li] | hR[li], freeA, vA, dhoA)):
                dl = edt(~lo_); dh = edt(~hi_)
                fr[li] = base & (dl >= w / 2 + max(c_n, 0.09) + MARGIN) & (dh >= w / 2 + max(c_n, 0.20) + MARGIN) & (dho >= w / 2 + 0.20 + MARGIN)
                vv &= (dl >= vd / 2 + max(c_n, 0.09) + MARGIN) & (dh >= vd / 2 + max(c_n, 0.20) + MARGIN) & (np.minimum(dl, dh) >= vh + 0.20 + MARGIN)
        vH &= dhoF >= vh + 0.20 + MARGIN; vA &= dhoA >= vh + 0.20 + MARGIN
        if net in forb:
            dp = d_plate[sl]
            vH &= dp >= vd / 2 + 0.04; vA &= dp >= vd / 2 + 0.04
            for li in (L["In2.Cu"], L["In3.Cu"], L["In4.Cu"]):
                freeH[li] &= dp >= w / 2 + 0.04; freeA[li] &= dp >= w / 2 + 0.04
        for (li, jj, ii) in allc:
            if wj0 <= jj < wj1 and wi0 <= ii < wi1:
                freeH[li, jj - wj0, ii - wi0] = True; freeA[li, jj - wj0, ii - wi0] = True
        if not allow_rip:
            freeH = freeA; vH = vA
        soft = freeH & ~freeA; vsoft = vH & ~vA
        # cost of a soft cell: rip count of the nearest blocking router net + contest history
        pen = None
        if soft.any() or vsoft.any():
            pen = np.zeros(shp, np.float32)
            rc = np.zeros(len(nets) + 2, np.float32)
            for k_, c_ in ripcnt.items():
                rc[k_] = c_
            hw = hist[sl]
            for li in range(NL):                         # cost of crossing router copper: base x rips of the net there + contest history
                pen[li] = pm * RIP_PEN * (1 + rc[np.clip(lr[li], 0, None)]) + HIST_W * hw
        # an end with no reachable neighbour cell even through router copper: fail at once
        def end_open(C, Cs):
            for (li, j, i) in C:
                a_, b_ = j - wj0, i - wi0
                if vH[a_, b_]:
                    return True
                for dj, di, _ in nb:
                    if 0 <= a_ + dj < shp[1] and 0 <= b_ + di < shp[2] and freeH[li, a_ + dj, b_ + di] and (li, j + dj, i + di) not in Cs:
                        return True
            return False
        if not end_open(Ss, Ss) or (not plane_goal_net(net) and not end_open(T, T)):
            return "no path (blocked end)", None
        # A* on flat lists (window frame); cost -1 = blocked
        Hh, Ww = shp[1], shp[2]; HWn = Hh * Ww
        lc = np.array(LAYER_COST, np.float32)[:, None, None]
        Cm = np.where(freeA, lc, np.where(freeH, lc + (pen if pen is not None else 0), -1.0)).astype(np.float32)
        inb = np.zeros((Hh, Ww), bool); inb[jmin - wj0 + 0:jmax - wj0, imin - wi0:imax - wi0] = True
        inb[0, :] = inb[-1, :] = False; inb[:, 0] = inb[:, -1] = False
        Cm[:, ~inb] = -1.0
        VC = 1.2 / GRID
        pmax = pen.max(axis=0) if pen is not None else 0.0
        Vm = np.where(vA, VC, np.where(vH, VC + 10.0 * pmax, -1.0)); Vm[~inb] = -1.0
        C = Cm.ravel().tolist(); V = Vm.ravel().tolist()
        tj = np.mean([t[1] for t in T]) - wj0; ti = np.mean([t[2] for t in T]) - wi0
        AA, BBm = np.meshgrid(np.arange(Hh), np.arange(Ww), indexing="ij")
        Hl = (HW * np.hypot(AA - tj, BBm - ti)).ravel().tolist()
        plane_goal = net == "GND"
        PG = (vA & ~hoA & inb).ravel().tolist() if plane_goal else None
        def fidx(c):
            return (c[0] * Hh + (c[1] - wj0)) * Ww + (c[2] - wi0)
        Tset = {fidx(t) for t in T}
        NN = NL * HWn
        g = [1e18] * NN; prev = [-1] * NN; pq = []
        for s_ in Ss:
            k = fidx(s_); g[k] = 0.0; heapq.heappush(pq, (Hl[k % HWn], 0.0, k))
        goal = None; nexp = 0; plane_via = False
        nbo = [(dj * Ww + di, cst) for dj, di, cst in nb]
        hp, hpush = heapq.heappop, heapq.heappush
        while pq and nexp < EXP:
            f_, gc, u = hp(pq)
            if gc > g[u]:
                continue
            nexp += 1
            if u in Tset:
                goal = u; break
            c2 = u % HWn
            if plane_goal and PG[c2]:
                goal = u; plane_via = True; break
            for off, cst in nbo:
                v = u + off
                cv = C[v]
                if cv < 0:
                    continue
                ng = gc + cst * cv
                if ng < g[v]:
                    g[v] = ng; prev[v] = u; hpush(pq, (ng + Hl[v % HWn], ng, v))
            vc = V[c2]
            if vc >= 0:
                l0 = u // HWn
                for l2 in range(NL):
                    if l2 != l0:
                        v = l2 * HWn + c2
                        if C[v] >= 0:
                            ng = gc + vc
                            if ng < g[v]:
                                g[v] = ng; prev[v] = u; hpush(pq, (ng + Hl[c2], ng, v))
        def unf(k):
            li_, r_ = divmod(k, HWn); a_, b_ = divmod(r_, Ww)
            return (li_, a_ + wj0, b_ + wi0)
        if goal is not None:
            pth = [goal]
            while prev[pth[-1]] >= 0:
                pth.append(prev[pth[-1]])
            path_cells = [unf(k) for k in reversed(pth)]
            goal = path_cells[-1]
        if goal is None:
            return "no path (expanded %d)" % nexp, None
        if os.environ.get("MAZE_DIAG"):
            return "diag ok", None
        path = path_cells
        segs, vias = [], []
        run = [path[0]]
        for q in path[1:]:
            if q[0] != run[-1][0]:
                vias.append((q[1], q[2]))
                if len(run) > 1:
                    segs.append((run[0][0], run))
                run = [q]
            else:
                run.append(q)
        if len(run) > 1:
            segs.append((run[0][0], run))
        if plane_via:
            vias.append((goal[1], goal[2]))
        # soft cells used -> rip the router components that block them
        softpts = [(q[0], q[1], q[2], "t") for q in path if not freeA[q[0], q[1] - wj0, q[2] - wi0]]
        softpts += [(None, j, i, "v") for (j, i) in vias if not vA[j - wj0, i - wi0]]
        reroute = []
        if softpts:
            P_ = [(float(gx[i]), float(gy[j]), li, kd) for (li, j, i, kd) in softpts]
            px = [p[0] for p in P_]; py = [p[1] for p in P_]
            bb = (min(px) - 1.0, min(py) - 1.0, max(px) + 1.0, max(py) + 1.0)
            hit = np.nonzero((BB[:, 0] <= bb[2]) & (BB[:, 2] >= bb[0]) & (BB[:, 1] <= bb[3]) & (BB[:, 3] >= bb[1]))[0]
            torip = []
            for k in hit:
                e = IT[k]
                if not (e["rm"] and e["alive"] and e["v"] != n and e["k"] in ("seg", "via") and not e.get("norip")) or k >= prot[0]:
                    continue
                ce = clr_of[e["v"]] if e["v"] > 0 else 0.09
                need_c = max(c_n, ce, 0.20 if (ce >= 0.15 or c_n >= 0.15) else 0.09)
                for (x, y, li, kd) in P_:
                    rr = (vd / 2) if kd == "v" else (w / 2)
                    if kd == "t" and li not in e["layers"]:
                        continue
                    d = segdist(e["a"], e["b"], (x, y)) if e["k"] == "seg" else math.hypot(x - e["c"][0], y - e["c"][1])
                    thr = e["r"] + rr + need_c + MARGIN
                    if e["k"] == "via":
                        thr = max(thr, e["rh"] + rr + 0.20 + MARGIN, (e["rh"] + vh + 0.20 + MARGIN) if kd == "v" else 0)
                    if kd == "v" and e["k"] == "seg":
                        thr = max(thr, e["r"] + vh + 0.20 + MARGIN)
                    if d < thr:
                        torip.append(k); break
            for (li, j, i, kd) in softpts:
                hist[max(0, j - 2):j + 3, max(0, i - 2):i + 3] += 1.0
            if torip:
                reroute += rip_set(sorted(set(torip)))
        # commit the new copper (router copper itself, rippable later)
        new = []
        for li, run_ in segs:
            pl = [(float(gx[r[2]]), float(gy[r[1]])) for r in run_]
            simp = [pl[0]]
            for k in range(1, len(pl) - 1):
                a, b, c = simp[-1], pl[k], pl[k + 1]
                if abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) > 1e-9:
                    simp.append(b)
            simp.append(pl[-1])
            for a, b in zip(simp, simp[1:]):
                r = w / 2
                new.append(add_item(dict(k="seg", v=n, net=net, rm=False, norip=net in NORIP, id="new", alive=True, layers=[li], a=a, b=b, r=r,
                                         bb=(min(a[0], b[0]) - r, min(a[1], b[1]) - r, max(a[0], b[0]) + r, max(a[1], b[1]) + r))))
        for (j, i) in vias:
            c = (float(gx[i]), float(gy[j]))
            new.append(add_item(dict(k="via", v=n, net=net, rm=False, norip=net in NORIP, id="new", alive=True, layers=list(range(NL)), c=c, r=vd / 2,
                                     rh=vh, d=vd, bb=(c[0] - vd / 2, c[1] - vd / 2, c[0] + vd / 2, c[1] + vd / 2))))
        return "ok", reroute

    DEPTH = int(os.environ.get("MAZE_DEPTH", "2"))
    prot = [10 ** 9]                                     # copper added inside the running transaction is never ripped by it

    def txn(pr, depth):
        """route pr; every run it rips must be rerouted (rips allowed down to depth 0), else everything is undone"""
        mark = len(journal)
        why, rr = route_pair(pr, allow_rip=depth > 0)
        if why != "ok":
            rollback(mark); return why, 0
        nr = 0
        for q in rr or []:
            w2, n2 = txn(q, depth - 1)
            if w2 not in ("ok", "ends already joined"):
                rollback(mark); return "rip not restorable (%s: %s)" % (q[0]["net"], w2), 0
            nr += 1 + n2
        return "ok", nr

    # ---------------------------------------------------------------- negotiated loop
    Q = deque(sorted(D["pairs"], key=lambda pr: math.hypot(pr[0]["p"][0] - pr[1]["p"][0], pr[0]["p"][1] - pr[1]["p"][1])))
    tries = {}; nok = 0; nrip = 0; it_ = 0; tries_now = [1]
    if os.environ.get("MAZE_DIAG"):
        res = {}
        for pr in Q:
            for win in (4.0, 8.0):
                tries_now[0] = 1 if win == 4.0 else 2
                why, _ = route_pair(pr)
                if why == "diag ok":
                    break
            k = why[:20]; res[k] = res.get(k, 0) + 1
        print("DIAG", os.environ.get("MAZE_DIAG_SOFT"), res); return
    while Q and time.time() - t_start < TLIM:
        pr = Q.popleft(); it_ += 1
        key = (pr[0]["net"] or pr[1]["net"], tuple(round(v, 1) for v in pr[0]["p"]), tuple(round(v, 1) for v in pr[1]["p"]))
        tries[key] = tries.get(key, 0) + 1
        if tries[key] > MAXTRY:
            failed.append(dict(net=key[0], a=pr[0]["p"], b=pr[1]["p"], why="max tries")); continue
        tries_now[0] = tries[key]
        prot[0] = len(IT)
        why, nr = txn(pr, DEPTH)
        if why == "ok":                                  # the transaction's copper becomes ordinary router copper
            bb = [1e9, 1e9, -1e9, -1e9]
            for k in range(prot[0], len(IT)):
                e = IT[k]
                if e["alive"] and not e["rm"] and not e.get("norip"):      # plane-net copper stays fixed (never soft)
                    e["rm"] = True; b = e["bb"]; bb = [min(bb[0], b[0]), min(bb[1], b[1]), max(bb[2], b[2]), max(bb[3], b[3])]
            if bb[0] < 1e9:
                repaint_R(bb)
        prot[0] = 10 ** 9
        if why == "ok":
            nok += 1; nrip += 1 if nr else 0
            print("it %d ok %s (%d ripped runs restored, queue %d, %.0f s)" % (it_, key[0], nr, len(Q), time.time() - t_start), flush=True)
        elif why.startswith("rip not") and tries[key] < MAXTRY:
            print("it %d retry %s %s" % (it_, key[0], why), flush=True)
            Q.append(pr)                                 # history raster has grown: the next try takes another way
        elif why.startswith("no path") and tries[key] == 1 and WIN > 4.0:
            Q.append(pr)
        elif why not in ("ends already joined", "end ripped"):
            failed.append(dict(net=key[0], a=pr[0]["p"], b=pr[1]["p"], why=why))
            print("it %d FAIL %s %s" % (it_, key[0], why), flush=True)
    for pr in Q:
        failed.append(dict(net=pr[0]["net"] or pr[1]["net"], a=pr[0]["p"], b=pr[1]["p"], why="time"))
    # ---------------------------------------------------------------- output: live new copper, removed board items
    routes = {}
    for e in IT:
        if e["id"] == "new" and e["alive"]:
            r = routes.setdefault(e["net"], dict(net=e["net"], segs=[], vias=[]))
            if e["k"] == "seg":
                r["segs"].append(dict(layer=SIG[e["layers"][0]], a=e["a"], b=e["b"], w=2 * e["r"]))
            else:
                r["vias"].append(dict(c=e["c"], d=e["d"], h=e["rh"]))
    json.dump(dict(routes=list(routes.values()), removed=sorted(removed), failed=failed,
                   stats=dict(iterations=it_, routed=nok, with_rip=nrip, ripped_board_items=len(removed), failed=len(failed),
                              seconds=round(time.time() - t_start))), open(out, "w"), indent=0)
    print("rrr: iterations %d routed %d (with rip %d) ripped board items %d failed %d" % (it_, nok, nrip, len(removed), len(failed)))
