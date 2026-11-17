"""[layout] Statistics of the routed V3-F board (KiCad python): track / via counts, minimum track width, via sizes, minimum
different-net copper spacing actually used (track-track, track-via, via-via on the same layer), copper layers used per net class,
utilisation from the placement check. usage: kicad-python layout_stats.py BOARD.kicad_pcb CHK.json DRC.json OUT.json"""
import collections, json, math, sys
import pcbnew

pcb, chk, drc, out = sys.argv[1:5]
TO = pcbnew.ToMM
brd = pcbnew.LoadBoard(pcb)
NC = json.load(open("/path/to/SolarVest_work/wristband/v3/design/netclasses.json"))["netclasses"]
cls = {}
for k, d in NC.items():
    if isinstance(d.get("nets"), list):
        for n in d["nets"]:
            cls[n] = k
segs, vias = [], []
for t in brd.GetTracks():
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition()
        vias.append(((TO(p.x), TO(p.y)), TO(t.GetWidth(pcbnew.F_Cu)), TO(t.GetDrill()), t.GetNetname()))
    else:
        segs.append(((TO(t.GetStart().x), TO(t.GetStart().y)), (TO(t.GetEnd().x), TO(t.GetEnd().y)), TO(t.GetWidth()),
                     brd.GetLayerName(t.GetLayer()), t.GetNetname()))


def dps(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]; L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def dss(a, b, c, d):
    return min(dps(a, c, d), dps(b, c, d), dps(c, a, b), dps(d, a, b))   # crossing different-net tracks would be a DRC short anyway


grid = collections.defaultdict(list)
for i, s in enumerate(segs):
    for gx in range(int(min(s[0][0], s[1][0])) - 1, int(max(s[0][0], s[1][0])) + 2):
        for gy in range(int(min(s[0][1], s[1][1])) - 1, int(max(s[0][1], s[1][1])) + 2):
            grid[(gx, gy)].append(i)
mins = 9.0; where = None
seen = set()
for cell, idx in grid.items():
    for a in idx:
        for b in idx:
            if a >= b or (a, b) in seen:
                continue
            seen.add((a, b))
            A, B = segs[a], segs[b]
            if A[3] != B[3] or A[4] == B[4]:
                continue
            d = dss(A[0], A[1], B[0], B[1]) - A[2] / 2 - B[2] / 2
            if d < mins:
                mins, where = d, (A[4], B[4], A[3])
minv = 9.0
for (c, dv, dr, n) in vias:
    for s in segs:
        if s[4] != n and abs(s[0][0] - c[0]) < 2 and abs(s[0][1] - c[1]) < 2:
            minv = min(minv, dps(c, s[0], s[1]) - dv / 2 - s[2] / 2)
layers = collections.defaultdict(set); length = collections.Counter()
for s in segs:
    k = cls.get(s[4], "SIGNAL"); layers[k].add(s[3]); length[s[3]] += math.hypot(s[1][0] - s[0][0], s[1][1] - s[0][1])
vsz = collections.Counter("%.2f/%.2f" % (dv, dr) for _, dv, dr, _ in vias)
c = json.load(open(chk)); d = json.load(open(drc))
g = c["gate1_metric"]
res = dict(board=pcb.split("/")[-1],
           utilisation=dict(project_count=g["project_count"]["utilisation_project"], v1_convention=g["project_count"]["utilisation_v1"],
                            courtyard_mm2=g["project_count"]["courtyard_mm2"], placement_mm2=g["placement_mm2"], note="information only (LEAD_NOTES 2e)"),
           tracks=len(segs), vias=len(vias), via_sizes_dia_drill_mm=dict(vsz),
           min_track_mm=round(min(s[2] for s in segs), 3), min_via_mm=dict(dia=min(v[1] for v in vias), drill=min(v[2] for v in vias)),
           min_track_to_track_space_mm=round(mins, 3), min_space_pair=where, min_via_to_track_space_mm=round(minv, 3),
           track_length_mm={k: round(v, 1) for k, v in length.items()},
           layers_used_per_netclass={k: sorted(v) for k, v in layers.items()},
           drc=dict(violations_error=sum(1 for v in d.get("violations", []) if v["severity"] == "error"),
                    violations_warning=sum(1 for v in d.get("violations", []) if v["severity"] == "warning"),
                    unconnected=len(d.get("unconnected_items", []))))
json.dump(res, open(out, "w"), indent=1)
print(json.dumps(res, indent=1))
