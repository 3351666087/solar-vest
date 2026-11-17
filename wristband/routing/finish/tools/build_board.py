"""Build a KiCad 10 board of the V3-F main board from a placement, for the V3-G1 routing trial (pcbnew python).
After layout/tools/build_main.py (v1) and write_project.py; reads v3/design (parts.json, netclasses.json, footprint libraries) and the
CAD zone file through lgeom.py. Nothing outside v3/layout is written.

usage: G1_GEOM=OUTDIR/geom.json kicad-python build_board.py PLACEMENT.json OUTDIR [--l3-over-plates] [--relax-clearance]
       (geom.json: [G1_ZONES=.. G1_VARIANT=.. G1_OPTS=..] venv-python dump_geom.py OUTDIR/geom.json)
Stages: footprints + nets; outline (CAD polygon) + motor cut-out; rule areas (antenna keep-out, plate voids on L5 and L6 - and on L3
unless --l3-over-plates, see below); L2 / L4 ground planes; WLCSP / DSBGA fan-out of fanout.py (locked); project file with the net classes
of v3/design/netclasses.json and JLC's 6-layer rules; custom rules.

Plate rule [v3/design/netclasses.json PLATE_VOID]: B.Cu and L5 are void under the two electrode plates, and no signal via may sit there
(only GND and nets behind >= 100 kOhm). A router cannot be told 'vias of some nets only', so the trial closes L3 over the plates as well:
a signal via there then has no layer to go to and the router does not place one, while GND pads still drop a via to the L2 / L4 planes.
This is stricter than the rule (L3 tracks may cross a plate); --l3-over-plates opens L3 and the vias are counted afterwards.
"""
import json, math, os, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fanout as FO


class _NS:
    pass


# KiCad's python has no numpy / shapely: the geometry comes from a dump written by the venv python (tools/dump_geom.py, same env)
_J = json.load(open(os.environ["G1_GEOM"]))
G = _NS(); P = _NS()
for _k, _v in _J["G"].items():
    setattr(G, _k, _v)
G.outline = lambda: [tuple(p) for p in _J["G"]["OUTLINE"]]
P.PARTS = json.load(open(G.DESIGN + "/parts.json"))["variants"][G.VARIANT]["parts"]

MM = pcbnew.FromMM
OX, OY = G.KICAD_ORIGIN
LIBS = {"easyeda_rev": G.DESIGN + "/lib/easyeda_rev.pretty", "solarband": G.DESIGN + "/lib/solarband.pretty",
        "rf": "/path/to/SolarVest_work/wristband/v3/layout/lib/rf.pretty"}
FP_OVERRIDE = {"AE1": "rf:AE1_lid_L1"}          # [S2d] AE1_lid_L1 with a 0.15 mm feed notch in its rule area (LEAD_NOTES 2i L-2)
PAD_ALIAS = {}
CU = {"F": pcbnew.F_Cu, "L2": pcbnew.In1_Cu, "L3": pcbnew.In2_Cu, "L4": pcbnew.In3_Cu, "L5": pcbnew.In4_Cu, "B": pcbnew.B_Cu}
ALL_CU = [CU[k] for k in ("F", "L2", "L3", "L4", "L5", "B")]
NC = json.load(open(G.DESIGN + "/netclasses.json"))
PLATES_OPEN = "--plates-open" in sys.argv
# [layout] R-2 "ECG-band" nets (switch between 0.05 and 150 Hz), from the net names: display COM / EXTCOMIN and display enables, O-2 heartbeat
# (CHG_DIS, O2_HB), LED / front-light / motor drives, button nets, slow enables. Together with classes PWR_HIGH and VDD_1V8 they get no via
# over a plate and no L3 / L5 track over a plate.
ECG_BAND = ["D_EXTCOMIN", "EXTCOMIN", "D_DISP", "DISP_EN", "DISP_CTRL", "CHG_DIS", "O2_HB", "LED1_DRV", "LED2_DRV", "ALERT_LED", "ALERT_A",
            "ALERT_K", "FL_EN", "FL_A", "FL_K", "MOTOR_PWM", "MOTOR_G", "MOTOR_S", "MOTOR_N", "BTN", "BTN_G", "BTN_N", "BTN_SUP", "SW_ON",
            "AVDD_EN", "NTC_EN", "INA_EN", "ECG_PWR_EN", "BQ_EN", "VOUT_EN", "EN_HOLD", "PWR_HOLD", "PV_INH", "PWR_CYC"]
