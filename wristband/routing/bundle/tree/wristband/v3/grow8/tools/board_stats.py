"""[grow] KiCad-python: track length per layer, via counts, vias over the plates per net (R-3) of a board.
usage: kicad-python board_stats.py BOARD.kicad_pcb GEOM.json OUT.json"""
import json, sys
import pcbnew

b = pcbnew.LoadBoard(sys.argv[1])
G = json.load(open(sys.argv[2]))["G"]
OX, OY = G["KICAD_ORIGIN"]
plates = {k: [[(OX + x, OY - y) for x, y in pg] for pg in G["SKIN"][k]["poly_board"]] for k in ("plate_E1", "plate_E2")}


def inside(p, poly):
    x, y = p; c = False
    for (x1, y1), (x2, y2) in zip(poly, poly[1:] + poly[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


tl = {}; vias = 0; over = {k: {} for k in plates}
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        vias += 1
        p = (pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y))
        for k, pgs in plates.items():
            if any(inside(p, pg) for pg in pgs):
                over[k][t.GetNetname()] = over[k].get(t.GetNetname(), 0) + 1
    else:
        ln = b.GetLayerName(t.GetLayer()); tl[ln] = tl.get(ln, 0.0) + pcbnew.ToMM(t.GetLength())
json.dump(dict(track_mm={k: round(v, 1) for k, v in tl.items()}, track_mm_total=round(sum(tl.values()), 1), vias=vias,
               vias_over_plates=over, vias_over_plates_total={k: sum(v.values()) for k, v in over.items()}), open(sys.argv[3], "w"), indent=1)
