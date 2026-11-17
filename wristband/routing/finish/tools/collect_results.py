"""Collect the V3-G1 placement runs into one table (work/g1_sets.json, work/g1_sets.md).
usage: venv-python collect_results.py"""
import glob, json, os, re
D = "/path/to/SolarVest_work/wristband/v3/layout"
WK = D + "/work"
SETS = [  # tag prefix, level, set name, pod, zone tag, what, cost to the wearer
 ("S0", "0", "S0", "41 x 32", "L41", "level-0 schematic on the stage-1 FPC corridor (reference only: its J13 land cannot be soldered, CAD lane)", "none"),
 ("S0A", "0 / 1", "S0A", "41 x 32", "L41_fpcdwg", "level-0 schematic + FPC outline as drawn, J13 beyond the tip with a bridge flex (CAD L1-A)", "none (bridge flex = new custom part)"),
 ("S1U", "1", "S1-U", "41 x 32", "L41_fpcdwg", "S0A + FID1, FID2 and the SWD group J12 under the FPC return run (this lane)", "none"),
 ("S1A3", "1", "S1-A3", "41 x 32", "L41_fold1p9_fpcdwg", "S0A + fold 1.9 mm from the glass edge (CAD L1-A3)", "none; SW1 courtyard 0.14 mm from the fold"),
 ("S1A3U", "1", "S1-A3U", "41 x 32", "L41_fold1p9_fpcdwg", "S1-A3 + fiducials and J12 under the FPC run", "none"),
 ("S1R05", "1", "S1-R05", "41 x 32", "L41_fpcdwg_raise0p05", "S0A + panel raised 0.05 mm (low zone 0.80 mm)", "window half +0.05 mm"),
 ("S1R10", "1", "S1-R10", "41 x 32", "L41_fpcdwg_raise0p1", "S0A + panel raised 0.10 mm (low zone 0.85 mm: U10, U15 fit under the panel)", "window half +0.10 mm"),
 ("S1R15", "1", "S1-R15", "41 x 32", "L41_fpcdwg_raise0p15", "S0A + panel raised 0.15 mm (low zone 0.90 mm)", "window half +0.15 mm"),
 ("S1A3R10", "1", "S1-A3R10", "41 x 32", "L41_fold1p9_fpcdwg_raise0p1", "S1-A3 + panel raised 0.10 mm", "window half +0.10 mm"),
 ("S2W33A", "2", "S2-33A", "41 x 33", "L41W33_fpcdwg", "41 x 33 pod (board 38 x 30) with L1-A", "+1 mm wide, +0.20 g"),
 ("S2W33A3", "2", "S2-33A3", "41 x 33", "L41W33_fold1p9_fpcdwg", "41 x 33 pod with L1-A3", "+1 mm wide, +0.20 g"),
 ("S2W34A", "2", "S2-34A", "41 x 34", "L41W34_fpcdwg", "41 x 34 pod (board 38 x 31) with L1-A", "+2 mm wide, +0.42 g"),
 ("S2W34A3", "2", "S2-34A3", "41 x 34", "L41W34_fold1p9_fpcdwg", "41 x 34 pod with L1-A3", "+2 mm wide, +0.42 g"),
 ("S3L42A", "3", "S3-42A", "42 x 32", "L42_fpcdwg", "42 x 32 pod (board 39 x 29) with L1-A", "+1 mm long, +0.19 g"),
 ("S3L42A3", "3", "S3-42A3", "42 x 32", "L42_fold1p9_fpcdwg", "42 x 32 pod, fold at 1.9 mm", "+1 mm long, +0.19 g"),
 ("S3L42A4", "3", "S3-42A4", "42 x 32", "L42_fold2p9_fpcdwg", "42 x 32 pod, fold at 2.9 mm", "+1 mm long, +0.19 g"),
 ("S23A3", "2 + 3", "S23-42x33A3", "42 x 33", "L42W33_fold1p9_fpcdwg", "42 x 33 pod with L1-A3", "+1 mm long, +1 mm wide, +0.42 g"),
 ("S2W33A3U", "2", "S2-33A3U", "41 x 33", "L41W33_fold1p9_fpcdwg", "41 x 33 pod with L1-A3 + fiducials and J12 under the FPC run", "+1 mm wide, +0.20 g"),
 ("S2W34A3U", "2", "S2-34A3U", "41 x 34", "L41W34_fold1p9_fpcdwg", "41 x 34 pod with L1-A3 + fiducials and J12 under the FPC run", "+2 mm wide, +0.42 g"),
 ("S23A3U", "2 + 3", "S23-42x33A3U", "42 x 33", "L42W33_fold1p9_fpcdwg", "42 x 33 pod with L1-A3 + fiducials and J12 under the FPC run", "+1 mm long, +1 mm wide, +0.42 g"),
]
MODES = {"A": "courtyard rule of v1 (pcbnew boxes 0.05 mm apart); JLC table: chip / SOT rows only",
         "B": "KiCad courtyard rule (centre lines may touch) + the whole JLC spacing table",
         "C": "v1 courtyard rule + the whole JLC spacing table (most robust)"}