# [grow G-3] LEAD_NOTES 2o P-1: six more plate-forbidden nets (they couple 74-402 uVpp into the ECG over the plates)
P1_NETS = ["NTC", "NTC_ADC", "I2C_SDA", "I2C_SCL", "O2_TC", "O2_TH"]
def plate_forbidden():
    pw = [n for n in NC["netclasses"]["PWR_HIGH"]["nets"]]
    return sorted(set(pw) | {"VDD_1V8"} | set(ECG_BAND) | set(P1_NETS))


def V(x, y):
    return pcbnew.VECTOR2I(MM(OX + x), MM(OY - y))


def lset(layers):
    s = pcbnew.LSET()
    for l in layers:
        s.AddLayer(l)
    return s


def poly_zone(brd, pts, layers, net=None, rule=False, name="", priority=0, **kw):
    z = pcbnew.ZONE(brd)
    z.SetLayerSet(lset(layers))
    if rule:
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(kw.get("tracks", False)); z.SetDoNotAllowVias(kw.get("vias", False))
        z.SetDoNotAllowZoneFills(kw.get("zones", False)); z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False)
    else:
        if net is not None:
            z.SetNet(net)
        z.SetLocalClearance(MM(kw.get("clearance", 0.15))); z.SetMinThickness(MM(kw.get("min_width", 0.1)))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL); z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        z.SetAssignedPriority(priority)
    if name:
        z.SetZoneName(name)
    ol = z.Outline(); ol.NewOutline()
    for x, y in pts:
        ol.Append(MM(OX + x), MM(OY - y))
    brd.Add(z)
    return z


def seg(brd, a, b, layer=pcbnew.Edge_Cuts, w=0.1):
    s = pcbnew.PCB_SHAPE(brd); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(V(*a)); s.SetEnd(V(*b)); s.SetLayer(layer); s.SetWidth(MM(w)); brd.Add(s)


def cls(name, track, clear, via=(0.3, 0.15), prio=0):
    return {"name": name, "clearance": clear, "track_width": track, "via_diameter": via[0], "via_drill": via[1], "diff_pair_width": 0.15,
            "diff_pair_gap": 0.2, "diff_pair_via_gap": 0.25, "microvia_diameter": 0.2, "microvia_drill": 0.1, "wire_width": 6, "bus_width": 12,
            "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": prio, "tuning_profile": ""}


def intra_rules(brd, clr):
    """footprints whose own pad gap (different nets) is below the net-class clearance: the vendor land pattern stands (v1 rule)"""
    out = []
    for f in brd.GetFootprints():
        pads = [p for p in f.Pads() if p.GetNetCode() > 0]
        worst = None
        for i in range(len(pads)):
            for j in range(i + 1, len(pads)):
                a, b = pads[i], pads[j]
                if a.GetNetCode() == b.GetNetCode():
                    continue
                req = max(clr.get(a.GetNetname(), 0.1), clr.get(b.GetNetname(), 0.1))
                ba, bb = a.GetBoundingBox(), b.GetBoundingBox()
                dx = max(0, max(ba.GetLeft(), bb.GetLeft()) - min(ba.GetRight(), bb.GetRight()))
                dy = max(0, max(ba.GetTop(), bb.GetTop()) - min(ba.GetBottom(), bb.GetBottom()))
                d = pcbnew.ToMM(math.hypot(dx, dy))
                if d < req - 1e-6:
                    worst = min(worst, d) if worst is not None else d
        if worst is not None:
            out.append((f.GetReference(), worst))
    return out


def class_clearance(cap):
    clr = {}
    for k, d in NC["netclasses"].items():
        if isinstance(d.get("nets"), list):
            for n in d["nets"]:
                clr[n] = min(d.get("clearance_mm", 0.1), cap)
    return clr


