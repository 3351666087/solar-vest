"""Build the SolarBand main board (KiCad 10, pcbnew python) from the netlist + placement.

Inputs : design/solarband_main_kicad.net (KiCad netlist exported from the schematic: refs, values, fields,
         symbol paths), design/parts.json (pin -> net), layout/work/placement_main.json (autoplace.py),
         place_main.py (anchors, mech pads), rf_geom.py (RF tracks), lgeom.py (outline, zones).
Output : layout/main/solarband_main.kicad_pcb (+ .kicad_pro written by write_project.py)
Stages : footprints (nets, fields, symbol paths, DNP / BOM / position attributes), outline with the TMP117 slot ring,
         stack-up JLC06081H-2116, rule areas, RF chain (tracks, feed via, fence), plane zones (L2, L5 GND; L4 VDD_1V8).
usage  : kicad-python build_main.py [--placement PATH]
"""
import json, math, os, re, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lgeom as G
import place_main as P
import rf_geom as RF

W = G.W
OUTDIR = W + "/layout/main"
PCB = OUTDIR + "/solarband_main.kicad_pcb"
LIBS = {"easyeda_rev": W + "/design/lib/easyeda_rev.pretty", "solarband": W + "/design/lib/solarband.pretty",
        "pv": W + "/design/lib/pv.pretty", "solarband_layout": W + "/layout/lib/solarband_layout.pretty"}
FP_OVERRIDE = {"J1": "solarband_layout:Contact_Castellated_2.0x2.4_D1.0",
               "J2": "solarband_layout:Contact_Castellated_2.0x2.4_D1.0",
               "AE1": "solarband_layout:IFA_B2_L6"}
MM = pcbnew.FromMM
OX, OY = G.KICAD_ORIGIN
CU = {"F": pcbnew.F_Cu, "B": pcbnew.B_Cu, "L2": pcbnew.In1_Cu, "L3": pcbnew.In2_Cu, "L4": pcbnew.In3_Cu,
      "L5": pcbnew.In4_Cu}
ALL_CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu]


def V(x, y):
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY - y))


def lset(layers):
    s = pcbnew.LSET()
    for l in layers:
        s.AddLayer(l)
    return s


# ------------------------------------------------------------------------------------- netlist parsing
def parse_kicad_net(path):
    """ref -> dict(value, footprint, fields{}, path '/sheet/sym')"""
    s = open(path).read()
    comps = {}
    for m in re.finditer(r"\(comp\s+\(ref \"([^\"]+)\"\)(.*?)\n\t\t\)\n", s, re.S):
        ref, body = m.group(1), m.group(2)
        d = {}
        d["value"] = re.search(r'\(value "([^"]*)"\)', body).group(1)
        fp = re.search(r'\(footprint "([^"]*)"\)', body)
        d["footprint"] = fp.group(1) if fp else ""
        d["fields"] = dict(re.findall(r'\(field\s+\(name "([^"]+)"\) "([^"]*)"\)', body))
        st = re.search(r'\(sheetpath\s+\(names "[^"]*"\)\s+\(tstamps "([^"]*)"\)\s*\)\s*\(tstamps "([^"]+)"\)', body)
        d["path"] = (st.group(1) + st.group(2)) if st else None
        comps[ref] = d
    return comps


def load_fp(fpid):
    lib, name = fpid.split(":")
    f = pcbnew.FootprintLoad(LIBS[lib], name)
    if f is None:
        raise SystemExit("footprint not found " + fpid)
    f.SetFPIDAsString(fpid)
    return f


