import json, sys, os, pcbnew
FP = os.path.expanduser("~/Applications/KiCad/KiCad/KiCad/KiCad.app/Contents/SharedSupport/footprints/")
def load(fpid):
    lib, name = fpid.split(":")
    path = FP + lib + ".pretty" if lib != "hw" else os.path.join(os.path.dirname(__file__), "lib/hw.pretty")
    return pcbnew.FootprintLoad(path, name)
seen = {}
for b in ("pmbh", "libb"):
    for ref, p in json.load(open(b + "_parts.json")).items():
        if p["footprint"] and p["footprint"] not in seen: seen[p["footprint"]] = ref
for fpid in sorted(seen):
    f = load(fpid)
    cy = f.GetCourtyard(pcbnew.F_CrtYd).BBox() if f.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else f.GetBoundingBox(False)
    mm = pcbnew.ToMM
    pads = [(p.GetNumber(), round(mm(p.GetPosition().x), 2), round(mm(p.GetPosition().y), 2)) for p in f.Pads()]
    print(f"{fpid:95s} crtyd x[{mm(cy.GetLeft()):6.2f},{mm(cy.GetRight()):6.2f}] y[{mm(cy.GetTop()):6.2f},{mm(cy.GetBottom()):6.2f}]  pads {pads[:6]}{'...' if len(pads) > 6 else ''}")
