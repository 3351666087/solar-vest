"""Through-via fan-out of the bare-die packages of SolarBand V3-F on JLC's standard 6-layer process (gate V3-G1).
[V3-G1] adapted from v2/layout/tools/fanout.py: nrf_wlcsp_plan re-planned for the V3-F pin assignment (all inner balls used).

Rules designed to [J = jlcpcb.com/capabilities/pcb-capabilities + help article "BGA Design Guidelines", cached in
cache/v2/jlc_cap, fetched 2026-11-12 23:41-23:44 UTC]:
  via 0.15 mm hole / 0.25 mm pad, filled and capped (POFV, default and free on 6-layer boards, 0.15-0.55 mm vias),
  track / space 0.09 / 0.09 mm (multilayer), BGA land 0.20 mm (ENIG) - 0.25 mm where a via sits in the land,
  via hole to track / inner-layer hole to copper 0.20 mm, hole to hole 0.20 mm, solder-mask dam 0.10 mm (1:1 openings).
No track passes between two lands (gap 0.20 mm < 0.27 mm) and none between two adjacent via holes on an inner layer
(gap 0.25 mm < 0.49 mm): every inner ball gets a via in its land and leaves on L3 through a position without a via.

Local frame = KiCad footprint frame at orientation 0 (x right, y down, mm), origin = package centre.
plan(ref) -> dict(vias=[(ball, net)], tracks=[(net, layer, [(x, y), ...], width)], nc=[balls], direct=[balls])
apply(brd, fp, plan) adds the copper to a pcbnew board for a footprint at any position / orientation.
"""
import math

W_FAN = 0.09           # fan-out track width [J multilayer minimum]
VIA = (0.15, 0.25)     # hole, pad [J]
BO = 0.9               # break-out distance beyond the outer ball row


def nrf_wlcsp_plan(pins):
    """nRF52832-CIAA WLCSP-50: 7 columns x 8 rows, 0.4 mm pitch; B1, C1, D4, D5, E4, E5 not populated.
    pins: ball -> net (None = NC). V3-F pin assignment [v3/design/parts.json U6]: every inner ball except C3 is used
    (P0.04 E6, P0.09 G6, P0.10 G5, P0.17 G3, P0.19 F3, P0.20 G2, P0.26 D3 are the new inner balls of BASELINE 6).

    Method (through vias only, JLC standard 6-layer, via 0.15 / 0.25 filled and capped in the land):
      ring 1 (perimeter, 27 balls)  F.Cu, straight out; B2 and C2 leave through the two empty positions B1, C1
      ring 2 (16 balls)             via in the land, L3 straight out under ring 1 (no via there); D2 = VSS_PA: via to the planes
      ring 3 signals D3, F4, F3     via in the land; all three leave through the only via-free door of ring 2 (C3 NC - C2 - C1), one per
                                    layer: D3 on L3, F4 on L5, F3 on L6 (B.Cu). The door is 0.25 mm wide between the B3 and D3 / D2 hole
                                    keep-outs (0.275 mm radius): one 0.09 mm track per layer, no second one.
      ring 3 grounds C4, C5, E3, F5 joined on F.Cu through the four empty centre positions; two vias in the empty positions D5, E5
                                    (not in a land), so that C4 stays via-free for the F4 / F3 tracks.
    The package therefore needs L3, L5 and L6 under it: it cannot sit over an electrode plate (B.Cu and L5 void there)."""
    X = lambda c: (c - 4) * 0.4
    Y = lambda r: ("ABCDEFGH".index(r) - 3.5) * 0.4
    pos = {b: (X(int(b[1])), Y(b[0])) for b in pins}
    xo, yo = 1.2 + BO, 1.4 + BO
    T, V, XV, direct, nc = [], [], [], [], []
    def f(b, end):
        if pins[b] is None:
            nc.append(b); return
        direct.append(b)
        T.append((pins[b], "F.Cu", [pos[b], end], W_FAN))
    def v(b, path, layer="In2.Cu"):
        if pins[b] is None:
            nc.append(b); return
        V.append((b, pins[b]))
        if path:
            T.append((pins[b], layer, [pos[b]] + path, W_FAN))
    for c in range(1, 8):
        f("A%d" % c, (X(c), -yo)); f("H%d" % c, (X(c), yo))
    for r in "DEFG":
        f(r + "1", (-xo, Y(r)))
    for r in "BCDEFG":
        f(r + "7", (xo, Y(r)))
    f("B2", (-xo, Y("B"))); f("C2", (-xo, Y("C")))                  # through the two empty positions B1, C1
    for c in (3, 4, 5, 6):
        v("B%d" % c, [(X(c), -yo)])                                 # row B: up, under row A
    for r in "CDEF":
        v(r + "6", [(xo, Y(r))])                                    # column 6: right, under column 7
    for c in (2, 3, 4, 5, 6):
        v("G%d" % c, [(X(c), yo)])                                  # row G: down, under row H
    v("E2", [(-xo, Y("E"))]); v("F2", [(-xo, Y("F"))])              # column 2: left, under column 1
    v("D2", None)                                                   # VSS_PA: via in the land to the L2 / L4 planes
    door = [(X(3), Y("C")), (-xo, Y("C"))]                          # over C3 (NC), C2, C1 (no vias)
    v("D3", door, "In2.Cu")                                         # L3: up to C3, then left
    centre = [(X(4), Y("E")), (X(4), Y("D")), (X(4), Y("C"))]       # over the empty positions E4, D4 and the via-free land C4
    v("F4", centre + [(X(3), Y("C")), (-xo, Y("C") + 0.0)], "In4.Cu")                         # L5
    v("F3", [(X(3), Y("E"))] + centre + [(X(3), Y("C")), (-xo, Y("C"))], "B.Cu")               # L6: over E3 (no via), then the centre
    # ground island on F.Cu in the empty centre + two vias in the empty positions D5, E5
    g = pins["C4"]
    for b in ("C4", "C5", "E3", "F5"):
        if pins[b] != g or g is None:
            raise ValueError("ball %s is not on the ground net: re-plan the centre" % b)
        direct.append(b)
    T.append((g, "F.Cu", [pos["C4"], (X(4), Y("D")), (X(4), Y("E")), pos["E3"]], 0.15))
    T.append((g, "F.Cu", [pos["C5"], (X(5), Y("D")), (X(5), Y("E")), pos["F5"]], 0.15))
    T.append((g, "F.Cu", [(X(4), Y("D")), (X(5), Y("D"))], 0.15))
    XV += [((X(5), Y("D")), g), ((X(5), Y("E")), g)]
    if pins.get("C3") is not None:
        raise ValueError("ball C3 is used (%s): the door of ring 2 is closed, re-plan" % pins["C3"])
    nc.append("C3")
    done = set(direct) | {b for b, _ in V} | set(nc)
    missing = sorted(set(pins) - done)
    if missing:
        raise ValueError("balls without an escape: %s" % missing)
    return dict(vias=V, xvias=XV, tracks=T, nc=sorted(set(nc)), direct=direct, pos=pos)


