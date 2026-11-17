"""V3-G1 routing trial: DRC (kicad-cli, JLC rule deck of build_board.py) + what is unrouted + vias over the electrode plates + tracks through
the narrow strip beside the motor cut-out.  usage: kicad-python analyze_route.py RUNDIR [routed|placed]
-> RUNDIR/route_summary.json (routed) ; prints a short summary."""
import collections, json, math, os, subprocess, sys
import pcbnew

KCLI = "kicad-cli"
W = "/path/to/SolarVest_work/wristband"
NC = json.load(open(W + "/v3/design/netclasses.json"))["netclasses"]
GND_NETS = set(NC["GND"]["nets"])
# nets behind >= 100 kOhm (v3/design/netclasses.json: MOHM_KEEPOUT hold / divider nodes, NTC_SENSE taps) may have a via over a plate [D PLATE_VOID]
HIZ = set(NC["MOHM_KEEPOUT"]["nets"])


def inside(pt, poly):
    x, y = pt; c = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            c = not c
    return c


def main():
    run = sys.argv[1]; which = sys.argv[2] if len(sys.argv) > 2 else "routed"
    pcb = run + ({"routed": "/v3f_g1_routed.kicad_pcb", "placed": "/v3f_g1.kicad_pcb"}.get(which) or "/%s.kicad_pcb" % which)   # [layout] or a board base name
    geom = json.load(open(run + "/geom.json"))["G"]
    OX, OY = geom["KICAD_ORIGIN"]
    rep = run + "/drc_%s.json" % which
    env = dict(os.environ, KICAD_CONFIG_HOME=os.environ.get("TMPDIR", "/tmp") + "/solarband_kicfg")
    os.makedirs(env["KICAD_CONFIG_HOME"] + "/10.0", exist_ok=True)
    subprocess.run([KCLI, "pcb", "drc", "--refill-zones", "--severity-all", "--format", "json", "--units", "mm", "-o", rep, pcb], capture_output=True, text=True, env=env)
    d = json.load(open(rep))
    cnt = collections.Counter()
    for sect in ("violations", "unconnected_items"):
        for v in d.get(sect, []):
            cnt["%s/%s/%s" % (sect, v["severity"], v["type"])] += 1
    unr = collections.Counter()
    for v in d.get("unconnected_items", []):
        nets = set()
        for i in v["items"]:
            s = i["description"]
            if "[" in s:
                nets.add(s[s.index("[") + 1:s.index("]")])
        unr[",".join(sorted(nets))] += 1
    brd = pcbnew.LoadBoard(pcb)
    plates = [[tuple(p) for p in pg] for key in ("plate_E1", "plate_E2") for pg in geom["SKIN"][key]["poly_board"]]
    FORB = set(json.load(open(run + "/plate_forbidden_nets.json"))) if os.path.exists(run + "/plate_forbidden_nets.json") else set()
    per_plate = {}; forb_bad = []
    vias = collections.Counter(); plate_v = collections.Counter(); length = collections.Counter(); plate_bad = []
    mc, md = geom["MOTOR_CENTER"], geom["MOTOR_CUT_D"]
    strip = collections.Counter(); below = collections.Counter()
    for t in brd.GetTracks():
        net = t.GetNetname()
        if t.GetClass() == "PCB_VIA":
            p = t.GetPosition(); x, y = pcbnew.ToMM(p.x) - OX, OY - pcbnew.ToMM(p.y)
            vias[net] += 1
            for key in ("plate_E1", "plate_E2"):        # [layout] R-3: via count per net over each plate
                if any(inside((x, y), [tuple(q) for q in pg]) for pg in geom["SKIN"][key]["poly_board"]):
                    per_plate.setdefault(key, collections.Counter())[net] += 1
                    if net in FORB:
                        forb_bad.append((key, net, round(x, 2), round(y, 2)))
            if any(inside((x, y), pl) for pl in plates):
                kind = "GND" if net in GND_NETS else "dot-pad electrode net (own plate)" if net in ("E1_PAD", "E1_LINK", "E2_PAD", "E2_LINK") else "TMP117 island" if net == "TMP117_ISLAND" else "R-2 forbidden net (not allowed)" if net in FORB else "R-2 signal (allowed)" if FORB else "high-Z (>= 100 kOhm)" if net in HIZ else "signal / supply (not allowed)"
                plate_v[kind] += 1
                if kind.startswith("signal"):
                    plate_bad.append((net, round(x, 2), round(y, 2)))
        else:
            a, b = t.GetStart(), t.GetEnd()
            ax, ay, bx, by = pcbnew.ToMM(a.x) - OX, OY - pcbnew.ToMM(a.y), pcbnew.ToMM(b.x) - OX, OY - pcbnew.ToMM(b.y)
            ln = brd.GetLayerName(t.GetLayer())
            length[ln] += math.hypot(bx - ax, by - ay)
            if md > 0 and (ax - mc[0]) * (bx - mc[0]) <= 0 and ax != bx:      # crosses the line X = motor centre
                yc = ay + (by - ay) * (mc[0] - ax) / (bx - ax)
                if yc > mc[1] + md / 2:
                    strip[ln] += 1
                elif yc < mc[1] - md / 2 and yc > mc[1] - md / 2 - 6.0:
                    below[ln] += 1
    npads = sum(1 for f in brd.GetFootprints() for p in f.Pads() if p.GetNetCode() > 0)
    res = dict(board=os.path.basename(pcb), drc_counts=dict(cnt), errors=sum(v for k, v in cnt.items() if k.startswith("violations/error")),
               unconnected=sum(v for k, v in cnt.items() if k.startswith("unconnected_items")), unrouted_by_net=dict(unr.most_common()),
               pads_with_net=npads, vias_total=sum(vias.values()), vias_over_plates=dict(plate_v), signal_vias_over_plates=plate_bad, vias_per_net_over_plate={k: dict(v.most_common()) for k, v in per_plate.items()}, forbidden_net_vias_over_plates=forb_bad,
               track_length_mm={k: round(v, 1) for k, v in length.items()},
               tracks_through_the_strip_between_cutout_and_far_edge=dict(strip), tracks_crossing_within_6mm_below_the_cutout=dict(below))
    json.dump(res, open(run + "/route_summary%s.json" % ({"routed": "", "placed": "_placed"}.get(which, "_" + which)), "w"), indent=1)
    print(json.dumps({k: res[k] for k in ("board", "drc_counts", "errors", "unconnected", "vias_total", "vias_over_plates", "track_length_mm",
                                          "tracks_through_the_strip_between_cutout_and_far_edge", "tracks_crossing_within_6mm_below_the_cutout")}, indent=0)[:1500])
    print("unrouted by net:", dict(unr.most_common(40)))
    print("signal vias over plates:", plate_bad[:30])


if __name__ == "__main__":
    main()