# ------------------------------------------------------------------------------------- board parts
def add_footprints(brd, nets, parts, comps, placement):
    missing = []
    for ref, p in sorted(parts.items()):
        if ref not in placement:
            missing.append(ref)
            continue
        q = placement[ref]
        fpid = FP_OVERRIDE.get(ref, p["footprint"])
        f = load_fp(fpid)
        brd.Add(f)
        f.SetReference(ref)
        # 3D models resolve through wristband/lib/easyeda.3dshapes (symlink to design/lib), footprints unchanged
        c = comps.get(ref, {})
        f.SetValue(c.get("value", p["value"]))
        if c.get("path"):
            f.SetPath(pcbnew.KIID_PATH(c["path"]))
        for k, v in c.get("fields", {}).items():
            if k in ("Footprint", "Datasheet", "Description") or not v:
                continue
            f.SetField(k, v)
        for fld in f.GetFields():
            if fld.GetName() not in ("Reference", "Value"):
                fld.SetVisible(False)
                fld.SetLayer(pcbnew.F_Fab)
        f.SetPosition(V(q["x"], q["y"]))
        f.SetOrientationDegrees(q["rot"])
        if q["side"] == "B":
            f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        for pad in f.Pads():
            n = p["pins"].get(pad.GetNumber())
            if n:
                pad.SetNet(nets[n])
        if p.get("dnp"):
            f.SetDNP(True); f.SetExcludedFromBOM(True); f.SetExcludedFromPosFiles(True)
        if not p.get("jlc_placed") and not p.get("dnp"):
            f.SetExcludedFromBOM(True); f.SetExcludedFromPosFiles(True)
        # reference designators live on the fab layer (dense board; review images carry the refs)
        r = f.Reference()
        r.SetLayer(pcbnew.B_Fab if q["side"] == "B" else pcbnew.F_Fab)
        r.SetTextSize(pcbnew.VECTOR2I(MM(0.4), MM(0.4))); r.SetTextThickness(MM(0.06))
        r.SetPosition(f.GetPosition()); r.SetVisible(True)
        f.Value().SetVisible(False)
        if re.match(r"^(R|C|L|FB)\d", ref) and p.get("kind") not in ("led", "diode"):
            for g in f.GraphicalItems():                 # body outline of non-polar passives -> fab layer
                if g.GetLayer() == pcbnew.F_SilkS:
                    g.SetLayer(pcbnew.F_Fab)
    if missing:
        raise SystemExit("no placement for %s" % missing)
    # board-only mechanical landing pads
    for name, (fp, x, y, side) in P.MECH.items():
        f = load_fp("solarband_layout:" + fp)
        brd.Add(f)
        f.SetReference(name); f.SetValue(fp)
        f.SetBoardOnly(True); f.SetExcludedFromBOM(True); f.SetExcludedFromPosFiles(True)
        f.SetPosition(V(x, y))
        if side == "B":
            f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        f.Reference().SetVisible(False); f.Value().SetVisible(False)


# ------------------------------------------------------------------------------------- outline
def seg(brd, a, b, layer=pcbnew.Edge_Cuts, w=0.1):
    s = pcbnew.PCB_SHAPE(brd); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(V(*a)); s.SetEnd(V(*b)); s.SetLayer(layer); s.SetWidth(MM(w)); brd.Add(s)


def arc(brd, c, start, mid, end, layer=pcbnew.Edge_Cuts, w=0.1):
    s = pcbnew.PCB_SHAPE(brd); s.SetShape(pcbnew.SHAPE_T_ARC)
    s.SetArcGeometry(V(*start), V(*mid), V(*end)); s.SetLayer(layer); s.SetWidth(MM(w)); brd.Add(s)


def outline(brd):
    Wd, H = G.BOARD_W, G.BOARD_H
    r = G.CORNER_R
    seg(brd, (r["BL"], 0), (Wd - r["BR"], 0))
    seg(brd, (Wd, r["BR"]), (Wd, H - r["TR"]))
    seg(brd, (Wd - r["TR"], H), (r["TL"], H))
    seg(brd, (0, H - r["TL"]), (0, r["BL"]))
    k = math.sqrt(0.5)
    for (cx, cy, rad, a0) in ((r["BL"], r["BL"], r["BL"], 180), (Wd - r["BR"], r["BR"], r["BR"], 270),
                              (Wd - r["TR"], H - r["TR"], r["TR"], 0), (r["TL"], H - r["TL"], r["TL"], 90)):
        p = lambda a: (cx + rad * math.cos(math.radians(a)), cy + rad * math.sin(math.radians(a)))
        arc(brd, (cx, cy), p(a0), p(a0 + 45), p(a0 + 90))
    # TMP117 slot ring: 4 L-shaped milled cut-outs (internal Edge.Cuts outlines)
    for poly in G.tmp_slots():
        for i in range(len(poly)):
            seg(brd, poly[i], poly[(i + 1) % len(poly)])


