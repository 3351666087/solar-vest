"""[layout] Staged routing of the fanned-out V3-F board (lead's method of 2026-11-15, steps 3-4). KiCad python.

Each stage: copy of the current board -> router-only keep-outs -> Specctra DSN whose network keeps only the stage's nets (plus nets that
already carry copper, which the router may complete) -> Freerouting 2.5.0 -> SES import into the current board -> tracks < 0.09 widened ->
every track locked before the next stage. Stages (plate regime of LEAD_NOTES 2e R-2: "closed" = no via over a plate and no L3 / L5 track
over a plate; "open" = both allowed, B.Cu void and the 1 mm dot keep-outs stay):
  1 rf_xtal         RF_50R and XTAL classes                                   open
  2 supply_forb     PWR_HIGH class + VDD_1V8 + GND class (plane pads left)    closed
  3 supply          PWR_LOW class                                             open
  4 analog_forb     ECG / analog classes that are also R-2 forbidden          closed
  5 analog          ECG_PAIR, ECG_ELECTRODE, ECG_LOCAL, PPG_ANALOG, NTC_SENSE, MOHM_KEEPOUT   open
  6 band            the remaining R-2 forbidden nets (ECG-band)               closed
  7 rest            all nets                                                  open
  8 r2fix           forbidden nets that broke R-2 in an open stage: ripped, re-routed   closed
  9 retry           all nets, more passes                                     open (then r2fix again)
Clean start (step 3): the B.Cu void areas (with the dot key-holes) and the U10 island keep-out (with holes at the island vias) are
fractured into hole-free polygons before export, so the router sees no pre-existing violation from them; via_at_smd ON (via in pad,
JLC 6-layer default process: epoxy filled and capped).
usage: kicad-python route_staged.py RUNDIR IN_BASE OUT_BASE [--passes N] [--retry-passes N] [--threads N] [--timeout S] [--from STAGE]
"""
import json, math, os, re, subprocess, sys, time
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import route_layout as RL

MM, TO = pcbnew.FromMM, pcbnew.ToMM
ALLCU = RL.ALLCU


def nc_sets(design):
    NC = json.load(open(design + "/netclasses.json"))["netclasses"]
    g = lambda *ks: set(n for k in ks for n in (NC[k].get("nets") if isinstance(NC.get(k, {}).get("nets"), list) else []))
    return g


def rect_minus(r, boxes):
    """rectangle r = (x0, y0, x1, y1) minus axis-aligned boxes -> list of hole-free rectangles (grid cells merged along x)"""
    xs = sorted({r[0], r[2]} | {min(max(v, r[0]), r[2]) for b in boxes for v in (b[0], b[2])})
    ys = sorted({r[1], r[3]} | {min(max(v, r[1]), r[3]) for b in boxes for v in (b[1], b[3])})
    out = []
    for y0, y1 in zip(ys, ys[1:]):
        run = None
        for x0, x1 in zip(xs, xs[1:]):
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            free = not any(b[0] < cx < b[2] and b[1] < cy < b[3] for b in boxes)
            if free and run is None:
                run = x0
            if not free and run is not None:
                out.append((run, y0, x0, y1)); run = None
        if run is not None:
            out.append((run, y0, xs[-1], y1))
    return [q for q in out if q[2] - q[0] > 1e-6 and q[3] - q[1] > 1e-6]


def rects_area(b, rects, layers, name, vias=False, tracks=False):
    for k, (x0, y0, x1, y1) in enumerate(rects):
        RL.rule_area(b, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layers, "%s_%d" % (name, k), vias=vias, tracks=tracks)


