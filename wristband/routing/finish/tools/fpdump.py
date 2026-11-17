"""[V3-G1] Dump the footprint geometry of every part of a V3-F variant (KiCad python) -> v3/layout/work/fpgeom_<variant>.json
(adapted from v2/layout/tools/fpdump.py: paths only; reads v3/design read-only)

Per ref: library id, courtyard bbox and every pad in the footprint's own frame (KiCad, y down, unrotated), side
(from v2/design/parts.json: F = sky, B = skin face). Used by autoplace.py (venv python, no KiCad import).
usage: kicad-python fpdump.py [variant ...]      (default: all variants of parts.json)
"""
import json, os, sys
import pcbnew

W = "/path/to/SolarVest_work/wristband"
V3 = W + "/v3"
OUT = os.environ.get("G1_WORK", V3 + "/finish/work")   # [eco3]
DES = os.environ.get("G1_DESIGN", V3 + "/design")                    # [layout] override: G1_DESIGN
LIBS = {"easyeda_rev": DES + "/lib/easyeda_rev.pretty", "solarband": DES + "/lib/solarband.pretty",
        "solarband_layout": V3 + "/layout/lib/solarband_layout.pretty", "rf": V3 + "/layout/lib/rf.pretty"}


def load(fpid):
    lib, name = fpid.split(":")
    f = pcbnew.FootprintLoad(LIBS[lib], name)
    if f is None:
        raise SystemExit("footprint not found: " + fpid)
    return f


def geom(f):
    cy = f.GetCourtyard(pcbnew.F_CrtYd)
    if cy.OutlineCount():
        bb = cy.BBox()
        crt = [pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())]
    else:
        crt = None
    pads = []
    for p in f.Pads():
        try:
            s = p.GetSize()
        except TypeError:
            s = p.GetSize(pcbnew.F_Cu)
        pads.append(dict(num=p.GetNumber(), x=pcbnew.ToMM(p.GetPosition().x), y=pcbnew.ToMM(p.GetPosition().y),
                         w=pcbnew.ToMM(s.x), h=pcbnew.ToMM(s.y), ang=p.GetOrientationDegrees(),
                         smd=p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD))
    if crt is None:   # copper-only parts without courtyard: pads bbox + 0.1
        xs = [q["x"] - q["w"] / 2 for q in pads] + [q["x"] + q["w"] / 2 for q in pads]
        ys = [q["y"] - q["h"] / 2 for q in pads] + [q["y"] + q["h"] / 2 for q in pads]
        crt = [min(xs) - 0.1, min(ys) - 0.1, max(xs) + 0.1, max(ys) + 0.1] if pads else [-0.1, -0.1, 0.1, 0.1]
    return crt, pads


FP_OVERRIDE = {"AE1": "rf:AE1_lid_L1"}          # [S2d] AE1_lid_L1 with a 0.15 mm feed notch in its rule area (LEAD_NOTES 2i L-2)


def main():
    allv = json.load(open(DES + "/parts.json"))["variants"]
    todo = sys.argv[1:] or list(allv)
    os.makedirs(OUT, exist_ok=True)
    cache = {}
    for v in todo:
        out = {}
        for ref, p in sorted(allv[v]["parts"].items()):
            fpid = FP_OVERRIDE.get(ref, p["footprint"])
            if fpid not in cache:
                cache[fpid] = geom(load(fpid))
            crt, pads = cache[fpid]
            out[ref] = dict(fpid=fpid, crt=crt, pads=pads, side=p["side"])
        json.dump(out, open(OUT + f"/fpgeom_{v}.json", "w"), indent=0)
        print(v, len(out), "footprints")


if __name__ == "__main__":
    main()
