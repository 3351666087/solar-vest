"""[layout] Finish the connections the autorouter left (lead's method of 2026-11-15, step 5): grid maze router (A*, 0.05 mm grid) on the
four signal layers F.Cu, In2.Cu (L3), In4.Cu (L5), B.Cu with through vias, run on a dump of the routed board.

  kicad-python maze_finish.py dump  BOARD.kicad_pcb DRC.json GEOM.json FORB.json OUT.json   (copper, keep-outs, unconnected pairs)
  venv-python  maze_finish.py route DUMP.json ROUTES.json                                   (A* per unconnected pair)
  kicad-python maze_finish.py apply BOARD.kicad_pcb ROUTES.json OUT.kicad_pcb               (adds the copper, fills the zones)

Rules used by the router (JLC 6-layer deck of build_board.py): copper to copper >= max(class clearance of both nets, capped 0.20) + 0.04 mm
grid margin; track width = the net class width (0.09 for Default / DISPLAY); via 0.38 / 0.15 (0.35 / 0.15 for classes with clearance
>= 0.10) with its hole >= 0.20 + 0.04 from other-net copper and >= 0.20 from other holes; copper >= 0.30 from the board edge and the motor
cut-out; no copper in the antenna pocket; B.Cu void over the plates; no via within 2.0 mm of a dot centre or on the U10 island; R-2:
PWR_HIGH / VDD_1V8 / ECG-band nets get no via over a plate and no L3 / L5 track over a plate.
"""
import json, math, sys

import os as _os
GRID = float(_os.environ.get("MAZE_GRID", "0.05"))
MARGIN = 1.3 * GRID                 # raster error: obstacle cell centres + path cell centres (0.7 grid each)
SIG = ["F.Cu", "In2.Cu", "In3.Cu", "In4.Cu", "B.Cu"]          # [S2e N-3] L4 (In3.Cu) carries signals; its VDD_1V8 pour yields
SOFT_POUR = "L4_VDD_1V8"
SIG6 = SIG
SIG8 = ["F.Cu", "In2.Cu", "In3.Cu", "In5.Cu", "In6.Cu", "B.Cu"]       # [grow8 P-5] 8 layers: In1 GND plane, In4 VDD_1V8 full plane


def _lid(brd):                                                         # [grow8] every copper layer of the board, 6 or 8
    import pcbnew
    ids = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.In5_Cu, pcbnew.In6_Cu, pcbnew.B_Cu]
    return {brd.GetLayerName(l): l for l in ids if brd.IsLayerEnabled(l)}
NORIP = ("GND", "VDD_1V8")                                   # router copper of the plane nets is never ripped (it reaches L2 / the L4 pours)


