"""[layout] Plane fan-out of the V3-F main board (KiCad python), after layout/tools/route_main.py (v1: fan-out vias before routing).

Every SMD pad of a plane net (GND -> L2 plane, VDD_1V8 -> L4 plane) that is not yet tied to a via of its net gets a short stub on its own
layer and a through via (filled + capped) next to the pad (no via in a pad: the WLCSP / DSBGA in-land vias of fanout.py are the only ones).
The four plate-dot pads (B.Cu, inside the B.Cu void) get a via >= 1 mm from the dot opening and a B.Cu stub; the B.Cu void rule area is
re-cut around that stub (key-hole). Locked fan-out stubs of the bare-die packages count as pads (their free end is the origin).

Checks per candidate (pure python geometry on the pads' copper polygons, tracks, vias):
  copper clearance = max(class clearance of both nets, as the project file: capped at 0.20) ; via hole to other-net copper >= 0.20 ;
  hole to hole >= 0.20 ; copper to board edge / motor cut-out >= 0.30 ; via not overlapping any pad ; not in the antenna keep-out ;
  VDD_1V8 vias not over a plate (netclasses.json PLATE_VOID) ; GND vias over a plate >= 1 mm from a dot opening ; no via or stub inside the
  WLCSP / DSBGA courtyards + 0.35 mm (their escape lanes) or under the SC-16S crystal X2 ; no plane via inside a PMIC_NO_POUR area ;
  B.Cu stubs not inside a plate void.
usage: kicad-python fanout_planes.py RUNDIR [BASE]      -> RUNDIR/BASE_fan.kicad_pcb (+ .kicad_pro / .kicad_dru copies), RUNDIR/fanout_planes.json
"""
import json, math, os, shutil, sys
import pcbnew

RUN = sys.argv[1]
BASE = RUN + "/" + (sys.argv[2] if len(sys.argv) > 2 else "v3f_g1")
GJ = json.load(open(RUN + "/geom.json"))["G"]
OX, OY = GJ["KICAD_ORIGIN"]
MM, TO = pcbnew.FromMM, pcbnew.ToMM
PLANE = {"GND": "In1.Cu", "VDD_1V8": "In3.Cu"}
DOTS = {"E11", "E12", "E21", "E22"}
BGA = ("U6", "U8", "U4", "U5")
NOCU = ("X2",)                      # SC-16S 32.768 kHz: no copper under the body (netclasses.json XTAL)
CU_EDGE = 0.30
CAP = 0.20
VIA_IN_PAD = True                   # [lead ruling 2026-11-15] via-in-pad on any pad (JLC 6L: epoxy filled and capped, hole 0.15-0.55)
ISL_NET = "TMP117_ISLAND"              # [layout] board-only net of the U10 thermal island (U10 pad 7 is NC in the netlist)
FEED_W = 0.18                       # 50-ohm microstrip on F.Cu over L2 (0.0994 mm 3313, er 4.1): ~0.18 mm [estimate; RF_50R structure open, SIM-12]


def P(x, y):                        # board frame -> page mm
    return (OX + x, OY - y)


