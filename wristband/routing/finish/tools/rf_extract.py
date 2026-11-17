"""Extract the as-built RF geometry from the main board (KiCad python, zones refilled): RF track segments with widths,
the filled F.Cu GND copper and the filled L2 copper around the RF path, the feed via, every via within 1.5 mm of the
RF centre line -> layout/work/rf_extract.json (input to sim/rf/sim12_cpwg/sim12_layout.py)."""
import json, sys
import pcbnew
sys.path.insert(0, __file__.rsplit("/", 1)[0])
import lgeom as G
OX, OY = G.KICAD_ORIGIN
b = pcbnew.LoadBoard(G.W + "/layout/main/solarband_main.kicad_pcb")
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
P = lambda v: (round(pcbnew.ToMM(v.x) - OX, 4), round(OY - pcbnew.ToMM(v.y), 4))
out = dict(tracks=[], vias=[], fill={})
for t in b.GetTracks():
    n = t.GetNetname()
    if t.GetClass() == "PCB_VIA":
        out["vias"].append(dict(net=n, pos=P(t.GetPosition()), dia=pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)), drill=pcbnew.ToMM(t.GetDrill())))
    elif n in ("RF_ANT", "RF_50R", "ANT_FEED"):
        out["tracks"].append(dict(net=n, a=P(t.GetStart()), b=P(t.GetEnd()), w=pcbnew.ToMM(t.GetWidth()), layer=t.GetLayerName()))
for z in b.Zones():
    if z.GetIsRuleArea() or z.GetNetname() != "GND":
        continue
    for ly in (pcbnew.F_Cu, pcbnew.In1_Cu):
        if not z.IsOnLayer(ly):
            continue
        fp = z.GetFilledPolysList(ly)
        polys = []
        for i in range(fp.OutlineCount()):
            ol = fp.Outline(i)
            pts = [P(ol.CPoint(k)) for k in range(ol.PointCount())]
            holes = []
            for h in range(fp.HoleCount(i)):
                hl = fp.Hole(i, h); holes.append([P(hl.CPoint(k)) for k in range(hl.PointCount())])
            polys.append(dict(outline=pts, holes=holes))
        out["fill"].setdefault(b.GetLayerName(ly), []).extend(polys)
json.dump(out, open(G.W + "/layout/work/rf_extract.json", "w"))
print("tracks", len(out["tracks"]), "vias", len(out["vias"]), {k: len(v) for k, v in out["fill"].items()})
