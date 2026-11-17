"""After routing: GND pours on L1, L3, L6 (L2/L5 GND and L4 VDD_1V8 planes exist since build_main), IFA short-leg
ground vias, GND stitching on a grid wherever a via fits, zone refill, all vias marked POFV (IPC-4761 VII).
usage: kicad-python post_route.py"""
import math, os, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lgeom as G
from build_main import V, MM, OX, OY, poly_zone, CU
from route_main import pofv

PCB = G.W + "/layout/main/solarband_main.kicad_pcb"
import json as _json
_NC = _json.load(open(G.W + "/design/netclasses.json"))["netclasses"]
CLR = {n: d.get("clearance_mm", d.get("gap_mm", 0.1)) for d in _NC.values() if isinstance(d.get("nets"), list) for n in d["nets"]}


def has_zone(brd, name):
    return any(z.GetZoneName() == name for z in brd.Zones())


def via_fits(brd, xy, dia=0.4, clr=0.15, layers_need_gnd=True):
    """True if a GND via at xy clears every non-GND copper item on every layer (pads, tracks, vias), the board
    edge and the rule areas that forbid vias"""
    p = V(*xy)
    r = MM(dia / 2 + clr)
    ed = MM(dia / 2 + 0.3)
    # outline / slots
    x, y = xy
    if x < 0.5 or y < 0.5 or x > G.BOARD_W - 0.5 or y > G.BOARD_H - 0.5:
        return False
    for z in brd.Zones():
        if z.GetIsRuleArea() and z.GetDoNotAllowVias() and z.Outline().Collide(p, MM(dia / 2)):
            return False
    for e in brd.GetDrawings():
        if e.GetLayer() == pcbnew.Edge_Cuts and e.HitTest(p, ed):
            return False
    for t in brd.GetTracks():
        if t.GetNetname() == "GND":
            if t.GetClass() == "PCB_VIA" and (t.GetPosition() - p).EuclideanNorm() < MM(dia / 2 + 0.2 + 0.25):
                return False                       # hole-to-hole margin
            continue
        if t.HitTest(p, MM(dia / 2 + max(clr, CLR.get(t.GetNetname(), 0.1)) + 0.02)):
            return False
    for f in brd.GetFootprints():
        if not f.GetBoundingBox(False).Inflate(r).Contains(p):
            continue
        for pad in f.Pads():
            if pad.GetNetname() == "GND" and pad.GetAttribute() == pcbnew.PAD_ATTRIB_SMD and pad.IsOnLayer(pcbnew.F_Cu):
                if pad.HitTest(p, r):
                    return False                   # never put a stitching via under an SMD GND pad
                continue
            if pad.HitTest(p, MM(dia / 2 + max(clr, CLR.get(pad.GetNetname(), 0.1)) + 0.02)):
                return False
        if f.GetCourtyard(pcbnew.F_CrtYd).Collide(p) if f.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else False:
            return False                           # keep stitching vias out of part bodies
    return True


def main():
    brd = pcbnew.LoadBoard(PCB)
    gnd = brd.FindNet("GND")
    full = list(G.rrect_outline())
    for name, ly in (("L1_GND", CU["F"]), ("L3_GND", CU["L3"]), ("L6_GND", CU["B"])):
        if not has_zone(brd, name):
            poly_zone(brd, full, [ly], net=gnd, name=name, priority=0, clearance=0.15, min_width=0.15)
    added = 0
    # IFA short leg: >= 2 ground vias within 0.5 mm of the L6 ground edge [sim10_ifa export short_leg note]
    for xy in ((14.45, 5.95), (15.05, 5.95)):
        if via_fits(brd, xy, 0.4, 0.15):
            v = pcbnew.PCB_VIA(brd); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetPosition(V(*xy)); v.SetDrill(MM(0.2))
            v.SetWidth(MM(0.4)); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(gnd); pofv(v); brd.Add(v); added += 1
    short_leg = added
    # stitching grid 1.6 mm (pours on L1/L3/L6 tied to L2/L5)
    y = 0.8
    while y < G.BOARD_H:
        x = 0.8 + (0.8 if int(y / 1.6) % 2 else 0)
        while x < G.BOARD_W:
            if not (x < 15.5 + 0.5 and y < 5.5 + 0.5) and via_fits(brd, (x, y)):
                v = pcbnew.PCB_VIA(brd); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetPosition(V(x, y)); v.SetDrill(MM(0.2))
                v.SetWidth(MM(0.4)); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(gnd); pofv(v); brd.Add(v); added += 1
            x += 1.6
        y += 1.6
    for t in brd.GetTracks():
        if t.GetClass() == "PCB_VIA":
            pofv(t)
    pcbnew.ZONE_FILLER(brd).Fill(brd.Zones())
    brd.Save(PCB)
    print("pours ok, short-leg vias", short_leg, "stitching vias", added - short_leg)


if __name__ == "__main__":
    main()
