"""Post-process a routed board: add a silkscreen pin-1 dot or cathode bar to every IC and polarised part (ruling P-6).

The mark goes into the footprint (so it moves with the part) on F.SilkS / B.SilkS, line width >= 0.15 mm:
  - polarised 2-pad parts (pin map kind diode / led / photodiode / ...): a cathode (reference-terminal) bar beside the outer end of
    the reference pad; if the bar does not fit, a dot;
  - every other non-passive part with >= 2 pads: a dot nearest to pad 1 (or A1).
A mark is placed only where it keeps >= 0.15 mm from every copper pad of the same side, >= 0.15 mm from every other silk item or mark,
>= 0.10 mm from via copper, >= 0.30 mm inside the board outline, outside the courtyards of other parts on that side (fallback: inside a neighbour's courtyard margin
but >= 0.05 mm from its body, the convex hull of its Fab graphics; reported per part), within 1.5 mm of the
reference pad, and clearly nearer to the reference pad than to any other pad of the part (the gate's R4 reads it that way).
Parts where no position fits are reported, never forced. Then KiCad DRC runs on input and output (all severities, no zone refill)
and the tool fails if the output has any violation the input did not have.

usage: python add_silk_marks.py --board IN.kicad_pcb --out OUT.kicad_pcb --report DIR [--design v3/design] [--no-drc]
exit: 0 done (with or without unplaced parts, see report), 1 DRC got worse, 2 error.
"""
import argparse, glob, json, math, os, re, shutil, subprocess, sys, uuid
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import polygonize, unary_union
from shapely.strtree import STRtree
from shapely import affinity

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pk  # noqa: E402

PASSIVE = re.compile(r"^(R|C|L|FB)\d")
POLAR = {"diode", "led", "photodiode", "tantalum", "electrolytic", "tvs_uni", "zener", "schottky"}
W = 0.15            # mark line width (mm)
DOT_R = 0.05        # dot circle radius; outer diameter = 2 * DOT_R + W = 0.25 mm
C_PAD, C_SILK, C_VIA, C_EDGE, NEAR = 0.15, 0.15, 0.10, 0.30, 1.5
C_BODY = 0.05       # fallback only (2026-11-16, final package): a mark may enter another part's courtyard margin when no position
                    # outside every courtyard exists, but keeps >= C_BODY from that part's body (convex hull of its Fab graphics)


def pad_board_poly(fp, p):
    """Pad outline in board coordinates (pad stored in the footprint's stored frame; rot relative to the footprint)."""
    g = p["prim"] if p.get("prim") is not None else (Point(0, 0).buffer(p["w"] / 2, 16) if p["shape"] in ("circle", "oval") and abs(p["w"] - p["h"]) < 1e-6
                                                     else box(-p["w"] / 2, -p["h"] / 2, p["w"] / 2, p["h"] / 2))
    g = affinity.rotate(g, -p["rot"], origin=(0, 0))
    g = affinity.translate(g, p["x"], p["y"])
    g = affinity.rotate(g, -fp["rot"], origin=(0, 0))
    return affinity.translate(g, fp["x"], fp["y"])


def to_stored(fp, xy):
    x, y = xy[0] - fp["x"], xy[1] - fp["y"]
    return pk.rot((x, y), -fp["rot"])


def outline(edges):
    segs = []
    for kind, pts in edges:
        if kind == "gr_line":
            segs.append(LineString([(pts[0][1], pts[0][2]), (pts[1][1], pts[1][2])]))
        elif kind == "gr_circle":
            c = [q for q in pts if q[0] == "center"][0]; e = [q for q in pts if q[0] == "end"][0]
            segs.append(Point(c[1], c[2]).buffer(math.hypot(e[1] - c[1], e[2] - c[2]), 64).exterior)
        elif kind == "gr_arc":
            segs.append(LineString([(q[1], q[2]) for q in pts]))
        elif kind == "gr_rect":
            s, e = pts[0], pts[1]; segs.append(box(s[1], s[2], e[1], e[2]).exterior)
        elif kind == "gr_poly":
            segs.append(Polygon([(q[1], q[2]) for q in pts]).exterior)
    polys = sorted(polygonize(unary_union(segs)), key=lambda p: -p.area)
    if not polys:
        raise SystemExit("no closed board outline on Edge.Cuts")
    out = polys[0]
    for h in polys[1:]:
        if out.contains(h.representative_point()):
            out = out.difference(h)
    return out