rows = []
for pre, lvl, name, pod, ztag, what, cost in SETS:
    for mode in ("B", "C", "A"):
        runs = []
        for f in sorted(glob.glob(f"{WK}/chk_{pre}_{mode}_s*.json")):
            m = re.search(r"_s(\d+)\.json$", f)
            if not m:
                continue
            c = json.load(open(f)); seed = int(m.group(1))
            if c["zones"] != ztag:
                continue
            sl = f"{WK}/slack_{pre}_{mode}_s{seed}.json"
            runs.append(dict(seed=seed, chk=os.path.basename(f), legal=c["legal"], legal_crit=c.get("legal_and_critical_pairs_within_limits"),
                             unplaced=len(c["hard"]["no_legal_spot"]), crit=len(c["hard"].get("critical_pair_violations", [])),
                             jlc_pairs=c["jlc_spacing_table"]["pairs_below_the_recommended_table"], g=c["gate1_metric"], z=c["zones_geometric"],
                             slack=json.load(open(sl)) if os.path.exists(sl) else None))
        if not runs:
            continue
        best = sorted(runs, key=lambda r: (not r["legal"], r["crit"], r["seed"]))[0]
        g = best["g"]; zz = best["z"]["by_h_max"]
        pc, pcb = g["project_count"], g["pcb_count_with_dnp_lands_and_fiducials"]
        zone_ok = all((v["utilisation_v1_bbox"] or 0) <= 0.62 for k, v in zz.items() if k != "under_fpc_run")
        util_ok = pcb["pass_project"] and pcb["pass_v1"] and g["tall_zone_baseline_convention"]["utilisation_v1"] <= 0.62 and zone_ok
        rows.append(dict(set=name, level=lvl, pod=pod, zone_file=ztag, mode=mode, what=what, cost=cost, seeds=[r["seed"] for r in runs],
                         legal_seeds=[r["seed"] for r in runs if r["legal"]], best_seed=best["seed"], legal=best["legal"], crit_beyond=best["crit"],
                         unplaced=best["unplaced"], jlc_pairs_below_table=best["jlc_pairs"], placement_mm2=g["placement_mm2"],
                         util_project_count=[pc["utilisation_project"], pc["utilisation_v1"]], util_pcb_count=[pcb["utilisation_project"], pcb["utilisation_v1"]],
                         util_v1_direct=[g["v1_measured_directly"]["project_count"], g["v1_measured_directly"]["pcb_count"]],
                         slack_to_062_v1_pcb_mm2=pcb["slack_to_0p62_v1_mm2"], slack_to_062_project_pcb_mm2=pcb["slack_to_0p62_project_mm2"],
                         tall_zone=[g["tall_zone_baseline_convention"]["utilisation_project"], g["tall_zone_baseline_convention"]["utilisation_v1"]],
                         zones={k: [v["utilisation_project"], v["utilisation_v1_bbox"], v["remaining_mm2"]] for k, v in zz.items()},
                         zones_total=[best["z"]["total"]["utilisation_project"], best["z"]["total"]["utilisation_v1_bbox"]],
                         slack_parts=(best["slack"]["C0402"]["extra_parts"], best["slack"]["R0201"]["extra_parts"]) if best["slack"] else None,
                         utilisation_criterion_met=bool(util_ok), per_zone_v1_ok=bool(zone_ok)))
        r = rows[-1]
        if not r["legal"]:
            r["verdict"] = "FAIL (no legal placement under these rules: %d parts without a spot)" % r["unplaced"]
        else:
            miss = []
            if not pcb["pass_project"]: miss.append("project %.3f" % pcb["utilisation_project"])
            if not pcb["pass_v1"]: miss.append("v1 %.3f" % pcb["utilisation_v1"])
            if not zone_ok: miss.append("a height zone above 0.62 on the box measure")
            r["verdict"] = ("PARTIAL (legal placement; 0.62 missed: " + ", ".join(miss) + "; whole-board routing not clean)") if miss else \
                           "PARTIAL (legal placement; 0.62 met on both measures, total and per zone; whole-board routing not shown clean)"
json.dump(dict(modes=MODES, rows=rows), open(WK + "/g1_sets.json", "w"), indent=1)
M = ["| Set | Level | Pod | Rules | Legal placement (seeds legal / run) | Placement area mm² | Utilisation project / v1, project count | Utilisation project / v1, with DNP lands + fiducials | Slack to 0.62 on v1 (with DNP + fid) mm² | Tall zone project / v1 | Height zones 0.55 / low / 1.05: v1 box measure | Still fits (0402 / 0201) | Critical pairs beyond limit | V3-G1 as written |",
     "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
for r in rows:
    zk = [k for k in r["zones"] if k != "under_fpc_run"]
    M.append("| %s | %s | %s | %s | %s (%d / %d) | %.1f | %.3f / %.3f | %.3f / %.3f | %+.1f | %.3f / %.3f | %s | %s | %d | %s |" % (
        r["set"], r["level"], r["pod"], r["mode"], "yes" if r["legal"] else "NO (%d parts without a spot)" % r["unplaced"], len(r["legal_seeds"]), len(r["seeds"]),
        r["placement_mm2"], *r["util_project_count"], *r["util_pcb_count"], r["slack_to_062_v1_pcb_mm2"], *r["tall_zone"],
        " / ".join("%.3f" % r["zones"][k][1] for k in zk), ("+%d / +%d" % r["slack_parts"]) if r["slack_parts"] else "-", r["crit_beyond"], r["verdict"]))
open(WK + "/g1_sets.md", "w").write("\n".join(M) + "\n")
print("\n".join(M))
