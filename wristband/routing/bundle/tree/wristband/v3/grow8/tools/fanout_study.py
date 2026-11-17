"""Gate 1 (c): escape study of the bare-die packages on JLC's standard 6-layer process, through vias only.

Builds a small 6-layer KiCad board with the real footprints (v2/design/lib/easyeda_rev.pretty) and the real pin
assignment (v2/design/parts.json, variant dock_wlcsp): U6 nRF52832-CIAA WLCSP-50, U8 MAX86141 WLP-20, U4 INA236
DSBGA-8. Adds the fan-out of fanout.py, GND planes on L2 and L4, joins the multi-ball supply nets outside the
packages, fills the zones and runs KiCad DRC with JLC's rules (project file written here).
usage: kicad-python fanout_study.py [--land 0.20|0.25] [--tag NAME]
"""
import json, os, subprocess, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fanout as FO

W = "@SVROOT@/wristband"
V3 = W + "/v3"
LIB = V3 + "/design/lib/easyeda_rev.pretty"
OUTD = V3 + "/layout/work/fanout"
VARIANT = os.environ.get("G1_VARIANT", "v3f")
KCLI = "@MACKICAD@/MacOS/kicad-cli"
MM = pcbnew.FromMM

RULES = {"min_clearance": 0.09, "min_track_width": 0.09, "min_via_diameter": 0.25, "min_via_annular_width": 0.05,
         "min_through_hole_diameter": 0.15, "min_hole_to_hole": 0.2, "min_hole_clearance": 0.2,
         "min_copper_edge_clearance": 0.2, "min_microvia_diameter": 0.2, "min_microvia_drill": 0.1,
         "min_silk_clearance": 0.0, "min_text_height": 0.6, "min_text_thickness": 0.08, "min_resolved_spokes": 1,
         "min_groove_width": 0.0, "solder_mask_to_copper_clearance": 0.0, "solder_mask_clearance": 0.0,
         "solder_mask_min_width": 0.1, "max_error": 0.005, "use_height_for_length_calcs": True,
         "allow_blind_buried_vias": False, "allow_microvias": False}


def cls(name, track, clear):
    return {"name": name, "clearance": clear, "track_width": track, "via_diameter": 0.25, "via_drill": 0.15,
            "diff_pair_width": 0.15, "diff_pair_gap": 0.2, "diff_pair_via_gap": 0.25, "microvia_diameter": 0.2,
            "microvia_drill": 0.1, "wire_width": 6, "bus_width": 12, "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)",
            "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647, "tuning_profile": ""}


def write_project(path_noext):
    pro = {"board": {"design_settings": {"defaults": {"zones": {"min_clearance": 0.09}}, "rules": RULES,
                                         "rule_severities": {"lib_footprint_issues": "ignore", "lib_footprint_mismatch": "ignore",
                                                             "silk_overlap": "ignore", "silk_over_copper": "ignore",
                                                             "silk_edge_clearance": "ignore", "track_dangling": "ignore"},
                                         "track_widths": [0.0, 0.09, 0.15], "via_dimensions": [{"diameter": 0.0, "drill": 0.0},
                                                                                              {"diameter": 0.25, "drill": 0.15}]},
                     "layer_presets": [], "viewports": []},
           "net_settings": {"classes": [cls("Default", 0.09, 0.09)], "meta": {"version": 4}, "net_colors": None,
                            "netclass_assignments": None, "netclass_patterns": []},
           "meta": {"filename": os.path.basename(path_noext) + ".kicad_pro", "version": 3},
           "pcbnew": {"page_layout_descr_file": ""}, "schematic": {"drawing": {}}, "sheets": []}
    json.dump(pro, open(path_noext + ".kicad_pro", "w"), indent=2)
    open(path_noext + ".kicad_dru", "w").write("""(version 1)
# JLCPCB standard multilayer process, as read on jlcpcb.com/capabilities/pcb-capabilities (cache/v2/jlc_cap, 2026-11-12)
(rule "JLC via 0.15 / 0.25 minimum"
  (condition "A.Type == 'Via'") (constraint hole_size (min 0.15mm)) (constraint via_diameter (min 0.25mm)) (constraint annular_width (min 0.05mm)))
(rule "JLC via hole to track / inner-layer hole to copper 0.20"
  (constraint hole_clearance (min 0.2mm)))
(rule "JLC hole to hole 0.20"
  (constraint hole_to_hole (min 0.2mm)))
(rule "JLC BGA pad to trace 0.09 (multilayer)"
  (condition "A.Type == 'Pad' && B.Type == 'Track'") (constraint clearance (min 0.09mm)))
(rule "JLC SMD pad to pad 0.15 (different nets)"
  (condition "A.Type == 'Pad' && B.Type == 'Pad'") (constraint clearance (min 0.15mm)))
""")


def seg(brd, a, b, layer=pcbnew.Edge_Cuts, w=0.1):
    s = pcbnew.PCB_SHAPE(brd); s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1]))); s.SetEnd(pcbnew.VECTOR2I(MM(b[0]), MM(b[1])))
    s.SetLayer(layer); s.SetWidth(MM(w)); brd.Add(s)


