"""Build the SolarBand PV board (2-layer 0.6 mm, ENIG, fab only, cells hand-soldered with Sn42Bi58) -> layout/pv/.

Frame: PV-local (u, v) = sky view (cell side = F.Cu), origin at the board's bottom-left, mm (lgeom.PV_*).
Mapping to the main-board frame: lgeom.pv_to_board(). Copper: cell pads on F.Cu; every accessory (JP1/JP2 solder
jumpers, TP1-TP4 test pads, J1/J2 lead pads) on B.Cu = the battery side, reachable before assembly; B.Cu PV- pour
except the RF band over the IFA (u > 19, v < 4.5) and the battery footprint (flat, no pads under the cell).
usage: kicad-python build_pv.py
"""
import json, os, re, subprocess, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lgeom as G
from build_main import parse_kicad_net, LIBS, poly_zone, rect_pts, patch_file

W = G.W
OUTDIR = W + "/layout/pv"
PCB = OUTDIR + "/solarband_pv.kicad_pcb"
MM = pcbnew.FromMM
OX, OY = 100.0, 130.0
FP_OVERRIDE = {"SC2": "solarband_layout:KXOB25-03X4TF_C2", "J1": "solarband_layout:WirePad_SMD_D1.6",
               "J2": "solarband_layout:WirePad_SMD_D1.6"}
# (u, v, rot, side)
PLACE = {"SC1": (*G.PV_CELLS["SC1"]["pos"], 90, "F"), "SC2": (*G.PV_CELLS["SC2"]["pos"], 90, "F"),
         "J1": (*G.PV_LEADS["J1"], 0, "B"), "J2": (*G.PV_LEADS["J2"], 0, "B"),
         "JP1": (15.2, 5.4, 0, "B"), "JP2": (6.2, 5.4, 180, "B"),
         "TP1": (17.6, 5.4, 0, "B"), "TP2": (17.6, 7.6, 0, "B"),
         "TP3": (2.6, 8.2, 0, "B"), "TP4": (8.8, 3.5, 0, "B")}


def V(u, v):
    return pcbnew.VECTOR2I(MM(OX + u), MM(OY - v))


def track(brd, net, pts, w, layer):
    for a, b in zip(pts[:-1], pts[1:]):
        t = pcbnew.PCB_TRACK(brd); t.SetStart(V(*a)); t.SetEnd(V(*b)); t.SetWidth(MM(w)); t.SetLayer(layer)
        t.SetNet(net); brd.Add(t)


def via(brd, net, xy):
    v = pcbnew.PCB_VIA(brd); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetPosition(V(*xy)); v.SetDrill(MM(0.3))
    v.SetWidth(MM(0.6)); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(net); brd.Add(v)


