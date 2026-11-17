"""[grow8 G-6 / P-5] Convert a plane-fanned 6-layer board into the plan-B 8-layer board (KiCad python).

  kicad-python to8l.py IN_fan.kicad_pcb OUT_fan.kicad_pcb [FORBIDDEN.json]

Layer map (v3/planb/planb.json): 6L F / In1 GND / In2 L3 sig / In3 L4 VDD_1V8 pour / In4 L5 sig / B
                              -> 8L F / In1 GND / In2 sig / In3 sig (new) / In4 VDD_1V8 full plane / In5 sig (new) / In6 sig (old L5) / B.
Tracks: In3 -> In4 (none on the fan board), In4 -> In6. Through vias stay through vias (they now span 8 layers), so the GND fan-out
reaches In1 and the VDD_1V8 fan-out reaches In4 unchanged.
Zones: every zone or rule area on all 6 copper layers -> *.Cu (all 8; this fixes the AE1 pocket keep-out, which listed In1..In4 only);
other layer sets by the map; the plate no-pour areas of old L5 also cover In5 (planb: no pour on In5 / In6 / B over the plates);
the antenna inner no-track area covers every inner layer; the RF ground-edge zones get In5 / In6 copies (GND edge on all 8 layers);
the VDD_1V8 pour becomes PLANE_VDD_1V8_In4 (board outline, no signals on In4).
Board thickness 1.0 mm (planb). The DRU keeps its (layer inner) R-2 rule; the forbidden-net list is rewritten from FORBIDDEN.json.
"""
import json, os, re, sys
import pcbnew

src, dst = sys.argv[1], sys.argv[2]
forbf = sys.argv[3] if len(sys.argv) > 3 else None
b = pcbnew.LoadBoard(src)
assert b.GetCopperLayerCount() == 6, "input must be the 6-layer fan board"
OLD = {"F.Cu": pcbnew.F_Cu, "In1.Cu": pcbnew.In1_Cu, "In2.Cu": pcbnew.In2_Cu, "In3.Cu": pcbnew.In3_Cu, "In4.Cu": pcbnew.In4_Cu, "B.Cu": pcbnew.B_Cu}
MAP = {pcbnew.F_Cu: pcbnew.F_Cu, pcbnew.In1_Cu: pcbnew.In1_Cu, pcbnew.In2_Cu: pcbnew.In2_Cu, pcbnew.In3_Cu: pcbnew.In4_Cu,
       pcbnew.In4_Cu: pcbnew.In6_Cu, pcbnew.B_Cu: pcbnew.B_Cu}
ALL6 = set(OLD.values())
b.SetCopperLayerCount(8)
b.GetDesignSettings().SetBoardThickness(pcbnew.FromMM(1.0))
ntr = 0
for t in b.GetTracks():
    if t.GetClass() != "PCB_VIA" and t.GetLayer() in MAP and MAP[t.GetLayer()] != t.GetLayer():
        t.SetLayer(MAP[t.GetLayer()]); ntr += 1
    if t.GetClass() == "PCB_VIA":
        t.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)


def lset(ids):
    s = pcbnew.LSET()
    for i in ids:
        s.AddLayer(i)
    return s


ALL8 = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.In5_Cu, pcbnew.In6_Cu, pcbnew.B_Cu]
INNER8 = ALL8[1:7]
log = []
zones = [(z, None) for z in b.Zones()] + [(z, f) for f in b.GetFootprints() for z in f.Zones()]
new = []
for z, fp in zones:
    cu = {l for l in z.GetLayerSet().Seq() if l in ALL6}
    other = [l for l in z.GetLayerSet().Seq() if l not in ALL6]
    name = z.GetZoneName()
    if not cu:
        continue
    if cu == ALL6:
        tgt = ALL8
    elif name.startswith("RF_GND_EDGE_"):
        tgt = sorted(cu)                                   # same named layer; In5 / In6 copies below
    elif name == "ANT_KEEPOUT_INNER_NO_TRACK":
        tgt = [pcbnew.B_Cu] + INNER8
    elif "NOPOUR_L5" in name:
        tgt = [pcbnew.In5_Cu, pcbnew.In6_Cu]
    else:
        tgt = sorted({MAP[l] for l in cu})
    z.SetLayerSet(lset(tgt + other))
    if z.GetNetname() == "VDD_1V8" and not z.GetIsRuleArea():
        z.SetZoneName("PLANE_VDD_1V8_In4")
    log.append((fp.GetReference() if fp else "", name, [b.GetLayerName(l) for l in tgt]))
    if name == "RF_GND_EDGE_In4.Cu":
        for nl in (pcbnew.In5_Cu, pcbnew.In6_Cu):
            c = pcbnew.ZONE(z)
            c.SetLayerSet(lset([nl])); c.SetZoneName("RF_GND_EDGE_" + b.GetLayerName(nl)); new.append(c)
for c in new:
    b.Add(c)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.Save(dst)
bi, bo = src[:-10], dst[:-10]
txt = open(bi + ".kicad_pro").read().replace(os.path.basename(bi) + ".kicad_pro", os.path.basename(bo) + ".kicad_pro")
open(bo + ".kicad_pro", "w").write(txt)
dru = open(bi + ".kicad_dru").read()
if forbf:
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import forb_dru
    dru = forb_dru.rewrite(dru, json.load(open(forbf)))
dru = dru.replace("JLCPCB standard 6-layer process", "JLCPCB 8-layer plan B (v3/planb, through vias only); 6-layer deck values")
open(bo + ".kicad_dru", "w").write(dru)
print("to8l: tracks moved", ntr, "| zones", len(log), "| new", len(new))
for r in log:
    print("  ", r)
