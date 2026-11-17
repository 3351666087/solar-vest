"""G9 rendering: one SVG per JLC-placed part in the board frame + a contact sheet grouped by risk."""
import html, math, os
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon

import pk
from cplgate import pad_poly, centroids

S = 40.0  # px per mm


def to_board(g, fp):
    if fp["side"] == "bottom":
        g = affinity.scale(g, 1, -1, origin=(0, 0))
    g = affinity.rotate(g, -fp["rot"], origin=(0, 0))
    return affinity.translate(g, fp["x"], fp["y"])


def gfx_geo(g, bottom_stored=False):
    pts = g["pts"]
    if bottom_stored:
        pts = [(x, -y) for x, y in pts]
    if g["kind"] == "fp_circle":
        return Point(pts[0]).buffer(max(g.get("r", 0), 0.02) + g["width"] / 2, 12) if g.get("fill") or g.get("r", 0) < 0.08 else \
            Point(pts[0]).buffer(g["r"] + g["width"] / 2, 16).difference(Point(pts[0]).buffer(max(g["r"] - g["width"] / 2, 0), 16))
    if g["kind"] == "fp_poly" and len(pts) >= 3:
        return Polygon(pts).buffer(0)
    return LineString(pts).buffer(max(g["width"], 0.04) / 2)


def path(g, x0, y0):
    out = []
    geoms = getattr(g, "geoms", [g])
    for q in geoms:
        if q.is_empty or not hasattr(q, "exterior"):
            continue
        for ring in [q.exterior] + list(q.interiors):
            c = list(ring.coords)
            out.append("M" + " L".join(f"{(x - x0) * S:.1f},{(y - y0) * S:.1f}" for x, y in c) + " Z")
    return " ".join(out)


def svg_part(P, fp, EM, ox, oy):
    th = P.get("theta", 0); dx, dy = P.get("offset_local", (0, 0))
    kpads = [p for p in pk.board_to_local(fp) if p["num"]]
    kg = [(p, to_board(pad_poly(p), fp)) for p in kpads]
    eg = [(p, to_board(pad_poly(p, dx, dy, th), fp)) for p in EM["pads"] if p["num"]] if EM else []
    es = []
    if EM:
        for g in EM["gfx"]:
            if "Silk" in g["layer"]:
                es.append(to_board(affinity.translate(affinity.rotate(gfx_geo(g), -th, origin=(0, 0)), dx, dy), fp))
    bs = [to_board(gfx_geo(g, fp["side"] == "bottom"), fp) for g in fp["gfx"] if "Silk" in g["layer"]]
    allg = [g for _, g in kg] + [g for _, g in eg]
    minx = min(g.bounds[0] for g in allg) - 1.2; miny = min(g.bounds[1] for g in allg) - 1.6
    maxx = max(g.bounds[2] for g in allg) + 1.2; maxy = max(g.bounds[3] for g in allg) + 1.0
    W, H = (maxx - minx) * S, (maxy - miny) * S
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{max(W, 300):.0f}" height="{H:.0f}" viewBox="0 0 {max(W, 300):.0f} {H:.0f}" '
         f'font-family="sans-serif"><rect width="100%" height="100%" fill="#fff"/>']
    for g in bs:
        o.append(f'<path d="{path(g, minx, miny)}" fill="#7a7a7a" opacity="0.8"/>')
    for p, g in kg:
        o.append(f'<path d="{path(g, minx, miny)}" fill="#e8b04a" stroke="#8a5a00" stroke-width="1"/>')
        c = g.centroid
        o.append(f'<text x="{(c.x - minx) * S:.1f}" y="{(c.y - miny) * S + 4:.1f}" font-size="10" text-anchor="middle" fill="#5a3a00">{html.escape(p["num"])}</text>')
    for p, g in eg:
        o.append(f'<path d="{path(g, minx, miny)}" fill="#2a6fdb" fill-opacity="0.35" stroke="#2a6fdb" stroke-width="1.2" stroke-dasharray="3,2"/>')
        c = g.centroid
        o.append(f'<text x="{(c.x - minx) * S + 6:.1f}" y="{(c.y - miny) * S - 4:.1f}" font-size="9" fill="#1a3f8a">{html.escape(p["num"])}</text>')
    for g in es:
        o.append(f'<path d="{path(g, minx, miny)}" fill="#c0392b" opacity="0.7"/>')
    refn = None
    pol = P.get("polarity") or ""
    if pol.startswith("reference terminal"):
        refn = pol.split("pad ")[1].split(" ")[0]
    elif any(p["num"] == "1" for p in kpads):
        refn = "1"
    elif any(p["num"] == "A1" for p in kpads):
        refn = "A1"
    if refn:
        c = centroids(kpads)[refn]; bx, by = pk.local_to_board(fp, c)
        o.append(f'<circle cx="{(bx - minx) * S:.1f}" cy="{(by - miny) * S:.1f}" r="5" fill="#000"/>')
    if "cpl" in P:  # CPL pose: origin and the turned EasyEDA +X axis
        cx, cy = P["cpl"]["x"] + ox, -P["cpl"]["y"] + oy
        r = math.radians(P["cpl"]["rot"]); sgn = 1 if fp["side"] == "top" else -1
        ex, ey = cx + sgn * 0.8 * math.cos(r), cy - 0.8 * math.sin(r)
        o.append(f'<line x1="{(cx - minx) * S:.1f}" y1="{(cy - miny) * S:.1f}" x2="{(ex - minx) * S:.1f}" y2="{(ey - miny) * S:.1f}" '
                 f'stroke="#16a085" stroke-width="2.5" marker-end="url(#a)"/>')
        o.insert(1, '<defs><marker id="a" markerWidth="8" markerHeight="8" refX="4" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#16a085"/></marker></defs>')
    col = {"GREEN": "#1e8449", "PREVIEW": "#2e86c1", "YELLOW": "#b7950b", "RED": "#c0392b", "UNKNOWN": "#7d3c98"}[P["verdict"]]
    t = f"{P['ref']} {P['lcsc']} {P['side']} | {P['verdict']} | theta {P.get('theta', '-')} | CPL rot {P.get('cpl', {}).get('rot', '-')}"
    o.append(f'<rect x="0" y="0" width="100%" height="30" fill="{col}"/><text x="4" y="12" font-size="11" fill="#fff">{html.escape(t)}</text>')
    o.append(f'<text x="4" y="25" font-size="9" fill="#fff">{html.escape((pol or "") [:90])}</text>')
    o.append(f'<line x1="6" y1="{H - 8:.0f}" x2="{6 + S:.0f}" y2="{H - 8:.0f}" stroke="#000" stroke-width="2"/><text x="{10 + S:.0f}" y="{H - 4:.0f}" font-size="9">1 mm</text>')
    o.append("</svg>")
    return "\n".join(o)


