"""Fabrication facts measured from the board + the fabrication README.

usage: python fab_info.py --board B --gerbers DIR --drc drc.json --zip ZIP --out FABDIR
"""
import argparse, glob, json, math, os, re, sys
from shapely.geometry import LineString, Point
from shapely.ops import polygonize, unary_union
from shapely.strtree import STRtree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pk  # noqa: E402
from cplgate import pad_poly  # noqa: E402
from render_gate import to_board  # noqa: E402

LAYERS = [("F.Cu", "gtl", "L1 top (sky side) signal + parts"), ("In1.Cu", "g1", "L2 GND plane (full)"),
          ("In2.Cu", "g2", "L3 signal"), ("In3.Cu", "g3", "L4 VDD_1V8 pours + signals"), ("In4.Cu", "g4", "L5 signal"),
          ("B.Cu", "gbl", "L6 bottom (skin side) signal, void over the plates except dot stubs")]
# plan B (ruling P-5, v3/planb/PLANB.md): 8 layers, GND In1, VDD_1V8 full plane In4, signals F, In2, In3, In5, In6, B
LAYERS8 = [("F.Cu", "gtl", "L1 top (sky side) signal + parts"), ("In1.Cu", "g1", "L2 GND plane (full)"),
           ("In2.Cu", "g2", "L3 signal"), ("In3.Cu", "g3", "L4 signal"), ("In4.Cu", "g4", "L5 VDD_1V8 plane (full)"),
           ("In5.Cu", "g5", "L6 signal, plate-facing"), ("In6.Cu", "g6", "L7 signal, plate-facing"),
           ("B.Cu", "gbl", "L8 bottom (skin side) signal, void over the plates except dot stubs")]


def copper_layers(raw):
    """Copper layer names declared in the board's (layers) list, in stack order."""
    lay = pk.first(raw, "layers") or []
    names = [q[1] for q in lay if isinstance(q, list) and len(q) > 2 and q[1].endswith(".Cu")]
    inner = sorted((n for n in names if n.startswith("In")), key=lambda n: int(n[2:-3]))
    return ["F.Cu"] + inner + ["B.Cu"]


