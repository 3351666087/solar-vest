"""BOM in JLC's upload format + the not-fitted and hand-fitted lists; every line checked against v3/design/BOM_v3f.csv,
BOM_full_v3f.csv and the board.

usage: python bom_jlc.py --board B.kicad_pcb --out DIR   -> DIR/BOM_JLC.csv, BOM_not_fitted.csv, BOM_hand_fitted.csv,
       BOM_copper_only.csv, bom_check.json ; exit 1 if any check fails
"""
import argparse, csv, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pk  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", required=True); ap.add_argument("--out", required=True); ap.add_argument("--design", default=pk.DESIGN)
    a = ap.parse_args(); D = a.design; os.makedirs(a.out, exist_ok=True)
    B = pk.load_board(a.board)["footprints"]
    full = pk.bom_full(os.path.join(D, "BOM_full_v3f.csv"))
    src = pk.read_csv(os.path.join(D, "BOM_v3f.csv"))
    idx = json.load(open(os.path.join(D, "lib", "easyeda_index.json")))
    fails, lines = [], []
    seen = set()
    for r in src:
        refs = [d.strip() for d in r["Designator"].split(",")]
        lc = r["LCSC"]
        if len(refs) != int(r["Qty"]):
            fails.append(f"{r['Designator']}: Qty {r['Qty']} != {len(refs)} designators")
        for d in refs:
            if d in seen:
                fails.append(f"{d}: on two BOM lines")
            seen.add(d)
            f = full.get(d)
            if not f:
                fails.append(f"{d}: not in BOM_full_v3f.csv"); continue
            if f["LCSC"] != lc or f["Class"] != "JLC-placed":
                fails.append(f"{d}: BOM_full says {f['LCSC']} / {f['Class']}, BOM_v3f says {lc}")
            if f["Footprint"] != r["Footprint"]:
                fails.append(f"{d}: footprint {r['Footprint']} vs BOM_full {f['Footprint']}")
            b = B.get(d)
            if not b:
                fails.append(f"{d}: not on the board")
            else:
                if b["fpid"] != r["Footprint"]:
                    fails.append(f"{d}: board footprint {b['fpid']} != BOM {r['Footprint']}")
                if "dnp" in b["attrs"] or "exclude_from_bom" in b["attrs"]:
                    fails.append(f"{d}: board marks it {sorted(b['attrs'])}")
                if (b["side"] == "top") != (r["Side"] == "top"):
                    fails.append(f"{d}: board side {b['side']} vs BOM {r['Side']}")
        pkg = idx.get(lc, {}).get("package_title") or r["Footprint"].split(":")[1].split("_", 1)[-1]
        lines.append(dict(Comment=r["Comment"], Designator=",".join(refs), Footprint=pkg, **{"LCSC Part #": lc}))
    jlc_full = {d for d, f in full.items() if f["Class"] == "JLC-placed"}
    if jlc_full != seen:
        fails.append(f"JLC-placed in BOM_full but not in BOM_v3f: {sorted(jlc_full - seen)}; reverse: {sorted(seen - jlc_full)}")
    with open(os.path.join(a.out, "BOM_JLC.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, ["Comment", "Designator", "Footprint", "LCSC Part #"]); w.writeheader(); w.writerows(lines)
    groups = {"BOM_not_fitted.csv": lambda c: c.startswith("DNP"), "BOM_hand_fitted.csv": lambda c: c.startswith("off the PCBA"),
              "BOM_copper_only.csv": lambda c: c.startswith("copper only")}
    counts = {}
    for fn, sel in groups.items():
        rows = [f for f in full.values() if sel(f["Class"])]
        counts[fn] = len(rows)
        for f_ in rows:
            b = B.get(f_["Ref"])
            if fn == "BOM_not_fitted.csv" and b and "dnp" not in b["attrs"] and "exclude_from_pos_files" not in b["attrs"]:
                fails.append(f"{f_['Ref']}: not fitted, but the board footprint is neither DNP nor excluded from the position file")
            f_["On_board"] = "yes" if b else "no"
        with open(os.path.join(a.out, fn), "w", newline="") as f:
            w = csv.DictWriter(f, ["Ref", "Value", "LCSC", "MPN", "Footprint", "Side", "Class", "Function", "On_board"], extrasaction="ignore")
            w.writeheader(); w.writerows(sorted(rows, key=lambda x: x["Ref"]))
    # value check (final package, 2026-11-16): the board's Value field against BOM_full; reported, never a fail; the BOM uses the design value
    value_diffs = [dict(ref=r, board=b["props"].get("Value"), design=full[r]["Value"], used="design") for r, b in sorted(B.items())
                   if r in full and b["props"].get("Value") not in (None, "", full[r]["Value"])]
    other = [r for r, b in B.items() if r not in full]
    if other:
        fails.append(f"board footprints not in BOM_full: {other}")
    chk = dict(lines=len(lines), placements=len(seen), not_fitted=counts["BOM_not_fitted.csv"], hand_fitted=counts["BOM_hand_fitted.csv"],
               copper_only=counts["BOM_copper_only.csv"], fails=fails, value_diffs=value_diffs, source=os.path.join(D, "BOM_v3f.csv"),
               source_sha256=pk.sha256(os.path.join(D, "BOM_v3f.csv")))
    pk.dump(chk, os.path.join(a.out, "bom_check.json"))
    print(json.dumps({k: v for k, v in chk.items() if k not in ("fails", "value_diffs")} | {"fails": len(fails), "value_diffs": [d["ref"] for d in value_diffs]}))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