# ------------------------------------------------------------------------------------- rule areas / zones
def poly_zone(brd, pts, layers, net=None, rule=False, name="", priority=0, **kw):
    z = pcbnew.ZONE(brd)
    z.SetLayerSet(lset(layers))
    if rule:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(kw.get("tracks", False))
        z.SetDoNotAllowVias(kw.get("vias", False))
        z.SetDoNotAllowZoneFills(kw.get("zones", False))
        z.SetDoNotAllowPads(kw.get("pads", False))
        z.SetDoNotAllowFootprints(kw.get("footprints", False))
    else:
        if net is not None:
            z.SetNet(net)
        z.SetLocalClearance(MM(kw.get("clearance", 0.15)))
        z.SetMinThickness(MM(kw.get("min_width", 0.12)))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        z.SetAssignedPriority(priority)
    if name:
        z.SetZoneName(name)
    ol = z.Outline(); ol.NewOutline()
    for x, y in pts:
        ol.Append(MM(OX + x), MM(OY - y))
    brd.Add(z)
    return z


def rect_pts(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def rule_areas(brd, placement):
    # IFA keep-out, all six layers: no tracks / vias / pours (the IFA copper is the AE1 net-tie footprint) [C-14]
    poly_zone(brd, G.IFA_KEEPOUT_POLY, ALL_CU, rule=True, name="IFA_KEEPOUT", tracks=True, vias=True, zones=True)
    # feed notch on L3-L6, L2 solid [C-14]
    x0, y0, x1, y1 = G.FEED_NOTCH
    poly_zone(brd, rect_pts(x0, y0, x1, y1), [CU["L3"], CU["L4"], CU["L5"], CU["B"]], rule=True, name="FEED_NOTCH_L3_L6",
              tracks=True, zones=True)
    # TMP117: 8 x 8 all-layer keep-out (no pours / vias; F.Cu traces over the bridges only); the 7 x 7 island is the
    # F.Cu GND zone inside it (SIM-13 design E, R-THERM-1)
    cx, cy = G.TMP117
    a, i = G.TMP_KEEPOUT / 2, G.TMP_ISLAND / 2
    inner = [CU["L2"], CU["L3"], CU["L4"], CU["L5"], CU["B"]]
    poly_zone(brd, rect_pts(cx - a, cy - a, cx + a, cy + a), inner, rule=True, name="TMP117_KEEPOUT_INNER",
              tracks=True, vias=True, zones=True)
    band = [(cx - a, cy - a), (cx + a, cy - a), (cx + a, cy + a), (cx - a, cy + a), (cx - a, cy - a),
            (cx - i, cy - i), (cx - i, cy + i), (cx + i, cy + i), (cx + i, cy - i), (cx - i, cy - i)]
    poly_zone(brd, band, [CU["F"]], rule=True, name="TMP117_BAND_F", vias=True, zones=True)
    poly_zone(brd, rect_pts(cx - i, cy - i, cx + i, cy + i), [CU["F"]], rule=True, name="TMP117_ISLAND_NOVIA", vias=True)
    poly_zone(brd, rect_pts(cx - i, cy - i, cx + i, cy + i), [CU["F"]], net=brd.FindNet("GND"), name="TMP117_ISLAND",
              priority=5, clearance=0.15)
    # PMIC no-pour island around the MOhm dividers, CREF and NT1, all layers [R-PMIC-1, C-20]
    for ref in ("R101", "R102", "R103", "R104", "R105", "R106", "R107", "C104", "NT1", "R113", "R114"):
        bb = brd.FindFootprintByReference(ref).GetBoundingBox(False)
        m = MM(0.35)
        pts = [(pcbnew.ToMM(bb.GetLeft() - m) - OX, OY - pcbnew.ToMM(bb.GetTop() - m)),
               (pcbnew.ToMM(bb.GetRight() + m) - OX, OY - pcbnew.ToMM(bb.GetTop() - m)),
               (pcbnew.ToMM(bb.GetRight() + m) - OX, OY - pcbnew.ToMM(bb.GetBottom() + m)),
               (pcbnew.ToMM(bb.GetLeft() - m) - OX, OY - pcbnew.ToMM(bb.GetBottom() + m))]
        poly_zone(brd, pts, ALL_CU, rule=True, name="MOHM_NOPOUR_" + ref, zones=True,
                  vias=(ref == "C104"))          # VREF_SAMP_100G: no via at CREF [C-20]
    # SC-32S: no copper under the crystal body on L1 [SII remark]
    f = brd.FindFootprintByReference("X2")
    x, y = placement["X2"]["x"], placement["X2"]["y"]
    hw, hh = (0.55, 0.7) if placement["X2"]["rot"] % 180 == 0 else (0.7, 0.55)
    poly_zone(brd, rect_pts(x - hw, y - hh, x + hw, y + hh), [CU["F"]], rule=True, name="X2_BODY", tracks=True,
              vias=True, zones=True)
    # net ties: no vias next to them (the router does not see their internal bridge)
    for ref in ("NT1", "NT2"):
        q = placement[ref]
        poly_zone(brd, rect_pts(q["x"] - 0.6, q["y"] - 0.45, q["x"] + 0.6, q["y"] + 0.45), ALL_CU, rule=True,
                  name="NOVIA_" + ref, vias=True)


def planes(brd):
    full = [(x, y) for x, y in G.rrect_outline()]
    gnd = brd.FindNet("GND")
    poly_zone(brd, full, [CU["L2"]], net=gnd, name="L2_GND", priority=1, clearance=0.15)
    poly_zone(brd, full, [CU["L5"]], net=gnd, name="L5_GND", priority=1, clearance=0.15)
    poly_zone(brd, full, [CU["L4"]], net=brd.FindNet("VDD_1V8"), name="L4_VDD_1V8", priority=1, clearance=0.15)


# ------------------------------------------------------------------------------------- RF chain
def add_track(brd, net, a, b, w, layer=pcbnew.F_Cu):
    t = pcbnew.PCB_TRACK(brd)
    t.SetStart(V(*a)); t.SetEnd(V(*b)); t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNet(net)
    brd.Add(t)
    return t


def add_via(brd, net, xy, drill=0.2, dia=0.4, filled=False):
    v = pcbnew.PCB_VIA(brd)
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetPosition(V(*xy)); v.SetDrill(MM(drill)); v.SetWidth(MM(dia))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(net)
    brd.Add(v)
    return v


def rf_chain(brd):
    for net, poly in RF.tracks():
        n = brd.FindNet(net)
        for i in range(len(poly) - 1):
            add_track(brd, n, poly[i], poly[i + 1], G.CPWG_W)
    v = add_via(brd, brd.FindNet("ANT_FEED"), G.FEED_VIA, G.FEED_VIA_DRILL, G.FEED_VIA_PAD)
    v.SetRemoveUnconnected(True)          # pads only on L1 and L6: L2 antipad set by the zone clearance
    return v


def fence(brd):
    """GND fence vias along the CPWG, kept only where they clear every non-GND copper item"""
    gnd = brd.FindNet("GND")
    pads = []
    for f in brd.GetFootprints():
        for p in f.Pads():
            if p.GetNetname() == "GND":
                continue
            bb = p.GetBoundingBox()
            pads.append((pcbnew.ToMM(bb.GetLeft()) - OX, OY - pcbnew.ToMM(bb.GetBottom()),
                         pcbnew.ToMM(bb.GetRight()) - OX, OY - pcbnew.ToMM(bb.GetTop())))
    segs = []
    for net, poly in RF.tracks():
        for i in range(len(poly) - 1):
            segs.append((poly[i], poly[i + 1]))

    def dseg(p, a, b):
        ax, ay = a; bx, by = b; px, py = p
        L2 = (bx - ax) ** 2 + (by - ay) ** 2
        t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * (bx - ax) + (py - ay) * (by - ay)) / L2))
        return math.hypot(px - ax - t * (bx - ax), py - ay - t * (by - ay))

    kept = []
    ko = G.IFA_KEEPOUT_POLY
    nx0, ny0, nx1, ny1 = G.FEED_NOTCH
    for (x, y) in RF.fence(pitch=0.9, off=0.48):
        if y < 5.5 + 0.25:
            continue
        if nx0 - 0.3 < x < nx1 + 0.3 and y < ny1 + 0.3:
            continue
        if any(dseg((x, y), a, b) < 0.085 + 0.15 + 0.2 - 1e-6 for a, b in segs):
            continue
        if any(x0 - 0.32 < x < x1 + 0.32 and y0 - 0.32 < y < y1 + 0.32 for (x0, y0, x1, y1) in pads):
            continue
        if math.hypot(x - G.FEED_VIA[0], y - G.FEED_VIA[1]) < 0.75:
            continue
        if any(math.hypot(x - a, y - b) < 0.6 for a, b in kept):
            continue
        kept.append((x, y))
    for xy in kept:
        add_via(brd, gnd, xy)
    return kept


