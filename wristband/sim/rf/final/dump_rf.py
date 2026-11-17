"""[rf final] Dump the RF corner of the closed board (KiCad python, read-only; zones refilled in memory only, never saved).
usage: KiCad-python dump_rf.py <board.kicad_pcb> rf_dump.json"""
import pcbnew, sys, json
b = pcbnew.LoadBoard(sys.argv[1]); TO = pcbnew.ToMM
OX, OY = 100.0, 130.0
B = lambda x, y: [round(TO(x) - OX, 4), round(OY - TO(y), 4)]
REG = (-0.5, -0.5, 14.0, 9.0)   # board frame window
inreg = lambda p: REG[0] <= p[0] <= REG[2] and REG[1] <= p[1] <= REG[3]
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
D = dict(board=sys.argv[1], fps={}, tracks=[], vias=[], pads=[], fills={}, edges=[])
for r in ("AE1", "J40", "C213", "C215", "L204"):
    f = b.FindFootprintByReference(r)
    D["fps"][r] = dict(pos=B(f.GetPosition().x, f.GetPosition().y), rot=f.GetOrientationDegrees(), value=f.GetValue(), dnp=f.IsDNP(),
                       fpid=f.GetFPIDAsString())
rfn = set()
for f in b.GetFootprints():
    for p in f.Pads():
        c = B(p.GetPosition().x, p.GetPosition().y)
        if p.GetNetname() in ("RF_50R", "ANT_FEED"): rfn.add(f.GetReference())
        if inreg(c) or p.GetNetname() in ("RF_50R", "ANT_FEED"):
            ps = p.GetEffectivePolygon(pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu)
            polys = []
            for i in range(ps.OutlineCount()):
                o = ps.Outline(i); polys.append([B(o.CPoint(k).x, o.CPoint(k).y) for k in range(o.PointCount())])
            D["pads"].append(dict(ref=f.GetReference(), num=p.GetNumber(), net=p.GetNetname(), c=c, layers=[b.GetLayerName(l) for l in p.GetLayerSet().Seq()][:3],
                                  drill=TO(p.GetDrillSize().x), poly=polys))
D["rf_refs"] = sorted(rfn)
for t in b.GetTracks():
    s, e = B(t.GetStart().x, t.GetStart().y), B(t.GetEnd().x, t.GetEnd().y)
    if not (inreg(s) or inreg(e) or t.GetNetname() in ("RF_50R", "ANT_FEED")): continue
    if t.Type() == pcbnew.PCB_VIA_T:
        D["vias"].append(dict(net=t.GetNetname(), c=s, d=TO(t.GetWidth(pcbnew.F_Cu)), drill=TO(t.GetDrillValue()),
                              layers=[b.GetLayerName(t.TopLayer()), b.GetLayerName(t.BottomLayer())]))
    else:
        D["tracks"].append(dict(net=t.GetNetname(), layer=t.GetLayerName(), s=s, e=e, w=TO(t.GetWidth())))
for z in b.Zones():
    if z.GetIsRuleArea(): continue
    for l in z.GetLayerSet().Seq():
        ln = b.GetLayerName(l)
        if not ln.endswith(".Cu"): continue
        fp = z.GetFilledPolysList(l)
        for i in range(fp.OutlineCount()):
            o = fp.Outline(i); pts = [B(o.CPoint(k).x, o.CPoint(k).y) for k in range(o.PointCount())]
            if any(inreg(p) for p in pts):
                holes = []
                for h in range(fp.HoleCount(i)):
                    hh = fp.Hole(i, h); holes.append([B(hh.CPoint(k).x, hh.CPoint(k).y) for k in range(hh.PointCount())])
                D["fills"].setdefault(ln, []).append(dict(net=z.GetNetname(), zone=z.GetZoneName(), outer=pts, holes=holes))
for d in b.GetDrawings():
    if d.GetLayerName() == "Edge.Cuts":
        D["edges"].append(dict(s=B(d.GetStart().x, d.GetStart().y), e=B(d.GetEnd().x, d.GetEnd().y), shape=d.GetShapeStr()))
# footprint graphic copper (AE1 feed leg is a custom pad, already in pads)
json.dump(D, open(sys.argv[2], "w"))
print({k: len(v) for k, v in D.items() if isinstance(v, (list, dict))}, D["rf_refs"])