# ------------------------------------------------------------------ geometry
def d_pt_seg(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0.0 if L == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def _ccw(a, b, c):
    return (c[1] - a[1]) * (b[0] - a[0]) - (b[1] - a[1]) * (c[0] - a[0])


def seg_x(a, b, c, d):
    d1, d2, d3, d4 = _ccw(c, d, a), _ccw(c, d, b), _ccw(a, b, c), _ccw(a, b, d)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def d_seg_seg(a, b, c, d):
    if seg_x(a, b, c, d):
        return 0.0
    return min(d_pt_seg(a, c, d), d_pt_seg(b, c, d), d_pt_seg(c, a, b), d_pt_seg(d, a, b))


def inside(p, poly):
    x, y = p; n = len(poly); c = False
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def d_pt_poly(p, poly):
    if inside(p, poly):
        return 0.0
    return min(d_pt_seg(p, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def d_seg_poly(a, b, poly):
    if inside(a, poly) or inside(b, poly):
        return 0.0
    return min(d_seg_seg(a, b, poly[i], poly[(i + 1) % len(poly)]) for i in range(len(poly)))


def circle(c, r, n=32):
    return [(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


# ------------------------------------------------------------------ board model
brd = pcbnew.LoadBoard(BASE + ".kicad_pcb")
NC = json.load(open(GJ["DESIGN"] + "/netclasses.json"))
CLR = {}
for k, d in NC["netclasses"].items():
    if isinstance(d.get("nets"), list):
        for n in d["nets"]:
            CLR[n] = min(d.get("clearance_mm", 0.1), CAP)
clr = lambda a, b: max(CLR.get(a, 0.1), CLR.get(b, 0.1)) + 0.005
LID = {"F.Cu": pcbnew.F_Cu, "In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu, "In3.Cu": pcbnew.In3_Cu, "In4.Cu": pcbnew.In4_Cu,
       "B.Cu": pcbnew.B_Cu}
CULAY = list(LID.values())

OBS = []                            # dict(net, layers:set, kind, geo, r_hole, ref)
GRID = {}


def gkeys(bb, pad=1.0):
    x0, y0, x1, y1 = bb
    for i in range(int(math.floor(x0 - pad)), int(math.floor(x1 + pad)) + 1):
        for j in range(int(math.floor(y0 - pad)), int(math.floor(y1 + pad)) + 1):
            yield (i, j)


def add_obs(o):
    OBS.append(o); k = len(OBS) - 1
    for key in gkeys(o["bb"], 0.0):
        GRID.setdefault(key, []).append(k)


def near(bb):
    s = set()
    for key in gkeys(bb, 1.0):
        s.update(GRID.get(key, ()))
    return [OBS[i] for i in s]


def pad_poly(p, layer):
    ps = pcbnew.SHAPE_POLY_SET()
    p.TransformShapeToPolygon(ps, layer, 0, MM(0.003), pcbnew.ERROR_INSIDE)
    out = []
    for k in range(ps.OutlineCount()):
        ol = ps.Outline(k)
        out.append([(TO(ol.CPoint(i).x), TO(ol.CPoint(i).y)) for i in range(ol.PointCount())])
    return out


def bb_pts(pts, r=0.0):
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    return (min(xs) - r, min(ys) - r, max(xs) + r, max(ys) + r)


PADPOLY = {}


def pk(p):                          # SWIG returns a new proxy per call: key pads by owner, number and position
    return (p.GetParentFootprint().GetReference(), p.GetNumber(), p.GetPosition().x, p.GetPosition().y)
for f in brd.GetFootprints():
    for p in f.Pads():
        for L in CULAY:
            if not p.IsOnLayer(L):
                continue
            for pg in pad_poly(p, L):
                if len(pg) < 3:
                    continue
                o = dict(net=p.GetNetname(), layers={L}, kind="poly", geo=pg, r_hole=None, ref=f.GetReference(), pad=p, pk=pk(p), bb=bb_pts(pg))
                add_obs(o); PADPOLY.setdefault(pk(p), []).append((L, pg))
for f in brd.GetFootprints():                                   # copper graphics of footprints (net ties NT1 / NT2)
    for g in f.GraphicalItems():
        if g.GetLayer() in CULAY and hasattr(g, "TransformShapeToPolygon"):
            ps = pcbnew.SHAPE_POLY_SET()
            g.TransformShapeToPolygon(ps, g.GetLayer(), 0, MM(0.003), pcbnew.ERROR_INSIDE)
            for kk in range(ps.OutlineCount()):
                ol = ps.Outline(kk); pg = [(TO(ol.CPoint(i).x), TO(ol.CPoint(i).y)) for i in range(ol.PointCount())]
                if len(pg) >= 3:
                    add_obs(dict(net="", layers={g.GetLayer()}, kind="poly", geo=pg, r_hole=None, ref=f.GetReference() + ":gfx", bb=bb_pts(pg)))
for t in brd.GetTracks():
    if t.GetClass() == "PCB_VIA":
        c = (TO(t.GetPosition().x), TO(t.GetPosition().y)); r = TO(t.GetWidth(pcbnew.F_Cu)) / 2
        add_obs(dict(net=t.GetNetname(), layers=set(CULAY), kind="circle", geo=(c, r), r_hole=TO(t.GetDrill()) / 2, ref=None, bb=bb_pts([c], r)))
    else:
        a = (TO(t.GetStart().x), TO(t.GetStart().y)); b = (TO(t.GetEnd().x), TO(t.GetEnd().y)); r = TO(t.GetWidth()) / 2
        add_obs(dict(net=t.GetNetname(), layers={t.GetLayer()}, kind="seg", geo=(a, b, r), r_hole=None, ref=None, bb=bb_pts([a, b], r)))

OUTLINE = [P(*q) for q in GJ["OUTLINE"]]
MC = P(*GJ["MOTOR_CENTER"]); MR = GJ["MOTOR_CUT_D"] / 2
k = GJ["ANT_KEEPOUT"]
ANT = [P(k[0] - 1, k[1] - 1), P(k[2], k[1] - 1), P(k[2], k[3]), P(k[0] - 1, k[3])]
PLATES = [[P(*q) for q in pg] for key in ("plate_E1", "plate_E2") for pg in GJ["SKIN"][key]["poly_board"]]
DOTC = {n: P(*c) for n, c in GJ["DOTS"].items()}


def fp_rect(ref, grow):
    f = brd.FindFootprintByReference(ref)
    if f is None:
        return None
    cy = f.GetCourtyard(pcbnew.B_CrtYd if f.IsFlipped() else pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False)
    x0, y0, x1, y1 = TO(bb.GetLeft()) - grow, TO(bb.GetTop()) - grow, TO(bb.GetRight()) + grow, TO(bb.GetBottom()) + grow
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


FORBID = {r: fp_rect(r, 0.35) for r in BGA if brd.FindFootprintByReference(r)}
FORBID.update({r: fp_rect(r, 0.0) for r in NOCU if brd.FindFootprintByReference(r)})
_isl = GJ.get("ZRECTS", {}).get("U10_island")
if _isl:                            # [S2b T-5] no other net's via or stub on the U10 island (key "U10": U10's own pads may fan out)
    FORBID["U10_island"] = [P(_isl[0], _isl[1]), P(_isl[2], _isl[1]), P(_isl[2], _isl[3]), P(_isl[0], _isl[3])]
NOPOUR = []
for z in brd.Zones():
    if z.GetIsRuleArea() and z.GetZoneName().startswith("PMIC_NO_POUR"):
        ol = z.Outline().Outline(0)
        NOPOUR.append([(TO(ol.CPoint(i).x), TO(ol.CPoint(i).y)) for i in range(ol.PointCount())])


def via_ok(c, rv, rh, net, own_ref, plane=True, own_pk=None):
    if not inside(c, OUTLINE) or d_pt_poly(c, OUTLINE) == 0 and False:
        return "outside"
    if min(d_pt_seg(c, OUTLINE[i], OUTLINE[(i + 1) % len(OUTLINE)]) for i in range(len(OUTLINE))) < CU_EDGE + rv:
        return "edge"
    if math.hypot(c[0] - MC[0], c[1] - MC[1]) < MR + CU_EDGE + rv:
        return "motor"
    if d_pt_poly(c, ANT) < rv + 0.05:
        return "antenna"
    for pg in PLATES:
        dp = d_pt_poly(c, pg)
        if net == "VDD_1V8" and dp < rv + 0.05:
            return "plate"
    if any(math.hypot(c[0] - q[0], c[1] - q[1]) < 2.0 + rv for q in DOTC.values()):     # R-2: 1.0 mm from every dot opening
        return "dot"
    for r, pg in FORBID.items():
        if r != own_ref and d_pt_poly(c, pg) < rv:
            return "forbid " + r
    if plane:
        for pg in NOPOUR:
            if d_pt_poly(c, pg) < rv + 0.2:
                return "nopour"
    for o in near((c[0] - 1, c[1] - 1, c[0] + 1, c[1] + 1)):
        same = o["net"] == net and net != ""
        if o["kind"] == "circle":
            (oc, orr) = o["geo"]; dd = math.hypot(c[0] - oc[0], c[1] - oc[1])
            if dd < rh + o["r_hole"] + 0.2:
                return "hole2hole"
            if not same and (dd - orr < rv + clr(net, o["net"]) or dd - orr < rh + 0.2 or dd - rv < o["r_hole"] + 0.2):
                return "via"
            continue
        if o["kind"] == "seg":
            a, b, r = o["geo"]; dd = d_pt_seg(c, a, b) - r
        else:
            dd = d_pt_poly(c, o["geo"])
        if o["kind"] == "poly" and "pad" in o and dd < rv + 0.02 and not (own_pk is not None and o.get("pk") == own_pk):
            return "on pad %s" % o["ref"]
        if not same and (dd < rv + clr(net, o["net"]) or dd < rh + 0.2):
            return "clear %s" % (o["ref"] or o["net"])
    return None


def seg_ok(a, b, w, layer, net, own_pad, own_ref):
    r = w / 2
    if layer == pcbnew.B_Cu:
        for pg in PLATES:
            if d_seg_poly(a, b, pg) < r + 0.01:
                return "B in plate"
    for rr, pg in FORBID.items():
        if rr != own_ref and d_seg_poly(a, b, pg) < r:
            return "forbid " + rr
    if min(d_seg_seg(a, b, OUTLINE[i], OUTLINE[(i + 1) % len(OUTLINE)]) for i in range(len(OUTLINE))) < CU_EDGE + r:
        return "edge"
    for o in near(bb_pts([a, b], 1.0)):
        if o["net"] == net and net != "":
            continue
        if o["kind"] == "circle":
            (oc, orr) = o["geo"]; dd = d_pt_seg(oc, a, b)
            if dd - orr < r + clr(net, o["net"]) or dd - r < o["r_hole"] + 0.2:
                return "via"
            continue
        if layer not in o["layers"]:
            continue
        if o["kind"] == "seg":
            c, d, rr = o["geo"]; dd = d_seg_seg(a, b, c, d) - rr
        else:
            dd = d_seg_poly(a, b, o["geo"])
        if dd < r + clr(net, o["net"]):
            return "clear %s" % (o["ref"] or o["net"])
    return None


def add_via(c, dia, drill, net):
    v = pcbnew.PCB_VIA(brd)
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetPosition(pcbnew.VECTOR2I(MM(c[0]), MM(c[1])))
    v.SetDrill(MM(drill)); v.SetWidth(MM(dia)); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    if net:
        v.SetNet(brd.FindNet(net))
    v.SetFillingMode(pcbnew.FILLING_MODE_FILLED); v.SetCappingMode(pcbnew.CAPPING_MODE_CAPPED); v.SetLocked(True)
    brd.Add(v)
    add_obs(dict(net=net, layers=set(CULAY), kind="circle", geo=(c, dia / 2), r_hole=drill / 2, ref=None, bb=bb_pts([c], dia / 2)))


def add_track(a, b, w, layer, net):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1]))); t.SetEnd(pcbnew.VECTOR2I(MM(b[0]), MM(b[1])))
    t.SetWidth(MM(w)); t.SetLayer(layer); t.SetLocked(True)
    if net:
        t.SetNet(brd.FindNet(net))
    brd.Add(t)
    add_obs(dict(net=net, layers={layer}, kind="seg", geo=(a, b, w / 2), r_hole=None, ref=None, bb=bb_pts([a, b], w / 2)))


# ------------------------------------------------------------------ connectivity of the plane nets (pads already tied to a via)
def comps(net):
    items = []
    for f in brd.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() == net:
                items.append(("pad", p, f))
    for t in brd.GetTracks():
        if t.GetNetname() == net:
            items.append(("via" if t.GetClass() == "PCB_VIA" else "trk", t, None))
    par = list(range(len(items)))
    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]; i = par[i]
        return i
    def pts(it):
        k, o, _ = it
        if k == "trk":
            return [(TO(o.GetStart().x), TO(o.GetStart().y)), (TO(o.GetEnd().x), TO(o.GetEnd().y))]
        return [(TO(o.GetPosition().x), TO(o.GetPosition().y))]
    def touch(i, j):
        ki, oi, _ = items[i]; kj, oj, _ = items[j]
        if ki == "pad" and kj == "pad":
            return False
        if ki == "pad" or kj == "pad":
            pad, other = (oi, items[j]) if ki == "pad" else (oj, items[i])
            for q in pts(other):
                for L, pg in PADPOLY.get(pk(pad), []):
                    if d_pt_poly(q, pg) < 0.01:
                        return True
            return False
        for a in pts(items[i]):
            for b in pts(items[j]):
                tol = 0.01
                if ki == "via":
                    tol = TO(oi.GetWidth(pcbnew.F_Cu)) / 2
                if kj == "via":
                    tol = max(tol, TO(oj.GetWidth(pcbnew.F_Cu)) / 2)
                if math.hypot(a[0] - b[0], a[1] - b[1]) < tol:
                    return True
        return False
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            if touch(i, j):
                par[find(i)] = find(j)
    groups = {}
    for i, it in enumerate(items):
        groups.setdefault(find(i), []).append(it)
    return list(groups.values())


