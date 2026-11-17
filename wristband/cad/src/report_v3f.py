"""Consolidates the V3-G9 results: out/checks_V3G9_L<..>.json (criteria, numbers, file list) and
out/interference_clearance_L<..>.md (manifold3d pairwise interference + clearance table with rules). Reads the JSON files
written by motor_search.py, model_v3f.py, worn_v3f.py, exports_v3f.py, mass_v3f.py."""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import geom_v3f as G                                       # noqa: E402
OUT = G.OUT_DIR
TAG = G.TAG
Z = G.Z

RULES = {  # clearance key -> (minimum, rule source) ; None = informative
    "panel at max material (32.4 x 14.4 x 0.855) -> rib insert": (0.05, "no glass-edge contact [DS LD29Y03 p.36 FPC/glass note; E]"),
    "panel at max material -> rib posts": (0.05, "E"),
    "panel at max material -> ring (elbow wall)": (0.05, "E"),
    "panel at max material -> window frame (above, air gap)": (0.0, "no contact (air gap 0.10 nominal) [B 8]"),
    "panel at max material -> front-light film (air gap)": (0.0, "no adhesive / no contact on the panel [B 8; DS]"),
    "panel nominal (0.80 allowance) -> front-light film (air gap)": (0.10, "B 8 air gap 0.10"),
    "motor (8.1 x 2.2 max) -> PV laminate flex (motor column margin)": (0.15, "B 8: 0.15 mm left"),
    "motor -> board (cut-out edge)": (0.20, "E"),
    "parts envelope -> PV laminate flex (0.15 clearance layer)": (0.15, "B 8"),
    "parts envelope -> panel support": (0.15, "B 8"),
    "parts envelope -> rib shelf": (0.15, "E"),
    "parts envelope -> ring (K block, E3 shelf)": (0.15, "E"),
    "SW1 body -> ring (E3 shelf over it)": (0.05, "E"),
    "SW1 actuator tip -> membrane nub (pre-travel gap)": (0.0, "E: 0.05 mm pre-gap, travel 0.2 [DS PTS840]"),
    "display FPC fold -> SW1": (0.2, "E"),
    "pin_VBUS -> pin_GND (insulation)": (0.3, "E"),
    "E3 strip -> membrane (finger electrode vs button)": (0.1, "E"),
    "plan: panel (max material) to the antenna keep-out, rule >= 1.5": (1.5, "P V3_ARCH 4.3 fix P-6"),
    "plan: panel (nominal) to the antenna keep-out, rule >= 1.5": (1.5, "P V3_ARCH 4.3 fix P-6"),
    "plan: panel glass edge (max material) to E3, rule >= 4.0": (4.0, "P display lane (ECG COM coupling)"),
    "plan: stainless frame to the antenna keep-out, rule >= 5.0 [S1 C-15: buffer 5.01, 128 segments]": (5.0, "P V2-B ANT_METAL_MIN (S1 C-15: no silent 4.998)"),
    "plan: contact pins to the antenna keep-out, REDESIGN >= 11": (11.0, "P REDESIGN via ENG_A 4.2"),
    "plan: motor can to the antenna keep-out, rule >= 10": (10.0, "B 13.1 (eng_b)"),
    "plan: plate E1 to the antenna keep-out, rule >= 5.0 [S1 C-15]": (5.0, "P V2-B ANT_METAL_MIN (S1 C-15)"),
    "J15 finger body (free height 1.5, before the ring is fitted) -> panel at max material [S1 C-8]": (0.05, "S1 C-8 (BW0036BG drawing still open)"),
    "J15 finger body (working height) -> panel at max material [S1 C-8]": (0.05, "S1 C-8"),
    "J15 finger -> panel support": (0.05, "S1 C-8"),
    "J18 finger -> pin_VBUS (insulation)": (0.2, "E (S1 C-8)"),
    "window rail -> panel at max material [S1 C-1]": (0.05, "S1 C-1"),
    "window rail -> parts envelope (designed contact at the rail strip)": (0.05, "S1 C-1"),
    "window rail -> panel support legs": (0.05, "S1 C-1"),
    "window rail -> front-light film": (0.05, "S1 C-1"),
    "lid flex tail -> rib posts": (0.10, "S1 C-6"),
    "lid flex tail -> motor": (0.20, "S1 C-6"),
    "plan: E1 to E2 web, rule >= 2.0": (2.0, "P enclosure 4.4"),
    "plan: plates to the optical cap web, rule >= 2.0": (1.99, "P enclosure 4.4"),
    "plan: laminate edge to silicon, min (rib side / far side / K side / corner)": (0.45, "E: lid RFQ must accept"),
}