def clean_keepouts(b, G, OX, OY):
    """step 3: hole-free router keep-outs. B.Cu void over each plate minus boxes around the fixed B.Cu copper inside it (dot pads,
    dot stubs, island patch); U10 island via keep-out minus boxes around the island's own vias."""
    plates = {key: G["PLATE_RECT"]["E1" if key == "plate_E1" else "E2"] for key in ("plate_E1", "plate_E2")}
    fixed = []
    for t in b.GetTracks():
        bb = t.GetBoundingBox()
        if t.GetClass() == "PCB_VIA" or t.GetLayer() == pcbnew.B_Cu:
            fixed.append((TO(bb.GetLeft()), TO(bb.GetTop()), TO(bb.GetRight()), TO(bb.GetBottom()), t.GetClass() == "PCB_VIA", t.GetNetname()))
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.IsOnLayer(pcbnew.B_Cu) and not p.IsOnLayer(pcbnew.F_Cu):
                bb = p.GetBoundingBox()
                fixed.append((TO(bb.GetLeft()), TO(bb.GetTop()), TO(bb.GetRight()), TO(bb.GetBottom()), False, p.GetNetname()))
    for z in ZONES:
        if not z.GetIsRuleArea() and z.GetZoneName() == "U10_THERMAL_ISLAND":
            bb = z.GetBoundingBox()
            fixed.append((TO(bb.GetLeft()), TO(bb.GetTop()), TO(bb.GetRight()), TO(bb.GetBottom()), False, "TMP117_ISLAND"))
    for key, pr in plates.items():
        r = (OX + pr[0], OY - pr[3], OX + pr[2], OY - pr[1])
        boxes = [(x0 - (0.05 if isvia else 0.3), y0 - (0.05 if isvia else 0.3), x1 + (0.05 if isvia else 0.3), y1 + (0.05 if isvia else 0.3))
                 for x0, y0, x1, y1, isvia, n in fixed if x1 > r[0] and x0 < r[2] and y1 > r[1] and y0 < r[3]]
        rects_area(b, rect_minus(r, boxes), (pcbnew.B_Cu,), "ROUTER_BVOID_" + key, tracks=True)
    isl = G.get("ZRECTS", {}).get("U10_island")
    if isl:
        r = (OX + isl[0], OY - isl[3], OX + isl[2], OY - isl[1])
        boxes = [(x0 - 0.12, y0 - 0.12, x1 + 0.12, y1 + 0.12) for x0, y0, x1, y1, isvia, n in fixed if isvia and n == "TMP117_ISLAND"]
        rects_area(b, rect_minus(r, boxes), ALLCU, "ROUTER_U10_ISLAND", vias=True)


def filter_network(dsn, keep):
    s = open(dsn).read()
    i0 = s.index("(network"); i1 = s.index("(wiring") if "(wiring" in s else len(s)
    net = s[i0:i1]
    # wires already on the board keep their nets in the network (the router may complete them)
    wired = set(re.findall(r"\(net \"?([^\s\"()]+)\"?\)\(type", s[i1:]))
    keep = set(keep) | wired
    out = []; i = 0; dropped = 0
    while i < len(net):
        m = re.compile(r"\(net \"?([^\s\"()]+)\"?\s*\n").search(net, i)
        if not m:
            out.append(net[i:]); break
        out.append(net[i:m.start()])
        depth = 0; j = m.start()
        while True:
            if net[j] == "(":
                depth += 1
            elif net[j] == ")":
                depth -= 1
                if depth == 0:
                    j += 1; break
            j += 1
        if m.group(1) in keep:
            out.append(net[m.start():j])
        else:
            dropped += 1
        i = j
    net2 = "".join(out)
    # class headers: drop the names of removed nets
    def cls(m):
        toks = m.group(2).split()
        kept = [t for t in toks if t.strip('"') in keep]
        if not kept:
            kept = []
        return "(class " + m.group(1) + (" " + " ".join(kept) if kept else "") + "\n" + m.group(3)
    net2 = re.sub(r"\(class (\S+)((?:\s+[^\s()]+)*)\s*\n(\s*\()", cls, net2)
    open(dsn, "w").write(s[:i0] + net2 + s[i1:])
    return len(keep), dropped


