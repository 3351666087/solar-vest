"""Minimal S-expression reader for KiCad files (.kicad_mod / .kicad_sym / .kicad_pcb) + pad/pin extractors."""
import re
_tok = re.compile(r'\s*(?:(\()|(\))|("(?:[^"\\]|\\.)*")|([^\s()"]+))')
def parse(text):
    stack, cur = [], []
    for m in _tok.finditer(text):
        o, c, s, a = m.groups()
        if o: stack.append(cur); cur = []
        elif c: done = cur; cur = stack.pop(); cur.append(done)
        elif s is not None: cur.append(s[1:-1].replace('\\"', '"'))
        elif a is not None: cur.append(a)
    return cur[0] if cur else None
def find(node, key):
    return [n for n in node if isinstance(n, list) and n and n[0] == key]
def first(node, key, default=None):
    r = find(node, key); return r[0] if r else default
def footprint_pads(path):
    """-> list of dict(num, type, shape, x, y, w, h, rot, layers) in footprint coordinates (mm, KiCad y down)."""
    fp = parse(open(path).read()); out = []
    for p in find(fp, "pad"):
        at = first(p, "at"); size = first(p, "size")
        out.append(dict(num=p[1], type=p[2], shape=p[3], x=float(at[1]), y=float(at[2]), rot=float(at[3]) if len(at) > 3 else 0.0,
                        w=float(size[1]), h=float(size[2]), layers=(first(p, "layers") or [None])[1:]))
    return out
def footprint_graphics(path, layer_sub="Silk"):
    fp = parse(open(path).read()); out = []
    for kind in ("fp_line", "fp_circle", "fp_arc", "fp_poly", "fp_rect"):
        for g in find(fp, kind):
            ly = first(g, "layer")
            if ly and layer_sub in ly[1]: out.append((kind, g))
    return out
def symbol_pins(sym_lib_path, name):
    lib = parse(open(sym_lib_path).read())
    for s in find(lib, "symbol"):
        if s[1] == name:
            pins = []
            def walk(n):
                for c in n:
                    if isinstance(c, list):
                        if c and c[0] == "pin":
                            nm = first(c, "name"); nu = first(c, "number")
                            pins.append(dict(num=nu[1], name=nm[1], etype=c[1]))
                        else: walk(c)
            walk(s); return pins
    return None
