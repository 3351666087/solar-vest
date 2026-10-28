"""Netlist (from SKiDL export) + placement table → KiCad 10 board, Freerouting-routed, GND poured both sides.

usage: kicad-python build_board.py <pmbh|libb> [--no-route]
"""
import json, os, sys, subprocess, importlib, shutil
import pcbnew

B = sys.argv[1]; ROUTE = "--no-route" not in sys.argv
HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, "out", B); os.makedirs(OUT, exist_ok=True)
FP = os.path.expanduser("~/Applications/KiCad/KiCad/KiCad/KiCad.app/Contents/SharedSupport/footprints/")
JAVA = os.path.join(os.environ.get("TMPDIR", "/tmp"), "tools/jre25/Contents/Home/bin/java")
FREEROUTING = os.path.join(os.environ.get("TMPDIR", "/tmp"), "tools/freerouting.jar")
plc = importlib.import_module(f"place_{B}")
parts = json.load(open(os.path.join(HERE, f"{B}_parts.json")))
O = (100.0, 100.0)                                    # board origin inside the KiCad sheet
MM = pcbnew.FromMM
def V(x, y): return pcbnew.VECTOR2I(MM(O[0] + x), MM(O[1] + y))

POWER_NETS = {"pmbh": ["PV_IN+", "PV_IN-", "PV_F", "VPV", "SW", "CSP", "VSYS", "BAT+", "VL_IN", "VLOAD", "PV_MID"],
              "libb": ["VLOAD", "VBIT", "VSC", "SC_MID", "PRE"]}[B]      # GND is carried by the pours; sense taps stay thin

