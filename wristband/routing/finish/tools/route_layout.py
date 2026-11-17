"""[layout] Signal routing of the fanned-out V3-F board: DSN export, Freerouting 2.5.0 (headless), SES import, zone fill, save.
After route_board.py (G1) / layout/tools/route_main.py (v1).

DSN is exported from a copy of the board that carries router-only keep-outs; the SES is imported into the real board. In1.Cu (GND) and
In3.Cu (VDD_1V8) are power layers; via_at_smd stays OFF (no via in an SMD pad); router vias 0.35 / 0.15 (project file: the 0.10 copper
clearance then also meets JLC's 0.20 hole-to-copper rule); tracks the router necks below 0.09 mm are widened to 0.09 after import.
Router-only keep-outs: no via of another net on the U10 island (T-5).

Plate regime (LEAD_NOTES 2e R-2), with --plates-open (board built with build_board.py --plates-open):
  stage 1  plates open for vias and for L3 / L5 tracks (B.Cu void and the 1 mm dot keep-outs stay);
  then     every net of plate_forbidden_nets.json (PWR_HIGH, VDD_1V8, ECG-band) that got a via over a plate or an L3 / L5 track over a
           plate is ripped up (its unlocked tracks and vias), every other track is locked;
  stage 2  the ripped nets are re-routed with no via over the plates and no L3 / L5 track over the plates.
Without --plates-open: one stage with no via over the plates (the r1 regime).
usage: kicad-python route_layout.py RUNDIR IN_BASE OUT_BASE [--plates-open] [--passes N] [--threads N] [--timeout S] [--fr a,b]
"""
import json, math, os, re, subprocess, sys, time
import pcbnew

W = "/path/to/SolarVest_work/wristband"
JAVA = "/opt/homebrew/opt/openjdk/bin/java"
FR = W + "/envs/freerouting/freerouting-2.5.0.jar"
MM, TO = pcbnew.FromMM, pcbnew.ToMM
ALLCU = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.In3_Cu, pcbnew.In4_Cu, pcbnew.B_Cu)


def pofv(v):
    v.SetFillingMode(pcbnew.FILLING_MODE_FILLED); v.SetCappingMode(pcbnew.CAPPING_MODE_CAPPED)


def fix_dsn(path):
    s = open(path).read()
    n = 0
    for ly in ("In1.Cu", "In3.Cu"):
        s, k = re.subn(r'\(layer "?%s"?\s*\(type signal\)' % re.escape(ly), '(layer %s\n      (type power)' % ly, s)
        n += k
    s = s.replace("(via_at_smd on)", "(via_at_smd off)")
    open(path, "w").write(s)
    return n


def rule_area(b, pts, layers, name, vias=False, tracks=False):
    z = pcbnew.ZONE(b); ls = pcbnew.LSET()
    for l in layers:
        ls.AddLayer(l)
    z.SetLayerSet(ls); z.SetIsRuleArea(True); z.SetDoNotAllowVias(vias); z.SetDoNotAllowTracks(tracks)
    z.SetDoNotAllowZoneFills(False); z.SetDoNotAllowPads(False); z.SetDoNotAllowFootprints(False); z.SetZoneName(name)
    for x, y in pts:
        z.AppendCorner(pcbnew.VECTOR2I(MM(x), MM(y)), -1)
    b.Add(z)


def inside(p, poly):
    x, y = p; c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def run_fr(run, pcb_in, tag, passes, threads, timeout, extra, plates_closed, G):
    OX, OY = G["KICAD_ORIGIN"]
    b = pcbnew.LoadBoard(pcb_in)
    for z in list(b.Zones()):                      # marker / R-2 areas without router meaning are not exported
        if z.GetIsRuleArea() and (z.GetZoneName().endswith("_AREA") or z.GetZoneName().startswith("PLATE_E") and z.GetZoneName().endswith("NOPOUR_L5")):
            b.Remove(z)
    isl = G.get("ZRECTS", {}).get("U10_island")
    if isl:
        rule_area(b, [(OX + isl[0], OY - isl[1]), (OX + isl[2], OY - isl[1]), (OX + isl[2], OY - isl[3]), (OX + isl[0], OY - isl[3])],
                  ALLCU, "ROUTER_U10_ISLAND", vias=True)
    if plates_closed:
        for key in ("plate_E1", "plate_E2"):
            for pg in G["SKIN"][key]["poly_board"]:
                pts = [(OX + x, OY - y) for x, y in pg]
                rule_area(b, pts, ALLCU, "ROUTER_NO_VIA_" + key, vias=True)
                rule_area(b, pts, (pcbnew.In2_Cu, pcbnew.In4_Cu), "ROUTER_NO_INNER_" + key, tracks=True)
    dsn, ses = run + "/" + tag + ".dsn", run + "/" + tag + ".ses"
    if not pcbnew.ExportSpecctraDSN(b, dsn):
        raise SystemExit("DSN export failed")
    print(tag, "DSN exported; power layers:", fix_dsn(dsn), flush=True)
    if os.path.exists(ses):
        os.remove(ses)
    cmd = [JAVA, "-Djava.awt.headless=true", "-jar", FR, "-de", dsn, "-do", ses, "-mp", passes, "-mt", threads,
           "--gui.enabled=false", "--usage_and_diagnostic_data.disable_analytics=true", "--user_data_path=" + run + "/frdata",
           "--logging.console.level=INFO", "-l", "en"] + extra
    t0 = time.time()
    with open(run + "/freerouting_" + tag + ".log", "w") as lf:
        pr = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT)
        try:
            pr.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pr.kill(); lf.write("\nTIMEOUT after %d s\n" % timeout); print("Freerouting timed out", flush=True)
    print(tag, "Freerouting wall time %.0f s" % (time.time() - t0), flush=True)
    if not os.path.exists(ses):
        raise SystemExit("no SES for " + tag)
    return ses


