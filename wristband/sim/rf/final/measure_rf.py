"""[rf final] Measure the feed geometry from rf_dump.json (closed board). usage: emsim-python measure_rf.py -> rf_geom_final.json"""
import json, math
from shapely.geometry import Polygon, LineString, Point, box
from shapely.ops import unary_union
D = json.load(open("rf_dump.json"))
FEED = (2.75, 3.0); MODEL_J40 = (3.30, 1.55)
pads = D["pads"]; trk = D["tracks"]; vias = D["vias"]
P = {(p["ref"], p["num"]): p for p in pads}
R = {}
R["parts"] = {k: dict(v, pos=v["pos"]) for k, v in D["fps"].items()}
j = D["fps"]["J40"]["pos"]; R["J40"] = dict(pos=j, rot=D["fps"]["J40"]["rot"] % 360, model_pos=MODEL_J40,
    shift_mm=round(math.dist(j, MODEL_J40), 3), shift_xy=[round(j[0] - MODEL_J40[0], 3), round(j[1] - MODEL_J40[1], 3)])
# AE1 feed copper (custom pad 1) and J40 land
ae = [p for p in pads if p["ref"] == "AE1" and p["num"] == "1"][0]
aep = unary_union([Polygon(q) for q in ae["poly"]]); jl = unary_union([Polygon(q) for q in P[("J40", "1")]["poly"]])
R["AE1_feed_copper"] = dict(bounds=[round(x, 3) for x in aep.bounds], area=round(aep.area, 3), J40_land_inside_frac=round(jl.intersection(aep).area / jl.area, 3),
                            J40_land_centroid=[round(jl.centroid.x, 3), round(jl.centroid.y, 3)])
# tracks per RF net (F.Cu), graph lengths
def segs(net): return [t for t in trk if t["net"] == net]
def tot(net):
    out = {}
    for t in segs(net):
        L = math.dist(t["s"], t["e"]); k = f'{t["layer"]} w{t["w"]:.3f}'; out[k] = round(out.get(k, 0) + L, 3)
    return out
R["tracks_by_width"] = {n: tot(n) for n in ("ANT_FEED", "RF_50R")}
R["vias_on_rf_nets"] = [v for v in vias if v["net"] in ("ANT_FEED", "RF_50R")]
# path lengths: Dijkstra over track endpoints + pad centres
import heapq
def graph(net):
    G = {}
    def add(a, b, w, L):
        a, b = tuple(a), tuple(b); G.setdefault(a, []).append((b, L, w)); G.setdefault(b, []).append((a, L, w))
    for t in segs(net): add(t["s"], t["e"], t["w"], math.dist(t["s"], t["e"]))
    nodes = list(G)
    for p in pads:
        if p["net"] != net: continue
        poly = unary_union([Polygon(q) for q in p["poly"]])
        for n in nodes:
            if poly.buffer(1e-3).contains(Point(n)): add(p["c"], n, 9, math.dist(p["c"], n))
    return G
def sp(G, a, b):
    a, b = tuple(a), tuple(b); dist = {a: 0}; prev = {}; h = [(0, a)]
    while h:
        d, u = heapq.heappop(h)
        if u == b: break
        if d > dist[u]: continue
        for v, L, w in G.get(u, []):
            if d + L < dist.get(v, 1e9): dist[v] = d + L; prev[v] = (u, w, L); heapq.heappush(h, (d + L, v))
    path = []; u = b
    while u in prev: path.append(prev[u][1:] + (u,)); u = prev[u][0]
    return dist.get(b), path[::-1]
G = graph("ANT_FEED")
# feed point = where the track meets AE1 pad / Y 3.0 line; add the feed point as a node on the X 2.75 track
fp = None
for t in segs("ANT_FEED"):
    ls = LineString([t["s"], t["e"]])
    x = ls.intersection(LineString([(0, 3.0), (6, 3.0)]))
    if not x.is_empty: fp = (round(x.x, 4), round(x.y, 4)); a, b2 = tuple(t["s"]), tuple(t["e"])
