"""G7 closed-loop check, written independently of cplgate.py (own readers, own transforms).

Reads only emitted files: the CPL, the JLC BOM (C-number per designator), the X2 Gerbers (copper with %TO.P pad
attributes, paste, silkscreen) and the EasyEDA footprint of each C-number (JLC's own view of the part).
Places every EasyEDA pad at the CPL pose and checks that it lands on the board's copper of the same designator and
pin, with paste on it; reports whether a board silkscreen mark lies under the EasyEDA pin-1 / polarity mark.

Frames: Gerber and CPL are mm, Y up, origin = the board's drill/place origin.
Top: EasyEDA (x, y_down) -> (x, -y) -> turned CCW by Rotation -> + (MidX, MidY).
Bottom (convention D_b, unverified until the bottom canary exists): the part is drawn in the bottom view
(board seen from below = top view mirrored about the Y axis) turned CCW by Rotation; mapped back to the top view
by negating x of the turned vector: (MidX - qx, MidY + qy).

usage: python g7_verify.py --cpl CPL.csv --bom BOM.csv --gerbers DIR --easyeda DIR --out g7.json [--quiet]
exit 0 all pass, 1 any failure.
"""
import argparse, csv, glob, json, math, os, re, sys
from shapely.geometry import LineString, Point, Polygon, box
from shapely import affinity
from shapely.ops import unary_union


# ------------------------------------------------------------------ Gerber reader (X2, as written by KiCad)
def read_gerber(path):
    txt = open(path).read()
    fs = re.search(r"%FSLAX(\d)(\d)Y(\d)(\d)\*%", txt)
    dec = int(fs.group(2)) if fs else 6
    macros, aps, flashes, regions, draws = {}, {}, [], [], []
    for m in re.finditer(r"%AM([A-Za-z0-9_]+)\*(.*?)%", txt, re.S):
        macros[m.group(1)] = m.group(2)
    for m in re.finditer(r"%ADD(\d+)([A-Za-z0-9_]+),?([^*]*)\*%", txt):
        aps[int(m.group(1))] = (m.group(2), [float(v) for v in m.group(3).split("X") if v])
    attr = {}
    cur = None; x = y = 0.0; in_reg = False; reg = []; dark = True
    body = re.sub(r"%AM.*?%", "", txt, flags=re.S)
    for st in re.finditer(r"%([^%]*)%|([^%*]*)\*", body):
        ext, cmd = st.group(1), st.group(2)
        if ext is not None:
            e = ext.rstrip("*")
            if e in ("LPC", "LPD"):
                dark = e == "LPD"; continue
            if e.startswith("TO."):
                k, _, v = e[3:].partition(",")
                attr[k] = v.split(",")
            elif e.startswith("TD"):
                k = e[2:].lstrip(".")
                if k:
                    attr.pop(k, None)
                else:
                    attr = {}
            continue
        cmd = (cmd or "").strip()
        if not cmd or cmd.startswith("G04"):
            continue
        if cmd == "G36":
            in_reg = True; reg = []; continue
        if cmd == "G37":
            if len(reg) >= 3 and dark:
                regions.append((Polygon(reg).buffer(0), dict(attr)))
            in_reg = False; reg = []; continue
        mm = re.fullmatch(r"(?:G0?[123])?D(\d+)", cmd)
        if mm and int(mm.group(1)) >= 10:
            cur = int(mm.group(1)); continue
        mc = re.fullmatch(r"(?:G0?[123])?(?:X(-?\d+))?(?:Y(-?\d+))?(?:I-?\d+)?(?:J-?\d+)?D0?([123])", cmd)
        if not mc:
            continue
        nx = int(mc.group(1)) / 10 ** dec if mc.group(1) else x
        ny = int(mc.group(2)) / 10 ** dec if mc.group(2) else y
        d = mc.group(3)
        if in_reg:
            if d == "2":
                if len(reg) >= 3 and dark:
                    regions.append((Polygon(reg).buffer(0), dict(attr)))
                reg = [(nx, ny)]
            else:
                reg.append((nx, ny))
        elif not dark:
            pass  # clear polarity (e.g. mask openings subtracted from silk): not an object
        elif d == "3":
            flashes.append((ap_shape(aps.get(cur), macros, nx, ny), dict(attr)))
        elif d == "1" and cur in aps:
            w = aps[cur][1][0] if aps[cur][1] else 0.05
            draws.append((LineString([(x, y), (nx, ny)]).buffer(w / 2, 6), dict(attr)))
        x, y = nx, ny
    return dict(flashes=flashes, regions=regions, draws=draws)


