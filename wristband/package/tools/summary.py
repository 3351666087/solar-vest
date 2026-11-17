"""Package summary: counts and verdicts of one make_package.sh run.

usage: python summary.py --out OUTDIR   (reads OUTDIR/{gate,assembly,fab,review})
"""
import argparse, csv, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pk  # noqa: E402


def j(path, default=None):
    return json.load(open(path)) if os.path.exists(path) else default


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); ap.add_argument("--codes", default="")
    a = ap.parse_args(); O = a.out
    codes = dict(x.split("=") for x in a.codes.split(",") if "=" in x)
    gate = j(os.path.join(O, "gate", "cpl_provenance.json"), {})
    g7 = j(os.path.join(O, "gate", "g7.json"), {}).get("summary", {})
    mut = j(os.path.join(O, "gate", "mutation_report.json"), {})
    bom = j(os.path.join(O, "assembly", "bom_check.json"), {})
    fab = j(os.path.join(O, "fab", "fab_info.json"), {})
    cpl = list(csv.DictReader(open(os.path.join(O, "gate", "candidate_NOT_FOR_UPLOAD", "CPL_JLC.csv"))))
    src = pk.read_csv(os.path.join(pk.DESIGN, "BOM_v3f.csv"))
    lib = {}
    for r in src:
        lib[r["Library"]] = lib.get(r["Library"], 0) + 1
    low = []
    sr = open(os.path.join(pk.DESIGN, "stock_report.md")).read()
    sec = sr.split("## Flagged lines")[1].split("\n## ")[0] if "## Flagged lines" in sr else ""
    for line in sec.splitlines():
        m = re.match(r"\| (C\d+) \| ([^|]+) \| ([^|]+) \| (\d+) \| (-?\d+) \| (-?\d+) \| ([^|]+) \|", line)
        if m:
            low.append(dict(lcsc=m.group(1), mpn=m.group(2).strip(), refs=m.group(3).strip(), stock=int(m.group(5)), presale=int(m.group(6)), why=m.group(7).strip()))
    S = dict(board=gate.get("g0", {}).get("board"), board_sha256=gate.get("g0", {}).get("board_sha256"),
             placed=dict(top=sum(1 for r in cpl if r["Layer"] == "Top"), bottom=sum(1 for r in cpl if r["Layer"] == "Bottom"),
                         jlc_set=bom.get("placements"), without_cpl_row=bom.get("placements", 0) - len(cpl)),
             bom=dict(unique_lines=bom.get("lines"), basic=lib.get("Basic", 0), preferred=lib.get("Preferred", 0), extended=lib.get("Extended", 0),
                      not_fitted=bom.get("not_fitted"), hand_fitted=bom.get("hand_fitted"), copper_only=bom.get("copper_only"),
                      check_failures=len(bom.get("fails", []))),
             low_stock=low, gate=dict(counts=gate.get("counts"), shippable=gate.get("shippable"), board_red=gate.get("board_red"), preview_pending=gate.get("preview_pending", [])),
             g7=dict(passed=g7.get("passed"), parts=g7.get("parts"), failed=g7.get("failed")),
             mutations={k: (v.get("verdict") if isinstance(v, dict) else v) for k, v in mut.items()},
             fab={k: fab.get(k) for k in ("outline_mm", "cutouts", "vias", "vias_in_smd_pads", "drc_errors", "drc_unconnected")},
             exit_codes=codes)
    ok = bool(S["gate"]["shippable"]) and not S["bom"]["check_failures"] and not g7.get("failed") and mut.get("verdict") == "PASS" \
        and fab.get("drc_errors") == 0 and fab.get("drc_unconnected") == 0
    S["orderable"] = ok
    pk.dump(S, os.path.join(O, "summary.json"))
    c = S["gate"]["counts"] or {}
    L = ["# Package summary", "",
         f"Board `{S['board']}` (sha256 {str(S['board_sha256'])[:16]}...). **Orderable: {('YES, after the ' + str(len(S['gate']['preview_pending'])) + ' JLC preview checks in upload/PREVIEW_CHECKS.md') if ok and S['gate']['preview_pending'] else ('YES' if ok else 'NO')}**", "",
         "| Item | Result |", "|---|---|",
         f"| Parts placed by JLC | top {S['placed']['top']}, bottom {S['placed']['bottom']} (CPL rows {len(cpl)} of {S['placed']['jlc_set']} JLC-placed; {S['placed']['without_cpl_row']} without a provable row) |",
         f"| Unique BOM lines | {S['bom']['unique_lines']}: Basic {S['bom']['basic']}, Preferred {S['bom']['preferred']}, Extended {S['bom']['extended']} |",
         f"| Not fitted / hand-fitted / copper only | {S['bom']['not_fitted']} / {S['bom']['hand_fitted']} / {S['bom']['copper_only']} |",
         f"| BOM check against v3/design/BOM_v3f.csv and the board | {'PASS' if not S['bom']['check_failures'] else 'FAIL (' + str(S['bom']['check_failures']) + ')'} |",
         f"| Low stock (stock_report.md) | {len(low)} lines: " + "; ".join(f"{x['lcsc']} {x['mpn']} ({x['refs']}) orderable {max(0, min(x['stock'], x['presale']))}" for x in low) + " |",
         f"| Placement gate | GREEN {c.get('GREEN', 0)}, PREVIEW {c.get('PREVIEW', 0)}, YELLOW {c.get('YELLOW', 0)}, RED {c.get('RED', 0)}, UNKNOWN {c.get('UNKNOWN', 0)}; board-level RED {len(S['gate']['board_red'] or [])} -> {'PASS (GREEN + PREVIEW rows: ' + ', '.join(S['gate']['preview_pending']) + ')' if S['gate']['shippable'] else 'NOT PASSED'} |",
         f"| G7 closed loop (CPL vs Gerber copper) | {S['g7']['passed']}/{S['g7']['parts']} pass |",
         f"| G8 mutations | {S['mutations']} |",
         f"| Board | {fab.get('outline_mm')}, cut-outs {fab.get('cutouts')}, vias {fab.get('vias')} ({fab.get('vias_in_smd_pads')} in pads) |",
         f"| DRC | {fab.get('drc_errors')} errors, {fab.get('drc_unconnected')} unconnected |", ""]
    open(os.path.join(O, "summary.md"), "w").write("\n".join(L) + "\n")
    print(json.dumps(dict(orderable=ok, gate=c, g7=S["g7"]["passed"], mutations=S["mutations"].get("verdict"))))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