# =============================================================================================== dump (KiCad python)
def dump(pcb, drc, geomf, forbf, out):
    import pcbnew
    TO = pcbnew.ToMM
    brd = pcbnew.LoadBoard(pcb)
    G = json.load(open(geomf))["G"]
    global SIG
    NLB = brd.GetCopperLayerCount()
    SIG = SIG8 if NLB == 8 else SIG6
    lid = _lid(brd)
    items = []
    keepset = set()
    if _os.environ.get("MAZE_KEEP_FROM"):
        for t in pcbnew.LoadBoard(_os.environ["MAZE_KEEP_FROM"]).GetTracks():
            keepset.add((t.GetClass(), t.GetLayer(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y))

    def removable(t):
        return not t.IsLocked() and t.GetNetname() not in NORIP and \
            (t.GetClass(), t.GetLayer(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y) not in keepset

    def poly(ps):
        res = []
        for k in range(ps.OutlineCount()):
            ol = ps.Outline(k)
            res.append([(TO(ol.CPoint(i).x), TO(ol.CPoint(i).y)) for i in range(ol.PointCount())])
        return res
    pads = []                                                              # [grow8 Q-2] pad copper per net (neck-down zones)
    for f in brd.GetFootprints():
        for p in f.Pads():
            if p.GetNetname():
                pp = []
                for ln in SIG:
                    if p.IsOnLayer(lid[ln]):
                        ps = pcbnew.SHAPE_POLY_SET(); p.TransformShapeToPolygon(ps, lid[ln], 0, pcbnew.FromMM(0.005), pcbnew.ERROR_INSIDE)
                        pp += poly(ps)
                        break
                c = p.GetPosition()
                pads.append(dict(ref=f.GetReference(), num=p.GetNumber(), net=p.GetNetname(), c=(TO(c.x), TO(c.y)), pts=pp))
            for ln in SIG:
                if p.IsOnLayer(lid[ln]):
                    ps = pcbnew.SHAPE_POLY_SET(); p.TransformShapeToPolygon(ps, lid[ln], 0, pcbnew.FromMM(0.005), pcbnew.ERROR_INSIDE)
                    for pg in poly(ps):
                        items.append(dict(k="poly", net=p.GetNetname(), layer=ln, pts=pg))
            if p.GetDrillSize().x > 0:
                c = p.GetPosition(); items.append(dict(k="hole", net=p.GetNetname(), c=(TO(c.x), TO(c.y)), r=TO(p.GetDrillSize().x) / 2))
        for g in f.GraphicalItems():
            if brd.GetLayerName(g.GetLayer()) in SIG:
                ps = pcbnew.SHAPE_POLY_SET(); g.TransformShapeToPolygon(ps, g.GetLayer(), 0, pcbnew.FromMM(0.005), pcbnew.ERROR_INSIDE)
                for pg in poly(ps):
                    items.append(dict(k="poly", net="", layer=brd.GetLayerName(g.GetLayer()), pts=pg))
    for t in brd.GetTracks():
        if t.GetClass() == "PCB_VIA":
            c = t.GetPosition()
            items.append(dict(k="via", net=t.GetNetname(), c=(TO(c.x), TO(c.y)), r=TO(t.GetWidth(pcbnew.F_Cu)) / 2, rh=TO(t.GetDrill()) / 2,
                              id=t.m_Uuid.AsString(), rm=removable(t)))
        else:
            ln = brd.GetLayerName(t.GetLayer())
            if ln in SIG:
                items.append(dict(k="seg", net=t.GetNetname(), layer=ln, a=(TO(t.GetStart().x), TO(t.GetStart().y)),
                                  b=(TO(t.GetEnd().x), TO(t.GetEnd().y)), r=TO(t.GetWidth()) / 2, id=t.m_Uuid.AsString(), rm=removable(t)))
    keep = []
    zones = list(brd.Zones())
    for z in zones:
        if z.GetIsRuleArea():
            ps = pcbnew.SHAPE_POLY_SET(z.Outline()); ps.Fracture()          # holes (dot key-holes) become slits
            for pg in poly(ps):
                keep.append(dict(name=z.GetZoneName(), layers=[ln for ln in lid if z.IsOnLayer(lid[ln])], tracks=z.GetDoNotAllowTracks(),
                                 vias=z.GetDoNotAllowVias(), pts=pg))
        else:
            for ln in SIG:
                if z.IsOnLayer(lid[ln]):
                    for pg in poly(z.GetFilledPolysList(lid[ln])):
                        items.append(dict(k="poly", net=z.GetNetname(), layer=ln, pts=pg, zone=z.GetZoneName()))
    d = json.load(open(drc))
    U = {}
    for f in brd.GetFootprints():
        for p in f.Pads():
            U[p.m_Uuid.AsString()] = p
    for t in brd.GetTracks():
        U[t.m_Uuid.AsString()] = t
    for z in zones:
        U[z.m_Uuid.AsString()] = z
    pairs = []
    for v in d.get("unconnected_items", []):
        ends = []
        for it in v["items"]:
            obj = U.get(it["uuid"])
            p = (it["pos"]["x"], it["pos"]["y"])
            net = it["description"][it["description"].index("[") + 1:it["description"].index("]")] if "[" in it["description"] else ""
            layers = SIG
            if obj is not None and obj.GetClass() == "PCB_TRACK":
                layers = [brd.GetLayerName(obj.GetLayer())]
            elif obj is not None and obj.GetClass() == "PAD":
                layers = [ln for ln in SIG if obj.IsOnLayer(lid[ln])]
            pz = False
            if obj is not None and obj.GetClass() == "ZONE":
                layers = [ln for ln in SIG if obj.IsOnLayer(lid[ln])]
                pz = not layers                                        # [grow8] zone only on a plane layer (In1 / In4 on 8 layers)
                layers = layers or SIG
            ends.append(dict(p=p, net=net, layers=layers, kind=obj.GetClass() if obj is not None else "?", pz=pz))
        if len(ends) == 2:
            pairs.append(ends)
    NC = json.load(open(G["DESIGN"] + "/netclasses.json"))["netclasses"]
    pro = json.load(open(pcb.replace(".kicad_pcb", ".kicad_pro")))
    cls = {c["name"]: c for c in pro["net_settings"]["classes"]}
    netcls = {}
    for pat in pro["net_settings"]["netclass_patterns"]:
        netcls[pat["pattern"]] = pat["netclass"]
    nets = sorted({it["net"] for it in items} | {e["net"] for pr in pairs for e in pr})
    rules = {n: dict(w=cls[netcls.get(n, "Default")]["track_width"], clr=cls[netcls.get(n, "Default")]["clearance"],
                     via=(cls[netcls.get(n, "Default")]["via_diameter"], cls[netcls.get(n, "Default")]["via_drill"])) for n in nets}
    OX, OY = G["KICAD_ORIGIN"]
    json.dump(dict(nl=NLB, sig=SIG, pads=pads, items=items, keep=keep, pairs=pairs, rules=rules, forb=json.load(open(forbf)),
                   outline=[(OX + x, OY - y) for x, y in G["OUTLINE"]], motor=[OX + G["MOTOR_CENTER"][0], OY - G["MOTOR_CENTER"][1], G["MOTOR_CUT_D"] / 2],
                   plates=[[(OX + x, OY - y) for x, y in pg] for key in ("plate_E1", "plate_E2") for pg in G["SKIN"][key]["poly_board"]],
                   dots=[(OX + x, OY - y) for x, y in G["DOTS"].values()]), open(out, "w"))
    print("dumped", len(items), "items,", len(pairs), "unconnected pairs")


# =============================================================================================== route (venv python, numpy / scipy)
def route(dumpf, out):
    import heapq
    import numpy as np
    from matplotlib.path import Path
    from scipy.ndimage import distance_transform_edt as edt
    D = json.load(open(dumpf))
    xs = [p[0] for p in D["outline"]]; ys = [p[1] for p in D["outline"]]
    X0, Y0 = min(xs) - 0.2, min(ys) - 0.2
    NX = int((max(xs) - X0 + 0.2) / GRID) + 1; NY = int((max(ys) - Y0 + 0.2) / GRID) + 1
    gx = X0 + GRID * np.arange(NX); gy = Y0 + GRID * np.arange(NY)
    XX, YY = np.meshgrid(gx, gy)                               # [NY, NX]
    L = {ln: i for i, ln in enumerate(SIG)}
    nets = sorted(D["rules"]); nid = {n: i + 1 for i, n in enumerate(nets)}; nid[""] = 0
    lab = np.zeros((4, NY, NX), np.int32)                     # copper owner per layer (0 = free, -1 = netless copper)
    hole = np.zeros((NY, NX), bool)

    def cells_box(x0, y0, x1, y1):
        i0 = max(0, int((x0 - X0) / GRID) - 1); i1 = min(NX, int((x1 - X0) / GRID) + 2)
        j0 = max(0, int((y0 - Y0) / GRID) - 1); j1 = min(NY, int((y1 - Y0) / GRID) + 2)
        return i0, i1, j0, j1

    def paint_poly(li, pts, v):
        pts = np.array(pts); i0, i1, j0, j1 = cells_box(pts[:, 0].min(), pts[:, 1].min(), pts[:, 0].max(), pts[:, 1].max())
        if i1 <= i0 or j1 <= j0:
            return
        sub = np.c_[XX[j0:j1, i0:i1].ravel(), YY[j0:j1, i0:i1].ravel()]
        m = Path(pts).contains_points(sub, radius=1e-9).reshape(j1 - j0, i1 - i0)
        lab[li, j0:j1, i0:i1][m] = v

    def segd(a, b, PX, PY):
        ax, ay = a; bx, by = b; dx, dy = bx - ax, by - ay; Ls = dx * dx + dy * dy
        t = np.zeros_like(PX) if Ls == 0 else np.clip(((PX - ax) * dx + (PY - ay) * dy) / Ls, 0, 1)
        return np.hypot(PX - ax - t * dx, PY - ay - t * dy)

    def paint_seg(li, a, b, r, v):
        i0, i1, j0, j1 = cells_box(min(a[0], b[0]) - r, min(a[1], b[1]) - r, max(a[0], b[0]) + r, max(a[1], b[1]) + r)
        m = segd(a, b, XX[j0:j1, i0:i1], YY[j0:j1, i0:i1]) <= r
        lab[li, j0:j1, i0:i1][m] = v

    for it in D["items"]:
        v = nid.get(it["net"], 0) or -1
        if it["k"] == "poly":
            paint_poly(L[it["layer"]], it["pts"], v)
        elif it["k"] == "seg":
            paint_seg(L[it["layer"]], it["a"], it["b"], it["r"], v)
        elif it["k"] == "via":
            for li in range(4):
                paint_seg(li, it["c"], it["c"], it["r"], v)
            i0, i1, j0, j1 = cells_box(it["c"][0] - it["rh"], it["c"][1] - it["rh"], it["c"][0] + it["rh"], it["c"][1] + it["rh"])
            hole[j0:j1, i0:i1] |= np.hypot(XX[j0:j1, i0:i1] - it["c"][0], YY[j0:j1, i0:i1] - it["c"][1]) <= it["rh"]
        elif it["k"] == "hole":
            i0, i1, j0, j1 = cells_box(it["c"][0] - it["r"], it["c"][1] - it["r"], it["c"][0] + it["r"], it["c"][1] + it["r"])
            hole[j0:j1, i0:i1] |= np.hypot(XX[j0:j1, i0:i1] - it["c"][0], YY[j0:j1, i0:i1] - it["c"][1]) <= it["r"]
    clr_of = np.zeros(len(nets) + 2)
    for n, r in D["rules"].items():
        clr_of[nid[n]] = r["clr"]
    # static masks
    pts = np.c_[XX.ravel(), YY.ravel()]
    inside = Path(D["outline"]).contains_points(pts).reshape(NY, NX)
    d_edge = edt(inside) * GRID
    mc = D["motor"]; d_motor = np.hypot(XX - mc[0], YY - mc[1]) - mc[2]
    plate = np.zeros((NY, NX), bool)
    for pg in D["plates"]:
        plate |= Path(pg).contains_points(pts).reshape(NY, NX)
    trk_block = np.zeros((4, NY, NX), bool); via_block = np.zeros((NY, NX), bool)
    for k in D["keep"]:
        if not k["pts"] or len(k["pts"]) < 3:
            continue
        m = Path(k["pts"]).contains_points(pts).reshape(NY, NX)
        if k["name"].endswith("_AREA") or "NOPOUR" in k["name"]:
            continue
        if k["tracks"]:
            for ln in k["layers"]:
                if ln in L:
                    trk_block[L[ln]] |= m
        if k["vias"]:
            via_block |= m
    trk_block[L["B.Cu"]] |= plate
    for dc in D["dots"]:
        via_block |= np.hypot(XX - dc[0], YY - dc[1]) < 2.0
    forb = set(D["forb"])
    routes = []; failed = []
    order = sorted(D["pairs"], key=lambda pr: math.hypot(pr[0]["p"][0] - pr[1]["p"][0], pr[0]["p"][1] - pr[1]["p"][1]))
    for pr in order:
        net = pr[0]["net"] or pr[1]["net"]
        if not net or net not in nid:
            failed.append(dict(net=net, why="no net")); continue
        n = nid[net]; ru = D["rules"][net]; w = ru["w"]; c_n = ru["clr"]
        vd, vh = ru["via"]
        other = (lab != 0) & (lab != n)
        # distance from other-net copper, split by the neighbour's class clearance (0.20 / below)
        hi_ids = [i for i in range(len(clr_of)) if clr_of[i] >= 0.15]
        hi = other & np.isin(lab, hi_ids)
        lo = other & ~hi
        free = np.ones((4, NY, NX), bool); vfree = (edt(~via_block) * GRID >= vd / 2 + 0.04) & (d_edge >= 0.30 + vd / 2 + MARGIN) & (d_motor >= 0.30 + vd / 2 + MARGIN)
        for li in range(4):
            dl = edt(~lo[li]) * GRID; dh = edt(~hi[li]) * GRID
            free[li] = (dl >= w / 2 + max(c_n, 0.09) + MARGIN) & (dh >= w / 2 + max(c_n, 0.20) + MARGIN) & (edt(~trk_block[li]) * GRID >= w / 2 + 0.04)
            free[li] &= (d_edge >= 0.30 + w / 2 + MARGIN) & (d_motor >= 0.30 + w / 2 + MARGIN)
            vfree &= (dl >= vd / 2 + max(c_n, 0.09) + MARGIN) & (dh >= vd / 2 + max(c_n, 0.20) + MARGIN)
            vfree &= (np.minimum(dl, dh) >= vh + 0.20 + MARGIN)
            vfree &= ~((lab[li] == -1) & False)
        dho = edt(~hole) * GRID
        vfree &= dho >= vh + 0.20 + MARGIN
        for li in range(4):                                   # JLC via hole to track 0.20 (existing holes)
            free[li] &= dho >= w / 2 + 0.20 + MARGIN
        if net in forb:
            dpl = edt(~plate) * GRID
            vfree &= dpl >= vd / 2 + 0.04
            free[L["In2.Cu"]] &= dpl >= w / 2 + 0.04; free[L["In4.Cu"]] &= dpl >= w / 2 + 0.04
        # sources / targets: own copper cells of the two ends
        def end_cells(e):
            li_s = [L[l] for l in e["layers"] if l in L]
            j = int(round((e["p"][1] - Y0) / GRID)); i = int(round((e["p"][0] - X0) / GRID))
            res = []
            for li in li_s:
                for dj in range(-3, 4):
                    for di in range(-3, 4):
                        jj, ii = j + dj, i + di
                        if 0 <= jj < NY and 0 <= ii < NX and lab[li, jj, ii] == n:
                            res.append((li, jj, ii))
            if not res:
                for li in li_s:
                    res.append((li, j, i))
                return res
            # grow over the whole copper island of this end (same net, same layer; through own vias to the other layers)
            seen = set(res); stack = list(res)
            while stack and len(seen) < 40000:
                li, jj, ii = stack.pop()
                for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    q = (li, jj + dj, ii + di)
                    if 0 <= q[1] < NY and 0 <= q[2] < NX and q not in seen and lab[q] == n:
                        seen.add(q); stack.append(q)
                if hole[jj, ii]:
                    for l2 in range(4):
                        q = (l2, jj, ii)
                        if q not in seen and lab[q] == n:
                            seen.add(q); stack.append(q)
            return list(seen)
        S = end_cells(pr[0]); T = set(end_cells(pr[1])) - set(S)
        if not T:
            failed.append(dict(net=net, why="ends already joined")); continue
        for (li, jj, ii) in list(S) + list(T):
            free[li, jj, ii] = True
        tj = np.mean([t[1] for t in T]); ti = np.mean([t[2] for t in T])
        jmin = int(max(0, min(min(s[1] for s in S), min(t[1] for t in T)) - int(8 / GRID))); jmax = int(min(NY, max(max(s[1] for s in S), max(t[1] for t in T)) + int(8 / GRID)))
        imin = int(max(0, min(min(s[2] for s in S), min(t[2] for t in T)) - int(8 / GRID))); imax = int(min(NX, max(max(s[2] for s in S), max(t[2] for t in T)) + int(8 / GRID)))
        h = lambda j, i: math.hypot(j - tj, i - ti)
        g = {}; prev = {}; pq = []
        for s in S:
            g[s] = 0.0; heapq.heappush(pq, (h(s[1], s[2]), 0.0, s))
        goal = None; nexp = 0; plane_via = False
        plane_goal = net in ("GND", "VDD_1V8")          # a via anywhere reaches the L2 GND / L4 VDD_1V8 plane
        nb = [(-1, 0, 1.0), (1, 0, 1.0), (0, -1, 1.0), (0, 1, 1.0), (-1, -1, 1.414), (-1, 1, 1.414), (1, -1, 1.414), (1, 1, 1.414)]
        while pq and nexp < int(_os.environ.get("MAZE_EXP", "1500000")):
            f_, gc, u = heapq.heappop(pq)
            if gc > g.get(u, 1e18):
                continue
            nexp += 1
            if u in T:
                goal = u; break
            if plane_goal and vfree[u[1], u[2]] and not hole[u[1], u[2]]:
                goal = u; plane_via = True; break
            li, j, i = u
            for dj, di, cst in nb:
                jj, ii = j + dj, i + di
                if jmin <= jj < jmax and imin <= ii < imax and free[li, jj, ii]:
                    v = (li, jj, ii); ng = gc + cst + (0.3 if li in (0, 3) and lab[li, jj, ii] == 0 and False else 0)
                    if ng < g.get(v, 1e18):
                        g[v] = ng; prev[v] = u; heapq.heappush(pq, (ng + h(jj, ii), ng, v))
            if vfree[j, i]:
                for l2 in range(4):
                    if l2 != li and free[l2, j, i]:
                        v = (l2, j, i); ng = gc + 1.2 / GRID
                        if ng < g.get(v, 1e18):
                            g[v] = ng; prev[v] = u; heapq.heappush(pq, (ng + h(j, i), ng, v))
        if goal is None:
            sfree = sum(1 for (li, j, i) in S for dj, di, _ in nb if 0 <= j + dj < NY and 0 <= i + di < NX and free[li, j + dj, i + di]
                        and (li, j + dj, i + di) not in set(S))
            tfree = sum(1 for (li, j, i) in T for dj, di, _ in nb if 0 <= j + dj < NY and 0 <= i + di < NX and free[li, j + dj, i + di]
                        and (li, j + dj, i + di) not in T)
            failed.append(dict(net=net, a=pr[0]["p"], b=pr[1]["p"], expanded=nexp, ka=pr[0]["kind"], kb=pr[1]["kind"],
                               la=pr[0]["layers"], lb=pr[1]["layers"], S=len(S), T=len(T), sfree=sfree, tfree=tfree)); continue
        path = [goal]
        while path[-1] in prev:
            path.append(prev[path[-1]])
        path.reverse()
        segs, vias = [], []
        run = [path[0]]
        for q in path[1:]:
            if q[0] != run[-1][0]:
                vias.append((float(gx[q[2]]), float(gy[q[1]])))
                if len(run) > 1:
                    segs.append((SIG[run[0][0]], [(float(gx[r[2]]), float(gy[r[1]])) for r in run]))
                run = [q]
            else:
                run.append(q)
        if len(run) > 1:
            segs.append((SIG[run[0][0]], [(float(gx[r[2]]), float(gy[r[1]])) for r in run]))
        if plane_via:
            vias.append((float(gx[goal[2]]), float(gy[goal[1]])))
        # simplify each polyline (drop collinear points), paint into the raster
        out_segs = []
        for ln, pl in segs:
            simp = [pl[0]]
            for k in range(1, len(pl) - 1):
                a, b, c = simp[-1], pl[k], pl[k + 1]
                if abs((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) > 1e-9:
                    simp.append(b)
            simp.append(pl[-1])
            for a, b in zip(simp, simp[1:]):
                out_segs.append(dict(layer=ln, a=a, b=b, w=w)); paint_seg(L[ln], a, b, w / 2, n)
        for c in vias:
            for li in range(4):
                paint_seg(li, c, c, vd / 2, n)
            i0, i1, j0, j1 = cells_box(c[0] - vh, c[1] - vh, c[0] + vh, c[1] + vh)
            hole[j0:j1, i0:i1] |= np.hypot(XX[j0:j1, i0:i1] - c[0], YY[j0:j1, i0:i1] - c[1]) <= vh
        routes.append(dict(net=net, segs=out_segs, vias=[dict(c=c, d=vd, h=vh) for c in vias]))
        print("routed", net, len(out_segs), "segments", len(vias), "vias", flush=True)
    json.dump(dict(routes=routes, failed=failed), open(out, "w"), indent=0)
    print("routed", len(routes), "failed", len(failed))


# =============================================================================================== apply (KiCad python)
def apply(pcb, routesf, out):
    import pcbnew, shutil
    MM = pcbnew.FromMM
    brd = pcbnew.LoadBoard(pcb)
    lid = _lid(brd)
    R = json.load(open(routesf))
    gone = set(R.get("removed", []))
    nrm = 0
    for t in list(brd.GetTracks()):
        if t.m_Uuid.AsString() in gone:
            brd.Remove(t); nrm += 1
    print("ripped", nrm, "router items")
    for r in R["routes"]:
        net = brd.FindNet(r["net"])
        for s in r["segs"]:
            t = pcbnew.PCB_TRACK(brd); t.SetStart(pcbnew.VECTOR2I(MM(s["a"][0]), MM(s["a"][1]))); t.SetEnd(pcbnew.VECTOR2I(MM(s["b"][0]), MM(s["b"][1])))
            t.SetWidth(MM(s["w"])); t.SetLayer(lid[s["layer"]]); t.SetNet(net); brd.Add(t)
        for v in r["vias"]:
            x = pcbnew.PCB_VIA(brd); x.SetViaType(pcbnew.VIATYPE_THROUGH); x.SetPosition(pcbnew.VECTOR2I(MM(v["c"][0]), MM(v["c"][1])))
            x.SetDrill(MM(v["h"])); x.SetWidth(MM(v["d"])); x.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); x.SetNet(net)
            x.SetFillingMode(pcbnew.FILLING_MODE_FILLED); x.SetCappingMode(pcbnew.CAPPING_MODE_CAPPED); brd.Add(x)
    pcbnew.ZONE_FILLER(brd).Fill(brd.Zones())
    brd.Save(out)
    base_in, base_out = pcb[:-len(".kicad_pcb")], out[:-len(".kicad_pcb")]
    import os
    for ext in (".kicad_pro", ".kicad_dru"):
        if base_out != base_in:
            txt = open(base_in + ext).read().replace(os.path.basename(base_in) + ".kicad_pro", os.path.basename(base_out) + ".kicad_pro")
            open(base_out + ext, "w").write(txt)
    print("applied", len(R["routes"]), "routes ->", out)


# =============================================================================================== strip (KiCad python)
def strip(pcb, drc, out):
    import os
    """delete every track / via named in an error-level DRC violation (the router's copper that breaks the JLC deck); pads stay"""
    import pcbnew, os
    brd = pcbnew.LoadBoard(pcb)
    U = {t.m_Uuid.AsString(): t for t in brd.GetTracks()}
    d = json.load(open(drc))
    gone = set(); kinds = {}
    ref = os.environ.get("MAZE_KEEP_FROM")                 # board whose copper is never stripped (the fan-out board)
    keep = set()
    if ref:
        for t in pcbnew.LoadBoard(ref).GetTracks():
            keep.add((t.GetClass(), t.GetLayer(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y))
    for t in brd.GetTracks():
        t.SetLocked(False)
    for v in d.get("violations", []):
        if v["severity"] != "error" and (v["type"] not in ("track_dangling", "via_dangling") or os.environ.get("MAZE_STRIP_ERRORS_ONLY")):
            continue
        if v["type"] == "unconnected_items":
            continue
        for it in v["items"]:
            t = U.get(it["uuid"])
            if t is not None and (t.GetClass(), t.GetLayer(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y) in keep:
                continue
            if t is not None and it["uuid"] not in gone:
                gone.add(it["uuid"]); kinds[v["type"]] = kinds.get(v["type"], 0) + 1
                brd.Remove(t)
    nd = 0
    pcbnew.ZONE_FILLER(brd).Fill(brd.Zones())
    brd.Save(out)
    base_in, base_out = pcb[:-len(".kicad_pcb")], out[:-len(".kicad_pcb")]
    for ext in (".kicad_pro", ".kicad_dru"):
        if base_out != base_in:
            txt = open(base_in + ext).read().replace(os.path.basename(base_in) + ".kicad_pro", os.path.basename(base_out) + ".kicad_pro")
            open(base_out + ext, "w").write(txt)
    print("stripped", len(gone), "items", kinds, "+ dangling tracks", nd)


if __name__ == "__main__":
    m = sys.argv[1]
    if m == "dump":
        dump(*sys.argv[2:7])
    elif m == "route":
        route(*sys.argv[2:4])
    elif m == "rrr":
        import maze_rrr
        maze_rrr.route(*sys.argv[2:4])
    elif m == "strip":
        strip(*sys.argv[2:5])
    elif m == "apply":
        apply(*sys.argv[2:5])