def ap_shape(ap, macros, x, y):
    if ap is None:
        return Point(x, y).buffer(0.01)
    t, p = ap
    if t == "C":
        g = Point(0, 0).buffer(p[0] / 2, 16)
    elif t == "R":
        g = box(-p[0] / 2, -p[1] / 2, p[0] / 2, p[1] / 2)
    elif t == "O":
        r = min(p[0], p[1]) / 2
        g = box(-p[0] / 2 + r, -p[1] / 2 + r, p[0] / 2 - r, p[1] / 2 - r).buffer(r, 8) if p[0] != p[1] else Point(0, 0).buffer(r, 16)
    elif t in macros:
        body = macros[t]
        prims = [l.strip() for l in body.split("*") if l.strip() and not l.strip().startswith("0 ")]
        parts = []
        for pr in prims:
            v = pr.split(",")
            sub = lambda s: p[int(s[1:]) - 1] if s.startswith("$") else float(s)
            if v[0] == "21":  # centre line: exposure, w, h, cx, cy, rot
                w, h, cx, cy, rot = (sub(q) for q in v[2:7])
                parts.append(affinity.rotate(box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), rot, origin=(0, 0)))
            elif v[0] == "4":  # outline: exposure, n, x0, y0 ... xn, yn, rot
                n = int(v[2]); pts = [(sub(v[3 + 2 * i]), sub(v[4 + 2 * i])) for i in range(n + 1)]
                parts.append(affinity.rotate(Polygon(pts).buffer(0), sub(v[3 + 2 * (n + 1)]), origin=(0, 0)))
            elif v[0] == "1":  # circle: exposure, d, cx, cy
                d, cx, cy = (sub(q) for q in v[2:5])
                parts.append(Point(cx, cy).buffer(d / 2, 16))
            elif v[0] == "20":  # vector line: exposure, w, x1, y1, x2, y2, rot
                w, x1, y1, x2, y2, rot = (sub(q) for q in v[2:8])
                parts.append(affinity.rotate(LineString([(x1, y1), (x2, y2)]).buffer(w / 2, cap_style=2), rot, origin=(0, 0)))
        g = unary_union(parts) if parts else Point(0, 0).buffer(0.01)
    else:
        g = Point(0, 0).buffer(0.01)
    return affinity.translate(g, x, y)


# ------------------------------------------------------------------ EasyEDA footprint reader (independent of pk.py)
PAD = re.compile(r"\(pad\s+\"?([^\s\"]*)\"?\s+(\w+)\s+(\w+)\s+\(at\s+(-?[\d.]+)\s+(-?[\d.]+)(?:\s+(-?[\d.]+))?\)\s+\(size\s+([\d.]+)\s+([\d.]+)\)")
CIRC = re.compile(r"\(fp_circle\s+\(center\s+(-?[\d.]+)\s+(-?[\d.]+)\)\s+\(end\s+(-?[\d.]+)\s+(-?[\d.]+)\)\s+\(layer\s+\"?F\.SilkS")


XY = re.compile(r"\(xy\s+(-?[\d.]+)\s+(-?[\d.]+)\)")


def easyeda_pads(path):
    t = open(path).read()
    pads = []
    ms = list(PAD.finditer(t))
    for i, m in enumerate(ms):
        num, typ, shp, x, y, a, w, h = m.groups()
        if not num or typ == "np_thru_hole":
            continue
        d = dict(num=num, shape=shp, x=float(x), y=-float(y), a=float(a or 0), w=float(w), h=float(h))
        if shp == "custom":  # outline polygon(s) of the custom pad, in pad coordinates, Y flipped to Y up
            seg = t[m.end(): ms[i + 1].start() if i + 1 < len(ms) else len(t)]
            pts = [(float(px), -float(py)) for px, py in XY.findall(seg)]
            wd = re.search(r"\(width\s+([\d.]+)\)", seg)
            if len(pts) >= 3:
                d["outline"] = Polygon(pts).buffer((float(wd.group(1)) if wd else 0) / 2, 4)
        pads.append(d)
    marks = [(float(m.group(1)), -float(m.group(2))) for m in CIRC.finditer(t)]
    return pads, marks


def pad_geom(p):
    if "outline" in p:
        g = p["outline"]
    else:
        g = Point(0, 0).buffer(p["w"] / 2, 16) if p["shape"] == "circle" else box(-p["w"] / 2, -p["h"] / 2, p["w"] / 2, p["h"] / 2)
    return affinity.translate(affinity.rotate(g, p["a"], origin=(0, 0)), p["x"], p["y"])


def place(g, X, Y, R, bottom):
    g = affinity.rotate(g, R, origin=(0, 0))
    if bottom:
        g = affinity.scale(g, -1, 1, origin=(0, 0))
    return affinity.translate(g, X, Y)