# ---------- project file with net classes (KiCad reads them when the board is loaded) ----------
def write_project(path):
    pro = {
        "board": {"design_settings": {"rules": {"min_clearance": 0.15, "min_track_width": 0.15, "min_via_diameter": 0.6, "min_through_hole_diameter": 0.3,
                                                 "min_copper_edge_clearance": 0.3, "min_hole_to_hole": 0.25, "min_silk_clearance": 0.0},
                                      "defaults": {"board_outline_line_width": 0.1}}},
        "net_settings": {
            "classes": [
                {"name": "Default", "clearance": 0.15, "track_width": 0.25, "via_diameter": 0.6, "via_drill": 0.3, "diff_pair_width": 0.2, "diff_pair_gap": 0.25,
                 "microvia_diameter": 0.3, "microvia_drill": 0.1, "wire_width": 6, "bus_width": 12, "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)",
                 "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 2147483647},
                {"name": "Power", "clearance": 0.15, "track_width": 0.8, "via_diameter": 0.8, "via_drill": 0.4, "diff_pair_width": 0.2, "diff_pair_gap": 0.25,
                 "microvia_diameter": 0.3, "microvia_drill": 0.1, "wire_width": 6, "bus_width": 12, "line_style": 0, "pcb_color": "rgba(0, 0, 0, 0.000)",
                 "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": 0}],
            "meta": {"version": 4},
            "netclass_assignments": None,
            "netclass_patterns": [{"netclass": "Power", "pattern": n} for n in POWER_NETS]},
        "meta": {"filename": os.path.basename(path), "version": 3}}
    json.dump(pro, open(path, "w"), indent=2)

def load_fp(fpid):
    lib, name = fpid.split(":")
    path = os.path.join(HERE, "lib/hw.pretty") if lib == "hw" else FP + lib + ".pretty"
    f = pcbnew.FootprintLoad(path, name)
    if f is None: raise SystemExit(f"footprint not found: {fpid}")
    f.SetFPIDAsString(fpid)
    return f

def build():
    brd = pcbnew.BOARD()
    brd.SetCopperLayerCount(2)
    nets = {}
    for p in parts.values():
        for n in p["pins"].values():
            if n and not n.startswith("__NOCONNECT") and n not in nets:
                ni = pcbnew.NETINFO_ITEM(brd, n); brd.Add(ni); nets[n] = ni
    missing = []
    for ref, p in parts.items():
        if not p["footprint"]: continue                    # schematic-only (XIAO symbol)
        f = load_fp(p["footprint"]); brd.Add(f)
        f.SetReference(ref); f.SetValue(p["value"])
        HW3D = os.path.join(HERE, "lib/hw.3dshapes")
        subst = {"JST_PH_S2B": "JST_PH_S2B-PH-SM4-TB", "JST_PH_S5B": "JST_PH_S5B-PH-SM4-TB", "Fuse_1812": "Fuse_1812_4532Metric", "SuperCap": "SuperCap_D10_L25_Flat"}
        name = p["footprint"].split(":")[1]
        for k, v in subst.items():
            if name.startswith(k):
                f.Models().clear()                       # SWIG iterates copies: replace, don't edit in place
                m = pcbnew.FP_3DMODEL(); m.m_Filename = os.path.join(HW3D, v + ".step"); f.Models().push_back(m)
        if ref.startswith("H") and p["catkey"] == "HOLE":
            x, y = plc.BOARD["holes"][int(ref[1:]) - 1]; f.SetPosition(V(x, y)); continue
        if ref not in plc.P: missing.append(ref); continue
        x, y, rot = plc.P[ref]
        f.SetPosition(V(x, y)); f.SetOrientationDegrees(rot)
        for pad in f.Pads():
            n = p["pins"].get(pad.GetNumber())
            if n and not n.startswith("__NOCONNECT"): pad.SetNet(nets[n])
        if p.get("lcsc"):
            f.SetField("LCSC", p["lcsc"])
            for fld in f.GetFields():
                if fld.GetName() == "LCSC": fld.SetVisible(False); fld.SetLayer(pcbnew.F_Fab)
        if p.get("jlc") == "user":
            f.SetExcludedFromBOM(True); f.SetExcludedFromPosFiles(True)
        if p["catkey"] in ("TP", "NETTIE"):
            f.SetExcludedFromBOM(True); f.SetExcludedFromPosFiles(True)
        # reference text: keep for ICs / transistors / connectors, hide on small passives and test points
        f.Reference().SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8))); f.Reference().SetTextThickness(MM(0.13))
        if p["catkey"] in ("TP", "NETTIE") or (ref[0] in "RCL" and not ref.startswith("RS")) or ref in getattr(plc, "HIDE_REF", ()):
            f.Reference().SetVisible(False)
    if missing: raise SystemExit(f"no placement for: {missing}")
    # no-via rule areas around net ties: the router cannot see the tie's internal copper bridge
    for f in brd.GetFootprints():
        if f.GetFPIDAsString().startswith("NetTie"):
            bb = f.GetBoundingBox(False); m = MM(0.6)
            ra = pcbnew.ZONE(brd); ra.SetIsRuleArea(True); ra.SetDoNotAllowVias(True); ra.SetDoNotAllowTracks(False)
            ra.SetDoNotAllowPads(False); ra.SetDoNotAllowZoneFills(False); ra.SetDoNotAllowFootprints(False)
            ra.SetLayerSet(pcbnew.LSET.AllCuMask())
            ol = ra.Outline(); ol.NewOutline()
            for x, y in ((bb.GetLeft() - m, bb.GetTop() - m), (bb.GetRight() + m, bb.GetTop() - m), (bb.GetRight() + m, bb.GetBottom() + m), (bb.GetLeft() - m, bb.GetBottom() + m)):
                ol.Append(int(x), int(y))
            brd.Add(ra)
    # outline (rounded rectangle)
    w, h, r = plc.BOARD["w"], plc.BOARD["h"], plc.BOARD["corner"]
    def seg(a, b):
        s = pcbnew.PCB_SHAPE(brd); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(V(*a)); s.SetEnd(V(*b)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1)); brd.Add(s)
    def arc(c, start, ang):
        s = pcbnew.PCB_SHAPE(brd); s.SetShape(pcbnew.SHAPE_T_ARC); s.SetCenter(V(*c)); s.SetStart(V(*start)); s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T)); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1)); brd.Add(s)
    seg((r, 0), (w - r, 0)); seg((w, r), (w, h - r)); seg((w - r, h), (r, h)); seg((0, h - r), (0, r))
    arc((w - r, r), (w - r, 0), 90); arc((w - r, h - r), (w, h - r), 90); arc((r, h - r), (r, h), 90); arc((r, r), (0, r), 90)
    # silkscreen labels
    def text(t, x, y, rot=0, size=1.0, layer=pcbnew.F_SilkS):
        tx = pcbnew.PCB_TEXT(brd); tx.SetText(t); tx.SetPosition(V(x, y)); tx.SetLayer(layer)
        tx.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size))); tx.SetTextThickness(MM(max(0.12, size * 0.15))); tx.SetTextAngleDegrees(rot)
        if layer == pcbnew.B_SilkS: tx.SetMirrored(True)
        brd.Add(tx)
    for lab in getattr(plc, "LABELS", []): text(*lab)
    bx, by = plc.BOARD["back_text"]
    text(f'{plc.BOARD["name"]}  {plc.BOARD["rev"]}', bx, by, 0, 1.2, pcbnew.B_SilkS)
    text("JLCJLCJLCJLC", bx, by + 2.2, 0, 1.0, pcbnew.B_SilkS)   # JLC order-number position
    return brd