def render_all(prov, B, outdir, design):
    os.makedirs(outdir, exist_ok=True)
    F = B["footprints"]; ox, oy = B["aux_origin"]
    groups = {"polarized": [], "ics_connectors": [], "passives": []}
    for P in prov["parts"]:
        fp = F[P["ref"]]
        EM = None
        ep = pk.easyeda_fp_path(P["lcsc"]) if "easyeda_fp" in P else None
        if ep:
            EM = pk.load_mod(ep)
        if "theta" not in P:
            P2 = dict(P, theta=0, offset_local=(0, 0))
        else:
            P2 = P
        open(os.path.join(outdir, P["ref"] + ".svg"), "w").write(svg_part(P2, fp, EM, ox, oy))
        g = "polarized" if (P.get("polarity") or "").startswith("reference") or P["proof_class"] in ("P", "1F", "2F", "4F", "M") and \
            P["ref"][0] in "DQ" else ("passives" if P["ref"][0] in "RCL" and P["ref"][:2] != "LE" else "ics_connectors")
        groups[g].append(P)
    order = {"RED": 0, "UNKNOWN": 1, "YELLOW": 2, "PREVIEW": 3, "GREEN": 4}
    h = ['<!doctype html><meta charset=utf-8><title>CPL gate overlays</title><style>body{font:12px sans-serif;background:#f4f4f4}'
         'section{display:flex;flex-wrap:wrap;gap:8px}figure{background:#fff;margin:0;padding:4px}</style>',
         '<p>Orange: board (KiCad) copper with pad numbers. Blue dashed: the EasyEDA footprint of the C-number placed by the CPL (JLC\'s view). '
         'Red: EasyEDA silkscreen (JLC pin-1 / polarity mark). Grey: board silkscreen. Black dot: KiCad reference pad (pin 1, cathode or +). '
         'Green arrow: CPL origin and the EasyEDA +X axis turned by the CPL rotation.</p>']
    for g, L in groups.items():
        h.append(f"<h2>{g} ({len(L)})</h2><section>")
        for P in sorted(L, key=lambda p: (order[p["verdict"]], p["ref"])):
            h.append(f'<figure><img src="{P["ref"]}.svg" width="300"><figcaption>{P["ref"]} {P["verdict"]}</figcaption></figure>')
        h.append("</section>")
    open(os.path.join(outdir, "index.html"), "w").write("\n".join(h))