def main():
    parts = json.load(open(W + "/design/parts.json"))["pv"]
    comps = parse_kicad_net(W + "/design/solarband_pv_kicad.net")
    os.makedirs(OUTDIR, exist_ok=True)
    brd = pcbnew.BOARD()
    brd.SetCopperLayerCount(2)
    nets = {}
    for p in parts.values():
        for n in p["pins"].values():
            if n and n not in nets:
                ni = pcbnew.NETINFO_ITEM(brd, n); brd.Add(ni); nets[n] = ni
    for ref, p in sorted(parts.items()):
        fpid = FP_OVERRIDE.get(ref, p["footprint"])
        lib, name = fpid.split(":")
        f = pcbnew.FootprintLoad(LIBS[lib], name); f.SetFPIDAsString(fpid)
        brd.Add(f)
        f.SetReference(ref); c = comps.get(ref, {}); f.SetValue(c.get("value", p["value"]))
        # 3D models resolve through wristband/lib/easyeda.3dshapes (symlink to design/lib), footprints unchanged
        if c.get("path"):
            f.SetPath(pcbnew.KIID_PATH(c["path"]))
        u, v, rot, side = PLACE[ref]
        f.SetPosition(V(u, v)); f.SetOrientationDegrees(rot)
        if side == "B":
            f.Flip(f.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        for pad in f.Pads():
            n = p["pins"].get(pad.GetNumber())
            if n:
                pad.SetNet(nets[n])
        for k, val in c.get("fields", {}).items():
            if k in ("Footprint", "Datasheet", "Description") or not val:
                continue
            f.SetField(k, val)
        for fld in f.GetFields():
            if fld.GetName() not in ("Reference", "Value"):
                fld.SetVisible(False); fld.SetLayer(pcbnew.F_Fab)
        f.SetExcludedFromPosFiles(True)                                  # fab-only board: nothing is placed by JLC
        if ref in ("SC1", "SC2", "JP1", "JP2"):
            f.SetExcludedFromBOM(False)                                  # match the symbols (parity)
        f.Value().SetVisible(False)
        if ref == "SC1":       # library '+' mark sits on SC2's outline: move it beside pad 1 (still outside the cell)
            for g in f.GraphicalItems():
                if g.GetClass() == "PCB_TEXT" and g.GetText() == "+":
                    g.SetPosition(V(10.25, 5.3))
        r = f.Reference()
        r.SetTextSize(pcbnew.VECTOR2I(MM(0.8), MM(0.8))); r.SetTextThickness(MM(0.12))
        if ref.startswith("SC"):
            r.SetLayer(pcbnew.F_Fab)
        else:
            r.SetLayer(pcbnew.B_SilkS); r.SetMirrored(True)
            dv = {"J1": -1.5, "J2": -1.5, "TP1": -1.5, "TP2": 1.6, "TP3": 1.6, "TP4": -1.5, "JP1": -1.5, "JP2": -1.5}[ref]
            r.SetPosition(V(u + (1.7 if ref in ("TP2",) else 0), v + dv))
    # outline R2.0
    import math
    Wd, H, R = G.PV_W, G.PV_H, G.PV_R
    def seg(a, b):
        s = pcbnew.PCB_SHAPE(brd); s.SetShape(pcbnew.SHAPE_T_SEGMENT); s.SetStart(V(*a)); s.SetEnd(V(*b))
        s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1)); brd.Add(s)
    def arc(cx, cy, a0):
        p = lambda a: (cx + R * math.cos(math.radians(a)), cy + R * math.sin(math.radians(a)))
        s = pcbnew.PCB_SHAPE(brd); s.SetShape(pcbnew.SHAPE_T_ARC)
        s.SetArcGeometry(V(*p(a0)), V(*p(a0 + 45)), V(*p(a0 + 90))); s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(MM(0.1)); brd.Add(s)
    seg((R, 0), (Wd - R, 0)); seg((Wd, R), (Wd, H - R)); seg((Wd - R, H), (R, H)); seg((0, H - R), (0, R))
    arc(R, R, 180); arc(Wd - R, R, 270); arc(Wd - R, H - R, 0); arc(R, H - R, 90)
    # tracks (0.5 mm, PV class) and vias next to the cell pads, under the cell bodies (tented)
    N = nets
    track(brd, N["CELL_A_P"], [(11.25, 9.0), (12.4, 9.0)], 0.5, pcbnew.F_Cu); via(brd, N["CELL_A_P"], (12.4, 9.0))
    track(brd, N["CELL_A_P"], [(12.4, 9.0), (12.4, 8.6), (15.85, 8.6), (15.85, 5.4)], 0.5, pcbnew.B_Cu)
    track(brd, N["CELL_A_P"], [(15.85, 5.4), (17.6, 5.4)], 0.5, pcbnew.B_Cu)
    track(brd, N["CELL_B_P"], [(4.3, 22.3), (4.3, 21.3)], 0.5, pcbnew.F_Cu); via(brd, N["CELL_B_P"], (4.3, 21.3))
    track(brd, N["CELL_B_P"], [(4.3, 21.3), (4.3, 7.0), (5.55, 7.0), (5.55, 5.4)], 0.5, pcbnew.B_Cu)
    track(brd, N["CELL_B_P"], [(2.6, 8.2), (4.3, 8.2)], 0.5, pcbnew.B_Cu)
    track(brd, N["PV_P"], [(6.85, 5.4), (12.75, 5.4), (12.75, 7.0)], 0.5, pcbnew.B_Cu)
    track(brd, N["PV_P"], [(12.75, 5.4), (14.55, 5.4)], 0.5, pcbnew.B_Cu)
    track(brd, N["PV_N"], [(4.3, 2.9), (4.3, 3.9)], 0.5, pcbnew.F_Cu); via(brd, N["PV_N"], (4.3, 3.9))
    track(brd, N["PV_N"], [(32.85, 12.6), (31.85, 12.6)], 0.5, pcbnew.F_Cu); via(brd, N["PV_N"], (31.85, 12.6))
    # B.Cu PV- pour: board minus the RF band over the IFA [L-07]
    bu, bv = G.PV_RF_BAND
    ri = R - 0.3
    def carc(cx, cy, a0, a1, n=12):
        return [(cx + ri * math.cos(math.radians(a0 + (a1 - a0) * k / n)), cy + ri * math.sin(math.radians(a0 + (a1 - a0) * k / n)))
                for k in range(n + 1)]
    pts = carc(R, R, 180, 270) + [(bu, 0.3), (bu, bv), (Wd - 0.3, bv)] + carc(Wd - R, H - R, 0, 90) + carc(R, H - R, 90, 180)
    z = pcbnew.ZONE(brd); z.SetLayer(pcbnew.B_Cu); z.SetNet(N["PV_N"]); z.SetLocalClearance(MM(0.3))
    z.SetMinThickness(MM(0.3)); z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS); z.SetZoneName("PV_N_pour")
    ol = z.Outline(); ol.NewOutline()
    for u, v in pts:
        ol.Append(MM(OX + u), MM(OY - v))
    brd.Add(z)
    # silk: board name / polarity notes on B.SilkS (mirrored)
    def text(t, u, v, size=0.8, layer=pcbnew.B_SilkS):
        tx = pcbnew.PCB_TEXT(brd); tx.SetText(t); tx.SetPosition(V(u, v)); tx.SetLayer(layer)
        tx.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size))); tx.SetTextThickness(MM(0.12)); tx.SetMirrored(layer == pcbnew.B_SilkS)
        brd.Add(tx)
    text("SolarBand PV A  SnBi 170-180C", 18.5, 23.4, 0.8)
    text("PV+", 13.6, 8.8, 0.8); text("PV-", 10.5, 8.8, 0.8)
    pcbnew.ZONE_FILLER(brd).Fill(brd.Zones())
    brd.Save(PCB)
    s = open(PCB).read()
    st = """    (stackup
      (layer "F.SilkS" (type "Top Silk Screen"))
      (layer "F.Paste" (type "Top Solder Paste"))
      (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
      (layer "F.Cu" (type "copper") (thickness 0.035))
      (layer "dielectric 1" (type "core") (thickness 0.51) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
      (layer "B.Cu" (type "copper") (thickness 0.035))
      (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
      (layer "B.Paste" (type "Bottom Solder Paste"))
      (layer "B.SilkS" (type "Bottom Silk Screen"))
      (copper_finish "ENIG")
      (dielectric_constraints no)
    )
"""
    s = re.sub(r"\(setup\s*\n", "(setup\n" + st, s, count=1)
    s = re.sub(r"\(general\s*\n\s*\(thickness [0-9.]+\)", "(general\n    (thickness 0.6)", s, count=1)
    open(PCB, "w").write(s)
    # project + rules
    pro = {"board": {"design_settings": {"rules": {"min_clearance": 0.15, "min_track_width": 0.15, "min_via_diameter": 0.45,
                                                   "min_through_hole_diameter": 0.3, "min_hole_to_hole": 0.25,
                                                   "min_copper_edge_clearance": 0.3, "min_via_annular_width": 0.1}},
                     "layer_presets": [], "viewports": []},
           "net_settings": {"classes": [{"name": "Default", "clearance": 0.2, "track_width": 0.3, "via_diameter": 0.6,
                                         "via_drill": 0.3, "diff_pair_width": 0.2, "diff_pair_gap": 0.25, "priority": 2147483647},
                                        {"name": "PV", "clearance": 0.2, "track_width": 0.5, "via_diameter": 0.6,
                                         "via_drill": 0.3, "diff_pair_width": 0.2, "diff_pair_gap": 0.25, "priority": 0}],
                            "meta": {"version": 4},
                            "netclass_patterns": [{"netclass": "PV", "pattern": n} for n in ("PV_P", "PV_N", "CELL_A_P", "CELL_B_P")]},
           "meta": {"filename": "solarband_pv.kicad_pro", "version": 3},
           "sheets": json.load(open(W + "/design/kicad/pv/solarband_pv.kicad_pro"))["sheets"]}
    json.dump(pro, open(OUTDIR + "/solarband_pv.kicad_pro", "w"), indent=2)
    import shutil
    for fn in os.listdir(W + "/design/kicad/pv"):
        if fn.endswith(".kicad_sch") or fn in ("solarband.kicad_sym", "sym-lib-table"):
            shutil.copy(os.path.join(W + "/design/kicad/pv", fn), os.path.join(OUTDIR, fn))
    open(OUTDIR + "/fp-lib-table", "w").write(open(W + "/layout/main/fp-lib-table").read())
    print("saved", PCB)


if __name__ == "__main__":
    main()