# ------------------------------------------------------------------------------------- stack-up (text patch)
STACKUP = """    (stackup
      (layer "F.SilkS" (type "Top Silk Screen"))
      (layer "F.Paste" (type "Top Solder Paste"))
      (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
      (layer "F.Cu" (type "copper") (thickness 0.035))
      (layer "dielectric 1" (type "prepreg") (thickness 0.1164) (material "2116") (epsilon_r 4.16) (loss_tangent 0.02))
      (layer "In1.Cu" (type "copper") (thickness 0.0152))
      (layer "dielectric 2" (type "core") (thickness 0.13) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
      (layer "In2.Cu" (type "copper") (thickness 0.0152))
      (layer "dielectric 3" (type "prepreg") (thickness 0.2028) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))
      (layer "In3.Cu" (type "copper") (thickness 0.0152))
      (layer "dielectric 4" (type "core") (thickness 0.13) (material "FR4") (epsilon_r 4.6) (loss_tangent 0.02))
      (layer "In4.Cu" (type "copper") (thickness 0.0152))
      (layer "dielectric 5" (type "prepreg") (thickness 0.1164) (material "2116") (epsilon_r 4.16) (loss_tangent 0.02))
      (layer "B.Cu" (type "copper") (thickness 0.035))
      (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
      (layer "B.Paste" (type "Bottom Solder Paste"))
      (layer "B.SilkS" (type "Bottom Silk Screen"))
      (copper_finish "ENIG")
      (dielectric_constraints no)
    )
"""