def dirs(c0, c_fp):
    a0 = math.atan2(c0[1] - c_fp[1], c0[0] - c_fp[0]) if math.hypot(c0[0] - c_fp[0], c0[1] - c_fp[1]) > 0.05 else 0.0
    ds = [a0 + i * math.pi / 8 for i in range(16)]
    return sorted(ds, key=lambda a: abs(math.remainder(a - a0, 2 * math.pi)))


def fan_one(origin, layer, net, pad, ref, fp_c, w, ext=False, dmin=None, dmax_extra=1.2):
    """origin: point; pad: pcbnew pad (or None for a stub end)"""
    sizes = [(0.4, 0.2), (0.3, 0.15)] if not ext else [(0.3, 0.15)]
    polys = [pg for L, pg in PADPOLY.get(pk(pad), []) if L == layer] if pad is not None else []
    if VIA_IN_PAD and pad is not None and not ext:      # [lead, 2026-11-15] via in the pad (JLC 6-layer: epoxy filled + capped)
        sz = pad.GetSize(layer); mn = TO(min(sz.x, sz.y))
        for dia, drill in ((0.3, 0.15), (0.25, 0.15)):
            if dia <= mn + 1e-6 and via_ok(origin, dia / 2, drill / 2, net, ref, own_pk=pk(pad)) is None:
                return origin, dia, drill, 0.0
    for dia, drill in sizes:
        rv = dia / 2
        for ang in dirs(origin, fp_c):
            ux, uy = math.cos(ang), math.sin(ang)
            # first distance where the via clears the own pad by 0.02
            d = dmin if dmin is not None else 0.0
            while d < 3.5 and polys and min(d_pt_poly((origin[0] + d * ux, origin[1] + d * uy), pg) for pg in polys) < rv + 0.03:
                d += 0.025
            if not polys and dmin is None:
                d = rv + w / 2 + 0.05
            dstart = d
            while d <= dstart + (dmax_extra if not ext else 2.5):
                c = (origin[0] + d * ux, origin[1] + d * uy)
                why = via_ok(c, rv, drill / 2, net, ref)
                if why is None:
                    why = seg_ok(origin, c, w, layer, net, pad, ref)
                    if why is None:
                        return c, dia, drill, d
                d += 0.05
    return None