def write_project(base, relax, cap=0.2):
    c = NC["netclasses"]
    # [lead 2026-11-15, step 2] JLC multilayer minimum 0.09 / 0.09 mm for the plain signal nets (Default) and the display lines;
    # router via 0.38 / 0.15: with 0.09 copper clearance its hole stays 0.20 from other copper (JLC via hole to track 0.20)
    classes = [cls("Default", 0.09, 0.09, via=(0.38, 0.15), prio=2147483647)]   # SIGNAL: 0.10 / 0.10, via 0.30 / 0.15 filled and capped (JLC POFV 0.15-0.55)
    patterns = []
    for i, (k, d) in enumerate(c.items()):
        if not isinstance(d.get("nets"), list):
            continue
        tr = d.get("track_mm", 0.15); cl_ = d.get("clearance_mm", 0.1)
        if k == "DISPLAY":
            tr, cl_ = 0.09, 0.09
        cl_ = min(cl_, 0.09 if relax else cap)                      # trial: class clearances above 0.20 mm (MOhm, electrode: 0.30) are capped at
                                                                     # 0.20 mm so that tracks can leave 0.4 / 0.5 mm-pitch pins; --relax-clearance: 0.10 mm
        via = (0.4, 0.2) if k in ("PWR_HIGH", "GND") else (0.38, 0.15) if cl_ < 0.1 else (0.35, 0.15)     # [layout] 0.35 / 0.15: the router's 0.10 copper clearance then also
                                                                           # meets JLC's 0.20 hole-to-copper rule (Freerouting has no hole rule)
        classes.append(cls(k, tr, cl_, via=via, prio=i))
        for n in d["nets"]:
            patterns.append({"netclass": k, "pattern": n})
    rules = {"min_clearance": 0.09, "min_track_width": 0.09, "min_via_diameter": 0.25, "min_via_annular_width": 0.05,
             "min_through_hole_diameter": 0.15, "min_hole_to_hole": 0.2, "min_hole_clearance": 0.2, "min_copper_edge_clearance": 0.2,
             "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1, "min_silk_clearance": 0.0, "min_text_height": 0.6,
             "min_text_thickness": 0.08, "min_resolved_spokes": 1, "min_groove_width": 0.0, "solder_mask_to_copper_clearance": 0.0,
             "solder_mask_clearance": 0.0, "solder_mask_min_width": 0.0, "max_error": 0.005, "use_height_for_length_calcs": True,
             "allow_blind_buried_vias": False, "allow_microvias": False}
    pro = {"board": {"design_settings": {"defaults": {"zones": {"min_clearance": 0.15}}, "rules": rules,
                                         "rule_severities": {"lib_footprint_issues": "ignore", "lib_footprint_mismatch": "ignore", "silk_overlap": "ignore",
                                                             "silk_over_copper": "ignore", "silk_edge_clearance": "ignore", "solder_mask_bridge": "ignore",
                                                             "text_height": "ignore", "text_thickness": "ignore", "footprint_type_mismatch": "ignore",
                                                             "missing_courtyard": "ignore", "starved_thermal": "ignore"},
                                         "track_widths": [0.0, 0.09, 0.1, 0.15, 0.2, 0.3],
                                         "via_dimensions": [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.25, "drill": 0.15},
                                                            {"diameter": 0.3, "drill": 0.15}, {"diameter": 0.4, "drill": 0.2}]},
                     "layer_presets": [], "viewports": []},
           "net_settings": {"classes": classes, "meta": {"version": 4}, "net_colors": None, "netclass_assignments": None, "netclass_patterns": patterns},
           "meta": {"filename": os.path.basename(base) + ".kicad_pro", "version": 3}, "pcbnew": {"page_layout_descr_file": ""},
           "schematic": {"drawing": {}}, "sheets": []}
    json.dump(pro, open(base + ".kicad_pro", "w"), indent=2)
    wl = " || ".join("A.intersectsCourtyard('%s') || B.intersectsCourtyard('%s')" % (r, r) for r in ("U6", "U8", "U4", "U5") if r in P.PARTS)
    open(base + ".kicad_dru", "w").write("""(version 1)
# JLCPCB standard 6-layer process, as read on jlcpcb.com/capabilities/pcb-capabilities (cache/v2/jlc_cap, 2026-11-12) + v3/design/netclasses.json
(rule "WLCSP / DSBGA fan-out: 0.09 / 0.09 inside the package courtyards only"
  (condition "%s")
  (constraint clearance (min 0.09mm)) (constraint track_width (min 0.09mm)))
(rule "JLC via 0.15 / 0.25 minimum"
  (condition "A.Type == 'Via'") (constraint hole_size (min 0.15mm)) (constraint via_diameter (min 0.25mm)) (constraint annular_width (min 0.05mm)))
(rule "JLC via hole to track / inner-layer hole to copper 0.20"
  (constraint hole_clearance (min 0.2mm)))
(rule "JLC hole to hole 0.20"
  (constraint hole_to_hole (min 0.2mm)))
""" % wl)