def export_stage(run, pcb_in, tag, keep, closed, G):
    OX, OY = G["KICAD_ORIGIN"]
    b = pcbnew.LoadBoard(pcb_in)
    global ZONES
    ZONES = list(b.Zones())                      # one listing only: SWIG loses the zone type after a board edit in this build
    for z in ZONES:                              # marker areas and the B.Cu voids leave the copper layers (not exported)
        n = z.GetZoneName()
        if z.GetIsRuleArea() and (n.endswith("_AREA") or n.endswith("NOPOUR_L5") or n.endswith("_VOID_BCU")):
            z.SetLayer(pcbnew.User_9)
    clean_keepouts(b, G, OX, OY)
    if closed:
        for key in ("plate_E1", "plate_E2"):
            for pg in G["SKIN"][key]["poly_board"]:
                pts = [(OX + x, OY - y) for x, y in pg]
                RL.rule_area(b, pts, ALLCU, "ROUTER_NO_VIA_" + key, vias=True)
                RL.rule_area(b, pts, (pcbnew.In2_Cu, pcbnew.In4_Cu), "ROUTER_NO_INNER_" + key, tracks=True)
    for t in b.GetTracks():
        t.SetLocked(True)
    dsn = run + "/" + tag + ".dsn"
    if not pcbnew.ExportSpecctraDSN(b, dsn):
        raise SystemExit("DSN export failed")
    RL.fix_dsn(dsn)
    s = open(dsn).read().replace("(via_at_smd off)", "(via_at_smd on)")
    open(dsn, "w").write(s)
    return dsn, filter_network(dsn, keep)


def run_freerouting(run, dsn, tag, passes, threads, timeout):
    ses = run + "/" + tag + ".ses"
    if os.path.exists(ses):
        os.remove(ses)
    cmd = [RL.JAVA, "-Djava.awt.headless=true", "-jar", RL.FR, "-de", dsn, "-do", ses, "-mp", str(passes), "-mt", str(threads),
           "--gui.enabled=false", "--usage_and_diagnostic_data.disable_analytics=true", "--user_data_path=" + run + "/frdata",
           "--logging.console.level=INFO", "-l", "en"]
    t0 = time.time()
    with open(run + "/freerouting_" + tag + ".log", "w") as lf:
        pr = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT)
        try:
            pr.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            pr.kill(); lf.write("\nTIMEOUT after %d s\n" % timeout)
    log = open(run + "/freerouting_" + tag + ".log").read()
    pre = re.search(r"(\d+) unfixable violation", log)
    fin = re.findall(r"\((\d+) unrouted and (\d+) violations\)", log)
    return (ses if os.path.exists(ses) else None), dict(wall_s=round(time.time() - t0), preexisting=int(pre.group(1)) if pre else 0,
                                                       last=fin[-1] if fin else None)


def r2_violators(brd, forb, G):
    OX, OY = G["KICAD_ORIGIN"]
    plates = [[(OX + x, OY - y) for x, y in pg] for key in ("plate_E1", "plate_E2") for pg in G["SKIN"][key]["poly_board"]]
    bad = set()
    for t in brd.GetTracks():
        n = t.GetNetname()
        if n not in forb:
            continue
        if t.GetClass() == "PCB_VIA":
            p = (TO(t.GetPosition().x), TO(t.GetPosition().y))
            if any(RL.inside(p, pl) for pl in plates):
                bad.add(n)
        elif t.GetLayer() in (pcbnew.In2_Cu, pcbnew.In4_Cu):
            a = (TO(t.GetStart().x), TO(t.GetStart().y)); e = (TO(t.GetEnd().x), TO(t.GetEnd().y))
            if any(RL.inside((a[0] + (e[0] - a[0]) * k / 10, a[1] + (e[1] - a[1]) * k / 10), pl) for k in range(11) for pl in plates):
                bad.add(n)
    return bad


PRE = set()
ZONES = []


def tkey(t):
    if t.GetClass() == "PCB_VIA":
        return ("v", t.GetPosition().x, t.GetPosition().y)
    return ("t", t.GetLayer(), t.GetStart().x, t.GetStart().y, t.GetEnd().x, t.GetEnd().y)