G.setdefault(fp, []).extend([(a, math.dist(fp, a), 0.17), (b2, math.dist(fp, b2), 0.17)]); G[a].append((fp, math.dist(fp, a), 0.17)); G[b2].append((fp, math.dist(fp, b2), 0.17))
c215_2 = P[("C215", "2")]["c"]; l204_1 = P[("L204", "1")]["c"]
lb, pb = sp(G, c215_2, fp); ls_, ps = sp(G, l204_1, c215_2)
R["feed_point_crossing_Y3"] = fp
R["l_b_C215pad2_centre_to_feed_mm"] = round(lb, 3)
R["stub_L204pad1_centre_to_C215pad2_centre_mm"] = round(ls_, 3)
R["L204pad1_to_feed_mm"] = round(lb + ls_, 3)
R["feed_path_widths"] = sorted({round(w, 3) for w, L, n in pb if w != 9})
R["stub_path_widths"] = sorted({round(w, 3) for w, L, n in ps if w != 9})
# pad-edge lengths (copper outside the land outlines)
def outside(path_net, path, refs):
    land = unary_union([Polygon(q) for p in pads if (p["ref"], p["num"]) in refs for q in p["poly"]])
    L = 0
    for w, l, n in path: pass
    return land
c215l = unary_union([Polygon(q) for q in P[("C215", "2")]["poly"]]); l204l = unary_union([Polygon(q) for q in P[("L204", "1")]["poly"]])
stub_line = unary_union([LineString([t["s"], t["e"]]) for t in segs("ANT_FEED") if abs(t["s"][1] - t["e"][1]) < 0.2 and min(t["s"][0], t["e"][0]) > 2.9])
R["stub_edge_to_edge_mm"] = round(stub_line.difference(c215l).difference(l204l).length, 3)
feed_line = unary_union([LineString([t["s"], t["e"]]) for t in segs("ANT_FEED")]).difference(stub_line)
R["feed_edge_C215land_to_Y3_mm"] = round(feed_line.difference(c215l).intersection(box(0, 3.0, 6, 6)).length, 3)
# RF_50R: C213.1 -> C215.1 and L201 -> C213.1
G2 = graph("RF_50R")
c213_1 = P[("C213", "1")]["c"]; c215_1 = P[("C215", "1")]["c"]
l1, p1 = sp(G2, c213_1, c215_1)
other = [p for p in pads if p["net"] == "RF_50R" and p["ref"] not in ("C213", "C215")]
R["RF_50R_pads"] = [(p["ref"], p["num"], p["c"]) for p in pads if p["net"] == "RF_50R"]
R["l_a_C213pad1_to_C215pad1_mm"] = round(l1, 3)
wl = {}
for w, L, n in p1:
    if w != 9: wl[round(w, 3)] = round(wl.get(round(w, 3), 0) + L, 3)
R["l_a_by_width_mm"] = wl
if other:
    l2, p2 = sp(G2, other[0]["c"], c213_1); R["chip_side_to_C213pad1_mm"] = round(l2, 3); R["chip_side_pad"] = other[0]["ref"] + "." + other[0]["num"]
    wl2 = {}
    for w, L, n in p2:
        if w != 9: wl2[round(w, 3)] = round(wl2.get(round(w, 3), 0) + L, 3)
    R["chip_side_by_width_mm"] = wl2
# gaps to F.Cu copper of other nets (filled GND + tracks + pads) along RF tracks
fcu_gnd = unary_union([Polygon(f["outer"], f["holes"]) for f in D["fills"].get("F.Cu", []) if f["net"] == "GND"])
others = unary_union([LineString([t["s"], t["e"]]).buffer(t["w"] / 2) for t in trk if t["layer"] == "F.Cu" and t["net"] not in ("RF_50R", "ANT_FEED")] +
                     [Polygon(q) for p in pads if p["net"] not in ("RF_50R", "ANT_FEED") and "F.Cu" in p["layers"] for q in p["poly"]] + [fcu_gnd])
gap = {}
for n in ("ANT_FEED", "RF_50R"):
    g = []
    for t in segs(n):
        if t["layer"] != "F.Cu": continue
        cu = LineString([t["s"], t["e"]]).buffer(t["w"] / 2, cap_style=2)
        g.append(dict(s=t["s"], e=t["e"], w=t["w"], gap=round(cu.distance(others), 3), gap_gnd_fill=round(cu.distance(fcu_gnd), 3) if not fcu_gnd.is_empty else None))
    gap[n] = g