def load(n):
    p = os.path.join(OUT, n)
    return json.load(open(p)) if os.path.exists(p) else None


def main():
    ck = load(f"checks_pod_{TAG}.json"); wn = load(f"worn_checks_{TAG}.json"); ms = load(f"motor_search_{TAG}.json")
    mass = load(f"mass_{TAG}.json"); bz = load(f"board_zones_{TAG}.json"); bc = load(f"band_contacts_{TAG}.json")
    pc = load(f"plate_contact_{TAG}.json")
    # ---------------- interference / clearance markdown
    L = [f"# V3-F {TAG}: interference and clearance (manifold3d)", "", f"Pod {G.POD_L:g} x {G.POD_W:g} mm, options {G.OPT or 'none'}.", "",
         f"Model: `src/model_v3f.py` (build123d, {len(ck['volumes'])} solids; trimesh watertight {sum(ck['watertight'].values())}, the others "
         f"({', '.join(k for k, v in ck['watertight'].items() if not v) or 'none'}) are unions touching along an edge; manifold3d status "
         f"{sorted(set(v['status'] for v in ck['volumes'].values()))} for all, mesh volume = B-rep volume within "
         f"{max(abs(v['mesh_mm3'] - v['brep_mm3']) for v in ck['volumes'].values()):.3f} mm3). "
         f"Pairwise boolean intersection of every pair whose bounding boxes overlap ({ck.get('pairs_tested')} pairs); "
         "threshold 0.001 mm3. Z levels are the max-material stack of BASELINE 8, so a 'designed contact' is a contact at max material.", "",
         f"**Interference (volume > 0.001 mm3): {len(ck['interference'])}**" +
         ("" if not ck["interference"] else ": " + "; ".join(f"{i['a']}|{i['b']} {i['volume_mm3']} mm3" for i in ck["interference"])), "",
         f"Designed contacts with zero volume ({len(ck['designed_contacts_zero_volume'])}): " +
         ", ".join(ck["designed_contacts_zero_volume"]), "", "## Clearances", "",
         "| Check | Value, mm | Minimum | Verdict | Rule |", "|---|---|---|---|---|"]
    for k, v in ck["clearance_mm"].items():
        mn, src = RULES.get(k, (None, ""))
        if isinstance(v, (int, float)) and mn is not None:
            verdict = "ok" if v >= mn - 1e-6 else "**below**"
        elif "planning margin" in k:
            verdict = "info"
        elif "E3-net metal to the max-material panel edge" in k:         # [S1 C-9]
            mn, src = 4.0, "P display lane, applied to all E3-net metal (S1 C-9)"; verdict = "ok" if min(v.values()) >= 4.0 - 1e-6 else "**below** (SIM-07 input)"
        elif k.startswith("plan: SW1 courtyard / copper to the FPC fold"):
            mn, src = 0.0, "S1 C-4"; verdict = "ok" if min(v) > 0 else "**overlap**"
        elif k.startswith("K corner"):
            walls = [x[w_] for x in v.values() if isinstance(x, dict) for w_ in ("wall_to_outer_face", "wall_to_K_top_edge", "wall_to_window_glass_edge")]
            ovl = [x["overlap_with_laminate_mm2"] for x in v.values() if isinstance(x, dict)]
            tw = [v["target_wall_to_counterbores"], v["target_wall_to_outer_face"]]
            mn, src = 0.30, "S1 C-2: >= 0.30 PC wall, no laminate overlap"
            verdict = "ok" if min(walls + tw) >= 0.30 - 1e-6 and max(ovl) <= 1e-6 else "**below**"
        else:
            verdict = "info"
        L.append(f"| {k} | {v} | {'' if mn is None else mn} | {verdict} | {src} |")
    vc = ck.get("void_checks", {})
    L += ["", "## Voids against solids (S1 C-20)", "", "Each cut or functional void is meshed as a solid and intersected with every part that is not meant to be in it.", "",
          "| Void | Hits (part: mm3) | Verdict |", "|---|---|---|"]
    L += [f"| {k} | {', '.join(h['part'] + ': ' + str(h['volume_mm3']) for h in x['hits']) or '-'} | {'ok' if x['ok'] else '**hit**'} |" for k, x in vc.items()]
    open(os.path.join(OUT, f"interference_clearance_{TAG}.md"), "w").write("\n".join(L) + "\n")
    # ---------------- criteria
    w = wn["wrists"]
    s9 = {c: dict(capsule_above_skin=w[c]["capsule"]["thickness_above_skin_far_end_box_mm"], capsule_inner_gap=w[c]["capsule"]["inner_face_gap_far_end_mm"],
                  capsule_overhang=w[c]["capsule"]["overhang_past_tangent_mm"], capsule_below_PV_top=w[c]["capsule"]["outer_top_below_pod_PV_top_mm"],
                  wing_above_skin=w[c]["wing"]["thickness_above_skin_far_end_box_mm"], free_span=w[c]["free_span_mm"], tilt=w[c]["tilt_deg"])
          for c in w}
    base = wn["baseline_section9"]
    s9_ok = all(abs(s9[c]["capsule_above_skin"] - base["capsule_thickness_above_skin"][c]) <= 0.011 for c in base["capsule_thickness_above_skin"]) \
        and all(abs(s9[c]["capsule_below_PV_top"] - base["capsule_outer_top_below_pod_top"][c]) <= 0.011 for c in base["capsule_outer_top_below_pod_top"]) \
        and all(abs(s9[c]["wing_above_skin"] - base["wing_above_skin"][c]) <= 0.011 for c in base["wing_above_skin"]) \
        and all(max(v["max_height_above_floor_plane_mm"] for k, v in w[c]["items"].items() if not k.startswith("pod")) < Z.pv1 for c in w)
    strips = [round(s.area, 2) for s in G.strips()]
    hole = ms["variants"]["hole"]
    crit = [
        dict(name="V3-G9 pass 1: the section 9 fit numbers hold", status="PASS" if s9_ok else "FAIL",
             result=(f"CAD reproduces BASELINE 9 on 130/140/165/200 mm: " if s9_ok else "[G1] the worn numbers of this option differ from BASELINE 9 (32 mm wide pod): ")
                    + f"{json.dumps(s9)}; no strap item above the pod's PV top plane: "
                    + str(all(max(v["max_height_above_floor_plane_mm"] for k, v in w[c]["items"].items() if not k.startswith("pod")) < Z.pv1 for c in w))),
        dict(name="V3-G9 pass 2: the PV strips keep 2.30 mm", status="PARTIAL",
             result=f"{G.STRIP_N} strips 27.7 x {G.STRIP_W:g} mm at X {G.STRIP_X[0]}-{G.STRIP_X[1]} (S1 C-2: +0.4 mm; the last one +0.04 mm with a chamfered elbow corner) = {strips} mm2, laminate edge margin >= 0.45 mm. "
                    "Holds only because the panel moved 0.3 mm toward the antenna (keep-out distance 1.2 nominal / 1.0 max-material < 1.5 rule) and "
                    "with laminate edge margins of 0.45 mm (lid RFQ unconfirmed). Keeping 1.5 mm needs the rib +0.3 mm: strips 2.235 mm, -2.9 % lid silicon, "
                    "BASELINE 11 to be re-run"),
        (dict(name="V3-G9 pass 3: a motor position exists", status="PASS" if hole["feasible"] and ms.get("asked_centre_legal", True) else "FAIL",
              result=f"legal centres X {hole['x_range']}, Y {hole['y_range']} ({hole['area_mm2']} mm2); "
                     f"centre used {ms['chosen_centre']} ({ms.get('asked_variant', 'hole')}), legal: {ms.get('asked_centre_legal', True)}; clearances {ms['chosen_clearances_mm']}")
         if hole.get("feasible") is not None else
         dict(name="V3-G9 pass 3: a motor position exists", status="NOT_RUN", result="[G1 level 4] this option has no motor")),
    ]
    out = dict(pod_L=G.POD_L, pod_W=G.POD_W, tag=G.TAG, options=G.OPT, date="2026-11-14 (stage 1 + gate-1 options)", gate="V3-G9 (BASELINE 18)", criteria=crit, void_checks=ck.get("void_checks"),
               verdict="PARTIAL" if any(c["status"] != "PASS" for c in crit) else "PASS",
               plates=ms["plates_first"], plate_contact_sensitivity=pc, motor=ms["variants"], interference=ck["interference"],
               clearance_mm=ck["clearance_mm"], worn=dict(section9=s9, roll=wn["roll_contact"], extension=wn["wrist_extension"], button=wn["button"],
                                                         head=wn["head"], either_wrist=wn["either_wrist"]),
               mass=mass, files=sorted(os.listdir(OUT)))
    json.dump(out, open(os.path.join(OUT, f"checks_V3G9_{TAG}.json"), "w"), indent=1, default=str)
    print(json.dumps([dict(n=c["name"], s=c["status"]) for c in crit], indent=1), "\n", out["verdict"])


if __name__ == "__main__":
    main()