def max86141_plan(pins):
    """MAX86141 WLP-20: 5 columns x 4 rows, 0.4 mm pitch. Inner balls B2, B3, B4, C2, C3, C4."""
    X = lambda c: (c - 3) * 0.4
    Y = lambda r: ("ABCD".index(r) - 1.5) * 0.4
    pos = {b: (X(int(b[1])), Y(b[0])) for b in pins}
    xo, yo = 0.8 + BO, 0.6 + BO
    T, V, direct, nc = [], [], [], []
    def f(b, end):
        if pins[b] is None:
            nc.append(b); return
        direct.append(b); T.append((pins[b], "F.Cu", [pos[b], end], W_FAN))
    for c in range(1, 6):
        f("A%d" % c, (X(c), -yo)); f("D%d" % c, (X(c), yo))
    f("B1", (-xo, Y("B"))); f("C1", (-xo, Y("C"))); f("B5", (xo, Y("B"))); f("C5", (xo, Y("C")))
    for b in ("B2", "C2", "C3", "C4", "B3", "B4"):
        if pins[b] is None:
            nc.append(b); continue
        V.append((b, pins[b]))
    if pins["B2"]:
        T.append((pins["B2"], "In2.Cu", [pos["B2"], (-xo, Y("B"))], W_FAN))       # left, under B1
    if pins["C2"] and pins["C2"] != "GND":
        T.append((pins["C2"], "In4.Cu", [pos["C2"], (-xo, Y("C"))], 0.15))        # supply ball: L5, under C1
    # same-net neighbours joined on F.Cu: C2-D2 (VDD), C3-D3 and C3-C4 (GND); their row-D stubs are then not needed
    for a, b in (("C2", "D2"), ("C3", "D3"), ("C3", "C4")):
        if pins[a] and pins[a] == pins[b]:
            T.append((pins[a], "F.Cu", [pos[a], pos[b]], 0.15))
    T[:] = [t for t in T if not (t[1] == "F.Cu" and t[2][0] == pos["D3"] and t[2][1] == (X(3), yo))]
    return dict(vias=V, tracks=T, nc=sorted(set(nc)), direct=direct, pos=pos)


