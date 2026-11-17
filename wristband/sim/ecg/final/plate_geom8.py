"""[ECG final] Copper of each net over plates E1 / E2 on the closed 8-layer board (copy of v3/prechecks/plate_geom.py, adapted).
Plates = the board's rule areas PLATE_E1_AREA / PLATE_E2_AREA. Stack (P-5): F, In1 GND, In2, In3, In4 VDD_1V8 plane, In5, In6, B.
- vias per net and plate with the B.Cu pad diameter
- track length per net, layer and plate, sampled every 0.025 mm; F/In1/In2/In3 samples are split into 'shielded' (In4 fill under the
  centre line and both edges + 0.1 mm, as v3/finish/tools/shield_check.py) and 'In4 gap'
- B.Cu pads over the plates
usage: kicad-python plate_geom8.py BOARD.kicad_pcb OUT.json"""
import json, math, sys
import pcbnew
from collections import defaultdict

pcb, out = sys.argv[1:3]
b = pcbnew.LoadBoard(pcb); MM, TO = pcbnew.FromMM, pcbnew.ToMM
lid = {b.GetLayerName(l): l for l in range(pcbnew.PCB_LAYER_ID_COUNT) if b.GetLayerName(l)}
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
PL = {z.GetZoneName().replace("PLATE_", "plate_").replace("_AREA", ""): z for z in b.Zones()
      if z.GetIsRuleArea() and z.GetZoneName() in ("PLATE_E1_AREA", "PLATE_E2_AREA")}
F4 = [z.GetFilledPolysList(lid["In4.Cu"]) for z in b.Zones() if not z.GetIsRuleArea() and z.IsOnLayer(lid["In4.Cu"])]
in4 = lambda p: any(ps.Contains(p) for ps in F4)


def which(p):
    for k, z in PL.items():
        if z.Outline().Contains(p):
            return k
    return None


vias = defaultdict(lambda: defaultdict(list)); trk = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))
gaps = defaultdict(list)
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        k = which(t.GetPosition())
        if k:
            vias[k][t.GetNetname()].append(round(TO(t.GetWidth(pcbnew.B_Cu)), 3))
        continue
    lay = b.GetLayerName(t.GetLayer()); a, c = t.GetStart(), t.GetEnd(); L = TO((c - a).EuclideanNorm()); n = max(1, int(L / 0.025))
    nn = max(1, (c - a).EuclideanNorm()); ux, uy = (c.x - a.x) / nn, (c.y - a.y) / nn; off = TO(t.GetWidth()) / 2 + 0.1
    for i in range(n + 1):
        p = pcbnew.VECTOR2I(int(a.x + (c.x - a.x) * i / n), int(a.y + (c.y - a.y) * i / n)); k = which(p)
        if not k:
            continue
        tag = lay
        if lay in ("F.Cu", "In1.Cu", "In2.Cu", "In3.Cu"):
            pts = [p] + [pcbnew.VECTOR2I(int(p.x - s * uy * MM(off)), int(p.y + s * ux * MM(off))) for s in (-1, 1)]
            ok = all(in4(q) for q in pts)
            tag = lay + (" shielded" if ok else " In4 gap")
            if not ok and len(gaps[t.GetNetname()]) < 40:
                gaps[t.GetNetname()].append([round(TO(p.x), 3), round(TO(p.y), 3), lay, k])
        trk[k][t.GetNetname()][tag] += L / (n + 1)
pads = defaultdict(lambda: defaultdict(list))
for f in b.GetFootprints():
    for p in f.Pads():
        if p.IsOnLayer(pcbnew.B_Cu):
            k = which(p.GetPosition())
            if k:
                pads[k][p.GetNetname()].append(f.GetReference() + "." + p.GetNumber())
res = dict(board=pcb, vias={k: dict(d) for k, d in vias.items()},
           tracks_mm={k: {n: {l: round(v, 3) for l, v in dd.items()} for n, dd in d.items()} for k, d in trk.items()},
           bcu_pads={k: dict(d) for k, d in pads.items()}, gap_points=dict(gaps))
json.dump(res, open(out, "w"), indent=1)
for k in sorted(vias):
    print(k, "vias", sum(len(v) for v in vias[k].values()), {n: len(v) for n, v in vias[k].items()})
for k in sorted(trk):
    for n, dd in sorted(trk[k].items()):
        if any(not l.endswith("shielded") for l in dd):
            print(k, n, {l: round(v, 2) for l, v in dd.items()})
print("bcu pads", {k: dict(d) for k, d in pads.items()})
