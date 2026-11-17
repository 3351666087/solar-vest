"""G8 mutation tests (run on every package build).

M1  CPL mutations, every placed part: rotation +90/+180/+270, layer flipped, shift of 0.6 x the smallest pad size
    -> the independent G7 check must reject each one.
M2  EasyEDA pad-number permutation (pads 1 <-> 2, or A1 <-> A2) for every non-passive part -> the gate must turn RED
    (non-polar two-pad parts are exempt: a swap there is the allowed modulo-180 case).
M3  wrong neighbouring package: each non-passive part gets another part's EasyEDA footprint with the same pad count
    -> the gate must turn RED.
M4  board copy with a few parts turned on the board (+90/+180/+270): the OLD CPL must fail G7 on exactly those parts;
    the gate re-run on the copy must emit a CPL that passes G7 (the CPL follows the board, never a table).

usage: python mutate.py --board B --gate GATEDIR --bom BOM_JLC.csv --gerbers DIR --work DIR --out mutation_report.json
"""
import argparse, csv, json, os, re, shutil, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import g7_verify as g7  # noqa: E402
import pk  # noqa: E402

KICAD = os.environ.get("KICAD_CLI", "kicad-cli")
PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))
M4_SET = [("U1", 90), ("U7", 180), ("D9", 180), ("Q20", 90), ("U21", 270), ("C101", 180), ("J13", 180)]


def rows(path):
    return list(csv.DictReader(open(path, newline="")))


def write_rows(rs, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]); w.writeheader(); w.writerows(rs)


