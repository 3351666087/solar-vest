"""cplgate: CPL placement gate (research/cpl-placement-gate.md §6, stages G0, G1, G3-G6, G9; G7 is g7_verify.py,
G8 is mutate.py). No network: EasyEDA footprints and symbols come from v3/design/lib (cached conversions).

usage: python cplgate.py --board B.kicad_pcb --pos kicad_pos.csv --out OUTDIR/gate [--waivers waivers.yaml]
                         [--easyeda-override REF=path.kicad_mod ...]   (mutation tests only)
exit: 0 every JLC-placed part GREEN (or waived YELLOW); 1 any RED / UNKNOWN / unwaived YELLOW; 2 infrastructure failure.
"""
import argparse, csv, glob, json, math, os, re, sys, time
from shapely.geometry import Point, Polygon, box
from shapely import affinity

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pk  # noqa: E402

PASSIVE = re.compile(r"^(R|C|L|FB)\d")
POLAR_KINDS = {"diode", "led", "photodiode", "tantalum", "electrolytic", "tvs_uni", "zener", "schottky"}
CATHODE = {"K", "C", "CATHODE", "KA", "-"}
ANODE = {"A", "ANODE", "+"}
ALIAS = {"VSS": "GND", "GNDPAD": "GND", "PGND": "GND", "VEE": "GND", "V-": "GND",  # VEE / V-: negative-rail pin of single-supply op-amps
         # and comparators, which EasyEDA names GND (TLV7031 C2863637 pin 2, TI "V-"; added 2026-11-16 for the final package)
"DNC": "NC", "N.C.": "NC", "NC": "NC",
         "CATHODE": "K", "C": "K", "KA": "K", "CC": "K", "ANODE": "A",
         "THERMALPAD": "EP", "EPAD": "EP", "PAD": "EP", "EXPOSEDPAD": "EP"}
NONPOLAR = {None, "none", "tvs_bi"}  # C = cathode is safe here: no BJT is JLC-placed
CRIT = re.compile(r"(VDD|VCC|VIN|VBAT|VOUT|VSYS|GND|VSS|OUT|VBUS|VREG|VDDA|DCC|DEC)")


# ---------------------------------------------------------------- geometry helpers (footprint frame, Y down)
def pad_poly(p, dx=0.0, dy=0.0, th=0.0, mirror=False):
    """Pad outline after an optional mirror (x -> -x), KiCad rotation th and translation."""
    x, y = p["x"], p["y"]
    if p.get("prim") is not None:
        g = p["prim"]
    elif p["shape"] == "circle":
        g = Point(0, 0).buffer(p["w"] / 2, 16)
    else:
        g = box(-p["w"] / 2, -p["h"] / 2, p["w"] / 2, p["h"] / 2)
    g = affinity.rotate(g, -p["rot"], origin=(0, 0))  # KiCad angle is CCW on screen = CW in Y-down maths
    g = affinity.translate(g, x, y)
    if mirror:
        g = affinity.scale(g, -1, 1, origin=(0, 0))
    g = affinity.rotate(g, -th, origin=(0, 0))
    return affinity.translate(g, dx, dy)


def centroids(pads):
    g = {}
    for p in pads:
        g.setdefault(p["num"], []).append((p["x"], p["y"]))
    return {n: (sum(a for a, _ in v) / len(v), sum(b for _, b in v) / len(v)) for n, v in g.items()}


def tf(pt, th, mirror=False):
    x, y = pt
    if mirror:
        x = -x
    return pk.rot((x, y), th)


def scan(K, E, mirror=False):
    common = [n for n in K if n in E]
    res = []
    if len(common) < 2:
        return common, res
    for th in (0, 90, 180, 270):
        pe = {n: tf(E[n], th, mirror) for n in common}
        dx = sum(K[n][0] - pe[n][0] for n in common) / len(common)
        dy = sum(K[n][1] - pe[n][1] for n in common) / len(common)
        e = math.sqrt(sum((pe[n][0] + dx - K[n][0]) ** 2 + (pe[n][1] + dy - K[n][1]) ** 2 for n in common) / len(common))
        res.append((e, th, dx, dy))
    return common, sorted(res)


def kabsch_deg(K, E, common):
    kc = [K[n] for n in common]; ec = [E[n] for n in common]
    kx = sum(p[0] for p in kc) / len(kc); ky = sum(p[1] for p in kc) / len(kc)
    ex = sum(p[0] for p in ec) / len(ec); ey = sum(p[1] for p in ec) / len(ec)
    s_dot = sum((a[0] - ex) * (b[0] - kx) + (a[1] - ey) * (b[1] - ky) for a, b in zip(ec, kc))
    s_crs = sum((a[0] - ex) * (b[1] - ky) - (a[1] - ey) * (b[0] - kx) for a, b in zip(ec, kc))
    phi = math.degrees(math.atan2(s_crs, s_dot))  # maths angle in the Y-down frame
    return (-phi) % 360  # KiCad convention


def shape_scan(Kp, Ep):
    """Name-blind fit by copper overlap (used when < 2 pad numbers are shared)."""
    ku = None
    for p in Kp:
        ku = pad_poly(p) if ku is None else ku.union(pad_poly(p))
    kc = ku.centroid
    res = []
    for th in (0, 90, 180, 270):
        eu = None
        for p in Ep:
            eu = pad_poly(p, th=th) if eu is None else eu.union(pad_poly(p, th=th))
        ec = eu.centroid
        eu = affinity.translate(eu, kc.x - ec.x, kc.y - ec.y)
        iou = eu.intersection(ku).area / max(eu.union(ku).area, 1e-9)
        res.append((1 - iou, th, kc.x - tf((0, 0), th)[0] - ec.x, kc.y - tf((0, 0), th)[1] - ec.y))
    return sorted(res)