def load_context(gerbers, bom, easyeda):
    lc = {}
    for r in csv.DictReader(open(bom, newline="")):
        for d in r["Designator"].split(","):
            lc[d.strip()] = r.get("LCSC Part #") or r.get("LCSC")
    G = {}
    for key, pat in (("top_cu", "*F_Cu.gtl"), ("bot_cu", "*B_Cu.gbl"), ("top_paste", "*F_Paste.gtp"), ("bot_paste", "*B_Paste.gbp"),
                     ("top_silk", "*F_Silkscreen.gto"), ("bot_silk", "*B_Silkscreen.gbo")):
        f = glob.glob(os.path.join(gerbers, pat))
        G[key] = read_gerber(f[0]) if f else dict(flashes=[], regions=[], draws=[])
    pads_by = {}
    for side in ("top", "bot"):
        for g, at in G[side + "_cu"]["flashes"] + G[side + "_cu"]["regions"]:
            if "P" in at:
                pads_by.setdefault((side, at["P"][0]), []).append((at["P"][1] if len(at["P"]) > 1 else "", g))
    paste = {s: unary_union([g for g, _ in G[s + "_paste"]["flashes"] + G[s + "_paste"]["regions"]]) for s in ("top", "bot")}
    silk = {s: unary_union([g for g, _ in G[s + "_silk"]["flashes"] + G[s + "_silk"]["regions"] + G[s + "_silk"]["draws"]]) for s in ("top", "bot")}
    fp = {}
    for c in set(lc.values()):
        f = glob.glob(os.path.join(easyeda, f"{c}_*.kicad_mod")) if c else []
        fp[c] = easyeda_pads(f[0]) if len(f) == 1 else None
    return dict(lc=lc, pads_by=pads_by, paste=paste, silk=silk, fp=fp)


def check_row(r, ctx):
    ref = r["Designator"]; X = float(r["Mid X"].rstrip("m")); Y = float(r["Mid Y"].rstrip("m")); R = float(r["Rotation"])
    bottom = r["Layer"].lower().startswith("b"); side = "bot" if bottom else "top"
    c = ctx["lc"].get(ref)
    out = dict(ref=ref, lcsc=c, side=side, fails=[], notes=[])
    if not ctx["fp"].get(c):
        out["fails"].append("no EasyEDA footprint to verify against"); return out
    pads, marks = ctx["fp"][c]
    board = ctx["pads_by"].get((side, ref), [])
    if not board:
        out["fails"].append(f"no copper flash with designator {ref} on the {side} layer")
    nopaste = 0; offs = []
    for p in pads:
        g = place(pad_geom(p), X, Y, R, bottom)
        same = [bg for pin, bg in board if pin == p["num"]]
        if same:
            bc = unary_union(same).centroid; offs.append((bc.x - g.centroid.x, bc.y - g.centroid.y))
        ov = max((bg.intersection(g).area / max(min(bg.area, g.area), 1e-9) for bg in same), default=0.0)
        if ov < 0.5 and not same and board and max((bg.intersection(g).area for _, bg in board), default=0) < 0.05 * g.area:
            out["notes"].append(f"JLC pad {p['num']} has no board pin of that number and lands on no copper (pad left out of the board land?)")
        elif ov < 0.5:
            other = [(pin, bg.intersection(g).area / max(min(bg.area, g.area), 1e-9)) for pin, bg in board if pin != p["num"]]
            hit = max(other, key=lambda t: t[1], default=("-", 0))
            out["fails"].append(f"JLC pad {p['num']} overlaps its board pad by {ov:.0%}" + (f"; lands on pin {hit[0]} ({hit[1]:.0%})" if hit[1] > 0.3 else ""))
        elif ctx["paste"][side].intersection(g).area < 0.2 * g.area:
            nopaste += 1
    if offs and board:
        mx = sum(o[0] for o in offs) / len(offs); my = sum(o[1] for o in offs) / len(offs)
        bmin = min(min(bg.bounds[2] - bg.bounds[0], bg.bounds[3] - bg.bounds[1]) for _, bg in board)
        out["centre_offset_mm"] = round(math.hypot(mx, my), 4)
        if math.hypot(mx, my) > 0.3 * bmin:
            out["fails"].append(f"part centre off by {math.hypot(mx, my):.3f} mm (> 0.3 x smallest board pad {bmin:.3f} mm)")
    if nopaste:
        out["notes"].append(f"{nopaste} pad(s) without paste under them")
    ms = [place(Point(m).buffer(0.05), X, Y, R, bottom) for m in marks]
    if ms:
        near = any(ctx["silk"][side].distance(m) < 0.3 for m in ms) if not ctx["silk"][side].is_empty else False
        out["silk_mark"] = "board silk under the JLC pin-1 mark" if near else "no board silk at the JLC pin-1 mark"
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cpl", required=True); ap.add_argument("--bom", required=True); ap.add_argument("--gerbers", required=True)
    ap.add_argument("--easyeda", required=True); ap.add_argument("--out", required=True); ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    ctx = load_context(a.gerbers, a.bom, a.easyeda)
    res = {r["Designator"]: check_row(r, ctx) for r in csv.DictReader(open(a.cpl, newline=""))}
    fails = {k: v["fails"] for k, v in res.items() if v["fails"]}
    summ = dict(parts=len(res), passed=len(res) - len(fails), failed=sorted(fails),
                silk_mark_found=sum(1 for v in res.values() if v.get("silk_mark", "").startswith("board")),
                silk_mark_missing=sum(1 for v in res.values() if v.get("silk_mark", "").startswith("no")),
                notes={k: v["notes"] for k, v in res.items() if v["notes"]})
    json.dump(dict(summary=summ, parts=res), open(a.out, "w"), indent=1)
    if not a.quiet:
        print(json.dumps({k: v for k, v in summ.items() if k != "notes"}))
    sys.exit(0 if not fails else 1)


if __name__ == "__main__":
    main()