def turn_on_board(text, ref, d):
    i = text.index(f'(property "Reference" "{ref}"')
    s = text.rindex("(footprint ", 0, i)
    depth = 0; e = s
    for e in range(s, len(text)):
        if text[e] == "(":
            depth += 1
        elif text[e] == ")":
            depth -= 1
            if depth == 0:
                break
    blk = text[s:e + 1]

    def bump(m):
        a = float(m.group(3) or 0) + d
        return f"(at {m.group(1)} {m.group(2)} {a % 360:g})"
    at = re.compile(r"\(at (-?[\d.]+) (-?[\d.]+)(?: (-?[\d.]+))?\)")
    m = at.search(blk)
    blk = blk[:m.start()] + bump(m) + blk[m.end():]
    out, pos = [], 0
    for pm in re.finditer(r"\(pad ", blk):
        if pm.start() < pos:
            continue
        m = at.search(blk, pm.end())
        out.append(blk[pos:m.start()]); out.append(bump(m)); pos = m.end()
    out.append(blk[pos:])
    return text[:s] + "".join(out) + text[e + 1:]


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def main():
    ap = argparse.ArgumentParser()
    for k in ("board", "pos", "gate", "bom", "gerbers", "work", "out"):
        ap.add_argument("--" + k, required=True)
    a = ap.parse_args()
    os.makedirs(a.work, exist_ok=True)
    ee = os.path.join(pk.DESIGN, "lib", "easyeda.pretty")
    prov = json.load(open(os.path.join(a.gate, "cpl_provenance.json")))
    parts = {p["ref"]: p for p in prov["parts"]}
    cpl = rows(os.path.join(a.gate, "candidate_NOT_FOR_UPLOAD", "CPL_JLC.csv"))
    ctx = g7.load_context(a.gerbers, a.bom, ee)
    rep = {}

    # M1
    tot = caught = 0; esc = []
    base_fail = [r["Designator"] for r in cpl if g7.check_row(r, ctx)["fails"]]
    B = pk.load_board(a.board)["footprints"]
    blind = sorted(r for r, p in parts.items() if p["verdict"] == "UNKNOWN" or any(x.startswith("UNKNOWN") for x in p.get("red_moved_to_preview", [])))
    for r in cpl:
        ref = r["Designator"]
        if ref in base_fail or ref in blind:
            continue  # single land: geometry cannot decide 0 vs 180; UNKNOWN, or PREVIEW under ruling P-6 (preview row + electrical test)
        mp = min(min(p["w"], p["h"]) for p in B[ref]["pads"] if p["num"])
        muts = [("rot+%d" % d, dict(r, Rotation=f"{(float(r['Rotation']) + d) % 360:.2f}")) for d in (90, 180, 270)]
        muts.append(("layer", dict(r, Layer="Bottom" if r["Layer"] == "Top" else "Top")))
        muts.append(("shift_x", dict(r, **{"Mid X": f"{float(r['Mid X'][:-2]) + 0.6 * mp:.4f}mm"})))
        muts.append(("shift_y", dict(r, **{"Mid Y": f"{float(r['Mid Y'][:-2]) + 0.6 * mp:.4f}mm"})))
        for name, m in muts:
            tot += 1
            if g7.check_row(m, ctx)["fails"]:
                caught += 1
            else:
                esc.append(f"{ref}:{name}")
    rep["M1_cpl_mutations"] = dict(parts=len(cpl) - len(base_fail), not_tested_single_land=blind, mutations=tot, caught=caught, escaped=esc,
                                   verdict="PASS" if not esc else "FAIL", g7_baseline_failures=base_fail)

    # M2 + M3 (one gate run each, overrides in a scratch footprint folder)
    def gate_with(over, tag):
        d = os.path.join(a.work, tag); os.makedirs(d, exist_ok=True)
        args = [PY, os.path.join(HERE, "cplgate.py"), "--board", a.board, "--pos", a.pos,
                "--out", d, "--no-render"]
        for ref, path in over.items():
            args += ["--easyeda-override", f"{ref}={path}"]
        r = run(args)
        if r.returncode == 2 or not os.path.exists(os.path.join(d, "cpl_provenance.json")):
            raise SystemExit(f"gate run {tag} failed: {r.stderr[-800:]}")
        return {p["ref"]: p for p in json.load(open(os.path.join(d, "cpl_provenance.json")))["parts"]}

    nonpass = [p for p in parts.values() if not re.match(r"^(R|C|L|FB)\d", p["ref"]) and p.get("easyeda_fp")]
    fpdir = os.path.join(a.work, "fp"); os.makedirs(fpdir, exist_ok=True)
    over, why = {}, {}
    for p in nonpass:
        src = os.path.join(ee, p["easyeda_fp"]); t = open(src).read()
        nums = re.findall(r"\(pad\s+\"?([^\s\"]+)\"?\s", t)
        u = sorted(set(nums), key=lambda n: (len(n), n))
        a1, a2 = ("1", "2") if "1" in u and "2" in u else (("A1", "A2") if "A1" in u and "A2" in u else (None, None))
        if not a1:
            continue
        t2 = re.sub(r"\(pad\s+\"?(%s|%s)\"?\s" % (a1, a2), lambda m: f"(pad {a2 if m.group(1) == a1 else a1} ", t)
        dst = os.path.join(fpdir, f"perm_{p['ref']}.kicad_mod"); open(dst, "w").write(t2); over[p["ref"]] = dst
        why[p["ref"]] = f"{a1}<->{a2}"
    res2 = gate_with(over, "m2_perm")
    exempt, caught2, esc2 = [], [], []
    for ref in over:
        q = res2[ref]; base = parts[ref]
        pol = base.get("polarity") or ""
        if pol.startswith("no polarity"):
            exempt.append(ref); continue
        if q["verdict"] in ("RED", "UNKNOWN") and q.get("red") != base.get("red"):
            caught2.append(ref)
        else:
            esc2.append(f"{ref} ({why[ref]}): gate {q['verdict']} theta {q.get('theta')} (base {base['verdict']})")
    rep["M2_pad_number_permutation"] = dict(mutated=len(over), exempt_mod180=exempt, caught=len(caught2), escaped=esc2,
                                            verdict="PASS" if not esc2 else "FAIL")

    # M3 wrong neighbouring package
    lib = {}
    for f in os.listdir(ee):
        n = len(set(re.findall(r"\(pad\s+\"?([^\s\"]+)\"?\s+(?:smd|thru_hole)", open(os.path.join(ee, f)).read())))
        lib.setdefault(n, []).append(f)
    over3, pair = {}, {}
    for p in nonpass:
        n = len({x["num"] for x in pk.load_mod(os.path.join(ee, p["easyeda_fp"]))["pads"] if x["num"]})
        fam = lambda f: re.split(r"[_-]L?\d", f.split("_", 1)[1])[0]
        cand = [f for f in lib.get(n, []) if f.split("_")[0] != p["lcsc"] and fam(f) != fam(p["easyeda_fp"])]
        if cand:
            cand.sort()
            over3[p["ref"]] = os.path.join(ee, cand[0]); pair[p["ref"]] = cand[0]
    res3 = gate_with(over3, "m3_wrongpkg")
    caught3, geo3, esc3 = [], [], []
    for ref in over3:
        q = res3[ref]
        newred = [x for x in q.get("red", []) if x not in parts[ref].get("red", [])]
        if q["verdict"] in ("RED", "UNKNOWN") and newred:
            caught3.append(ref)
            if [x for x in newred if not x.startswith("G2 binding")]:
                geo3.append(ref)
            else:
                esc3.append(f"{ref} given {pair[ref]}: only the G2 binding check fires; geometry alone passes")
        else:
            esc3.append(f"{ref} given {pair[ref]}: NOT caught ({q['verdict']})")
    hard = [e for e in esc3 if "NOT caught" in e]
    rep["M3_wrong_package"] = dict(mutated=len(over3), caught=len(caught3), caught_by_geometry=len(geo3), geometry_blind=esc3,
                                   verdict="PASS" if not hard else "FAIL")

    # M4 parts turned on a board copy
    txt = open(a.board).read()
    for ref, d in M4_SET:
        txt = turn_on_board(txt, ref, d)
    mb = os.path.join(a.work, "mutant_board.kicad_pcb"); open(mb, "w").write(txt)
    gd = os.path.join(a.work, "mutant_gerbers"); os.makedirs(gd, exist_ok=True)
    r = run([KICAD, "pcb", "export", "gerbers", "--layers", "F.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS", "--use-drill-file-origin",
             "-o", gd, mb])
    mpos = os.path.join(a.work, "mutant_pos.csv")
    run([KICAD, "pcb", "export", "pos", "--format", "csv", "--units", "mm", "--side", "both", "--use-drill-file-origin", "-o", mpos, mb])
    ctx4 = g7.load_context(gd, a.bom, ee)
    old_fail = sorted(rw["Designator"] for rw in cpl if g7.check_row(rw, ctx4)["fails"])
    mg = os.path.join(a.work, "mutant_gate")
    run([PY, os.path.join(HERE, "cplgate.py"), "--board", mb, "--pos", mpos, "--out", mg, "--no-render"])
    new = rows(os.path.join(mg, "candidate_NOT_FOR_UPLOAD", "CPL_JLC.csv"))
    new_fail = sorted(rw["Designator"] for rw in new if g7.check_row(rw, ctx4)["fails"])
    oldr = {rw["Designator"]: rw["Rotation"] for rw in cpl}; newr = {rw["Designator"]: rw["Rotation"] for rw in new}
    want = sorted(x for x, _ in M4_SET)
    rep["M4_board_copy_turned"] = dict(turned=[f"{x}+{d}" for x, d in M4_SET], old_cpl_fails_g7=old_fail,
                                       new_cpl_fails_g7=new_fail,
                                       new_rotations={x: f"{oldr.get(x)} -> {newr.get(x)}" for x in want},
                                       verdict="PASS" if old_fail == want and not new_fail else "FAIL")
    rep["verdict"] = "PASS" if all(v["verdict"] == "PASS" for k, v in rep.items() if k.startswith("M")) else "FAIL"
    pk.dump(rep, a.out)
    print(json.dumps({k: (v["verdict"] if isinstance(v, dict) else v) for k, v in rep.items()}))
    sys.exit(0 if rep["verdict"] == "PASS" else 1)


if __name__ == "__main__":
    main()
