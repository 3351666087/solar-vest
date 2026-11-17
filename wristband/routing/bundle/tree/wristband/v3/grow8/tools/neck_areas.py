"""[grow8 Q-2] Neck-down at pads: rule areas + DRU rules (KiCad python).

  kicad-python neck_areas.py BOARD.kicad_pcb [RADIUS_MM=1.5]      (in place: BOARD.kicad_pcb and BOARD.kicad_dru)

Ruling Q-2 (LEAD_NOTES 2p): within 1.5 mm of a pad it connects to, any net may use JLC's minimum track and clearance (0.09 / 0.09 mm).
For every routed net: one rule area NECK_<k>_AREA (all copper layers, nothing disallowed) = union of that net's pads grown by RADIUS.
DRU (appended, so these custom rules override the net-class clearances):
  "Q-2 neck clearance"      a track of width < 0.095 mm of net X enclosed by NECK_X: clearance 0.09 to everything
  "Q-2 neck only at pads"   a track of width < 0.095 mm of a net whose class width is > 0.09, not enclosed by NECK_X: disallowed
The router (pfroute.py "neck") uses 1.4 mm from the pad copper, so a 0.09 track ends inside the 1.5 mm area.
"""
import json, re, sys
import pcbnew

pcb = sys.argv[1]
R = float(sys.argv[2]) if len(sys.argv) > 2 else 1.5
SKIP = {"", "TMP117_ISLAND"}
MM = pcbnew.FromMM
b = pcbnew.LoadBoard(pcb)
pro = json.load(open(pcb[:-10] + ".kicad_pro"))
cls = {c["name"]: c for c in pro["net_settings"]["classes"]}
netcls = {p["pattern"]: p["netclass"] for p in pro["net_settings"]["netclass_patterns"]}
for z in list(b.Zones()):
    if z.GetIsRuleArea() and z.GetZoneName().startswith("NECK_"):
        b.Remove(z)
bynet = {}
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname() not in SKIP:
            bynet.setdefault(p.GetNetname(), []).append(p)
names = {}
cu = pcbnew.LSET.AllCuMask(b.GetCopperLayerCount())
for k, net in enumerate(sorted(bynet)):
    ps = pcbnew.SHAPE_POLY_SET()
    for p in bynet[net]:
        lay = pcbnew.F_Cu if p.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
        q = pcbnew.SHAPE_POLY_SET(); p.TransformShapeToPolygon(q, lay, MM(R), MM(0.005), pcbnew.ERROR_INSIDE)
        ps.BooleanAdd(q)
    ps.Simplify()
    nm = "NECK_%d_AREA" % k
    for i in range(ps.OutlineCount()):                        # one rule area per piece (a saved zone keeps one outline); same name
        z = pcbnew.ZONE(b); z.SetIsRuleArea(True); z.SetLayerSet(cu)
        z.SetDoNotAllowTracks(False); z.SetDoNotAllowVias(False); z.SetDoNotAllowPads(False); z.SetDoNotAllowZoneFills(False)
        z.SetDoNotAllowFootprints(False); z.SetZoneName(nm)
        z.Outline().AddOutline(ps.Outline(i))
        for h in range(ps.HoleCount(i)):
            z.Outline().AddHole(ps.Hole(i, h))
        b.Add(z)
    names[net] = nm
b.Save(pcb)
wide = [n for n in names if cls[netcls.get(n, "Default")]["track_width"] > 0.0951]
clr = " || ".join("(A.NetName == '%s' && A.enclosedByArea('%s'))" % (n, names[n]) for n in sorted(names))
bad = " || ".join("(A.NetName == '%s' && !A.enclosedByArea('%s'))" % (n, names[n]) for n in sorted(wide))
m = re.search(r'WLCSP / DSBGA fan-out[^\n]*\n  \(condition "([^"]*)"', open(pcb[:-10] + ".kicad_dru").read())
if m:                                                         # the existing 0.09 / 0.09 package fan-out inside the WLCSP courtyards stays legal
    bad = "!(%s) && (%s)" % (m.group(1).replace("B.intersectsCourtyard", "A.intersectsCourtyard"), bad)
dru = open(pcb[:-10] + ".kicad_dru").read()
dru = re.sub(r"\n# \[grow8 Q-2\].*", "", dru, flags=re.S).rstrip("\n") + "\n"
dru += ("# [grow8 Q-2] neck-down at pads (LEAD_NOTES 2p): 0.09 / 0.09 mm within %.1f mm of an own pad (areas NECK_k_AREA)\n" % R +
        "(rule \"Q-2 neck clearance\"\n  (condition \"A.Type == 'Track' && A.Width < 0.095mm && (%s)\")\n  (constraint clearance (min 0.09mm)))\n" % clr +
        "(rule \"Q-2 neck only at pads\"\n  (condition \"A.Type == 'Track' && A.Width < 0.095mm && (%s)\")\n  (constraint disallow track))\n" % bad)
open(pcb[:-10] + ".kicad_dru", "w").write(dru)
json.dump(dict(radius=R, areas=names, wide_nets=sorted(wide)), open(pcb[:-10] + "_neck.json", "w"), indent=0)
print("neck areas:", len(names), "nets,", len(wide), "wide nets")
