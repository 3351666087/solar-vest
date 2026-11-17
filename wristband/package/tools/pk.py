"""Shared readers for the production package (board, footprints, symbols, netlist, BOMs).

Frames: KiCad board frame is mm, Y down. "Footprint frame" = library frame of the footprint (rotation undone,
bottom-side mirror undone). Rotation convention: KiCad's, i.e. a positive angle turns CCW as seen on screen (Y down).
"""
import csv, hashlib, json, math, os, re

DESIGN = os.environ.get("V3_DESIGN", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "design"))

_tok = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))')


def parse(text):
    stack, cur = [], []
    for m in _tok.finditer(text):
        o, c, s, a = m.groups()
        if o:
            stack.append(cur); cur = []
        elif c:
            done = cur; cur = stack.pop(); cur.append(done)
        elif s is not None:
            cur.append(s[1:-1].replace('\\"', '"'))
        elif a is not None:
            cur.append(a)
    return cur[0] if cur else None


def find(node, key):
    return [n for n in node if isinstance(n, list) and n and n[0] == key]


def first(node, key, default=None):
    r = find(node, key)
    return r[0] if r else default


def sha256(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def rot(p, deg):
    """KiCad rotation (Y down, positive = CCW on screen)."""
    t = math.radians(deg); x, y = p
    return (x * math.cos(t) + y * math.sin(t), -x * math.sin(t) + y * math.cos(t))


def _pad(p, fp_rot=0.0, board=False):
    at = first(p, "at"); size = first(p, "size")
    ang = float(at[3]) if len(at) > 3 else 0.0
    if board:
        ang -= fp_rot  # board files store the absolute pad angle
    lay = (first(p, "layers") or ["layers"])[1:]
    net = first(p, "net")
    rr = first(p, "roundrect_rratio")
    d = dict(num=str(p[1]), type=p[2], shape=p[3], x=float(at[1]), y=float(at[2]), rot=ang % 360,
             w=float(size[1]), h=float(size[2]), layers=lay,
             net=(net[-1] if net else None), rratio=float(rr[1]) if rr else 0.0)
    prim = first(p, "primitives")
    if p[3] == "custom" and prim:
        from shapely.geometry import Point, Polygon, box
        from shapely.ops import unary_union
        gs = [Point(0, 0).buffer(max(d["w"], d["h"]) / 2, 8)]
        for g in prim[1:]:
            if not isinstance(g, list):
                continue
            wd = first(g, "width"); wd = float(wd[1]) if wd else 0.0
            if g[0] == "gr_poly":
                pts = [(float(q[1]), float(q[2])) for q in find(first(g, "pts"), "xy")]
                gs.append(Polygon(pts).buffer(wd / 2, 4))
            elif g[0] == "gr_rect":
                s_, e_ = first(g, "start"), first(g, "end")
                gs.append(box(float(s_[1]), float(s_[2]), float(e_[1]), float(e_[2])).buffer(wd / 2, 4))
            elif g[0] == "gr_circle":
                c_, e_ = first(g, "center"), first(g, "end")
                gs.append(Point(float(c_[1]), float(c_[2])).buffer(math.hypot(float(e_[1]) - float(c_[1]), float(e_[2]) - float(c_[2])) + wd / 2, 16))
        u = unary_union(gs)
        d["prim"] = u  # pad-local outline (pad angle not applied)
        b = u.bounds
        d["w"], d["h"] = b[2] - b[0], b[3] - b[1]
    return d


def _graphics(fp):
    out = []
    for kind in ("fp_line", "fp_circle", "fp_arc", "fp_poly", "fp_rect"):
        for g in find(fp, kind):
            ly = first(g, "layer")
            if not ly:
                continue
            st = first(g, "stroke"); w = first(g, "width")
            width = float(first(st, "width")[1]) if st and first(st, "width") else (float(w[1]) if w else 0.0)
            fill = first(g, "fill")
            d = dict(kind=kind, layer=ly[1], width=width, fill=bool(fill and fill[1] in ("solid", "yes")))
            if kind == "fp_line" or kind == "fp_rect":
                s, e = first(g, "start"), first(g, "end")
                d["pts"] = [(float(s[1]), float(s[2])), (float(e[1]), float(e[2]))]
            elif kind == "fp_circle":
                c, e = first(g, "center"), first(g, "end")
                d["pts"] = [(float(c[1]), float(c[2]))]
                d["r"] = math.hypot(float(e[1]) - float(c[1]), float(e[2]) - float(c[2]))
            elif kind == "fp_arc":
                d["pts"] = [(float(q[1]), float(q[2])) for q in (first(g, "start"), first(g, "mid") or first(g, "start"), first(g, "end")) if q]
            elif kind == "fp_poly":
                d["pts"] = [(float(q[1]), float(q[2])) for q in find(first(g, "pts"), "xy")]
                if kind == "fp_poly" and not fill:
                    d["fill"] = True  # easyeda2kicad polys are filled
            out.append(d)
    return out


def load_board(path):
    """-> dict(footprints={ref: fp}, edges=[...], aux_origin=(x, y))."""
    b = parse(open(path).read())
    setup = first(b, "setup")
    ao = first(setup, "aux_axis_origin") if setup else None
    fps = {}
    for fp in find(b, "footprint"):
        props = {q[1]: q[2] for q in find(fp, "property") if len(q) > 2}
        ref = props.get("Reference", "?")
        at = first(fp, "at"); r = float(at[3]) if len(at) > 3 else 0.0
        attr = first(fp, "attr") or ["attr"]
        layer = first(fp, "layer")[1]
        fps[ref] = dict(ref=ref, fpid=fp[1], layer=layer, side="bottom" if layer == "B.Cu" else "top",
                        x=float(at[1]), y=float(at[2]), rot=r % 360, attrs=set(attr[1:]), props=props,
                        pads=[_pad(p, r, board=True) for p in find(fp, "pad")],
                        gfx=_graphics(fp), uuid=(first(fp, "uuid") or [None, None])[1])
    edges = []
    for kind in ("gr_line", "gr_arc", "gr_circle", "gr_rect", "gr_poly"):
        for g in find(b, kind):
            ly = first(g, "layer")
            if ly and ly[1] == "Edge.Cuts":
                pts = []
                for k in ("start", "mid", "end", "center"):
                    q = first(g, k)
                    if q:
                        pts.append((k, float(q[1]), float(q[2])))
                if kind == "gr_poly":
                    pts = [("xy", float(q[1]), float(q[2])) for q in find(first(g, "pts"), "xy")]
                edges.append((kind, pts))
    return dict(footprints=fps, edges=edges, aux_origin=(float(ao[1]), float(ao[2])) if ao else (0.0, 0.0))


def load_mod(path):
    """Footprint library file (.kicad_mod, old 'module' or new 'footprint' syntax) -> dict(pads, gfx, name)."""
    fp = parse(open(path).read())
    return dict(name=fp[1], pads=[_pad(p) for p in find(fp, "pad")], gfx=_graphics(fp))


def board_to_local(fp):
    """Pads of a board footprint in the footprint frame. Board files store local coordinates already flipped for
    B.Cu parts; KiCad flips top-bottom (local y -> -y) so the library frame is recovered by negating y."""
    out = []
    for p in fp["pads"]:
        q = dict(p)
        if fp["side"] == "bottom":
            q["y"] = -q["y"]; q["rot"] = (-q["rot"]) % 360
        out.append(q)
    return out


def local_to_board(fp, xy):
    x, y = xy
    if fp["side"] == "bottom":
        y = -y
    dx, dy = rot((x, y), fp["rot"]) if fp["side"] == "top" else rot((x, y), fp["rot"])
    return (fp["x"] + dx, fp["y"] + dy)


def load_sym_pins(path):
    """easyeda.kicad_sym -> {symbol name: {pin number: pin name}}."""
    lib = parse(open(path).read()); out = {}
    for s in find(lib, "symbol"):
        pins = {}

        def walk(n):
            for c in n:
                if isinstance(c, list):
                    if c and c[0] == "pin":
                        nm, nu = first(c, "name"), first(c, "number")
                        if nm and nu:
                            pins[str(nu[1])] = str(nm[1])
                    else:
                        walk(c)
        walk(s)
        out[s[1]] = pins
    return out


def load_netlist_pins(path):
    """KiCad netlist -> {(ref, pin): (net, pinfunction)}; the '_<pin>' suffix the generator appends is removed."""
    nl = parse(open(path).read()); out = {}
    for net in find(first(nl, "nets"), "net"):
        name = first(net, "name")[1]
        for nd in find(net, "node"):
            ref, pin = first(nd, "ref")[1], str(first(nd, "pin")[1])
            pf = first(nd, "pinfunction")
            f = pf[1] if pf else ""
            if f.endswith("_" + pin):
                f = f[: -len(pin) - 1]
            out[(ref, pin)] = (name, f)
    return out


def read_csv(path):
    return list(csv.DictReader(open(path, newline="")))


def load_yaml(path):
    import yaml
    return yaml.safe_load(open(path))


def bom_full(path=None):
    return {r["Ref"]: r for r in read_csv(path or os.path.join(DESIGN, "BOM_full_v3f.csv"))}


def easyeda_fp_path(lcsc):
    d = os.path.join(DESIGN, "lib", "easyeda.pretty")
    c = [f for f in os.listdir(d) if f.split("_")[0] == lcsc]
    return os.path.join(d, c[0]) if len(c) == 1 else None


def lib_fp_path(fpid):
    lib, name = fpid.split(":", 1)
    return os.path.join(DESIGN, "lib", f"{lib}.pretty", name + ".kicad_mod")


def dump(obj, path):
    json.dump(obj, open(path, "w"), indent=1, default=lambda o: sorted(o) if isinstance(o, set) else str(o))
