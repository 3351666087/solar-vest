"""V3-G1 routing trial: Specctra DSN export of the built board, Freerouting 2.5.0 (headless), SES import, saved as *_routed.kicad_pcb.
After layout/tools/route_main.py (v1). Every via is filled and capped (JLC POFV). The fan-out of build_board.py is locked.
usage: kicad-python route_board.py RUNDIR [--passes N] [--threads N] [--timeout S] [--import-only] [--fr comma,list,of,extra,freerouting,flags]
Layers for the router: F.Cu, In2.Cu (L3), In4.Cu (L5) and B.Cu carry signals; In1.Cu (L2) and In3.Cu (L4) are GND planes (power layers).
"""
import json, os, re, subprocess, sys, time
import pcbnew

W = "@SVROOT@/wristband"
JAVA = "/opt/homebrew/opt/openjdk/bin/java"
FR = W + "/envs/freerouting/freerouting-2.5.0.jar"


def pofv(v):
    try:
        v.SetFillingMode(pcbnew.FILLING_MODE_FILLED); v.SetCappingMode(pcbnew.CAPPING_MODE_CAPPED)
    except Exception:
        pass


def fix_dsn(path):
    s = open(path).read()
    n = 0
    for ly in ("In1.Cu", "In3.Cu"):
        s, k = re.subn(r'\(layer "?%s"?\s*\(type signal\)' % re.escape(ly), '(layer %s\n      (type power)' % ly, s)
        n += k
    s = s.replace("(via_at_smd off)", "(via_at_smd on)")
    open(path, "w").write(s)
    return n


def main():
    run = sys.argv[1]
    arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
    passes, threads, timeout = arg("--passes", "25"), arg("--threads", "4"), int(arg("--timeout", "2400"))
    pcb = run + "/v3f_g1.kicad_pcb"
    out = run + "/v3f_g1_routed.kicad_pcb"
    dsn, ses = run + "/v3f_g1.dsn", run + "/v3f_g1.ses"
    if "--import-only" not in sys.argv:
        brd = pcbnew.LoadBoard(pcb)
        if not pcbnew.ExportSpecctraDSN(brd, dsn):
            raise SystemExit("DSN export failed")
        print("DSN exported; plane layers set to power:", fix_dsn(dsn), flush=True)
        if os.path.exists(ses):
            os.remove(ses)
        cmd = [JAVA, "-Djava.awt.headless=true", "-jar", FR, "-de", dsn, "-do", ses, "-mp", passes, "-mt", threads,
               "--gui.enabled=false", "--usage_and_diagnostic_data.disable_analytics=true", "--user_data_path=" + run + "/frdata",
               "--logging.console.level=INFO", "-l", "en"] + [x for x in arg("--fr", "").split(",") if x]
        print(" ".join(cmd[3:]), flush=True)
        t0 = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            open(run + "/freerouting.log", "w").write(r.stdout + r.stderr)
        except subprocess.TimeoutExpired as e:
            open(run + "/freerouting.log", "w").write((e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")) +
                                                      (e.stderr.decode() if isinstance(e.stderr, bytes) else (e.stderr or "")) + "\nTIMEOUT after %d s\n" % timeout)
            print("Freerouting timed out after", timeout, "s", flush=True)
        print("Freerouting wall time %.0f s" % (time.time() - t0), flush=True)
    if not os.path.exists(ses):
        raise SystemExit("no SES; see " + run + "/freerouting.log")
    brd = pcbnew.LoadBoard(pcb)
    if not pcbnew.ImportSpecctraSES(brd, ses):
        raise SystemExit("SES import failed")
    nv = nt = 0
    for v in brd.GetTracks():
        if v.GetClass() == "PCB_VIA":
            pofv(v); nv += 1
        else:
            nt += 1
    brd.Save(out)
    for ext in (".kicad_pro", ".kicad_dru"):
        open(run + "/v3f_g1_routed" + ext, "w").write(open(run + "/v3f_g1" + ext).read().replace("v3f_g1.kicad_pro", "v3f_g1_routed.kicad_pro"))
    print("routed board saved", out, "track segments", nt, "vias", nv)


if __name__ == "__main__":
    main()
