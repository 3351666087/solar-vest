"""[S2e, LEAD_NOTES 2l N-3] How VDD_1V8 is distributed once L4 also carries signals: L4 pour fragments, VDD_1V8 tracks per layer,
vias, and for every 1.8 V decoupling capacitor the distance from its VDD_1V8 pad to the nearest VDD_1V8 via and whether an L4 pour
fragment lies within 1 mm. Also counts the signal tracks on L4.
usage: kicad-python vdd18_stats.py BOARD.kicad_pcb STATS.json   (adds key 'vdd_1v8' and 'l4_signal' to STATS.json)"""
import json, math, sys
import pcbnew

MM = pcbnew.FromMM; TO = pcbnew.ToMM
b = pcbnew.LoadBoard(sys.argv[1])
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
L4 = pcbnew.In3_Cu
frag = []
pour = pcbnew.SHAPE_POLY_SET()
for z in b.Zones():
    if not z.GetIsRuleArea() and z.GetNetname() == "VDD_1V8" and z.IsOnLayer(L4):
        fp = z.GetFilledPolysList(L4)
        for k in range(fp.OutlineCount()):
            one = pcbnew.SHAPE_POLY_SET(); one.AddOutline(fp.Outline(k))
            frag.append(round(one.Area() / 1e12, 2))
        pour.Append(fp)
vias = [t for t in b.GetTracks() if t.GetClass() == "PCB_VIA" and t.GetNetname() == "VDD_1V8"]
tl, l4sig = {}, {}
for t in b.GetTracks():
    if t.GetClass() != "PCB_TRACK":
        continue
    ln = b.GetLayerName(t.GetLayer())
    if t.GetNetname() == "VDD_1V8":
        tl[ln] = tl.get(ln, 0) + TO(t.GetLength())
    elif t.GetLayer() == L4:
        l4sig[t.GetNetname()] = l4sig.get(t.GetNetname(), 0) + TO(t.GetLength())
dec = []
for f in b.GetFootprints():
    if not f.GetReference().startswith("C"):
        continue
    nets = {p.GetNetname() for p in f.Pads()}
    if "VDD_1V8" not in nets or "GND" not in nets:
        continue
    p = [q for q in f.Pads() if q.GetNetname() == "VDD_1V8"][0]
    c = p.GetPosition()
    dv = min((TO(int(math.hypot(v.GetPosition().x - c.x, v.GetPosition().y - c.y))) for v in vias), default=99.0)
    near = bool(pour.OutlineCount()) and pour.Collide(c, MM(1.0))
    dec.append(dict(ref=f.GetReference(), via_mm=round(dv, 3), l4_pour_within_1mm=near, ok=dv <= 1.0 or near))
S = json.load(open(sys.argv[2]))
S["vdd_1v8"] = dict(method="N-3: L4 VDD_1V8 pour refilled around the L4 signal tracks (local pours); fragments joined by VDD_1V8 tracks "
                           "and vias on the other layers; L2 stays a full GND plane",
                    l4_pour_fragments=len(frag), l4_pour_fragment_areas_mm2=sorted(frag, reverse=True), l4_pour_area_mm2=round(sum(frag), 1),
                    track_length_mm={k: round(v, 1) for k, v in tl.items()}, vias=len(vias),
                    decoupling=dec, decoupling_rule_1mm=("PASS" if all(d["ok"] for d in dec) else "FAIL"),
                    decoupling_failing=[d["ref"] for d in dec if not d["ok"]])
S["l4_signal"] = dict(nets=len(l4sig), track_length_mm=round(sum(l4sig.values()), 1), by_net={k: round(v, 1) for k, v in sorted(l4sig.items(), key=lambda x: -x[1])})
json.dump(S, open(sys.argv[2], "w"), indent=1)
print("VDD_1V8: L4 fragments", len(frag), "vias", len(vias), "decoupling", S["vdd_1v8"]["decoupling_rule_1mm"], "| L4 signal nets", len(l4sig))