def main():
    ap = argparse.ArgumentParser()
    for k in ("board", "gerbers", "drc", "zip", "out"):
        ap.add_argument("--" + k, required=True)
    a = ap.parse_args()
    raw = pk.parse(open(a.board).read())
    B = pk.load_board(a.board); F = B["footprints"]; ox, oy = B["aux_origin"]
    # outline
    segs, circles = [], []
    for kind, pts in B["edges"]:
        d = {k: (x, y) for k, x, y in pts}
        if kind == "gr_line":
            segs.append(LineString([d["start"], d["end"]]))
        elif kind == "gr_circle":
            c, e = d["center"], d["end"]; circles.append((c, math.dist(c, e)))
    polys = list(polygonize(unary_union(segs)))
    outer = max(polys, key=lambda p: p.area) if polys else None
    bx = outer.bounds if outer else (0, 0, 0, 0)
    cut = [dict(kind="circle", centre_mm=(round(c[0] - ox, 3), round(-(c[1] - oy), 3)), diameter_mm=round(2 * r, 3)) for c, r in circles]
    cut += [dict(kind="polygon", area_mm2=round(p.area, 2)) for p in polys if p is not outer and outer and p.within(outer.buffer(0.01))]
    # vias, tracks
    vias = []
    for v in pk.find(raw, "via"):
        at = pk.first(v, "at"); sz = pk.first(v, "size"); dr = pk.first(v, "drill")
        vias.append((float(at[1]), float(at[2]), float(sz[1]), float(dr[1])))
    widths = [float(pk.first(s, "width")[1]) for s in pk.find(raw, "segment")]
    smd = []
    for fp in F.values():
        for p in fp["pads"]:
            if p["type"] == "smd" and p["num"]:
                lp = dict(p)
                if fp["side"] == "bottom":
                    lp["y"] = -lp["y"]; lp["rot"] = (-lp["rot"]) % 360
                smd.append(to_board(pad_poly(lp), fp))
    tree = STRtree(smd)
    vip = sum(1 for x, y, s, d in vias if any(smd[i].contains(Point(x, y)) for i in tree.query(Point(x, y))))
    drc = json.load(open(a.drc)) if os.path.exists(a.drc) else {}
    errs = [v for v in drc.get("violations", []) if v.get("severity") == "error"]
    unc = len(drc.get("unconnected_items", []))
    th = 1.0
    cu = copper_layers(raw); nl = len(cu)
    table = {6: LAYERS, 8: LAYERS8}.get(nl) or [(c, ("g%d" % i) if c.startswith("In") else ("gtl" if c == "F.Cu" else "gbl"),
                                                "signal (no role table for this layer count) ⚠") for i, c in enumerate(cu)]
    info = dict(board=os.path.abspath(a.board), board_sha256=pk.sha256(a.board),
                outline_mm=dict(width=round(bx[2] - bx[0], 3), height=round(bx[3] - bx[1], 3), closed=bool(outer)),
                cutouts=cut, vias=len(vias), via_min_diameter=min((v[2] for v in vias), default=None),
                via_min_drill=min((v[3] for v in vias), default=None), vias_in_smd_pads=vip,
                track_min_width=min(widths, default=None), tracks=len(widths),
                drc_errors=len(errs), drc_unconnected=unc, drc_error_types=sorted({v.get("type") for v in errs}),
                thickness_mm=th, copper_layers=cu, layer_count=nl, gerber_zip=os.path.basename(a.zip), gerber_zip_sha256=pk.sha256(a.zip))
    pk.dump(info, os.path.join(a.out, "fab_info.json"))
    files = sorted(os.path.basename(f) for f in glob.glob(os.path.join(a.gerbers, "*")))
    L = ["# Fabrication README: SolarBand V3-F main board", "",
         f"Board file sha256 `{info['board_sha256'][:16]}...`; Gerber zip `{info['gerber_zip']}` sha256 `{info['gerber_zip_sha256'][:16]}...`.",
         "Generated by `v3/package/make_package.sh`; every number below is measured from the board file by `tools/fab_info.py` unless marked ⚠.", "",
         "## Order parameters", "",
         "| Item | Value |", "|---|---|",
         f"| Layers | {nl} ({', '.join(cu)}) |",
         f"| Board size | {info['outline_mm']['width']} × {info['outline_mm']['height']} mm (outline closed: {'yes' if info['outline_mm']['closed'] else 'NO'}) |",
         "| Finished thickness | **1.0 mm** (BASELINE §8: PCB 1.0 mm + tolerance 1.10 mm in the stack)" + ("; 8 layers at 1.0 mm is not confirmed by JLC ❓ (P-5); 1.2 mm adds 0.22 mm to the pod |" if nl == 8 else " |"),
         f"| Stack-up | JLC's standard {nl}-layer stack for 1.0 mm, chosen in the order form ⚠" + ("; no published 8-layer template, estimate in v3/planb/PLANB.md §2 ⚠" if nl == 8 else "") + " (no controlled-impedance line on this board; the lid antenna feed is a short leg on L1 ⚠) |",
         "| Material | FR-4, JLC standard Tg ⚠ |",
         "| Copper | outer 1 oz, inner 0.5 oz (JLC multilayer default) ⚠ |",
         "| Surface finish | **ENIG** ⚠ (lane choice: 0.40 mm-pitch WLCSP / BGA lands (U4, U5, U6, U8) and the spring-finger and plate-dot contacts need a flat, gold surface; HASL is not suitable) |",
         f"| Via covering | **Epoxy-filled and capped (via-in-pad, POFV)** on every via: {info['vias']} vias, {info['vias_in_smd_pads']} of them inside SMD pads (LEAD_NOTES K-7); vias over the plates must be tented and plugged on B.Cu (R-2): POFV covers this |",
         f"| Minimum via | {info['via_min_drill']} mm drill / {info['via_min_diameter']} mm pad (JLC multilayer minimum 0.15 / 0.25 as in the board's .kicad_dru) |",
         f"| Minimum track | {info['track_min_width']} mm (0.09 / 0.09 mm only inside the WLCSP / DSBGA courtyards, .kicad_dru) |",
         "| Solder mask / silkscreen | any colour; part silkscreen = the pin-1 / polarity marks added by `tools/add_silk_marks.py` (step 0 of make_package.sh, report `silk/silk_marks.md`) |",
         "| Outline | Edge.Cuts (`.gm1`) incl. the motor cut-out: " + "; ".join(
             (f"circle Ø{c['diameter_mm']} mm at ({c['centre_mm'][0]}, {c['centre_mm'][1]})" if c["kind"] == "circle" else f"polygon {c['area_mm2']} mm²") for c in cut) + " |",
         "| Origin | all Gerbers, drill files and the CPL use the board's drill/place origin |", "",
         "## Layer files (KiCad Protel names, accepted by JLC ⚠)", "", "| File | Layer | Use |", "|---|---|---|"]
    for ly, ext, use in table:
        f = [x for x in files if x.lower().endswith("." + ext)]
        L.append(f"| {f[0] if f else '-'} | {ly} | {use} |")
    for ext, what in (("gto", "top silkscreen"), ("gbo", "bottom silkscreen"), ("gts", "top mask"), ("gbs", "bottom mask"),
                      ("gtp", "top paste (stencil)"), ("gbp", "bottom paste (stencil)"), ("gm1", "board outline incl. motor cut-out")):
        f = [x for x in files if x.lower().endswith("." + ext)]
        L.append(f"| {f[0] if f else '-'} | {what} | |")
    for x in files:
        if x.endswith(".drl"):
            L.append(f"| {x} | {'non-plated' if 'NPTH' in x else 'plated'} drill, Excellon mm decimal | |")
    L += ["", "## Board checks at export", "",
          f"- KiCad DRC (kicad-cli, board rules): **{info['drc_errors']} errors**, **{info['drc_unconnected']} unconnected items** "
          f"({'PASS' if info['drc_errors'] == 0 and info['drc_unconnected'] == 0 else 'FAIL: not fit to order'}).",
          "- A board with any unconnected item must not be ordered; the package marks such a run as a dry run.", ""]
    open(os.path.join(a.out, "README_FAB.md"), "w").write("\n".join(L) + "\n")
    print(json.dumps({k: info[k] for k in ("layer_count", "outline_mm", "cutouts", "vias", "vias_in_smd_pads", "drc_errors", "drc_unconnected")}))


if __name__ == "__main__":
    main()