def zone(brd, rect, layer, net, name):
    z = pcbnew.ZONE(brd)
    ls = pcbnew.LSET(); ls.AddLayer(layer); z.SetLayerSet(ls)
    z.SetNet(net); z.SetLocalClearance(MM(0.09)); z.SetMinThickness(MM(0.1))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL); z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    z.SetZoneName(name)
    ol = z.Outline(); ol.NewOutline()
    for x, y in ((rect[0], rect[1]), (rect[2], rect[1]), (rect[2], rect[3]), (rect[0], rect[3])):
        ol.Append(MM(x), MM(y))
    brd.Add(z)


def track(brd, net, pts, layer, w):
    for i in range(len(pts) - 1):
        t = pcbnew.PCB_TRACK(brd)
        t.SetStart(pcbnew.VECTOR2I(MM(pts[i][0]), MM(pts[i][1]))); t.SetEnd(pcbnew.VECTOR2I(MM(pts[i + 1][0]), MM(pts[i + 1][1])))
        t.SetWidth(MM(w)); t.SetLayer(layer); t.SetNet(net); brd.Add(t)


def via(brd, net, xy, drill=0.15, dia=0.25):
    v = pcbnew.PCB_VIA(brd); v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetPosition(pcbnew.VECTOR2I(MM(xy[0]), MM(xy[1]))); v.SetDrill(MM(drill)); v.SetWidth(MM(dia))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(net)
    try:
        v.SetFillingMode(pcbnew.FILLING_MODE_FILLED); v.SetCappingMode(pcbnew.CAPPING_MODE_CAPPED)
    except Exception:
        pass
    brd.Add(v)