def symmetry_order(pads):
    """How many of the 4 right-angle turns map the copper (centres and pad sizes) onto itself, ignoring numbers."""
    def eff(p):
        w, h = round(p["w"], 3), round(p["h"], 3)
        return (w, h) if p["shape"] == "circle" or round(p["rot"]) % 180 == 0 else (h, w)
    pts = [(p["x"], p["y"], eff(p)) for p in pads]
    cx = sum(p[0] for p in pts) / len(pts); cy = sum(p[1] for p in pts) / len(pts)
    n = 0
    for th in (0, 90, 180, 270):
        ok = True
        for x, y, (w, h) in pts:
            rx, ry = pk.rot((x - cx, y - cy), th)
            tw, th_ = (h, w) if th % 180 else (w, h)
            if not any(abs(rx - (a - cx)) < 0.03 and abs(ry - (b - cy)) < 0.03 and abs(tw - c[0]) < 0.011 and abs(th_ - c[1]) < 0.011
                       for a, b, c in pts):
                ok = False; break
        n += ok
    return n


def min_pitch(pads):
    c = [(p["x"], p["y"]) for p in pads]
    d = [math.hypot(a[0] - b[0], a[1] - b[1]) for i, a in enumerate(c) for b in c[i + 1:]]
    d = [v for v in d if v > 1e-6]
    return min(d) if d else 1.0


def norm(n, pin=None, easyeda=False):
    """Canonical pin name; None when the source gives no real name (the name is just the pin number)."""
    n = (n or "").upper().replace("~", "").replace("{", "").replace("}", "").replace("OVERLINE", "")
    n = re.sub(r"[^A-Z0-9+\-./]", "", n)
    if len(n) > 1:
        n = n.lstrip("/")  # active-low marker, dropped by some sources
    if easyeda:
        n = re.sub(r"^\d+(?=[A-Z])", "", n)  # EasyEDA symbols sometimes prefix the package pin number
    if not n or n == str(pin) or re.fullmatch(r"\d+", n):
        return None
    return ALIAS.get(n, n)


def same_name(vals):
    """Names agree when equal, or when one is the other without a trailing index (A ~ A1) and has no digits itself."""
    v = sorted(set(vals), key=len)
    base = v[0]
    return all(x == base or (not re.search(r"\d", base) and re.fullmatch(re.escape(base) + r"\d+", x)) for x in v)


def silk_mass(gfx, axis_x=True):
    """Signed silk asymmetry along the pad axis (EasyEDA footprint frame): returns (signed, total)."""
    s = t = 0.0
    for g in gfx:
        if "Silk" not in g["layer"]:
            continue
        pts = g["pts"]
        if g["kind"] == "fp_circle":
            m = math.pi * max(g.get("r", 0), g["width"] / 2) ** 2 * 4; c = pts[0]
        elif g["kind"] == "fp_poly" and len(pts) >= 3:
            poly = Polygon(pts); m = abs(poly.area) * 4; c = (poly.centroid.x, poly.centroid.y)
        else:
            m = math.hypot(pts[-1][0] - pts[0][0], pts[-1][1] - pts[0][1]) * max(g["width"], 0.1)
            c = (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))
        v = c[0] if axis_x else c[1]
        s += m * (1 if v > 0.02 else -1 if v < -0.02 else 0); t += m
    return s, t