def gfx_board_geo(fp, g):
    pts = [pk.rot(q, fp["rot"]) for q in g["pts"]]
    pts = [(fp["x"] + x, fp["y"] + y) for x, y in pts]
    if g["kind"] == "fp_circle":
        return Point(pts[0]).buffer(g.get("r", 0) + g["width"] / 2, 12)
    if g["kind"] == "fp_poly" and len(pts) >= 3:
        return Polygon(pts).buffer(g["width"] / 2)
    if g["kind"] == "fp_rect":
        (x0, y0), (x1, y1) = pts[0], pts[1]
        return box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)).exterior.buffer(max(g["width"], 0.01) / 2)
    return LineString(pts).buffer(max(g["width"], 0.01) / 2) if len(pts) >= 2 else Point(pts[0]).buffer(0.01)


def vias(text):
    out = []
    for m in re.finditer(r"\(via\b(.*?)\(at ([-\d.]+) ([-\d.]+)\)\s*\(size ([-\d.]+)\)", text, re.S):
        out.append(Point(float(m.group(2)), float(m.group(3))).buffer(float(m.group(4)) / 2, 12))
    return out


def courtyard(fp, side):
    lay = "F.CrtYd" if side == "top" else "B.CrtYd"
    gs = [gfx_board_geo(fp, g) for g in fp["gfx"] if g["layer"] in (lay, lay.replace("CrtYd", "Courtyard"))]
    if not gs:
        return None
    u = unary_union(gs)
    hull = u.convex_hull
    return hull if hull.area > 0.01 else None


def silk_items(text):
    """Board-level silk graphics (not footprint children)."""
    out = {"top": [], "bottom": []}
    depth0 = re.finditer(r"\n\t\((gr_line|gr_poly|gr_circle|gr_rect|gr_arc|gr_text)\b", text)
    for m in depth0:
        blk = text[m.start(): text.find("\n\t)", m.start()) + 3]
        ly = re.search(r'\(layer "([^"]+)"', blk)
        if not ly or "Silk" not in ly.group(1):
            continue
        side = "top" if ly.group(1).startswith("F.") else "bottom"
        xy = [(float(a), float(b)) for a, b in re.findall(r"\((?:start|end|center|mid|xy|at) ([-\d.]+) ([-\d.]+)", blk)]
        if xy:
            out[side].append(LineString(xy).buffer(0.1) if len(xy) > 1 else Point(xy[0]).buffer(0.5))
    return out