def dsbga8_plan(pins):
    """INA236 DSBGA-8 (YBJ): 4 columns x 2 rows, every ball on the perimeter: F.Cu only."""
    T, direct, nc, pos = [], [], [], {}
    for b, n in pins.items():
        c = "ABCD".index(b[0]); r = int(b[1])
        x = (c - 1.5) * 0.4; y = 0.2 if r == 1 else -0.2
        pos[b] = (x, y)
        if n is None:
            nc.append(b); continue
        direct.append(b)
        T.append((n, "F.Cu", [(x, y), (x, y + (BO + 0.0) * (1 if r == 1 else -1))], W_FAN))
    return dict(vias=[], tracks=T, nc=nc, direct=direct, pos=pos)


def to_board(fp_pos_mm, orient_deg, flipped=False):
    """local KiCad (x, y down) -> board KiCad coordinates for a footprint at fp_pos_mm, orientation orient_deg"""
    a = math.radians(orient_deg)
    c, s = math.cos(a), math.sin(a)
    def tf(p):
        x, y = p
        if flipped:
            x = -x
        return (fp_pos_mm[0] + x * c + y * s, fp_pos_mm[1] - x * s + y * c)
    return tf


def apply(brd, fp, plan, pcbnew, check=True):
    """add the vias and tracks of plan to board brd for footprint fp; returns (n_vias, n_tracks)"""
    MM = pcbnew.FromMM
    pos = fp.GetPosition()
    tf = to_board((pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)), fp.GetOrientationDegrees(), fp.IsFlipped())
    pads = {p.GetNumber(): p for p in fp.Pads()}
    if check:                                           # the plan's ball positions must be the footprint's pad centres
        for b, lp in plan["pos"].items():
            bp = tf(lp); pp = pads[b].GetPosition()
            if abs(bp[0] - pcbnew.ToMM(pp.x)) > 1e-3 or abs(bp[1] - pcbnew.ToMM(pp.y)) > 1e-3:
                raise ValueError("fan-out plan does not match the footprint at ball %s: %s vs (%.3f, %.3f)" % (
                    b, bp, pcbnew.ToMM(pp.x), pcbnew.ToMM(pp.y)))
    lay = {"F.Cu": pcbnew.F_Cu, "In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu, "In3.Cu": pcbnew.In3_Cu,
           "In4.Cu": pcbnew.In4_Cu, "B.Cu": pcbnew.B_Cu}
    nv = nt = 0
    for b, net in plan["vias"]:
        v = pcbnew.PCB_VIA(brd)
        v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetPosition(pads[b].GetPosition())
        v.SetDrill(MM(VIA[0])); v.SetWidth(MM(VIA[1])); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(brd.FindNet(net))
        try:
            v.SetFillingMode(pcbnew.FILLING_MODE_FILLED); v.SetCappingMode(pcbnew.CAPPING_MODE_CAPPED)
        except Exception:
            pass
        brd.Add(v); nv += 1
    for lp, net in plan.get("xvias", []):               # vias outside the lands (empty positions of the array)
        bp = tf(lp)
        v = pcbnew.PCB_VIA(brd)
        v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetPosition(pcbnew.VECTOR2I(MM(bp[0]), MM(bp[1])))
        v.SetDrill(MM(VIA[0])); v.SetWidth(MM(VIA[1])); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(brd.FindNet(net))
        try:
            v.SetFillingMode(pcbnew.FILLING_MODE_FILLED); v.SetCappingMode(pcbnew.CAPPING_MODE_CAPPED)
        except Exception:
            pass
        brd.Add(v); nv += 1
    for net, layer, pts, w in plan["tracks"]:
        n = brd.FindNet(net)
        for i in range(len(pts) - 1):
            a, b_ = tf(pts[i]), tf(pts[i + 1])
            t = pcbnew.PCB_TRACK(brd)
            t.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1]))); t.SetEnd(pcbnew.VECTOR2I(MM(b_[0]), MM(b_[1])))
            t.SetWidth(MM(w)); t.SetLayer(lay[layer]); t.SetNet(n)
            brd.Add(t); nt += 1
    return nv, nt