def main():
    run, inb, outb = sys.argv[1], sys.argv[2], sys.argv[3]
    arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    passes, rpasses, threads, timeout = int(arg("--passes", "8")), int(arg("--retry-passes", "20")), arg("--threads", "4"), int(arg("--timeout", "2400"))
    G = json.load(open(run + "/geom.json"))["G"]
    g = nc_sets(G["DESIGN"])
    forb = set(json.load(open(run + "/plate_forbidden_nets.json")))
    allnets = None
    cur = run + "/" + inb + ".kicad_pcb"
    proj = run + "/" + inb
    analog = g("ECG_PAIR", "ECG_ELECTRODE", "ECG_LOCAL", "PPG_ANALOG", "NTC_SENSE", "MOHM_KEEPOUT")
    stages = [("rf_xtal", g("RF_50R", "XTAL"), False, passes),
              ("supply_forb", (g("PWR_HIGH") | {"VDD_1V8"} | g("GND")), True, passes),
              ("supply", g("PWR_LOW") - forb, False, passes),
              ("analog_forb", analog & forb, True, passes),
              ("analog", analog - forb, False, passes),
              ("band", set(forb), True, passes),
              ("rest", None, False, passes),
              ("r2fix", "R2", True, passes),
              ("retry", None, False, rpasses),
              ("r2fix2", "R2", True, passes)]
    start = arg("--from", stages[0][0])
    report = json.load(open(run + "/staged_" + outb + ".json")) if os.path.exists(run + "/staged_" + outb + ".json") and start != stages[0][0] else {}
    PRE.update(tkey(t) for t in pcbnew.LoadBoard(run + "/" + inb + ".kicad_pcb").GetTracks())
    go = False
    for name, nets, closed, ps in stages:
        go = go or name == start
        if not go:
            continue
        if arg("--to", None) and report.get("_stop"):
            break                                          # [S2d K-7] one Freerouting stage: --from rest --to rest
        if arg("--to", None) == name:
            report["_stop"] = True
        b0 = pcbnew.LoadBoard(cur)
        if allnets is None:
            allnets = {p.GetNetname() for f in b0.GetFootprints() for p in f.Pads()} - {""}
        if nets == "R2":
            bad = r2_violators(b0, forb, G)
            if not bad:
                report[name] = dict(skipped="no R-2 violation"); continue
            n_rip = 0
            for t in list(b0.GetTracks()):             # rip only the router's copper of the offending nets (fan-out items stay)
                if t.GetNetname() in bad and tkey(t) not in PRE:
                    b0.Remove(t); n_rip += 1
            report[name + "_ripped"] = dict(nets=sorted(bad), items=n_rip)
            ripped = run + "/" + outb + "_" + name + "_in.kicad_pcb"; b0.Save(ripped); cur_in = ripped; nets = bad
        else:
            cur_in = cur
            nets = allnets if nets is None else nets
        tag = outb + "_" + name
        dsn, (nkeep, ndrop) = export_stage(run, cur_in, tag, nets, closed, G)
        ses, info = run_freerouting(run, dsn, tag, ps, threads, timeout)
        info.update(nets_in_network=nkeep, nets_dropped=ndrop, regime="closed" if closed else "open")
        if ses:
            brd = RL.import_ses(cur_in, ses)
            for t in brd.GetTracks():
                t.SetLocked(True)
            cur = run + "/" + tag + ".kicad_pcb"
            brd.Save(cur)
        report[name] = info
        json.dump(report, open(run + "/staged_" + outb + ".json", "w"), indent=1)
        print(name, info, flush=True)
    brd = pcbnew.LoadBoard(cur)
    pcbnew.ZONE_FILLER(brd).Fill(brd.Zones())
    out = run + "/" + outb + ".kicad_pcb"
    brd.Save(out)
    for ext in (".kicad_pro", ".kicad_dru"):
        open(run + "/" + outb + ext, "w").write(open(proj + ext).read().replace(inb + ".kicad_pro", outb + ".kicad_pro"))
    print("routed board saved", out, flush=True)


if __name__ == "__main__":
    main()