def main():
    log = dict(placed=[], failed=[], skipped_connected=0, dots=[])
    # ---- plate dots (B.Cu, electrode nets): via >= 1 mm from the opening, key-hole in the B.Cu void
    keyholes = []
    for ref in sorted(DOTS):
        f = brd.FindFootprintByReference(ref)
        if f is None:
            continue
        p = list(f.Pads())[0]; net = p.GetNetname()
        c0 = (TO(p.GetPosition().x), TO(p.GetPosition().y))
        best = None
        for ang in [i * math.pi / 8 for i in range(16)]:
            for d in (2.2, 2.35, 2.5, 2.7, 2.9, 3.1):
                c = (c0[0] + d * math.cos(ang), c0[1] + d * math.sin(ang))
                if via_ok(c, 0.15, 0.075, net, ref, plane=False) is None:
                    a = (c0[0] + 0.9 * math.cos(ang), c0[1] + 0.9 * math.sin(ang))
                    best = (d, c, a); break
            if best:
                break
        if not best:
            log["failed"].append(dict(ref=ref, net=net, why="dot via")); continue
        d, c, a = best
        add_via(c, 0.3, 0.15, net); add_track(c0, c, 0.2, pcbnew.B_Cu, net)
        keyholes.append((c0, c))
        log["dots"].append(dict(ref=ref, net=net, via=[round(c[0] - OX, 3), round(OY - c[1], 3)], dist=d))
    # ---- [LEAD_NOTES T-5] U10 (TMP117) thermal-via island: 4 x 4 mm part-free (placement), exposed pad -> filled vias -> isolated B.Cu
    #      patch facing plate E1 (no net, under solder mask: the EP is not tied to an electrode net)
    isl = None
    f = brd.FindFootprintByReference("U10")
    if f is not None:
        ep = max(f.Pads(), key=lambda q: q.GetSize(pcbnew.F_Cu).x * q.GetSize(pcbnew.F_Cu).y)
        ni = pcbnew.NETINFO_ITEM(brd, ISL_NET); brd.Add(ni); ep.SetNet(ni)     # board-only net: EP (NC in the netlist), vias, patch
        bb = ep.GetBoundingBox(); c0 = (TO(ep.GetPosition().x), TO(ep.GetPosition().y))
        ax = (1.0, 0.0) if bb.GetWidth() >= bb.GetHeight() else (0.0, 1.0)
        L = TO(max(bb.GetWidth(), bb.GetHeight())) / 2
        pts = [(c0[0] + ax[0] * s, c0[1] + ax[1] * s) for s in (-0.35, 0.35)]          # in the exposed pad (lead's thermal island)
        outs = [(c0[0] + ax[0] * s, c0[1] + ax[1] * s) for s in (-1.75, 1.75)]          # beyond the courtyard, inside the island
        for q in pts + outs:
            add_via(q, 0.3, 0.15, ISL_NET)
        for s, q in ((-1, outs[0]), (1, outs[1])):
            add_track((c0[0] + ax[0] * s * (L - 0.2), c0[1] + ax[1] * s * (L - 0.2)), q, 0.4, pcbnew.F_Cu, ISL_NET)
        h = 1.8
        isl = [(c0[0] - h, c0[1] - h), (c0[0] + h, c0[1] - h), (c0[0] + h, c0[1] + h), (c0[0] - h, c0[1] + h)]
        z = pcbnew.ZONE(brd); ls = pcbnew.LSET(); ls.AddLayer(pcbnew.B_Cu); z.SetLayerSet(ls); z.SetNet(ni)
        z.SetLocalClearance(MM(0.2)); z.SetMinThickness(MM(0.1)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_NEVER); z.SetZoneName("U10_THERMAL_ISLAND"); z.SetAssignedPriority(5)
        ol = z.Outline(); ol.NewOutline()
        for q in isl:
            ol.Append(MM(q[0]), MM(q[1]))
        brd.Add(z)
        add_obs(dict(net=ISL_NET, layers={pcbnew.B_Cu}, kind="poly", geo=isl, r_hole=None, ref="U10:island", bb=bb_pts(isl)))
        log["u10_island"] = dict(vias=len(pts) + len(outs), patch_mm=2 * h, centre_board=[round(c0[0] - OX, 3), round(OY - c0[1], 3)])
    # re-cut the B.Cu plate voids around the dot stubs
    for z in list(brd.Zones()):
        if z.GetIsRuleArea() and z.GetZoneName().endswith("_VOID_BCU"):
            ps = z.Outline()
            for c0, c in keyholes:
                hole = pcbnew.SHAPE_POLY_SET()
                for pg in (circle(c0, 1.0 + 0.25), circle(c, 0.15 + 0.25)):
                    hole.NewOutline()
                    for q in pg:
                        hole.Append(MM(q[0]), MM(q[1]))
                ang = math.atan2(c[1] - c0[1], c[0] - c0[0]); nx, ny = -math.sin(ang) * 0.4, math.cos(ang) * 0.4
                hole.NewOutline()
                for q in ((c0[0] + nx, c0[1] + ny), (c[0] + nx, c[1] + ny), (c[0] - nx, c[1] - ny), (c0[0] - nx, c0[1] - ny)):
                    hole.Append(MM(q[0]), MM(q[1]))
                hole.Simplify()
                ps.BooleanSubtract(hole)
            if isl:
                hole = pcbnew.SHAPE_POLY_SET(); hole.NewOutline()
                cx = sum(q[0] for q in isl) / 4; cy = sum(q[1] for q in isl) / 4
                for q in isl:
                    hole.Append(MM(cx + (q[0] - cx) * 1.15), MM(cy + (q[1] - cy) * 1.15))
                ps.BooleanSubtract(hole)
    # ---- [LEAD_NOTES 2h A-2] RF corner with the PA_fill_booster radiator: CPWG feed (W 0.17 / gap 0.15, RF json) from C215.2 and
    #      L204.1 to the feed point (2.75, 3.00); GND strips on all six layers along the pocket edges Y 3.0 and X 5.0; GND stitching
    #      vias 0.4 / 0.2 at <= 1.0 mm pitch, 0.3-0.5 mm back from the edges
    if brd.FindFootprintByReference("AE1") is not None:      # [S2d] lid antenna L1: pad 1 = feed leg (top edge Y 3.00, rule-area notch 2.85-3.00)
        fp_pad = lambda r, n: [q for q in brd.FindFootprintByReference(r).Pads() if q.GetNumber() == n][0]
        pc = lambda q: (TO(q.GetPosition().x), TO(q.GetPosition().y))
        fpt = P(2.75, 3.00); j = P(2.75, 3.15); tip = P(2.75, 2.95)
        rf = dict(feed_tracks=[], stitch=[], stitch_failed=[])
        add_track(j, tip, 0.17, pcbnew.F_Cu, "ANT_FEED")
        for r, n in (("C215", "2"), ("L204", "1")):
            if brd.FindFootprintByReference(r) is None:
                continue
            c = pc(fp_pad(r, n))
            if r == "L204" and brd.FindFootprintByReference("C215") is not None:   # [S2e] L204 beside C215: pad to pad, clear of AE1's GND pad
                c2 = pc(fp_pad("C215", "2"))
                add_track(c, c2, 0.17, pcbnew.F_Cu, "ANT_FEED")
                rf["feed_tracks"].append(dict(pad="L204.1", via="C215.2", length_to_feed_mm=round(math.hypot(c[0] - c2[0], c[1] - c2[1]) + math.hypot(c2[0] - j[0], c2[1] - j[1]) + 0.15, 3)))
                continue
            why = seg_ok(c, j, 0.17, pcbnew.F_Cu, "ANT_FEED", None, r)
            add_track(c, j, 0.17, pcbnew.F_Cu, "ANT_FEED")
            rf["feed_tracks"].append(dict(pad="%s.%s" % (r, n), length_to_feed_mm=round(math.hypot(c[0] - j[0], c[1] - j[1]) + 0.15, 3),
                                          check=why or "ok"))
        strip = [P(0.0, 3.0), P(5.0, 3.0), P(5.0, 0.0), P(6.2, 0.0), P(6.2, 4.3), P(0.0, 4.3)]
        for L in CULAY:
            z = pcbnew.ZONE(brd); ls = pcbnew.LSET(); ls.AddLayer(L); z.SetLayerSet(ls); z.SetNet(brd.FindNet("GND"))
            z.SetLocalClearance(MM(0.15)); z.SetMinThickness(MM(0.1)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS); z.SetAssignedPriority(10); z.SetZoneName("RF_GND_EDGE_" + brd.GetLayerName(L))
            for q in strip:
                z.AppendCorner(pcbnew.VECTOR2I(MM(q[0]), MM(q[1])), -1)
            brd.Add(z)
        line = [((x, 3.4), "Y3") for x in [0.75 + 0.5 * i for i in range(9)]] + [((5.4, y), "X5") for y in (0.45, 1.2, 1.95, 2.7)] + [((5.4, 3.4), "corner")]
        last = {}
        for (x, y), edge in line:
            done = False
            for dx, dy in ((0, 0), (0, 0.1), (0, -0.1), (0.15, 0), (-0.15, 0), (0.15, 0.1), (-0.15, 0.1)):
                xx, yy = (x + dx, y + dy) if edge != "X5" else (x + dy, y + dx)
                c = P(xx, yy)
                if via_ok(c, 0.2, 0.1, "GND", None) is None:
                    add_via(c, 0.4, 0.2, "GND"); rf["stitch"].append([round(xx, 2), round(yy, 2)]); done = True; break
            if not done:
                rf["stitch_failed"].append([x, y])
        log["rf_corner"] = rf
    # ---- 50-ohm feed stub: from the antenna-side pad of the match (ANT_FEED, AE1 left out) to the antenna keep-out edge (F.Cu)
    if brd.FindFootprintByReference("AE1") is None:
        feed = [(f, p) for f in brd.GetFootprints() for p in f.Pads() if p.GetNetname() == "ANT_FEED"]
        if feed:
            f, p = min(feed, key=lambda e: d_pt_poly((TO(e[1].GetPosition().x), TO(e[1].GetPosition().y)), ANT))
            c0 = (TO(p.GetPosition().x), TO(p.GetPosition().y))
            best = min(((d_pt_seg(c0, ANT[i], ANT[(i + 1) % 4]), i) for i in range(4)))
            a, b = ANT[best[1]], ANT[(best[1] + 1) % 4]
            dx, dy = b[0] - a[0], b[1] - a[1]; L2 = dx * dx + dy * dy
            t = max(0.0, min(1.0, ((c0[0] - a[0]) * dx + (c0[1] - a[1]) * dy) / L2))
            e = (a[0] + t * dx, a[1] + t * dy)
            add_track(c0, e, FEED_W, pcbnew.F_Cu, "ANT_FEED")
            log["feed_stub"] = dict(from_pad="%s.%s" % (f.GetReference(), p.GetNumber()), end_board=[round(e[0] - OX, 3), round(OY - e[1], 3)],
                                    width=FEED_W, length=round(math.hypot(e[0] - c0[0], e[1] - c0[1]), 3))
    # ---- plane nets
    for net in ("GND", "VDD_1V8"):
        for g in comps(net):
            if any(k == "via" for k, _, _ in g):
                log["skipped_connected"] += sum(1 for k, _, _ in g if k == "pad"); continue
            pads = [(o, f) for k, o, f in g if k == "pad"]
            if not pads or all(f.GetReference() == "AE1" for o, f in pads):
                continue                                         # [S2e] AE1's GND pad sits in the RF_GND_EDGE pour (stitched to L2)
            if all(o.GetDrillSize().x > 0 for o, f in pads):
                continue                                         # through-hole: on the planes already
            # dangling locked stub ends (bare-die fan-out): origin = the free end
            trk = [o for k, o, _ in g if k == "trk"]
            done = False
            if trk:
                ends = {}
                for t in trk:
                    for q in ((TO(t.GetStart().x), TO(t.GetStart().y)), (TO(t.GetEnd().x), TO(t.GetEnd().y))):
                        key = (round(q[0], 3), round(q[1], 3)); ends.setdefault(key, [0, t]); ends[key][0] += 1
                pad0, f0 = pads[0]
                fc = (TO(f0.GetPosition().x), TO(f0.GetPosition().y))
                free = [(q, t) for q, (n, t) in ends.items() if n == 1 and not any(
                    d_pt_poly(q, pg) < 0.01 for o, f in pads for L, pg in PADPOLY.get(pk(o), []))]
                free.sort(key=lambda e: -math.hypot(e[0][0] - fc[0], e[0][1] - fc[1]))
                for q, t in free[:1]:
                    w = TO(t.GetWidth())
                    r = fan_one(q, t.GetLayer(), net, None, f0.GetReference(), fc, max(w, 0.1), dmin=0.0)
                    if r is None:
                        r = fan_one(q, t.GetLayer(), net, None, f0.GetReference(), fc, max(w, 0.1), ext=True, dmin=0.0)
                    if r:
                        c, dia, drill, d = r
                        add_via(c, dia, drill, net)
                        if d > 1e-3:
                            add_track(q, c, max(w, 0.1), t.GetLayer(), net)
                        log["placed"].append(dict(ref=f0.GetReference(), pad="stub", net=net, via=dia, stub=round(d, 3))); done = True
            if done:
                continue
            # one via per connected group: try each pad of the group (smallest footprint first)
            ok = False
            for ext in (False, True):
                for p, f in pads:
                    if p.GetDrillSize().x > 0:
                        continue
                    L = pcbnew.B_Cu if p.IsOnLayer(pcbnew.B_Cu) and not p.IsOnLayer(pcbnew.F_Cu) else pcbnew.F_Cu
                    c0 = (TO(p.GetPosition().x), TO(p.GetPosition().y)); fc = (TO(f.GetPosition().x), TO(f.GetPosition().y))
                    sz = p.GetSize(L) if True else None
                    w = max(0.1, min(0.25, 0.9 * min(TO(sz.x), TO(sz.y))))
                    if f.GetReference() == "AE1":
                        r = fan_one(c0, L, net, p, "AE1", fc, 0.2, ext=True, dmax_extra=3.0)
                    else:
                        r = fan_one(c0, L, net, p, f.GetReference(), fc, w, ext=ext)
                    if r:
                        c, dia, drill, d = r
                        add_via(c, dia, drill, net)
                        if d > 1e-3:
                            add_track(c0, c, w, L, net)
                        log["placed"].append(dict(ref=f.GetReference(), pad=p.GetNumber(), net=net, via=dia, stub=round(d, 3), ext=ext))
                        ok = True; break
                if ok:
                    break
            if not ok:
                log["failed"].append(dict(net=net, pads=["%s.%s" % (f.GetReference(), o.GetNumber()) for o, f in pads]))
    # ---- second chance: tie a failed pad to a same-net pad of its own footprint that now has a via (pin-width straight link,
    #      e.g. a QFN exposed pad to its ground pin: no via in the pad)
    tied = {}
    for net in ("GND", "VDD_1V8"):
        for g in comps(net):
            has_via = any(k == "via" for k, _, _ in g)
            for k, o, f in g:
                if k == "pad":
                    tied[pk(o)] = has_via
    still = []
    for x in log["failed"]:
        if "pads" not in x:
            still.append(x); continue
        okx = False
        for name in x["pads"]:
            ref, num = name.split(".", 1)
            f = brd.FindFootprintByReference(ref)
            p = [q for q in f.Pads() if q.GetNumber() == num][0]
            L = pcbnew.B_Cu if p.IsOnLayer(pcbnew.B_Cu) and not p.IsOnLayer(pcbnew.F_Cu) else pcbnew.F_Cu
            pc = (TO(p.GetPosition().x), TO(p.GetPosition().y))
            mates = [q for q in f.Pads() if q.GetNetname() == x["net"] and tied.get(pk(q)) and pk(q) != pk(p)]
            mates.sort(key=lambda q: math.hypot(TO(q.GetPosition().x) - pc[0], TO(q.GetPosition().y) - pc[1]))
            for q in mates:
                qc = (TO(q.GetPosition().x), TO(q.GetPosition().y))
                sz = q.GetSize(L); w = max(0.1, min(0.2, TO(min(sz.x, sz.y))))
                cands = []
                # along the mate's long axis toward p (stays in the mate's own lane between its neighbours)
                ang = math.radians(q.GetOrientationDegrees())
                ax = (math.cos(ang), -math.sin(ang)) if sz.x >= sz.y else (math.sin(ang), math.cos(ang))
                sgn = 1 if (pc[0] - qc[0]) * ax[0] + (pc[1] - qc[1]) * ax[1] > 0 else -1
                ax = (ax[0] * sgn, ax[1] * sgn)
                ppolys = [pg for LL, pg in PADPOLY.get(pk(p), []) if LL == L]
                for dd in [i * 0.05 for i in range(1, 60)]:
                    e = (qc[0] + ax[0] * dd, qc[1] + ax[1] * dd)
                    if ppolys and any(inside(e, pg) and d_pt_poly(e, [pg[0]]) > 0 for pg in ppolys) and \
                            min(min(d_pt_seg(e, pg[i], pg[(i + 1) % len(pg)]) for i in range(len(pg))) for pg in ppolys) > w / 2:
                        cands.append((qc, e)); break
                cands.append((qc, pc))
                for a, b in cands:
                    if seg_ok(a, b, w, L, x["net"], p, ref) is None:
                        add_track(a, b, w, L, x["net"]); okx = True
                        log["placed"].append(dict(ref=ref, pad=num, net=x["net"], link_to=q.GetNumber(), w=w)); break
                if okx:
                    break
            if okx:
                break
        if not okx:
            still.append(x)
    log["failed"] = still
    out = BASE + "_fan"
    brd.Save(out + ".kicad_pcb")
    for ext in (".kicad_pro", ".kicad_dru"):
        shutil.copy(BASE + ext, out + ext)
    s = open(out + ".kicad_pro").read().replace(os.path.basename(BASE) + ".kicad_pro", os.path.basename(out) + ".kicad_pro")
    open(out + ".kicad_pro", "w").write(s)
    log["n_placed"] = len(log["placed"]); log["n_failed"] = len(log["failed"])
    json.dump(log, open(RUN + "/fanout_planes.json", "w"), indent=1)
    print("fan-out vias placed", log["n_placed"], "failed", log["n_failed"], "already tied", log["skipped_connected"], "dots", len(log["dots"]))
    for x in log["failed"]:
        print("  FAILED", x)


if __name__ == "__main__":
    main()