def import_ses(pcb_in, ses):
    brd = pcbnew.LoadBoard(pcb_in)
    if not pcbnew.ImportSpecctraSES(brd, ses):
        raise SystemExit("SES import failed")
    nw = 0
    for t in brd.GetTracks():
        if t.GetClass() == "PCB_VIA":
            pofv(t)
        elif t.GetWidth() < MM(0.09):
            t.SetWidth(MM(0.09)); nw += 1
    print("tracks widened to 0.09 mm:", nw, flush=True)
    return brd


def main():
    run, inb, outb = sys.argv[1], sys.argv[2], sys.argv[3]
    arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    passes, threads, timeout = arg("--passes", "20"), arg("--threads", "4"), int(arg("--timeout", "3600"))
    extra = [x for x in arg("--fr", "").split(",") if x]
    opened = "--plates-open" in sys.argv
    G = json.load(open(run + "/geom.json"))["G"]; OX, OY = G["KICAD_ORIGIN"]
    pcb = run + "/" + inb + ".kicad_pcb"
    ses = run_fr(run, pcb, outb + "_s1", passes, threads, timeout, extra, not opened, G)
    brd = import_ses(pcb, ses)
    rip = {}
    if opened:
        forb = set(json.load(open(run + "/plate_forbidden_nets.json")))
        plates = [[(OX + x, OY - y) for x, y in pg] for key in ("plate_E1", "plate_E2") for pg in G["SKIN"][key]["poly_board"]]
        bad = set()
        for t in brd.GetTracks():
            n = t.GetNetname()
            if n not in forb or t.IsLocked():
                continue
            if t.GetClass() == "PCB_VIA":
                p = (TO(t.GetPosition().x), TO(t.GetPosition().y))
                if any(inside(p, pl) for pl in plates):
                    bad.add(n)
            elif t.GetLayer() in (pcbnew.In2_Cu, pcbnew.In4_Cu):
                a = (TO(t.GetStart().x), TO(t.GetStart().y)); e = (TO(t.GetEnd().x), TO(t.GetEnd().y))
                for k in range(11):
                    q = (a[0] + (e[0] - a[0]) * k / 10, a[1] + (e[1] - a[1]) * k / 10)
                    if any(inside(q, pl) for pl in plates):
                        bad.add(n); break
        for t in list(brd.GetTracks()):
            if t.GetNetname() in bad and not t.IsLocked():
                rip[t.GetNetname()] = rip.get(t.GetNetname(), 0) + 1
                brd.Remove(t)
            else:
                t.SetLocked(True)
        print("stage 2: ripped nets", sorted(rip), flush=True)
        mid = run + "/" + outb + "_s1.kicad_pcb"
        brd.Save(mid)
        for ext in (".kicad_pro", ".kicad_dru"):
            open(run + "/" + outb + "_s1" + ext, "w").write(open(run + "/" + inb + ext).read().replace(inb + ".kicad_pro", outb + "_s1.kicad_pro"))
        if bad:
            ses2 = run_fr(run, mid, outb + "_s2", passes, threads, timeout, extra, True, G)
            brd = import_ses(mid, ses2)
    pcbnew.ZONE_FILLER(brd).Fill(brd.Zones())
    out = run + "/" + outb + ".kicad_pcb"
    brd.Save(out)
    for ext in (".kicad_pro", ".kicad_dru"):
        s = open(run + "/" + inb + ext).read().replace(inb + ".kicad_pro", outb + ".kicad_pro")
        open(run + "/" + outb + ext, "w").write(s)
    nv = sum(1 for t in brd.GetTracks() if t.GetClass() == "PCB_VIA")
    json.dump(dict(ripped=rip, vias=nv), open(run + "/route_" + outb + ".json", "w"), indent=1)
    print("routed board saved", out, "vias", nv, flush=True)


if __name__ == "__main__":
    main()
