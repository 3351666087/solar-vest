"""[grow8 Q-3] In4 (VDD_1V8 plane) under the plate-forbidden tracks on the shielded layers (KiCad python).

  kicad-python shield_check.py BOARD.kicad_pcb FORBIDDEN.json OUT.json [LAYERS=In2.Cu,In3.Cu] [PLANE=In4.Cu]

Refills the zones, then samples every forbidden-net track on the shielded layers inside a plate (PLATE_E1_AREA / PLATE_E2_AREA) every
0.025 mm along its centre line and at both edges + 0.1 mm; a sample not inside the plane layer's fill (and the In1 GND fill) is a gap.
Writes per net: length over the plates, gap length under In4 and In1, gap positions (board page mm).
"""
import json, math, sys
import pcbnew

pcb, forbf, outf = sys.argv[1:4]
LAY = (sys.argv[4] if len(sys.argv) > 4 else "In2.Cu,In3.Cu").split(",")
PL = sys.argv[5] if len(sys.argv) > 5 else "In4.Cu"
b = pcbnew.LoadBoard(pcb); MM, TO = pcbnew.FromMM, pcbnew.ToMM
forb = set(json.load(open(forbf)))
lid = {b.GetLayerName(l): l for l in range(pcbnew.PCB_LAYER_ID_COUNT) if b.GetLayerName(l)}
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
plates = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetZoneName() in ("PLATE_E1_AREA", "PLATE_E2_AREA")]


def fills(layer):
    res = []
    for z in b.Zones():
        if not z.GetIsRuleArea() and z.IsOnLayer(lid[layer]):
            res.append(z.GetFilledPolysList(lid[layer]))
    return res


F4, F1 = fills(PL), fills("In1.Cu")
inside = lambda polys, p: any(ps.Contains(p) for ps in polys)
res = {}
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA" or t.GetNetname() not in forb or b.GetLayerName(t.GetLayer()) not in LAY:
        continue
    a, c = t.GetStart(), t.GetEnd(); L = TO((c - a).EuclideanNorm()); n = max(1, int(L / 0.025))
    ux, uy = ((c.x - a.x) / max(1, (c - a).EuclideanNorm()), (c.y - a.y) / max(1, (c - a).EuclideanNorm()))
    off = TO(t.GetWidth()) / 2 + 0.1
    r = res.setdefault(t.GetNetname(), dict(over_plate_mm=0.0, gap_in4_mm=0.0, gap_in1_mm=0.0, gaps=[]))
    for k in range(n + 1):
        p = pcbnew.VECTOR2I(int(a.x + (c.x - a.x) * k / n), int(a.y + (c.y - a.y) * k / n))
        if not any(z.Outline().Contains(p) for z in plates):
            continue
        r["over_plate_mm"] += L / (n + 1)
        pts = [p] + [pcbnew.VECTOR2I(int(p.x - s * uy * MM(off)), int(p.y + s * ux * MM(off))) for s in (-1, 1)]
        if not all(inside(F4, q) for q in pts):
            r["gap_in4_mm"] += L / (n + 1)
            if len(r["gaps"]) < 20:
                r["gaps"].append([round(TO(p.x), 3), round(TO(p.y), 3), b.GetLayerName(t.GetLayer())])
        if not all(inside(F1, q) for q in pts):
            r["gap_in1_mm"] += L / (n + 1)
for r in res.values():
    for k in ("over_plate_mm", "gap_in4_mm", "gap_in1_mm"):
        r[k] = round(r[k], 2)
tot = dict(over_plate_mm=round(sum(r["over_plate_mm"] for r in res.values()), 2), gap_in4_mm=round(sum(r["gap_in4_mm"] for r in res.values()), 2),
           gap_in1_mm=round(sum(r["gap_in1_mm"] for r in res.values()), 2))
json.dump(dict(layers=LAY, plane=PL, total=tot, nets=res), open(outf, "w"), indent=1)
print("shield check:", tot)