def add_gnd_zones(brd):
    w, h = plc.BOARD["w"], plc.BOARD["h"]
    gnd = brd.FindNet("GND")
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        z = pcbnew.ZONE(brd); z.SetLayer(layer); z.SetNet(gnd); z.SetIsFilled(False)
        z.SetLocalClearance(MM(0.25)); z.SetMinThickness(MM(0.25))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_THT_THERMAL)   # SMD pads solid, THT pads thermal
        z.SetThermalReliefGap(MM(0.3)); z.SetThermalReliefSpokeWidth(MM(0.5))
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        ol = z.Outline(); ol.NewOutline()
        for x, y in ((0.3, 0.3), (w - 0.3, 0.3), (w - 0.3, h - 0.3), (0.3, h - 0.3)): ol.Append(MM(O[0] + x), MM(O[1] + y))
        brd.Add(z)
    pcbnew.ZONE_FILLER(brd).Fill(brd.Zones())

def fix_dsn(path):
    """KiCad's Python DSN export ignores project net classes: rewrite them (µm units)."""
    import re
    s = open(path).read()
    s = s.replace('(padstack "Via[0-1]_600:300_um"', '(padstack "Via[0-1]_800:400_um"\n      (shape (circle F.Cu 800))\n      (shape (circle B.Cu 800))\n      (attach off)\n    )\n    (padstack "Via[0-1]_600:300_um"', 1)
    s = s.replace('(via "Via[0-1]_600:300_um")', '(via "Via[0-1]_600:300_um" "Via[0-1]_800:400_um")', 1)
    s = re.sub(r"\(rule\s*\(width 200\)\s*\(clearance 200\)", "(rule\n      (width 250)\n      (clearance 150)", s, count=1)
    m = re.search(r"\(class kicad_default(.*?)\(circuit", s, re.S)
    nets = re.findall(r'"[^"]+"|[^\s()]+', m.group(1))
    def bare(n): return n.strip('"')
    pw = [n for n in nets if bare(n) in POWER_NETS]; sig = [n for n in nets if bare(n) not in POWER_NETS]
    end = s.find("(wiring", m.start()); blk_end = s.rfind(")", m.start(), end); blk_end = s.rfind(")", m.start(), blk_end)
    PW = int(os.environ.get("POWER_W_UM", "600"))
    new = (f"(class kicad_default {' '.join(sig)}\n      (circuit (use_via \"Via[0-1]_600:300_um\"))\n      (rule (width 250) (clearance 150))\n    )\n"
           f"    (class Power {' '.join(pw)}\n      (circuit (use_via \"Via[0-1]_800:400_um\"))\n      (rule (width {PW}) (clearance 150))\n    )\n  ")
    s = s[:m.start()] + new + s[blk_end + 1:]
    open(path, "w").write(s)

def main():
    pcb = os.path.join(OUT, f"{B}.kicad_pcb"); pro = os.path.join(OUT, f"{B}.kicad_pro")
    write_project(pro)
    brd = build(); brd.Save(pcb)
    brd = pcbnew.LoadBoard(pcb)                    # reload so the project's net classes apply
    if ROUTE:
        dsn, ses = os.path.join(OUT, f"{B}.dsn"), os.path.join(OUT, f"{B}.ses")
        if not pcbnew.ExportSpecctraDSN(brd, dsn): raise SystemExit("DSN export failed")
        fix_dsn(dsn)
        frdata = os.path.join(os.path.dirname(FREEROUTING), "frdata"); os.makedirs(frdata, exist_ok=True)
        cmd = [JAVA, "-Djava.awt.headless=true", "-jar", FREEROUTING, "-de", dsn, "-do", ses, "-mp", str(int(os.environ.get("FR_PASSES", "20"))), "-mt", "4",
               "--gui.enabled=false", "-da", "-dl", "-dct", "0", f"--user_data_path={frdata}", "--logging.console.level=INFO"]
        print("freerouting:", " ".join(cmd[3:]), flush=True)
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        open(os.path.join(OUT, "freerouting.log"), "w").write(r.stdout + r.stderr)
        if not os.path.exists(ses): raise SystemExit("Freerouting produced no SES; see freerouting.log")
        if not pcbnew.ImportSpecctraSES(brd, ses): raise SystemExit("SES import failed")
    add_gnd_zones(brd)
    brd.Save(pcb)
    print("saved", pcb)

main()