def fp_block_span(text, ref):
    m = re.search(r'\(property "Reference" "%s"' % re.escape(ref), text)
    if not m:
        return None
    s = text.rfind("\n\t(footprint ", 0, m.start()) + 1
    depth = 0
    for i in range(s, len(text)):
        ch = text[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return s, i
    return None


def sexpr_mark(fp, mark, layer):
    u = str(uuid.uuid4())
    if mark["kind"] == "dot":
        cx, cy = to_stored(fp, mark["c"])
        return (f'\t\t(fp_circle (center {cx:.4f} {cy:.4f}) (end {cx + DOT_R:.4f} {cy:.4f}) (stroke (width {W}) (type solid)) (fill yes) '
                f'(layer "{layer}") (uuid "{u}"))\n')
    (ax, ay), (bx, by) = to_stored(fp, mark["a"]), to_stored(fp, mark["b"])
    return f'\t\t(fp_line (start {ax:.4f} {ay:.4f}) (end {bx:.4f} {by:.4f}) (stroke (width {W}) (type solid)) (layer "{layer}") (uuid "{u}"))\n'


def mark_geo(mark):
    if mark["kind"] == "dot":
        return Point(mark["c"]).buffer(DOT_R + W / 2, 16)
    return LineString([mark["a"], mark["b"]]).buffer(W / 2, 8)


def drc(kicad, board, out_json):
    r = subprocess.run([kicad, "pcb", "drc", "--format", "json", "--severity-all", "-o", out_json, board], capture_output=True, text=True)
    try:
        d = json.load(open(out_json))
    except Exception:
        return None, r.stderr[-400:]
    cnt = {}
    for v in d.get("violations", []):
        k = f"{v.get('severity')}:{v.get('type')}"
        cnt[k] = cnt.get(k, 0) + 1
    cnt["unconnected"] = len(d.get("unconnected_items", []))
    return cnt, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", required=True); ap.add_argument("--out", required=True); ap.add_argument("--report", required=True)
    ap.add_argument("--design", default=pk.DESIGN); ap.add_argument("--no-drc", action="store_true")
    ap.add_argument("--kicad-cli", default=os.environ.get("KICAD_CLI", "kicad-cli"))
    a = ap.parse_args()
    os.makedirs(a.report, exist_ok=True)
    text = open(a.board).read()
    B = pk.load_board(a.board); F = B["footprints"]
    full = pk.bom_full(os.path.join(a.design, "BOM_full_v3f.csv"))
    pm = {os.path.basename(f)[:-5]: pk.load_yaml(f) for f in glob.glob(os.path.join(a.design, "pinmap", "C*.yaml"))}
    area = outline(B["edges"]).buffer(-C_EDGE)
    vg = vias(text)
    body = {}
    obst = {"top": {"pad": [], "silk": list(silk_items(text)["top"]), "crt": []}, "bottom": {"pad": [], "silk": list(silk_items(text)["bottom"]), "crt": []}}
    for r, fp in F.items():
        for p in fp["pads"]:
            lay = " ".join(p["layers"])
            g = pad_board_poly(fp, p)
            if p["type"] in ("thru_hole", "np_thru_hole") or "*.Cu" in lay:
                obst["top"]["pad"].append((r, g)); obst["bottom"]["pad"].append((r, g))
            elif "F.Cu" in lay:
                obst["top"]["pad"].append((r, g))
            elif "B.Cu" in lay:
                obst["bottom"]["pad"].append((r, g))
        for g in fp["gfx"]:
            if "Silk" in g["layer"]:
                obst["top" if g["layer"].startswith("F.") else "bottom"]["silk"].append(gfx_board_geo(fp, g))
        cy = courtyard(fp, fp["side"])
        if cy is not None:
            obst[fp["side"]]["crt"].append((r, cy))
        fab = [gfx_board_geo(fp, g) for g in fp["gfx"] if g["layer"] in (("F.Fab", "F.Fabrication") if fp["side"] == "top" else ("B.Fab", "B.Fabrication"))]
        body[r] = unary_union(fab).convex_hull if fab else cy

    targets = []
    for r, fp in sorted(F.items()):
        info = full.get(r, {})
        if PASSIVE.match(r) or info.get("Class") != "JLC-placed":
            continue
        pads = [p for p in fp["pads"] if p["num"] and p["type"] != "np_thru_hole"]
        if len(pads) < 2:
            continue
        m = pm.get(info.get("LCSC"), {}) or {}
        pol = m.get("polarity") if isinstance(m.get("polarity"), dict) else {}
        nums = {p["num"] for p in pads}
        refn, kind = None, "dot"
        if pol.get("kind") in POLAR and len(nums) == 2 and pol.get("reference_pin") and str(pol.get("reference_pin")) in nums:
            refn, kind = str(pol["reference_pin"]), "bar"
        elif "1" in nums:
            refn = "1"
        elif "A1" in nums:
            refn = "A1"
        if refn:
            targets.append((r, fp, pads, refn, kind))

    placed, unplaced, new_text = [], [], text
    for r, fp, pads, refn, kind in targets:
        side = fp["side"]; O = obst[side]
        own = [pad_board_poly(fp, p) for p in pads]
        refp = unary_union([pad_board_poly(fp, p) for p in pads if p["num"] == refn])
        others = unary_union([pad_board_poly(fp, p) for p in pads if p["num"] != refn])
        hull = unary_union(own).convex_hull
        pad_tree = [g for rr, g in O["pad"]]
        crt = [g for rr, g in O["crt"] if rr != r]
        crt_ref = [rr for rr, g in O["crt"] if rr != r]
        vtree = vg
        allg = pad_tree + O["silk"] + crt + vtree
        tree = STRtree(allg) if allg else None
        npad, nsilk, ncrt = len(pad_tree), len(O["silk"]), len(crt)

        def ok(mk, relax=False):
            g = mark_geo(mk)
            if not area.contains(g):
                return "edge"
            if refp.distance(g) > NEAR:
                return "far"
            if others.distance(g) < refp.distance(g) + 0.1:
                return "ambiguous"
            if tree is not None:
                for i in tree.query(g.buffer(C_PAD)):
                    i = int(i); og = allg[i]
                    if i < npad:
                        if og.distance(g) < C_PAD:
                            return "pad"
                    elif i < npad + nsilk:
                        if og.distance(g) < C_SILK:
                            return "silk"
                    elif i < npad + nsilk + ncrt:
                        if og.intersects(g):
                            bo = body.get(crt_ref[i - npad - nsilk])
                            if not relax or bo is None or bo.distance(g) < C_BODY:
                                return "courtyard"
                    elif og.distance(g) < C_VIA:
                        return "via"
            return None

        cands = []
        if kind == "bar":
            q = [p for p in pads if p["num"] == refn][0]; o = [p for p in pads if p["num"] != refn][0]
            cref = refp.centroid; coth = pad_board_poly(fp, o).centroid
            ux, uy = cref.x - coth.x, cref.y - coth.y; L = math.hypot(ux, uy) or 1; ux, uy = ux / L, uy / L
            # extent of the reference pad along the axis and across it
            proj = [((x - cref.x) * ux + (y - cref.y) * uy, -(x - cref.x) * uy + (y - cref.y) * ux) for x, y in refp.exterior.coords]
            ext = max(t[0] for t in proj); half = max(abs(t[1]) for t in proj)
            for extra in (0.0, 0.05, 0.1, 0.2, 0.3):
                d = ext + C_PAD + W / 2 + extra
                c = (cref.x + ux * d, cref.y + uy * d)
                for hl in (half, max(half * 0.7, 0.2), 0.2):
                    cands.append(dict(kind="bar", a=(c[0] - uy * hl, c[1] + ux * hl), b=(c[0] + uy * hl, c[1] - ux * hl), score=extra + (half - hl)))
        rb = refp.bounds; cen = hull.centroid
        step = 0.05
        xs = [rb[0] - NEAR + i * step for i in range(int((rb[2] - rb[0] + 2 * NEAR) / step) + 1)]
        ys = [rb[1] - NEAR + i * step for i in range(int((rb[3] - rb[1] + 2 * NEAR) / step) + 1)]
        dots = []
        for x in xs:
            for y in ys:
                pt = Point(x, y)
                d = refp.distance(pt)
                if d < C_PAD + DOT_R + W / 2 - 1e-9 or d > NEAR:
                    continue
                inside = hull.buffer(0.05).contains(pt)
                away = math.hypot(x - cen.x, y - cen.y)
                dots.append(dict(kind="dot", c=(x, y), score=10 + d + (1.0 if inside else 0.0) - 0.05 * away))
        cands += sorted(dots, key=lambda m: m["score"])
        why = {}
        choice = None
        for mk in cands:
            w = ok(mk)
            if w is None:
                choice = mk; break
            why[w] = why.get(w, 0) + 1
        fallback = None
        if choice is None:  # second pass: courtyard margin of a neighbour allowed, its body kept clear (C_BODY)
            for mk in cands:
                if ok(mk, relax=True) is None:
                    choice = mk; fallback = "in a neighbour's courtyard margin, >= %.2f mm from its body (Fab outline)" % C_BODY; break
        if choice is None:
            unplaced.append(dict(ref=r, side=side, ref_pad=refn, wanted=kind, candidates=len(cands), blocked_by=why)); continue
        g = mark_geo(choice)
        O["silk"].append(g)
        layer = "F.SilkS" if side == "top" else "B.SilkS"
        span = fp_block_span(new_text, r)
        new_text = new_text[:span[1]] + sexpr_mark(fp, choice, layer) + "\t" + new_text[span[1]:]
        ent = dict(ref=r, side=side, ref_pad=refn, mark=choice["kind"], width=W,
                   at=[round(v, 3) for v in (choice["c"] if choice["kind"] == "dot" else g.centroid.coords[0])],
                   gap_to_ref_pad=round(refp.distance(g), 3))
        if choice["kind"] == "dot" and kind == "bar":
            ent["note"] = "cathode bar did not fit; dot instead"
        if fallback:
            ent["note"] = (ent.get("note", "") + "; " if ent.get("note") else "") + fallback
        placed.append(ent)

    open(a.out, "w").write(new_text)
    for ext in (".kicad_pro", ".kicad_dru", ".kicad_prl"):
        src = a.board[:-10] + ext
        if os.path.exists(src):
            shutil.copy(src, a.out[:-10] + ext)
    res = dict(input=os.path.abspath(a.board), output=os.path.abspath(a.out), input_sha256=pk.sha256(a.board), output_sha256=pk.sha256(a.out),
               rules=dict(width=W, dot_outer_diameter=2 * DOT_R + W, pad=C_PAD, silk=C_SILK, via=C_VIA, edge=C_EDGE, near=NEAR),
               targets=len(targets), placed=len(placed), unplaced=unplaced, marks=placed)
    code = 0
    if not a.no_drc:
        c0, e0 = drc(a.kicad_cli, a.board, os.path.join(a.report, "drc_before.json"))
        c1, e1 = drc(a.kicad_cli, a.out, os.path.join(a.report, "drc_after.json"))
        worse = {k: (c0 or {}).get(k, 0) for k in (c1 or {})} if c1 is not None else None
        worse = {k: f"{(c0 or {}).get(k, 0)} -> {v}" for k, v in (c1 or {}).items() if v > (c0 or {}).get(k, 0)} if c1 is not None else {"drc": "failed " + str(e1)}
        res["drc"] = dict(before=c0, after=c1, worse=worse)
        if worse:
            code = 1
    pk.dump(res, os.path.join(a.report, "silk_marks.json"))
    L = ["# Silk marks added (add_silk_marks.py)", "", f"Input `{res['input']}` -> `{res['output']}`", "",
         f"Targets {len(targets)} (ICs and polarised parts, JLC-placed, >= 2 pads); placed {len(placed)}; **not placed {len(unplaced)}**.", "",
         f"Rules: line width {W} mm, dot outer diameter {2 * DOT_R + W:.2f} mm; clearances: pad {C_PAD}, silk {C_SILK}, via {C_VIA}, board edge {C_EDGE} mm; "
         f"within {NEAR} mm of the reference pad and nearer to it than to any other pad; outside other parts' courtyards "
         f"(fallback when nothing fits: inside a neighbour's courtyard margin but >= {C_BODY} mm from its body; marked in the table).", ""]
    if "drc" in res:
        L += [f"DRC (all severities, no refill) before {res['drc']['before']}", "", f"after {res['drc']['after']}", "",
              f"New violations: {res['drc']['worse'] or 'none'}", ""]
    L += ["## Not placed (no legal position)", "", "| Ref | Side | Ref pad | Wanted | Candidates | Blocked by |", "|---|---|---|---|---|---|"]
    L += [f"| {u['ref']} | {u['side']} | {u['ref_pad']} | {u['wanted']} | {u['candidates']} | {u['blocked_by']} |" for u in unplaced] or ["| - | | | | | |"]
    L += ["", "## Placed", "", "| Ref | Side | Pad | Mark | Board XY | Gap to pad |", "|---|---|---|---|---|---|"]
    L += [f"| {p['ref']} | {p['side']} | {p['ref_pad']} | {p['mark']}{' (' + p['note'] + ')' if p.get('note') else ''} | {p['at']} | {p['gap_to_ref_pad']} |" for p in placed]
    open(os.path.join(a.report, "silk_marks.md"), "w").write("\n".join(L) + "\n")
    print(json.dumps(dict(targets=len(targets), placed=len(placed), unplaced=[u["ref"] for u in unplaced], drc_worse=res.get("drc", {}).get("worse"))))
    sys.exit(code)


if __name__ == "__main__":
    main()