def patch_file(path):
    s = open(path).read()
    s = re.sub(r"\(setup\s*\n", "(setup\n" + STACKUP, s, count=1)
    s = re.sub(r"\(general\s*\n\s*\(thickness [0-9.]+\)", "(general\n    (thickness 0.8264)", s, count=1)
    # layer user names L1..L6 (JLC order form / Gerber naming)
    for k, nm in (("F.Cu", "L1_top_skin"), ("In1.Cu", "L2_GND"), ("In2.Cu", "L3_SIG"), ("In3.Cu", "L4_PWR"),
                  ("In4.Cu", "L5_GND"), ("B.Cu", "L6_bottom_sky")):
        s = re.sub(r'\((\d+) "%s" signal\)' % re.escape(k), r'(\1 "%s" signal "%s")' % (k, nm), s, count=1)
    open(path, "w").write(s)


def intra_rules(brd):
    """DRC rules for vendor land patterns whose own pad gap is below the net-class clearance (e.g. 0402 at 0.294 mm
    in the 0.3 mm MOhm class): the clearance between two pads of the SAME footprint is the vendor's land pattern
    (copper = EasyEDA/JLC, C-05), so it is set to the JLC minimum for that pair only."""
    nc = json.load(open(W + "/design/netclasses.json"))["netclasses"]
    CLR = {}
    for k, d in nc.items():
        if isinstance(d.get("nets"), list):
            for n in d["nets"]:
                CLR[n] = d.get("clearance_mm", d.get("gap_mm", 0.1))
    out = []
    for f in brd.GetFootprints():
        pads = [p for p in f.Pads() if p.GetNetCode() > 0]
        worst = None
        for i in range(len(pads)):
            for j in range(i + 1, len(pads)):
                a, b = pads[i], pads[j]
                if a.GetNetCode() == b.GetNetCode():
                    continue
                req = max(CLR.get(a.GetNetname(), 0.1), CLR.get(b.GetNetname(), 0.1))
                ba, bb = a.GetBoundingBox(), b.GetBoundingBox()
                dx = max(0, max(ba.GetLeft(), bb.GetLeft()) - min(ba.GetRight(), bb.GetRight()))
                dy = max(0, max(ba.GetTop(), bb.GetTop()) - min(ba.GetBottom(), bb.GetBottom()))
                d = pcbnew.ToMM(math.hypot(dx, dy))
                if d < req - 1e-6:
                    worst = min(worst, d) if worst is not None else d
        if worst is not None:
            out.append((f.GetReference(), worst))
    return out


