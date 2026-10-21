import pcbnew, json, math, os
res = {}
for b in ("pmbh", "libb"):
    B = pcbnew.LoadBoard(os.path.expandvars(f"$TMPDIR/hw/out/{b}/{b}.kicad_pcb")); res[b] = {}
    for f in B.GetFootprints():
        r = f.GetOrientationDegrees(); P = f.GetPosition(); pads = {}
        for pd in f.Pads():
            q = pd.GetPosition(); x, y = pcbnew.ToMM(q.x - P.x), pcbnew.ToMM(q.y - P.y)
            t = math.radians(-r)  # undo visual CCW rotation (y-down)
            ux, uy = x * math.cos(t) + y * math.sin(t), -x * math.sin(t) + y * math.cos(t)
            pads.setdefault(pd.GetNumber(), []).append((round(ux, 3), round(uy, 3)))
        res[b][f.GetReference()] = dict(rot=r % 360, pads=pads)
json.dump(res, open("kicad_pads.json", "w"))
print({b: len(v) for b, v in res.items()}, res["pmbh"]["Q8"])
