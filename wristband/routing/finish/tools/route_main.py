"""Route the SolarBand main board: pre-placed fan-out vias (WLP inner balls, QFN/WSON exposed pads), Specctra DSN
export, Freerouting 2.5.0 (headless), SES import. Every via is IPC-4761 type VII (filled + capped = JLC POFV).

usage: kicad-python route_main.py [--passes N] [--no-route]
Layer use for the router: L1 (F.Cu), L3 (In2) and L6 (B.Cu) carry signals; L2/L5 are GND planes and L4 the
VDD_1V8 plane (declared as power layers to Freerouting). L6 tracks stay out of X < 16.5, Y < 8.5 (IFA ground edge).
"""
import json, os, re, subprocess, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lgeom as G
from build_main import V, MM, OX, OY, poly_zone, rect_pts, CU

W = G.W
PCB = W + "/layout/main/solarband_main.kicad_pcb"
RUN = W + "/layout/work/route_v1"
JAVA = "/opt/homebrew/opt/openjdk/bin/java"
FR = W + "/envs/freerouting/freerouting-2.5.0.jar"

# fan-out vias placed before routing: ref -> list of (pad or local offset, drill, dia)
EP_VIAS = {"U6": [(-1.2, -1.2), (0, -1.2), (1.2, -1.2), (-1.2, 0), (0, 0), (1.2, 0), (-1.2, 1.2), (0, 1.2), (1.2, 1.2)],
           "U7": [(-0.7, -0.7), (0.7, -0.7), (-0.7, 0.7), (0.7, 0.7)],
           "U1": [(-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5)],
           "U2": [(0, -0.45), (0, 0.45)], "U11": [(-0.45, 0), (0.45, 0)]}
BGA_VIA_BALLS = {"U8": ["B2", "C2", "C3", "C4"]}


def pofv(v):
    v.SetFillingMode(pcbnew.FILLING_MODE_FILLED)
    v.SetCappingMode(pcbnew.CAPPING_MODE_CAPPED)


def add_via_at(brd, net, pos, drill, dia):
    v = pcbnew.PCB_VIA(brd)
    v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetPosition(pos); v.SetDrill(MM(drill)); v.SetWidth(MM(dia))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(net); pofv(v)
    brd.Add(v)
    return v


def fanout(brd):
    n = 0
    for ref, offs in EP_VIAS.items():
        f = brd.FindFootprintByReference(ref)
        ep = max((p for p in f.Pads() if p.GetNetname() == "GND"), key=lambda p: p.GetBoundingBox().GetArea())
        c = ep.GetPosition()
        bb = ep.GetBoundingBox()
        swap = len(offs) == 2 and (bb.GetWidth() > bb.GetHeight()) != (abs(offs[0][0]) > abs(offs[0][1]))
        for dx, dy in offs:
            if swap:
                dx, dy = dy, dx
            add_via_at(brd, ep.GetNet(), pcbnew.VECTOR2I(c.x + MM(dx), c.y + MM(dy)), 0.2, 0.4)
            n += 1
    for ref, balls in BGA_VIA_BALLS.items():
        f = brd.FindFootprintByReference(ref)
        for p in f.Pads():
            if p.GetNumber() in balls and p.GetNetCode() > 0:
                add_via_at(brd, p.GetNet(), p.GetPosition(), 0.15, 0.25)
                n += 1
    for v in brd.GetTracks():
        if v.GetClass() == "PCB_VIA":
            pofv(v)
    return n


def l6_router_keepout(brd):
    """keep L6 traces away from the IFA ground edge (X < 16.5, Y < 8.5) - tracks only, pour allowed"""
    poly_zone(brd, rect_pts(-1, 5.5, 16.5, 8.5), [CU["B"]], rule=True, name="L6_IFA_EDGE_NOTRACK", tracks=True)


def fix_dsn(path):
    s = open(path).read()
    # planes: L2/L5 GND and L4 VDD_1V8 are power layers for the router
    for ly in ("L2_GND", "L4_PWR", "L5_GND"):
        s = re.sub(r'\(layer %s\s*\(type signal\)' % re.escape(ly), '(layer %s\n      (type power)' % ly, s)
    s = s.replace("(via_at_smd off)", "(via_at_smd on)")
    open(path, "w").write(s)
    return s


def main():
    passes = sys.argv[sys.argv.index("--passes") + 1] if "--passes" in sys.argv else "60"
    os.makedirs(RUN, exist_ok=True)
    brd = pcbnew.LoadBoard(PCB)
    if not any(z.GetZoneName() == "L6_IFA_EDGE_NOTRACK" for z in brd.Zones()):
        l6_router_keepout(brd)
    nv = fanout(brd)
    print("fan-out vias", nv)
    brd.Save(PCB)
    if "--no-route" in sys.argv:
        return
    dsn, ses = RUN + "/main.dsn", RUN + "/main.ses"
    if not pcbnew.ExportSpecctraDSN(brd, dsn):
        raise SystemExit("DSN export failed")
    fix_dsn(dsn)
    cmd = [JAVA, "-Djava.awt.headless=true", "-jar", FR, "-de", dsn, "-do", ses, "-mp", passes, "-mt", "8",
           "--gui.enabled=false", "--usage_and_diagnostic_data.disable_analytics=true",
           "--user_data_path=" + RUN + "/frdata", "--logging.console.level=INFO", "-l", "en"]
    print(" ".join(cmd[3:]), flush=True)
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=7200)
    open(RUN + "/freerouting.log", "w").write(r.stdout + r.stderr)
    if not os.path.exists(ses):
        raise SystemExit("no SES; see " + RUN + "/freerouting.log")
    brd = pcbnew.LoadBoard(PCB)
    if not pcbnew.ImportSpecctraSES(brd, ses):
        raise SystemExit("SES import failed")
    for v in brd.GetTracks():
        if v.GetClass() == "PCB_VIA":
            pofv(v)
    brd.Save(PCB)
    print("routed + saved", PCB)


if __name__ == "__main__":
    main()