R["gaps"] = gap
# In1 (GND plane) under the RF tracks: solid?
in1 = unary_union([Polygon(f["outer"], f["holes"]) for f in D["fills"].get("In1.Cu", []) if f["net"] == "GND"])
rfcu = unary_union([LineString([t["s"], t["e"]]).buffer(t["w"] / 2 + 0.15) for t in trk if t["net"] in ("ANT_FEED", "RF_50R") and t["layer"] == "F.Cu"])
rfcu_out = rfcu.intersection(box(0, 3.0, 40, 34))
R["In1_under_rf_tracks_coverage"] = round(rfcu_out.intersection(in1).area / rfcu_out.area, 4)
# stitching vias: GND vias near Y 3.0 edge (X 0.26-5.0) and X 5.0 edge (Y 0-3.0)
gv = [v for v in vias if v["net"] == "GND"]
rowY = sorted([v for v in gv if 3.0 <= v["c"][1] <= 3.0 + 0.8 and v["c"][0] <= 5.6], key=lambda v: v["c"][0])
rowX = sorted([v for v in gv if 5.0 <= v["c"][0] <= 5.0 + 0.8 and v["c"][1] <= 3.6], key=lambda v: v["c"][1])
def pitch(vs, ax):
    xs = [v["c"][ax] for v in vs]; return [round(b - a, 3) for a, b in zip(xs, xs[1:])]
R["stitch"] = dict(
    row_Y3=[dict(c=v["c"], back=round(v["c"][1] - 3.0, 3), d=v["d"]) for v in rowY], row_Y3_pitch=pitch(rowY, 0),
    row_X5=[dict(c=v["c"], back=round(v["c"][0] - 5.0, 3), d=v["d"]) for v in rowX], row_X5_pitch=pitch(rowX, 1))
# solid ground edges: GND fill on each layer along the edges (fraction of edge length covered within 0.3 mm)
edgeY = LineString([(0.26, 3.05), (5.0, 3.05)]); edgeX = LineString([(5.05, 0.3), (5.05, 3.0)])
cov = {}
for ln, fl in D["fills"].items():
    g = unary_union([Polygon(f["outer"], f["holes"]) for f in fl if f["net"] == "GND"])
    if g.is_empty: continue
    cov[ln] = dict(Y3=round(edgeY.intersection(g.buffer(0.05)).length / edgeY.length, 3), X5=round(edgeX.intersection(g.buffer(0.05)).length / edgeX.length, 3))
R["gnd_edge_coverage"] = cov
# pocket contents: any copper other than AE1/J40 within the pocket (Y < 3.0, X < 5.0)
pocket = box(0, 0, 5.0, 3.0)
foreign = []
for t in trk:
    if LineString([t["s"], t["e"]]).buffer(t["w"] / 2).intersection(pocket).area > 1e-4 and not (t["net"] == "ANT_FEED"):
        foreign.append(("trk", t["net"], t["layer"], t["s"], t["e"]))
for v in vias:
    if Point(v["c"]).buffer(v["d"] / 2).intersection(pocket).area > 1e-4: foreign.append(("via", v["net"], v["c"]))
for ln, fl in D["fills"].items():
    for f in fl:
        a = Polygon(f["outer"], f["holes"]).intersection(pocket).area
        if a > 1e-3: foreign.append(("fill", ln, f["net"], round(a, 3)))
R["pocket_foreign_copper"] = foreign
ant_feed_trk_in_pocket = [(t["layer"], t["s"], t["e"], t["w"]) for t in segs("ANT_FEED") if LineString([t["s"], t["e"]]).intersection(pocket).length > 0]
R["ANT_FEED_tracks_in_pocket"] = ant_feed_trk_in_pocket
# copper to board edge near the corner (x<=6,y<=4)
edge = unary_union([LineString([e["s"], e["e"]]) for e in D["edges"] if e["shape"] in ("Line", "Segment")])
cu_corner = unary_union([Polygon(q) for p in pads if p["c"][0] < 6 and p["c"][1] < 4.5 for q in p["poly"]] +
                        [Polygon(f["outer"], f["holes"]).intersection(box(-1, -1, 6, 4.5)) for fl in D["fills"].values() for f in fl])
R["corner_copper_to_edge_min_mm"] = round(cu_corner.distance(edge), 3) if not edge.is_empty else None
json.dump(R, open("rf_geom_final.json", "w"), indent=1, default=str)
for k, v in R.items():
    if k not in ("gaps",): print(k, json.dumps(v, default=str)[:600])
for n, g in R["gaps"].items():
    print(n, [(x["w"], x["gap"], x["gap_gnd_fill"]) for x in g])