def main():
    pl_path, outdir = sys.argv[1], sys.argv[2]
    l3_open = "--l3-over-plates" in sys.argv
    relax = "--relax-clearance" in sys.argv
    os.makedirs(outdir, exist_ok=True)
    base = outdir + "/" + (sys.argv[sys.argv.index("--base") + 1] if "--base" in sys.argv else "v3f_g1")
    placement = json.load(open(pl_path))["parts"]
    parts = P.PARTS
    brd = pcbnew.BOARD(); brd.SetCopperLayerCount(6)
    nets = {}
    for p in parts.values():
        for n in p["pins"].values():
            if n and n not in nets:
                ni = pcbnew.NETINFO_ITEM(brd, n); brd.Add(ni); nets[n] = ni
    for ref, p in sorted(parts.items()):
        if ref == "AE1" and "--no-ae1" in sys.argv:
            continue                                     # [layout] radiator placeholder left out: the keep-out stays copper-free (RF lane)
        q = placement[ref]
        lib, name = FP_OVERRIDE.get(ref, p["footprint"]).split(":")
        f = pcbnew.FootprintLoad(LIBS[lib], name)
        f.SetFPIDAsString(FP_OVERRIDE.get(ref, p["footprint"])); brd.Add(f); f.SetReference(ref); f.SetValue(p["value"][:40])
        f.SetPosition(V(q["x"], q["y"])); f.SetOrientationDegrees(q["rot"])
        if q["side"] == "B":
            f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        for pad in f.Pads():
            n = p["pins"].get(PAD_ALIAS.get(ref, {}).get(pad.GetNumber(), pad.GetNumber()))
            if n:
                pad.SetNet(nets[n])
        if p.get("dnp"):
            f.SetDNP(True)
        f.Reference().SetVisible(False); f.Value().SetVisible(False)
        for g in list(f.GraphicalItems()):
            if g.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS):
                g.SetLayer(pcbnew.F_Fab if g.GetLayer() == pcbnew.F_SilkS else pcbnew.B_Fab)
    # outline + motor cut-out
    o = G.outline()
    for i in range(len(o)):
        seg(brd, o[i], o[(i + 1) % len(o)])
    if G.MOTOR_CUT_D > 0:
        c = pcbnew.PCB_SHAPE(brd); c.SetShape(pcbnew.SHAPE_T_CIRCLE)
        c.SetCenter(V(*G.MOTOR_CENTER)); c.SetEnd(V(G.MOTOR_CENTER[0] + G.MOTOR_CUT_D / 2, G.MOTOR_CENTER[1]))
        c.SetLayer(pcbnew.Edge_Cuts); c.SetWidth(MM(0.1)); brd.Add(c)
    # rule areas
    k = G.ANT_KEEPOUT
    kp = [(k[0] - 1, k[1] - 1), (k[2], k[1] - 1), (k[2], k[3]), (k[0] - 1, k[3])]
    poly_zone(brd, kp, ALL_CU, rule=True, name="ANT_KEEPOUT_NO_VIA_NO_POUR", vias=True, zones=True)
    poly_zone(brd, kp, ALL_CU[1:], rule=True, name="ANT_KEEPOUT_INNER_NO_TRACK", tracks=True)      # the feed enters on F.Cu only (trial)
    # [layout] B.Cu void and the inner voids are separate rule areas: fanout_planes.py re-cuts the B.Cu one around the dot-pad stubs
    void_layers = [CU["L5"]] + ([] if l3_open else [CU["L3"]])
    for nm, key in (("E1", "plate_E1"), ("E2", "plate_E2")):
        for pg in G.SKIN[key]["poly_board"]:
            if PLATES_OPEN:     # [layout, LEAD_NOTES 2e R-2] L3 / L5 open over the plates (no pour on L5); net rules in the .kicad_dru
                poly_zone(brd, [tuple(p_) for p_ in pg], [CU["L5"]], rule=True, name="PLATE_%s_NOPOUR_L5" % nm, zones=True)
                poly_zone(brd, [tuple(p_) for p_ in pg], ALL_CU, rule=True, name="PLATE_%s_AREA" % nm, zones=False)
            else:
                poly_zone(brd, [tuple(p_) for p_ in pg], void_layers, rule=True, name="PLATE_%s_VOID" % nm, tracks=True, zones=True)
            poly_zone(brd, [tuple(p_) for p_ in pg], [CU["B"]], rule=True, name="PLATE_%s_VOID_BCU" % nm, tracks=True, zones=True)
    _isl = _J["G"].get("ZRECTS", {}).get("U10_island")
    if _isl:                    # [S2b T-5] only the island's own thermal vias on the 4 x 4 mm U10 island (rule in the .kicad_dru)
        poly_zone(brd, [(_isl[0], _isl[1]), (_isl[2], _isl[1]), (_isl[2], _isl[3]), (_isl[0], _isl[3])], ALL_CU, rule=True, name="U10_ISLAND_AREA")
    if PLATES_OPEN:             # R-2: no via within 1.0 mm of a dot opening (opening D 2.0 -> keep-out circle R 2.0 for every via)
        for dn, (dx, dy) in G.DOTS.items():
            poly_zone(brd, [(dx + 2.0 * math.cos(2 * math.pi * i / 40), dy + 2.0 * math.sin(2 * math.pi * i / 40)) for i in range(40)],
                      ALL_CU, rule=True, name="DOT_%s_NO_VIA" % dn, vias=True)
    # planes: L2 GND; L4 = GND (G1 trials) or the VDD_1V8 plane (--l4-net VDD_1V8, layout lane)
    full = [tuple(p_) for p_ in G.outline()]
    l4 = sys.argv[sys.argv.index("--l4-net") + 1] if "--l4-net" in sys.argv else "GND"
    poly_zone(brd, full, [CU["L2"]], net=nets["GND"], name="L2_GND", priority=1)
    poly_zone(brd, full, [CU["L4"]], net=nets[l4], name="L4_" + l4, priority=1)
    # [layout] PMIC_NO_POUR (netclasses.json rule_areas): no plane under the divider / CREF / MOhm hold-node / O-2 chain footprints
    if "--pmic-no-pour" in sys.argv:
        npr = [r for r in ("R101", "R102", "R103", "R104", "R105", "R106", "R107", "R125", "R126", "C121", "C104", "NT1",
                           "R170", "R171", "R172", "R174", "C174") if r in parts]
        for r in npr:
            f = brd.FindFootprintByReference(r)
            bb = f.GetCourtyard(pcbnew.F_CrtYd).BBox() if f.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else f.GetBoundingBox(False)
            x0, x1 = pcbnew.ToMM(bb.GetLeft()) - OX, pcbnew.ToMM(bb.GetRight()) - OX
            y0, y1 = OY - pcbnew.ToMM(bb.GetBottom()), OY - pcbnew.ToMM(bb.GetTop())
            poly_zone(brd, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], [CU["L2"], CU["L4"]], rule=True, name="PMIC_NO_POUR_" + r, zones=True)
    # fan-out of the bare-die packages (fanout.py), locked so that the router keeps it
    FO.BO = 0.5                                                   # stubs end at the courtyard line (the router continues from there)
    summ = {}
    for ref, fn in (("U6", FO.nrf_wlcsp_plan), ("U8", FO.max86141_plan), ("U4", FO.dsbga8_plan), ("U5", FO.dsbga8_plan)):
        if ref not in parts:
            continue
        f = brd.FindFootprintByReference(ref)
        pins = {pad.GetNumber(): parts[ref]["pins"].get(pad.GetNumber()) for pad in f.Pads()}
        plan = fn(pins)
        nv, nt = FO.apply(brd, f, plan, pcbnew)
        summ[ref] = dict(vias=nv, track_segments=nt, direct=len(plan["direct"]), nc=plan["nc"])
    for t in brd.GetTracks():
        t.SetLocked(True)
    ds = brd.GetDesignSettings(); ds.SetAuxOrigin(V(0, 0)); ds.SetGridOrigin(V(0, 0))
    brd.Save(base + ".kicad_pcb")
    write_project(base, relax)
    rules = intra_rules(brd, class_clearance(0.09 if relax else 0.2))
    if PLATES_OPEN:
        nets_here = {n.GetNetname() for n in brd.GetNetInfo().NetsByName().values()} if hasattr(brd.GetNetInfo(), "NetsByName") else set()
        cond = " || ".join("A.NetName == '%s'" % n for n in plate_forbidden())
        area = "(A.intersectsArea('PLATE_E1_AREA') || A.intersectsArea('PLATE_E2_AREA'))"
        with open(base + ".kicad_dru", "a") as fh:
            fh.write('# [layout] LEAD_NOTES 2e R-2: PWR_HIGH, VDD_1V8 and ECG-band nets: no via over a plate, no inner-layer track over a plate\n')
            fh.write('(rule "R-2 no via of a forbidden net over a plate"\n  (condition "A.Type == \'Via\' && %s && (%s)")\n  (constraint disallow via))\n' % (area, cond))
            fh.write('(rule "R-2 no inner track of a forbidden net over a plate"\n  (layer inner)\n  (condition "A.Type == \'Track\' && %s && (%s)")\n  (constraint disallow track))\n' % (area, cond))
        json.dump(plate_forbidden(), open(outdir + "/plate_forbidden_nets.json", "w"), indent=0)
    if _J["G"].get("ZRECTS", {}).get("U10_island"):
        with open(base + ".kicad_dru", "a") as fh:
            fh.write('(rule "T-5 U10 island: no via of another net"\n  (condition "A.Type == \'Via\' && A.NetName != \'TMP117_ISLAND\' && A.intersectsArea(\'U10_ISLAND_AREA\')")\n  (constraint disallow via))\n')
    with open(base + ".kicad_dru", "a") as fh:
        fh.write('(rule "S2d J40 sits on the AE1 spring land (LEAD_NOTES 2i L-1)"\n  (condition "(A.Reference == \'J40\' && B.Reference == \'AE1\') || (A.Reference == \'AE1\' && B.Reference == \'J40\')")\n  (constraint courtyard_clearance (min -10mm)))\n')
        fh.write("# vendor land patterns (own pad gap below the net-class clearance) - generated by build_board.intra_rules\n")
        for ref, d in sorted(rules):
            fh.write('(rule "land pattern %s (own pad gap %.3f mm)"\n  (condition "A.memberOfFootprint(\'%s\') && B.memberOfFootprint(\'%s\')")\n'
                     '  (constraint clearance (min 0.09mm)))\n' % (ref, d, ref, ref))
    print("intra-footprint land-pattern rules:", len(rules))
    json.dump(dict(placement=os.path.basename(pl_path), zones=G.ZTAG, variant=G.VARIANT, opts=G.OPTS, l3_open_over_plates=l3_open,
                   relaxed_class_clearance=relax, fanout=summ, footprints=len(parts), nets=len(nets)), open(base + "_build.json", "w"), indent=1)
    print("saved", base + ".kicad_pcb", "footprints", len(parts), "nets", len(nets), "fan-out", summ)


if __name__ == "__main__":
    main()