def main():
    land = float(sys.argv[sys.argv.index("--land") + 1]) if "--land" in sys.argv else 0.20
    tag = sys.argv[sys.argv.index("--tag") + 1] if "--tag" in sys.argv else "land%03d" % round(land * 100)
    rot = float(sys.argv[sys.argv.index("--rot") + 1]) if "--rot" in sys.argv else 0.0
    out = OUTD
    os.makedirs(out, exist_ok=True)
    base = out + "/fanout_" + tag
    parts = json.load(open(V3 + "/design/parts.json"))["variants"][VARIANT]["parts"]
    brd = pcbnew.BOARD(); brd.SetCopperLayerCount(6)
    nets = {}
    def net(n):
        if n not in nets:
            ni = pcbnew.NETINFO_ITEM(brd, n); brd.Add(ni); nets[n] = ni
        return nets[n]
    place = {"U6": (100.0, 100.0), "U8": (107.0, 100.0), "U4": (112.5, 98.0), "U5": (112.5, 102.0)}
    plans = {}
    for ref, (x, y) in place.items():
        p = parts[ref]
        f = pcbnew.FootprintLoad(LIB, p["footprint"].split(":")[1])
        f.SetFPIDAsString(p["footprint"]); brd.Add(f); f.SetReference(ref); f.SetValue(p["value"])
        f.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y))); f.SetOrientationDegrees(rot)
        for pad in f.Pads():
            n = p["pins"].get(pad.GetNumber())
            if n:
                pad.SetNet(net(n if n == "GND" else ref + "/" + n))
            if abs(land - 0.20) > 1e-9:
                pad.SetSize(pcbnew.F_Cu, pcbnew.VECTOR2I(MM(land), MM(land)))
        pins = {pad.GetNumber(): p["pins"].get(pad.GetNumber()) for pad in f.Pads()}
        pins = {k: (v if v in (None, "GND") else ref + "/" + v) for k, v in pins.items()}
        plan = {"U6": FO.nrf_wlcsp_plan, "U8": FO.max86141_plan, "U4": FO.dsbga8_plan, "U5": FO.dsbga8_plan}[ref](pins)
        plans[ref] = plan
        nv, nt = FO.apply(brd, f, plan, pcbnew)
        print(ref, p["value"], "balls", len(pins), "F.Cu escapes", len(plan["direct"]), "vias (in lands + in empty positions)", nv, "NC", len(plan["nc"]), plan["nc"],
              "inner-layer escapes", {l: sum(1 for t in plan["tracks"] if t[1] == l) for l in ("In2.Cu", "In4.Cu", "B.Cu")})
    # outline
    x0, y0, x1, y1 = 95.0, 95.0, 117.0, 105.0
    for a, b in (((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))):
        seg(brd, a, b)
    zone(brd, (x0 + 0.3, y0 + 0.3, x1 - 0.3, y1 - 0.3), pcbnew.In1_Cu, net("GND"), "L2_GND")
    zone(brd, (x0 + 0.3, y0 + 0.3, x1 - 0.3, y1 - 0.3), pcbnew.In3_Cu, net("GND"), "L4_GND")
    # join the nets that have more than one ball, outside the packages, so that DRC "unconnected" is meaningful
    # (nets are prefixed with the package reference, GND excepted: connections between packages are not part of this study)
    if rot == 0:
        ux, uy = place["U6"]; yo = 1.4 + FO.BO
        vd = net("U6/VDD_1V8")                                # A7 (up) and H7 (down) joined on B.Cu right of the package
        via(brd, vd, (ux + 1.2, uy - yo)); via(brd, vd, (ux + 1.2, uy + yo))
        track(brd, vd, [(ux + 1.2, uy - yo), (ux + 2.9, uy - yo), (ux + 2.9, uy + yo), (ux + 1.2, uy + yo)], pcbnew.B_Cu, 0.2)
        ux, uy = place["U8"]; xo8, yo8 = 0.8 + FO.BO, 0.6 + FO.BO
        pg = net("U8/PD_GND")                                 # D4 (down) and C5 (right), around the PD1_IN stub of D5
        track(brd, pg, [(ux + 0.4, uy + yo8), (ux + 0.4, uy + yo8 + 0.4), (ux + xo8 + 0.3, uy + yo8 + 0.4), (ux + xo8 + 0.3, uy + 0.2),
                        (ux + xo8, uy + 0.2)], pcbnew.F_Cu, 0.09)
        g = net("GND")
        ux, uy = place["U4"]
        via(brd, g, (ux - 0.2, uy + 0.2 + FO.BO)); via(brd, g, (ux + 0.2, uy - 0.2 - FO.BO))   # B1, C2 stub ends -> planes
        ux, uy = place["U5"]                                  # [V3-F] U5: C2 GND; B1 (A0) and D2 (VS) both on INA_VS, joined on B.Cu
        via(brd, g, (ux + 0.2, uy - 0.2 - FO.BO))
        iv = net("U5/INA_VS")
        via(brd, iv, (ux - 0.2, uy + 0.2 + FO.BO)); via(brd, iv, (ux + 0.6, uy - 0.2 - FO.BO))
        track(brd, iv, [(ux - 0.2, uy + 0.2 + FO.BO), (ux + 1.7, uy + 0.2 + FO.BO), (ux + 1.7, uy - 0.2 - FO.BO), (ux + 0.6, uy - 0.2 - FO.BO)], pcbnew.B_Cu, 0.15)
    # self-test of the rule deck: deliberate defects, each must be reported (--mutant N)
    mutant = int(sys.argv[sys.argv.index("--mutant") + 1]) if "--mutant" in sys.argv else 0
    if mutant:
        ux, uy = place["U6"]
        dn = net("MUTANT")
        if mutant == 1:      # F.Cu track between the lands D1 and E1 (gap 0.20 mm)
            track(brd, dn, [(ux - 2.0, uy + 0.0), (ux - 1.0, uy + 0.0)], pcbnew.F_Cu, 0.09)
        elif mutant == 2:    # L3 track between the via holes of B3 and B4 (gap 0.25 mm)
            track(brd, dn, [(ux - 0.2, uy - 2.0), (ux - 0.2, uy - 0.6)], pcbnew.In2_Cu, 0.09)
        elif mutant == 3:    # extra via 0.3 mm from the via in C4: hole to hole 0.15 mm
            via(brd, net("GND"), (ux + 0.0, uy - 0.3))
        elif mutant == 4:    # via 0.10 / 0.20 mm, below the standard-process minimum
            via(brd, dn, (ux + 3.5, uy + 3.0), 0.10, 0.20)
        elif mutant == 5:    # F.Cu track 0.07 mm
            track(brd, dn, [(ux + 3.5, uy + 3.0), (ux + 4.5, uy + 3.0)], pcbnew.F_Cu, 0.07)
        elif mutant == 6:    # [V3-F] a second L3 track through the door of ring 2, 0.18 mm beside the D3 escape (0.09 / 0.09)
            track(brd, dn, [(ux - 0.4, uy - 0.78), (ux - 2.3, uy - 0.78)], pcbnew.In2_Cu, 0.09)
    for t in brd.GetTracks():
        if t.GetClass() == "PCB_VIA":
            try:
                t.SetFillingMode(pcbnew.FILLING_MODE_FILLED); t.SetCappingMode(pcbnew.CAPPING_MODE_CAPPED)
            except Exception:
                pass
    pcbnew.ZONE_FILLER(brd).Fill(brd.Zones())
    brd.Save(base + ".kicad_pcb")
    write_project(base)
    rep = base + "_drc.json"
    env = dict(os.environ, KICAD_CONFIG_HOME=os.environ.get("TMPDIR", "/tmp") + "/solarband_kicfg")
    os.makedirs(env["KICAD_CONFIG_HOME"] + "/10.0", exist_ok=True)
    r = subprocess.run([KCLI, "pcb", "drc", "--severity-all", "--format", "json", "--units", "mm", "-o", rep, base + ".kicad_pcb"],
                       capture_output=True, text=True, env=env)
    print(r.stdout.strip()[-300:], r.stderr.strip()[-300:])
    d = json.load(open(rep))
    import collections
    cnt = collections.Counter()
    for sect in ("violations", "unconnected_items"):
        for v in d.get(sect, []):
            cnt[(sect, v["severity"], v["type"])] += 1
    for k, v in sorted(cnt.items()):
        print("%5d  %-18s %-8s %s" % (v, k[0], k[1], k[2]))
    for sect in ("violations", "unconnected_items"):
        for v in d.get(sect, [])[:25]:
            print("  -", sect, v["type"], "|", v["description"], "|", "; ".join(
                i["description"] + " @(%.3f,%.3f)" % (i["pos"]["x"], i["pos"]["y"]) for i in v["items"]))
    json.dump(dict(tag=tag, land=land, rules=RULES, counts={"%s/%s/%s" % k: v for k, v in cnt.items()},
                   plans={r: dict(vias=p["vias"], nc=p["nc"], direct=p["direct"]) for r, p in plans.items()}),
              open(base + "_summary.json", "w"), indent=1)
    print("saved", base + ".kicad_pcb", "violations", len(d.get("violations", [])), "unconnected", len(d.get("unconnected_items", [])))


if __name__ == "__main__":
    main()
