"""Print courtyard / pad bounding boxes of every footprint used on the main board (inspection only)."""
import json, sys, pcbnew
W = "@SVROOT@/wristband/design"
LIBS = {"easyeda_rev": W + "/lib/easyeda_rev.pretty", "solarband": W + "/lib/solarband.pretty", "pv": W + "/lib/pv.pretty"}
parts = json.load(open(W + "/parts.json"))[sys.argv[1] if len(sys.argv) > 1 else "main"]
seen = {}
tot = 0
for ref, p in sorted(parts.items()):
    lib, name = p["footprint"].split(":")
    if name not in seen:
        f = pcbnew.FootprintLoad(LIBS[lib], name)
        cy = f.GetCourtyard(pcbnew.F_CrtYd)
        bb = cy.BBox() if cy.OutlineCount() else None
        pb = f.GetBoundingBox(False)
        pads = list(f.Pads())
        pbb = None
        for pd in pads:
            b = pd.GetBoundingBox()
            pbb = b if pbb is None else (pbb.Merge(b) or pbb)
        cw = pcbnew.ToMM(bb.GetWidth()) if bb else None; ch = pcbnew.ToMM(bb.GetHeight()) if bb else None
        seen[name] = (cw, ch, len(pads), pcbnew.ToMM(pbb.GetWidth()) if pbb else 0, pcbnew.ToMM(pbb.GetHeight()) if pbb else 0,
                      sorted(set(pd.GetNumber() for pd in pads))[:6], [ (pd.GetNumber(), round(pcbnew.ToMM(pd.GetPosition().x),3), round(pcbnew.ToMM(pd.GetPosition().y),3)) for pd in pads][:3])
    cw, ch = seen[name][:2]
    if cw: tot += cw * ch
for k, v in seen.items(): print(k, v)
print("sum courtyard area mm2:", round(tot, 1))