def silk_dots(gfx):
    return [g["pts"][0] for g in gfx if "Silk" in g["layer"] and g["kind"] == "fp_circle"]


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", required=True); ap.add_argument("--pos", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--waivers", default=None); ap.add_argument("--design", default=pk.DESIGN)
    ap.add_argument("--easyeda-override", action="append", default=[])
    ap.add_argument("--no-render", action="store_true")
    ap.add_argument("--preview-rules", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "preview_rules.yaml"))
    a = ap.parse_args()
    prules = pk.load_yaml(a.preview_rules) if a.preview_rules and os.path.exists(a.preview_rules) else {}
    D = a.design; os.makedirs(a.out, exist_ok=True)
    over = dict(s.split("=", 1) for s in a.easyeda_override)
    board_reds, board_notes = [], []

    # G0 inputs frozen
    bdir = os.path.dirname(os.path.abspath(a.board))
    locks = [f for f in os.listdir(bdir) if f.endswith(".lck") or "autosave" in f.lower() or f.startswith("~")]
    if locks:
        board_reds.append(f"G0: KiCad lock/autosave files beside the board: {locks}")
    g0 = dict(board=os.path.abspath(a.board), board_sha256=pk.sha256(a.board),
              design_inputs={f: pk.sha256(os.path.join(D, f)) for f in ("BOM_v3f.csv", "BOM_full_v3f.csv", "parts.json",
                                                                         "placement_proof.json", "netlist/solarband_v3f_kicad.net")},
              run_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

    B = pk.load_board(a.board); F = B["footprints"]; ox, oy = B["aux_origin"]
    full = pk.bom_full(os.path.join(D, "BOM_full_v3f.csv"))
    jbom = pk.read_csv(os.path.join(D, "BOM_v3f.csv"))
    nl = pk.load_netlist_pins(os.path.join(D, "netlist", "solarband_v3f_kicad.net"))
    syms = pk.load_sym_pins(os.path.join(D, "lib", "easyeda.kicad_sym"))
    idx = json.load(open(os.path.join(D, "lib", "easyeda_index.json")))
    pmaps = {os.path.basename(f)[:-5]: pk.load_yaml(f) for f in glob.glob(os.path.join(D, "pinmap", "C*.yaml"))}
    proof = {r["ref"]: r for r in json.load(open(os.path.join(D, "placement_proof.json")))["parts"]}
    waivers = (pk.load_yaml(a.waivers) or {}).get("waivers", []) if a.waivers and os.path.exists(a.waivers) else []
    # pads the reviewed-footprint manifest deletes on purpose, with a written datasheet reason (e.g. SW1 pad 5, review D-9)
    deleted = {}
    mf = os.path.join(D, "lib", "easyeda_rev_manifest.json")
    if os.path.exists(mf):
        for name, ent in json.load(open(mf)).get("footprints", {}).items():
            for ch in ent.get("changes", []):
                m = re.match(r"COPPER: pad (\S+) deleted .*?; (.+)", ch)
                if m:
                    deleted.setdefault(name[:-10], {})[m.group(1)] = m.group(2)[:160]

    # G1 inventory and consistency
    S = sorted(r for r, x in full.items() if x["Class"] == "JLC-placed")
    bom_refs = sorted(d.strip() for r in jbom for d in r["Designator"].split(","))
    if S != bom_refs:
        board_reds.append(f"G1: BOM_v3f designators != JLC-placed set: only BOM {sorted(set(bom_refs) - set(S))}, only set {sorted(set(S) - set(bom_refs))}")
    missing = [r for r in S if r not in F]
    if missing:
        board_reds.append(f"G1: JLC-placed parts missing on the board: {missing}")
    extra = [r for r in F if r not in full]
    if extra:
        board_reds.append(f"G1: board footprints not in BOM_full_v3f: {extra}")
    for r, fp in F.items():  # non-JLC footprints must not reach the CPL
        if r not in S and r in full and "exclude_from_pos_files" not in fp["attrs"] and "dnp" not in fp["attrs"] and fp["pads"]:
            board_notes.append(f"G1: {r} ({full[r]['Class']}) is not JLC-placed but has no exclude_from_pos_files / dnp attribute; the gate leaves it out of the CPL")
    pos = {}
    for row in csv.DictReader(open(a.pos)):
        pos.setdefault(row["Ref"], row)
    g1_diff = []
    for r in S:
        if r not in F:
            continue
        fp = F[r]; q = pos.get(r)
        if q is None:
            g1_diff.append(f"{r}: absent from kicad-cli pos export"); continue
        px, py = fp["x"] - ox, -(fp["y"] - oy)
        dr = (float(q["Rot"]) - fp["rot"]) % 360
        if abs(float(q["PosX"]) - px) > 1e-3 or abs(float(q["PosY"]) - py) > 1e-3 or min(dr, 360 - dr) > 0.01 or q["Side"] != fp["side"]:
            g1_diff.append(f"{r}: parser ({px:.4f},{py:.4f},{fp['rot']},{fp['side']}) vs kicad-cli ({q['PosX']},{q['PosY']},{q['Rot']},{q['Side']})")
    if g1_diff:
        board_reds.append("G1: parser != kicad-cli pos export: " + "; ".join(g1_diff))

    # board annotation (R1 / R2 substitutes) and net cross-check against the schematic netlist
    if not any("LCSC" in fp["props"] for fp in F.values()):
        board_notes.append("R1: the board file carries no LCSC field; the gate takes the C-number from BOM_full_v3f.csv and checks it against the footprint name")
    net_diff = []
    for r in S:
        if r not in F:
            continue
        for p in F[r]["pads"]:
            if not p["num"] or p["type"] == "np_thru_hole":
                continue
            want = nl.get((r, p["num"]))
            if want and p["net"] and want[0] != p["net"]:
                if want[0].startswith("unconnected-"):
                    board_notes.append(f"G1: {r}.{p['num']} is unconnected in the netlist and on board net {p['net']} (deliberate board-only net, e.g. R-5 island)")
                    continue
                net_diff.append(f"{r}.{p['num']}: board {p['net']} netlist {want[0]}")
    if net_diff:
        board_reds.append(f"G1: board pad nets differ from the netlist ({len(net_diff)}): " + "; ".join(net_diff[:12]))
    board_notes.append("R2: the board pads carry no pinfunction; the gate reads pin functions from v3/design/netlist/solarband_v3f_kicad.net "
                       f"(pad nets on the board agree with that netlist: {'yes' if not net_diff else 'NO'})")

    parts, rows_cpl = [], []
    for r in S:
        try:
            if r not in F:
                continue
            fp = F[r]; info = full[r]; lc = info["LCSC"]
            red, yel, notes = [], [], []
            P = dict(ref=r, lcsc=lc, value=info["Value"], mpn=info["MPN"], fpid=fp["fpid"], side=fp["side"],
                     kicad_rot=fp["rot"], anchor=(round(fp["x"] - ox, 4), round(-(fp["y"] - oy), 4)),
                     proof_class=proof.get(r, {}).get("proof_class", "-"))
            # R1 substitute
            fpc = fp["fpid"].split(":")[1].split("_")[0]
            if not re.match(r"^C\d+$", lc):
                red.append("R1: no C-number")
            elif fpc != lc:
                notes.append(f"R1: board land is {fpc}'s footprint, the part is {lc}")
            if "exclude_from_pos_files" in fp["attrs"]:
                red.append("R6: exclude_from_pos_files on a JLC-placed part")
            if fp["rot"] % 90 > 1e-6 and not any(w.get("ref") == r and w.get("rule") == "R7" for w in waivers):
                red.append(f"R7: rotation {fp['rot']:.1f} deg is not a multiple of 90 (no waiver)")
            if fp["side"] == "bottom":
                red.append("R3: JLC-placed on the bottom side and no bottom canary verified within 60 days (§6.6)")
            # G2 (offline): EasyEDA footprint for this C-number
            ep_path = over.get(r) or pk.easyeda_fp_path(lc)
            if not ep_path:
                red.append(f"R8/G2: no EasyEDA footprint for {lc} in v3/design/lib/easyeda.pretty (not fetched: offline gate)")
                P.update(verdict="RED", red=red, yellow=yel, notes=notes); parts.append(P); continue
            P["easyeda_fp"] = os.path.basename(ep_path)
            bound = idx.get(lc, {}).get("footprint", "").split(":")[-1]
            if os.path.basename(ep_path).split("_")[0] != lc or (bound and os.path.basename(ep_path)[:-10] != bound):
                red.append(f"G2 binding: footprint file {os.path.basename(ep_path)} is not {lc}'s EasyEDA footprint ({bound or 'not in easyeda_index.json'})")
            if idx.get(lc, {}).get("proxy_of") and r not in over:
                red.append(f"PROXY: no EasyEDA record for {lc}; the fit and the CPL use the labelled proxy land of {idx[lc]['proxy_of']} "
                           f"({os.path.basename(ep_path)}); JLC's own 0 deg for {lc} is unknown")
            P["easyeda_fp_sha256"] = pk.sha256(ep_path)
            EM = pk.load_mod(ep_path)
            Kp = [p for p in pk.board_to_local(fp) if p["num"] and p["type"] != "np_thru_hole"]
            Ep = [p for p in EM["pads"] if p["num"] and p["type"] != "np_thru_hole"]
            P["pads"] = dict(kicad=len(Kp), easyeda=len(Ep))
            K, E = centroids(Kp), centroids(Ep)
            sym = symmetry_order(Kp); P["sym_order"] = sym
            common, res = scan(K, E)
            _, resm = scan(K, E, mirror=True)
            method = "pad-number pairing + Kabsch + discrete scan"
            if len(common) >= 2:
                th_raw = kabsch_deg(K, E, common); P["theta_raw"] = round(th_raw, 3)
                if min(th_raw % 90, 90 - th_raw % 90) > 1.0:
                    red.append(f"G4: theta_raw {th_raw:.2f} deg is not within 1 deg of a multiple of 90")
                err, th, dx, dy = res[0]; margin = res[1][0] - err
                if resm and resm[0][0] * 10 < err and err > 0.02:
                    red.append(f"G4: mirrored fit {resm[0][0]:.3f} beats plain {err:.3f} by 10x: numbering mirrored")
            else:
                method = "name-blind copper overlap (fewer than 2 shared pad numbers)"
                sr = shape_scan(Kp, Ep); err, th, dx, dy = sr[0]; margin = sr[1][0] - err
                if margin < 0.05:
                    P.update(theta=th)
                    red.append(f"UNKNOWN: {len(common)} shared pad number(s); copper fits at {th} and {sr[1][1]} deg alike: geometry cannot decide (JLC preview + waiver)")
            P.update(theta=th, rms=round(err, 4), margin=round(margin, 4), method=method, offset_local=(round(dx, 4), round(dy, 4)))
            mp = min_pitch(Kp)
            kmin = min(min(p["w"], p["h"]) for p in Kp)
            if len(common) >= 2 and err > 0.4 * kmin:
                red.append(f"G4: pitch: numbered fit rms {err:.3f} mm > 0.4 x smallest KiCad pad dimension {kmin:.3f} mm")
            # fit grade by overlap
            bad, tight, big = [], [], []
            kpolys = {}
            for p in Kp:
                kpolys.setdefault(p["num"], []).append(p)
            unpaired_e = [p["num"] for p in Ep if p["num"] not in kpolys]
            dl = deleted.get(fp["fpid"].split(":", 1)[1], {})
            for n in sorted(set(unpaired_e) & set(dl)):
                notes.append(f"G4: EasyEDA pad {n} has no board pad: deleted on purpose in easyeda_rev_manifest.json ({dl[n]})")
            unpaired_e = [n for n in unpaired_e if n not in dl]
            unpaired_k = sorted({p["num"] for p in Kp if p["num"] not in E})
            for p in Ep:
                if p["num"] not in kpolys:
                    continue
                eg = pad_poly(p, dx, dy, th)
                ks = kpolys[p["num"]]
                best = max(ks, key=lambda q: pad_poly(q).intersection(eg).area)
                kg = pad_poly(best)
                ov = kg.intersection(eg).area / max(min(kg.area, eg.area), 1e-9)
                if ov < 0.5:
                    bad.append(f"{p['num']}({ov:.0%})")
                inner = affinity.scale(kg, 0.8, 0.8, origin=kg.centroid)
                if not inner.contains(eg.centroid):
                    tight.append(p["num"])
                if kg.area >= 1.5 * eg.area:
                    big.append(p["num"])
            if bad:
                red.append(f"G4: count/pitch: EasyEDA pads overlap their KiCad pad by < 50 %: {bad[:8]}")
            if unpaired_e or unpaired_k:
                msg = f"G4: pad numbers not paired: EasyEDA-only {sorted(set(unpaired_e))[:8]}, KiCad-only {unpaired_k[:8]}"
                (yel if len(common) >= 2 else red).append(msg)
            if tight:
                yel.append(f"G4: fits_tight (JLC pad centre outside the inner 80 % of the KiCad pad): {tight[:8]}")
            if big:
                notes.append(f"KiCad pad >= 1.5x the EasyEDA pad: {big[:8]}")
            same_lib = fpc == lc
            P["prior"] = "same-library land: theta 0 expected" if same_lib else "land from another part"
            if same_lib and th != 0:
                yel.append(f"G4 prior: the land is {lc}'s own EasyEDA footprint but theta = {th}")
            # G3 pin identity
            passive = bool(PASSIVE.match(r))
            pm = pmaps.get(lc)
            polk = None
            if pm and isinstance(pm.get("polarity"), dict):
                polk = pm["polarity"].get("kind")
            kf = {p["num"]: nl.get((r, p["num"]), (None, ""))[1] for p in Kp}
            P["identity"] = {}
            if not passive:
                sname = idx.get(lc, {}).get("symbol")
                es = syms.get(sname, {}) if sname else {}
                ds = {str(k): v.get("name") for k, v in (pm or {}).get("pins", {}).items()} if pm else {}
                if not pm:
                    red.append(f"G3: no datasheet pin map pinmap/{lc}.yaml")
                if not es:
                    notes.append("G3: no EasyEDA symbol pins in easyeda.kicad_sym")
                agree = tot = 0; dis = []
                for n in sorted(set(kf) | set(ds) | set(es)):
                    vals = {k: norm(v, n, k == "easyeda") for k, v in (("kicad", kf.get(n)), ("datasheet", ds.get(n)), ("easyeda", es.get(n)))}
                    vals = {k: v for k, v in vals.items() if v}
                    if len(vals) < 2:
                        continue
                    tot += 1
                    if same_name(vals.values()):
                        agree += 1
                    else:
                        dis.append((n, vals))
                P["identity"] = dict(pins_compared=tot, agree=agree, disagree=[f"{n}:{v}" for n, v in dis][:12])
                p1 = [d for d in dis if d[0] in ("1", "A1")]
                crit = [d for d in dis if any(CRIT.search(v) for v in d[1].values())]
                if p1:
                    red.append(f"G3: pin-1 name differs across sources: {p1[0][1]}")
                if tot and agree / tot < 0.95:
                    red.append(f"G3: only {agree}/{tot} named pins agree across sources")
                if crit:
                    red.append(f"G3: supply/ground/output pin names disagree: {[f'{n}:{v}' for n, v in crit][:6]}")
                rv = pm.get("reviewed") or {} if pm else {}
                if pm and polk in POLAR_KINDS and "human" not in str(rv.get("by", "")).lower():
                    if str(rv.get("by", "")).strip() == "independent-agent" and rv.get("date") and rv.get("source") and rv.get("compared"):
                        # ruling P-6: an independent agent's review replaces the human pin-map review; the human check moves to the preview row
                        P.setdefault("preview", []).append(
                            f"G3 (P-6): pin map reviewed by an independent agent on {rv['date']} ({rv.get('result', '')}); the human check is this preview row")
                    else:
                        red.append("G3: polarized part: pin map not marked 'reviewed: human' or 'reviewed: independent-agent' with evidence (G3 / ruling P-6)")
            # G5 polarity
            votes, pol = [], None
            if (polk in POLAR_KINDS and len(Kp) == 2) or (sym > 1 and not passive):
                if polk in POLAR_KINDS and len(Kp) == 2:
                    ref_kind = (pm["polarity"].get("reference") or "K").upper()
                    want = CATHODE if ref_kind in ("K", "C") else {"+"}
                    kref = [n for n, f in kf.items() if (norm(f, n) or "") in ({"K"} if want == CATHODE else want)]
                    sname = idx.get(lc, {}).get("symbol"); es = syms.get(sname, {}) if sname else {}
                    if len(es) == 2:
                        sv = set()
                        for n, nm in es.items():
                            u = norm(nm, n, True)
                            if (u == "K" and want == CATHODE) or (u == "+" and want == {"+"}):
                                sv.add(n)
                            elif (u == "A" and want == CATHODE) or (u == "-" and want == {"+"}):
                                sv.add([m for m in es if m != n][0])
                        if len(sv) == 1:
                            votes.append(("symbol-label", sv.pop()))
                        elif sv:
                            votes.append(("symbol-label", "conflict"))
                    pads_x = sorted(Ep, key=lambda q: q["x"]); axis_x = abs(pads_x[0]["x"] - pads_x[1]["x"]) >= abs(pads_x[0]["y"] - pads_x[1]["y"])
                    lo, hi = (sorted(Ep, key=lambda q: q["x"]) if axis_x else sorted(Ep, key=lambda q: q["y"]))
                    s, t = silk_mass(EM["gfx"], axis_x)
                    if t > 0 and abs(s) / t > 0.2:
                        votes.append(("footprint-band", (hi if s > 0 else lo)["num"]))
                    # The '-RD' / '-FD' package token is NOT a side marker (gate prep 2026-11-16: in the 9 '-RD' footprints of
                    # easyeda.pretty pad 1 sits at -X in 6 and at +X in 3; the silk dot sits at pad 1 in all 9). Recorded, not voted.
                    tok = re.search(r"-(FD|RD)(?:-|_|\.|$)", EM["name"])
                    if tok:
                        notes.append(f"G5: package token -{tok.group(1)} recorded, not counted (not a side marker in the EasyEDA library)")
                    dots = silk_dots(EM["gfx"]) if want == CATHODE else []  # JLC aligns the body's cathode mark with the footprint dot
                    if dots:
                        dd = [(min(math.hypot(c[0] - q["x"], c[1] - q["y"]) for q in Ep), c) for c in dots]
                        d0 = min(dd)[1]
                        near = sorted(Ep, key=lambda q: math.hypot(d0[0] - q["x"], d0[1] - q["y"]))
                        if math.hypot(d0[0] - near[1]["x"], d0[1] - near[1]["y"]) - math.hypot(d0[0] - near[0]["x"], d0[1] - near[0]["y"]) > 0.1:
                            votes.append(("footprint pin-1 dot", near[0]["num"]))
                    if pm["polarity"].get("reference_pin"):
                        votes.append(("pinmap", str(pm["polarity"]["reference_pin"])))
                    jl = {v for _, v in votes}
                    P["polarity_votes"] = votes
                    if len(votes) < 2 or len(jl) != 1:
                        red.append(f"G5: polarity vote needs >= 2 sources and no dissent: {votes}")
                    elif len(kref) != 1:
                        red.append(f"G5: KiCad reference terminal not found from pin functions {kf}")
                    elif jl.pop() != kref[0]:
                        red.append(f"G5: JLC reference pad {votes[0][1]} does not land on KiCad reference pad {kref[0]}")
                    else:
                        pol = f"reference terminal {ref_kind} = pad {kref[0]} (votes: {', '.join(s for s, _ in votes)})"
                elif len(Kp) < 2:
                    pass  # single land: already UNKNOWN from G4
                elif (not pm or polk in NONPOLAR) and len({(round(p["w"], 3), round(p["h"], 3)) for p in Kp}) == 1 and len(Kp) == 2:
                    pol = "no polarity per pin map, identical pads: 180 deg equivalent (G5 modulo-180 rule)"
                else:  # IC / multi-pad part whose copper is turn-symmetric: settle pin 1
                    one = "1" if "1" in E else ("A1" if "A1" in E else None)
                    if one is None:
                        red.append("G5: copper is turn-symmetric and no pad 1 / A1 exists")
                    else:
                        if P["identity"].get("pins_compared") and not any(d.startswith(one + ":") for d in P["identity"]["disagree"]):
                            votes.append(("pin-1 identity (G3)", "agree"))
                        dots = silk_dots(EM["gfx"])
                        if dots:
                            d0 = min(dots, key=lambda c: min(math.hypot(c[0] - q["x"], c[1] - q["y"]) for q in Ep))
                            near = min(Ep, key=lambda q: math.hypot(d0[0] - q["x"], d0[1] - q["y"]))["num"]
                            mx = sum(v[0] for v in E.values()) / len(E); my = sum(v[1] for v in E.values()) / len(E)
                            e1 = E[one]
                            quad = all((abs(e1[i] - (mx, my)[i]) < 0.05) or ((e1[i] - (mx, my)[i]) * (d0[i] - (mx, my)[i]) > 0) for i in (0, 1))
                            votes.append(("footprint pin-1 dot", "agree" if near == one or quad else f"dissent (dot near pad {near}, other quadrant)"))
                        tok = re.search(r"-(TL|TR|BL|BR)(?:-|_|$)", EM["name"])
                        if tok:
                            e1 = E[one]; cx = sum(v[0] for v in E.values()) / len(E); cy = sum(v[1] for v in E.values()) / len(E)
                            q = ("T" if e1[1] < cy else "B") + ("L" if e1[0] < cx else "R")
                            votes.append(("package corner token", "agree" if q == tok.group(1) else f"dissent ({tok.group(1)} vs pad {one} at {q})"))
                        act = pm["polarity"].get("actuator") if pm and isinstance(pm.get("polarity"), dict) else None
                        if act:  # mechanical part: the maker drawing puts the actuator opposite a named EasyEDA pad
                            n5 = str(act.get("opposite_easyeda_pad"))
                            q5 = [q for q in Ep if q["num"] == n5]
                            xs = [q["x"] for q in Ep]; ys = [q["y"] for q in Ep]
                            bb = (min(xs) - 0.6, min(ys) - 0.6, max(xs) + 0.6, max(ys) + 0.6)
                            out_pts = [pt for g in EM["gfx"] if "Silk" in g["layer"] and g["kind"] != "fp_circle" for pt in g["pts"]
                                       if not (bb[0] <= pt[0] <= bb[2] and bb[1] <= pt[1] <= bb[3])]
                            cxx = sum(xs) / len(xs); cyy = sum(ys) / len(ys)
                            if q5 and out_pts:
                                ax_ = sum(p_[0] for p_ in out_pts) / len(out_pts) - cxx; ay_ = sum(p_[1] for p_ in out_pts) / len(out_pts) - cyy
                                dot = ax_ * (q5[0]["x"] - cxx) + ay_ * (q5[0]["y"] - cyy)
                                votes.append((f"maker drawing (actuator opposite pad {n5}) + EasyEDA actuator silk", "agree" if dot < 0 else "dissent (actuator silk on the pad-5 side)"))
                            else:
                                votes.append((f"maker drawing (actuator opposite pad {n5})", f"dissent (EasyEDA pad {n5} or actuator silk not found)"))
                        P["polarity_votes"] = votes
                        ag = [v for v in votes if v[1] == "agree"]
                        if len(ag) < 2 or len(ag) != len(votes):
                            red.append(f"G5: turn-symmetric copper ({sym}-fold): pin-1 vote needs >= 2 agreeing sources and no dissent: {votes}")
                        else:
                            pol = f"pin 1 settled ({', '.join(s for s, _ in votes)})"
            elif sym > 1 and passive:
                same = len({(round(p["w"], 3), round(p["h"], 3)) for p in Kp}) == 1
                pol = "non-polar passive: 180 deg equivalent" if same else None
                if not same:
                    yel.append("G5: passive with turn-symmetric centres but unequal pads")
            P["polarity"] = pol
            if margin < 0.5 * mp and not (sym > 1 and pol):
                if len(common) >= 2:
                    red.append(f"G4: uniqueness margin {margin:.3f} < 0.5 x min pitch {mp:.3f}")
            # G6 CPL synthesis
            org_local = (dx, dy)
            bx, by = pk.local_to_board(fp, org_local)
            if fp["side"] == "top":
                crot = (fp["rot"] + th) % 360
            else:  # bottom-view convention D_b (see PACKAGE.md); unverified without the canary
                best = None
                for c10 in range(0, 3600):
                    c = c10 / 10.0; e = 0.0
                    for n in E:
                        ex, ey = E[n]
                        vx, vy = pk.rot((ex, ey), c)  # EasyEDA frame turned by c (screen CCW, bottom view)
                        tx, ty = (bx - vx, by + vy)  # bottom view mirrored back to the top view
                        fx, fy = tf(E[n], th)
                        kx, ky = pk.local_to_board(fp, (fx + dx, fy + dy))  # where the fit puts this EasyEDA pad
                        e += (tx - kx) ** 2 + (ty - ky) ** 2
                    if best is None or e < best[0]:
                        best = (e, c)
                crot = best[1]
            P.update(cpl=dict(x=round(bx - ox, 4), y=round(-(by - oy), 4), rot=round(crot % 360, 2), layer=fp["side"]))
            P.update(red=red, yellow=yel, notes=notes)
            wv = [w for w in waivers if w.get("ref") == r and w.get("lcsc") == lc and w.get("easyeda_fp_sha256") == P["easyeda_fp_sha256"]
                  and w.get("fp_uuid") == fp["uuid"]]
            P["waived"] = bool(wv)
            P["verdict"] = verdict_of(P)  # provisional; final after R4 and the P-6 preview rules
            parts.append(P)
        except Exception as exc:  # fail closed, never skip
            parts.append(dict(ref=r, lcsc=full[r]["LCSC"], side=F[r]["side"], fpid=F[r]["fpid"], proof_class=proof.get(r, {}).get("proof_class", "-"),
                              verdict="RED", red=[f"gate error: {type(exc).__name__}: {exc}"], yellow=[], notes=[]))

    # R5: polarized 2-terminal parts point the same way
    dirs = {}
    for P in parts:
        if P.get("polarity", "") and P["polarity"].startswith("reference terminal"):
            fp = F[P["ref"]]; n = P["polarity"].split("pad ")[1].split(" ")[0]
            Kp = pk.board_to_local(fp); c = centroids(Kp); o = [v for k, v in c.items() if k != n][0]
            a0 = pk.local_to_board(fp, o); a1 = pk.local_to_board(fp, c[n])
            ang = round(math.degrees(math.atan2(-(a1[1] - a0[1]), a1[0] - a0[0]))) % 360
            dirs.setdefault(ang, []).append(P["ref"])
    if len(dirs) > 1:
        board_notes.append(f"R5: polarized 2-terminal parts point {len(dirs)} ways (reference terminal direction, deg: refs): "
                           + "; ".join(f"{k}: {','.join(v)}" for k, v in sorted(dirs.items())) + " -> YELLOW without a waiver")
    # R4: board silk polarity / pin-1 mark near the reference pad (polarized parts and ICs)
    for P in parts:
        fp = F[P["ref"]]
        if PASSIVE.match(P["ref"]) or "easyeda_fp" not in P:
            continue
        Kp = pk.board_to_local(fp)
        if len(Kp) < 2:
            continue
        refn = "1" if any(p["num"] == "1" for p in Kp) else ("A1" if any(p["num"] == "A1" for p in Kp) else None)
        if P.get("polarity", "") and P["polarity"].startswith("reference terminal"):
            refn = P["polarity"].split("pad ")[1].split(" ")[0]
        if refn is None:
            continue
        rp = [pad_poly(p) for p in Kp if p["num"] == refn]
        cu = None
        for p in Kp:
            g = pad_poly(p).buffer(0.05)
            cu = g if cu is None else cu.union(g)
        side = "F.SilkS" if fp["side"] == "top" else "B.SilkS"
        ok, geos = [], []
        for g in fp["gfx"]:
            if g["layer"] not in (side, "F.Silkscreen", "B.Silkscreen"):
                continue
            pts = g["pts"]
            if fp["side"] == "bottom":
                pts = [(x, -y) for x, y in pts]
            if g["kind"] == "fp_circle":
                geo = Point(pts[0]).buffer(max(g.get("r", 0) + g["width"] / 2, 0.01))
                wid = 2 * g.get("r", 0) + g["width"] if g.get("fill") or g.get("r", 0) < g["width"] else g["width"]
            elif g["kind"] == "fp_poly" and len(pts) >= 3:
                geo = Polygon(pts).buffer(0); mrr = geo.minimum_rotated_rectangle.exterior.coords
                wid = min(math.dist(mrr[0], mrr[1]), math.dist(mrr[1], mrr[2]))
            else:
                from shapely.geometry import LineString
                geo = LineString(pts).buffer(g["width"] / 2); wid = g["width"]
            if min(r_.distance(geo) for r_ in rp) <= 1.5 and not geo.intersects(cu):
                ok.append(wid); geos.append(geo)
        P["silk_mark"] = dict(items_near_ref=len(ok), max_width=round(max(ok), 3) if ok else 0.0)
        # R4b: the board mark and JLC's own footprint mark (EasyEDA silk dot, placed by the fit) must point at the same pad
        try:
            EM = pk.load_mod(os.path.join(D, "lib", "easyeda.pretty", P["easyeda_fp"]))
            Ep_ = [q for q in EM["pads"] if q["num"]]
            dots = silk_dots(EM["gfx"])
            if ok and dots and "theta" in P and len({p["num"] for p in Kp}) >= 2:
                lc_ = {p["num"]: (p["x"], p["y"]) for p in Kp}
                cen_ = centroids(Kp)
                d0 = min(dots, key=lambda c: min(math.hypot(c[0] - q["x"], c[1] - q["y"]) for q in Ep_))
                fx, fy = tf(d0, P["theta"]); jl = (fx + P["offset_local"][0], fy + P["offset_local"][1])
                jpad = min(cen_, key=lambda n: math.dist(cen_[n], jl))
                g0_ = min(geos, key=lambda g: min(r_.distance(g) for r_ in rp))
                bpad = min(cen_, key=lambda n: Point(cen_[n]).distance(g0_))
                P["silk_mark"].update(board_mark_pad=bpad, jlc_mark_pad=jpad)
                if bpad != jpad:
                    P.setdefault("red", []).append(f"R4b: board silk mark at pad {bpad} but JLC's footprint mark at pad {jpad}: JLC follows the silk")
        except Exception as exc:  # fail closed
            P.setdefault("red", []).append(f"R4b: check failed: {type(exc).__name__}: {exc}")
        if not ok:
            P.setdefault("yellow", []).append(f"R4: no board silk mark within 1.5 mm of reference pad {refn} clear of copper")
        elif max(ok) < 0.15:
            P.setdefault("yellow", []).append(f"R4: silk mark near pad {refn} is {max(ok):.2f} mm wide (< 0.15)")

    # ruling P-6: rows that wait only for the JLC preview (preview_rules.yaml); final verdicts
    for P in parts:
        apply_preview_rules(P, prules, proof)
        P["verdict"] = verdict_of(P)

    # outputs
    cnt = {}
    for P in parts:
        cnt[P["verdict"]] = cnt.get(P["verdict"], 0) + 1
    ok = not board_reds and all(P["verdict"] in ("GREEN", "PREVIEW") for P in parts)
    prev = sorted((P for P in parts if P["verdict"] == "PREVIEW"), key=lambda p: p["ref"])
    prov = dict(gate="cplgate (v3/package/tools/cplgate.py)", spec="research/cpl-placement-gate.md §6 + ruling P-6 (preview_rules.yaml)", g0=g0,
                board_red=board_reds, board_notes=board_notes, counts=cnt, shippable=ok,
                preview_pending=[P["ref"] for P in prev], parts=parts)
    pk.dump(prov, os.path.join(a.out, "cpl_provenance.json"))
    cand = os.path.join(a.out, "candidate_NOT_FOR_UPLOAD")
    os.makedirs(cand, exist_ok=True)
    write_cpl(parts, os.path.join(cand, "CPL_JLC.csv"))
    write_report(prov, os.path.join(a.out, "cplgate_report.md"))
    write_preview(prev, os.path.join(a.out, "PREVIEW_CHECKS.md"), g0)
    if ok:
        h = g0["board_sha256"][:12]
        up = os.path.join(a.out, "upload_" + h); os.makedirs(up, exist_ok=True)
        write_cpl(parts, os.path.join(up, "CPL_JLC.csv"))
        write_preview(prev, os.path.join(up, "PREVIEW_CHECKS.md"), g0)
    if not a.no_render:
        import render_gate
        render_gate.render_all(prov, B, os.path.join(a.out, "overlays"), D)
    print(json.dumps(dict(counts=cnt, board_red=len(board_reds), shippable=ok, preview_pending=len(prev))))
    sys.exit(0 if ok else 1)


def verdict_of(P):
    red = P.get("red", [])
    if red:
        return "UNKNOWN" if all(x.startswith("UNKNOWN") for x in red) else "RED"
    if P.get("yellow") and not P.get("waived"):
        return "YELLOW"
    if P.get("preview"):
        return "PREVIEW"
    return "GREEN"


def apply_preview_rules(P, prules, proof):
    """Ruling P-6. A red reason becomes a preview item only if the row's own entry (same ref AND C-number) allows it, and only
    when ALL of the part's red reasons are allowed; otherwise nothing moves. YELLOW is never moved. Each PREVIEW row gets the
    thing to look at in the JLC preview and its electrical test."""
    ent = [e for e in (prules or {}).get("rows", []) if P["ref"] in (e.get("refs") or []) and e.get("lcsc") == P["lcsc"]]
    red = P.get("red", [])
    allow = [pat for e in ent for pat in (e.get("allow") or [])]
    pv = list(P.get("preview", []))
    if ent and red and all(any(re.search(p_, x) for p_ in allow) for x in red):
        pv += [f"P-6 ({ent[0]['why']}): {x}" for x in red]
        P["red_moved_to_preview"] = list(red)
        P["red"] = []
    elif ent and not red:
        pv.append(f"P-6 ({ent[0]['why']})")
    if pv:
        looks = [e["look"] for e in ent if e.get("look")]
        g3 = (prules or {}).get("g3_look", {}).get(P["ref"])
        if g3 and g3 != "see the bottom row":
            looks.append(g3)
        P["preview"] = pv
        P["preview_look"] = " / ".join(looks) or "MISSING: no look item in preview_rules.yaml"
        P["preview_test"] = proof.get(P["ref"], {}).get("g10_item") or "MISSING: no electrical test in placement_proof.json"
        if not looks or P["preview_test"].startswith("MISSING"):
            P.setdefault("red", []).append("P-6: PREVIEW row without a look item or an electrical test")


def write_preview(prev, path, g0):
    L = ["# JLC preview checks (ruling P-6): do these before any payment", "",
         f"Board sha256 {g0['board_sha256'][:16]}... gate run {g0['run_utc']}. Every machine check passed for these rows; each waits only for the "
         "human look in JLC's placement preview (and the 2D production file after engineer review). Any mismatch or any JLC change = STOP.", "",
         "| ☐ | Ref | LCSC | Side | CPL rot | Why it waits | Look at this in the JLC preview | Electrical test |", "|---|---|---|---|---|---|---|---|"]
    for P in prev:
        why = "; ".join(P.get("preview", [])).replace("|", "/")
        L.append(f"| ☐ | {P['ref']} | {P['lcsc']} | {P['side']} | {P.get('cpl', {}).get('rot', '-')} | {why} | {P.get('preview_look', '')} | {P.get('preview_test', '')} |")
    if not prev:
        L.append("| - | none | | | | | | |")
    open(path, "w").write("\n".join(L) + "\n")


def write_cpl(parts, path):
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Designator", "Mid X", "Mid Y", "Layer", "Rotation"])
        for P in sorted(parts, key=lambda p: p["ref"]):
            if "cpl" not in P:
                continue
            c = P["cpl"]
            w.writerow([P["ref"], f"{c['x']:.4f}mm", f"{c['y']:.4f}mm", "Top" if c["layer"] == "top" else "Bottom", f"{c['rot']:.2f}"])


def write_report(prov, path):
    L = ["# cplgate report", "", f"Board: `{prov['g0']['board']}` sha256 {prov['g0']['board_sha256'][:16]}..., run {prov['g0']['run_utc']}",
         "", f"**Shippable: {'YES (GREEN)' if prov['shippable'] else 'NO'}**  counts: {prov['counts']}", "", "## Board-level", ""]
    L += [f"- RED {x}" for x in prov["board_red"]] + [f"- note {x}" for x in prov["board_notes"]]
    L += ["", "## Parts (not GREEN first)", "", "| Ref | LCSC | Side | Verdict | theta | CPL rot | rms | margin | sym | Class | Reasons |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    order = {"RED": 0, "UNKNOWN": 1, "YELLOW": 2, "PREVIEW": 3, "GREEN": 4}
    for P in sorted(prov["parts"], key=lambda p: (order[p["verdict"]], p["ref"])):
        why = "; ".join(P.get("red", []) + P.get("yellow", []) + [f"PREVIEW: {x}" for x in P.get("preview", [])]).replace("|", "/")
        c = P.get("cpl", {})
        L.append(f"| {P['ref']} | {P['lcsc']} | {P['side']} | {P['verdict']} | {P.get('theta', '-')} | {c.get('rot', '-')} | {P.get('rms', '-')} | "
                 f"{P.get('margin', '-')} | {P.get('sym_order', '-')} | {P['proof_class']} | {why or (P.get('polarity') or '')} |")
    open(path, "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