def main():
    pl_path = sys.argv[sys.argv.index("--placement") + 1] if "--placement" in sys.argv else W + "/layout/work/placement_main.json"
    placement = json.load(open(pl_path))["parts"]
    parts = json.load(open(W + "/design/parts.json"))["main"]
    comps = parse_kicad_net(W + "/design/solarband_main_kicad.net")
    os.makedirs(OUTDIR, exist_ok=True)
    brd = pcbnew.BOARD()
    brd.SetCopperLayerCount(6)
    nets = {}
    for p in parts.values():
        for n in p["pins"].values():
            if n and n not in nets:
                ni = pcbnew.NETINFO_ITEM(brd, n); brd.Add(ni); nets[n] = ni
    add_footprints(brd, nets, parts, comps, placement)
    outline(brd)
    rule_areas(brd, placement)
    rf_chain(brd)
    kept = fence(brd)
    planes(brd)
    ds = brd.GetDesignSettings()
    ds.SetAuxOrigin(V(0, 0)); ds.SetGridOrigin(V(0, 0))
    brd.Save(PCB)
    patch_file(PCB)
    # regenerate the custom rules: base (write_project.py) + intra-footprint land-pattern exceptions
    import subprocess
    subprocess.run(["@SVROOT@/venv/bin/python", HERE + "/write_project.py"], check=True,
                   capture_output=True)
    b2 = pcbnew.LoadBoard(PCB)
    rules = intra_rules(b2)
    with open(OUTDIR + "/solarband_main.kicad_dru", "a") as fh:
        fh.write("# vendor land patterns (pad gap < net-class clearance) - generated by build_main.intra_rules\n")
        for ref, d in sorted(rules):
            fh.write('(rule "land pattern %s (own pad gap %.3f mm)"\n  (condition "A.memberOfFootprint(\'%s\') && '
                     'B.memberOfFootprint(\'%s\')")\n  (constraint clearance (min 0.09mm)))\n' % (ref, d, ref, ref))
    print("intra-footprint rules:", len(rules))
    print("saved", PCB, "fence vias", len(kept))


if __name__ == "__main__":
    main()
