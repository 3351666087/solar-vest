"""Independent check of a V3-F placement + gate-1 area bookkeeping (V3-G1).
Re-computes every hard rule from the zone file with exact polygons (shapely); it does not use the placer's raster or its violation list.
usage: venv-python check_placement.py placement.json [out.json]

Hard rules (all must be empty for legal = true):
  courtyard_overlaps      overlap boxes of two sky-side parts closer than the gap rule of the run (gap=v1: pcbnew bounding boxes 0.05 mm
                          apart; gap=dru: F.CrtYd centre lines may touch)
  zone_violations         centre-line courtyard of a movable part outside the board minus the 0.5 mm edge band, on a keep-out / cut-out /
                          no-part zone / post or rail foot / K or J11 zone, or under a height limit below body + 0.05 mm
  plate_violations        NO_PLATE part over an electrode plate (B.Cu / L5 void: no signal via)
  bshadow_violations      NO_BSHADOW part above a skin-face pad
  ecg_violations          movable aggressor closer than 8 mm to an ECG input / electrode item
  anchor_violations       an anchor's courtyard on a zero zone that is not its own, or outside its own CAD part / land zone
Quality rule of this lane, reported next to 'legal' (key legal_and_critical_pairs_within_limits):
  critical_pair_violations a part of place_main.CRIT farther from its IC pin than its limit (switcher inductors, decoupling, crystals,
                          protection diodes at their entry)
  pad_gap_violations      copper pads of two different sky-side parts closer than 0.15 mm (JLC SMD pad gap, different nets)
Reported, not part of 'legal' (fixed by the pod, not by the placement): fixed aggressors (J13, J16, J17) against the ECG items.
Areas: project metric and v1's bounding-box measure as v3/design/tools/area_check.py + the CAD lane's stage-1 convention
(v3/cad/src/options_table.py areas()), with and without DNP lands and sky fiducials; geometric utilisation per height zone.
"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from shapely.geometry import box, Polygon
from shapely.ops import unary_union
import lgeom as G
import place_main as P
from autoplace import load, ov

V1 = 399.5 / 360.7
LIMIT = 0.62
PANEL = 33.0 * 15.0
HAND_LANDS = ("J13", "J16", "J17")
ANCHOR_TOL = 0.0                        # mm per side, anchored part vs its own CAD zone [layout]
FIXED_REFS = ("J3", "J4", "J5", "J10", "J7", "J9", "J6", "J12", "TP1", "TP2", "TP3", "TP4", "TP5")
LID_POSTS_V2 = 12.3
ANCHOR_ZONE = {"SW1": "SW1", "D10": "D10", "J15": "J15_land", "J18": "J18_land", "J11": "J11_land", "J6": "J6_land", "J13": "J13_land",
               "J16": "J16_land", "J17": "J17_zone", "J19": "frame_gnd_land", "U10": "U10_island", "J3": "land_A", "J4": "land_A", "J5": "land_A", "J10": "land_A", "J7": "land_B", "J9": "land_B"}
OWN_ZERO = {"J15": ("K_zone",), "J18": ("K_zone",), "J11": ("J11_zone",), "AE1": ("antenna_keepout",), "J17": ("motor_edge_keepout",),
            "J16": ("film_tail", "rail_foot_X35.3"),   # [S2d] CAD J16_land overlaps the X35.3 foot keep-out margin by 0.15 mm (post body clear): reported in LAYOUT.md
             "J6": ("lid_tail",), "J13": ("fpc_tail", "fpc_corridor"),
            "J19": ("frame_gnd_zone",), "U10": ("U10_island",), "J40": ("antenna_keepout",)}


def pad_rects(o):
    """copper pad boxes of a part in the board frame (rotation in 90 deg steps)"""
    out = []
    r = -o.r if o.side == "B" else o.r
    c, s = round(math.cos(math.radians(r))), round(math.sin(math.radians(r)))
    for num, px, py, w, h in o.padlist:
        x = o.x + px * c - py * s; y = o.y + px * s + py * c
        ww, hh = (w, h) if c != 0 else (h, w)
        out.append((x - ww / 2, y - hh / 2, x + ww / 2, y + hh / 2))
    return out


def rect_gap(a, b):
    dx = max(0.0, max(a[0], b[0]) - min(a[2], b[2])); dy = max(0.0, max(a[1], b[1]) - min(a[3], b[3]))
    return math.hypot(dx, dy)


CHECKED_ANCHORS = {"D15", "Q20"}


def main():
    pl = json.load(open(sys.argv[1]))
    parts, obj, nets = load()
    for r, q in pl["parts"].items():
        if r in obj:
            obj[r].x, obj[r].y, obj[r].r = q["x"], q["y"], q["rot"]
    sky = [r for r in obj if obj[r].side == "F"]
    unplaced = sorted(r for r, v in pl.get("violations", {}).items() if v.get("no_legal_spot"))
    anchors = set(P.ANCHORS) - CHECKED_ANCHORS     # [S2e] D15 / Q20 are fixed by the placer but checked like free parts
    res = dict(variant=G.VARIANT, zones=G.ZTAG, opts=G.OPTS, gap_rule=G.GAPMODE, placement=os.path.basename(sys.argv[1]),
               board_mm=[G.BOARD_W, G.BOARD_H])
    Z, ZP = G.ZONES, G.ZP
    zero = {n: ZP[n] for n, z in Z.items() if z["kind"] in G.ZERO_KINDS}
    zero_u = unary_union(list(zero.values()))
    zero_ufpc = unary_union([p for n, p in zero.items() if n not in G.FPC_RUN])
    hl = {n: (float(z["h_max_mm"]), ZP[n]) for n, z in Z.items() if z["kind"] == "height_limit"}
    cadland = unary_union([ZP[n] for n, z in Z.items() if z["kind"] in ("part", "land")]) if G.CADLANDS else Polygon()

    def allowed(o):
        dead = zero_ufpc if o.ref in P.UFPC_REFS else zero_u
        a = G.INNER.difference(dead).difference(cadland)
        if o.need > 0:
            low = [p for (h, p) in hl.values() if h < o.need - 1e-9]
            if low:
                a = a.difference(unary_union(low))
            if o.need > G.H_GENERAL + 1e-9 and o.ref not in anchors:   # [layout] the general zone limit; [S2d K-3] zones above it (PV half 1.20) allow taller parts
                hi = [p for (h, p) in hl.values() if h >= o.need - 1e-9 and h > G.H_GENERAL]
                a = a.intersection(unary_union(hi)) if hi else Polygon()
        return a

    cache = {}
    # ---- hard rules
    from shapely import affinity

    def cpoly(r):                                   # [S2d] true courtyard polygon (J40 sits at 340 deg; boxes only for 90-degree steps)
        o = obj[r]
        if abs(o.r) % 90 < 1e-6:
            return box(*o.cl())
        return affinity.translate(affinity.rotate(box(*o.cl0), -o.r if o.side == "B" else o.r, origin=(0, 0)), o.x, o.y)

    def gap_between(a, b):
        if abs(obj[a].r) % 90 > 1e-6 or abs(obj[b].r) % 90 > 1e-6:
            pa, pb = cpoly(a), cpoly(b)
            return -1.0 if pa.intersection(pb).area > 1e-6 else pa.distance(pb)
        ca, cb = obj[a].cl(), obj[b].cl()
        dx = max(ca[0], cb[0]) - min(ca[2], cb[2]); dy = max(ca[1], cb[1]) - min(ca[3], cb[3])
        return max(dx, dy)                          # < 0: the centre-line boxes overlap; else the box-to-box gap (Chebyshev, as the placer)
    over, cl_over, jlc_full = [], [], []
    live = [r for r in sky if r not in unplaced]
    for i, a in enumerate(live):
        for b in live[i + 1:]:
            g = gap_between(a, b)
            if g > 2.0:
                continue
            both_anchor = a in anchors and b in anchors
            if {a, b} == {"AE1", "J40"}:
                continue                                    # [S2d] J40 is soldered on AE1's spring land by design (LEAD_NOTES 2i L-1)
            if g < -1e-6:
                cl_over.append((a, b, round(g, 4)))
            need = 0.0 if both_anchor else P.pair_gap(a, b)        # anchor pairs are fixed by the pod (land rows touch by design)
            if g < need - 1e-6:
                over.append((a, b, round(g, 4), round(need, 3)))
            nf = P.pair_gap(a, b, "full")
            if not both_anchor and g < nf - 1e-6 and nf > P.BASE_GAP + 1e-9 and P.jclass(a) and P.jclass(b):
                jlc_full.append((a, b, P.jclass(a), P.jclass(b), round(g + P.margin(a) + P.margin(b), 3)))
    zone, plate, bsh = {}, {}, {}
    bshadow = [box(*obj[r].cl()) for r in obj if obj[r].side == "B"]
    for r in sky:
        if r in anchors or r in unplaced:
            continue
        o = obj[r]
        k = (r in P.UFPC_REFS, round(o.need, 3))
        if k not in cache:
            cache[k] = allowed(o)
        c = box(*o.cl())
        bad = c.area - c.intersection(cache[k]).area
        if bad > 1e-6:
            zone[r] = round(bad, 4)
        if r in P.NO_PLATE:
            a_ = c.intersection(G.PLATE_U).area
            if a_ > 1e-6:
                plate[r] = round(a_, 4)
        if r in P.NO_BSHADOW:
            a_ = sum(c.intersection(b_).area for b_ in bshadow)
            if a_ > 1e-6:
                bsh[r] = round(a_, 4)
        if r in P.ON_PLATE:
            a_ = c.area - c.intersection(G.PLATE_U).area
            if a_ > 1e-6:
                plate[r + " (must be over a plate)"] = round(a_, 4)
    # ---- anchors against the zone file
    anch = {}
    anch_info = {}
    for r in sorted(anchors):
        if obj[r].side != "F":
            continue
        c = cpoly(r)
        own = [n for n in OWN_ZERO.get(r, ())]
        bad = sum(c.intersection(p).area for n, p in zero.items() if n not in own)
        zn = ANCHOR_ZONE.get(r)
        outside = (c.area - c.intersection(ZP[zn].buffer(ANCHOR_TOL, join_style=2)).area) if zn and zn in ZP else 0.0   # [layout] ANCHOR_TOL: J13_land is 7.65 mm, the S2a courtyard 7.66 mm (CAD rounding); reported in LAYOUT.md
        off_board = c.area - c.intersection(G.BOARD).area
        anch_info[r] = dict(courtyard=[round(v, 3) for v in obj[r].cl()], cad_zone=zn, outside_own_zone_mm2=round(outside, 3),
                            on_other_zero_zone_mm2=round(bad, 3), beyond_board_edge_mm2=round(off_board, 3))
        if bad > 1e-3 or (outside - off_board) > 1e-3:
            anch[r] = anch_info[r]
    # ---- ECG distance
    def ept(it):
        return obj[it[0]].pad(it[1]) if isinstance(it, tuple) else (obj[it].x, obj[it].y)
    ecg, ecg_fixed = {}, {}
    dmin = 99.0
    for s in P.SWITCHERS:
        for it in P.ECG_ITEMS:
            q = ept(it); d = math.hypot(obj[s].x - q[0], obj[s].y - q[1]); dmin = min(dmin, d)
            if d < P.ECG_MIN:
                ecg["%s-%s" % (s, it)] = round(d, 2)
    for s in P.FIXED_AGGR:
        for it in P.ECG_ITEMS:
            ref = it[0] if isinstance(it, tuple) else it
            q = ept(it); d = math.hypot(obj[s].x - q[0], obj[s].y - q[1])
            if d < P.ECG_MIN:
                if ref in anchors or (s == "J16" and ref in P.E3_TIED):
                    ecg_fixed["%s-%s" % (s, it)] = round(d, 2)        # both fixed by the pod (or tied to the E3 spring): not a placement choice
                else:
                    ecg["%s-%s" % (s, it)] = round(d, 2)
    # ---- critical proximity pairs of this lane
    crit = []
    for (pp, ic, pad, dm) in P.CRIT:
        if pp in unplaced or ic in unplaced:
            continue
        tx, ty = obj[ic].pad(pad)
        d = min(math.hypot(px - tx, py - ty) for px, py in (obj[pp].pad(k) for k in obj[pp].pads0))
        if d > dm + 1e-6:
            crit.append((pp, ic, round(d, 2), dm))
    # ---- copper pad gap between different sky parts (JLC SMD pad gap 0.15 mm)
    pr = {r: pad_rects(obj[r]) for r in sky if r not in unplaced}
    bbx = {r: obj[r].bb() for r in pr}
    padgap = []
    pmin = (99.0, None)
    keys = sorted(pr)
    for i, a in enumerate(keys):
        for b in keys[i + 1:]:
            if rect_gap(bbx[a], bbx[b]) > 0.6:
                continue
            g = min(rect_gap(x, y) for x in pr[a] for y in pr[b])
            if g < pmin[0]:
                pmin = (g, (a, b))
            if g < G.JLC["smd_pad_gap"] - 1e-9:
                padgap.append((a, b, round(g, 3)))
    # ---- [S2e N-4] LEAD_NOTES 2j J-2 (Q20's drain land faces J18) and J-3 (D15's courtyard within 1 mm of J18's)
    j23 = {}
    if all(r in obj for r in ("Q20", "J18", "D15")):
        qd = obj["Q20"].pad("2"); qs = [obj["Q20"].pad(k) for k in ("1", "3")]
        qc = ((qs[0][0] + qs[1][0]) / 2, (qs[0][1] + qs[1][1]) / 2)
        v1 = (qd[0] - qc[0], qd[1] - qc[1]); v2 = (obj["J18"].x - obj["Q20"].x, obj["J18"].y - obj["Q20"].y)
        ang = math.degrees(math.acos(max(-1, min(1, (v1[0] * v2[0] + v1[1] * v2[1]) / math.hypot(*v1) / math.hypot(*v2)))))
        dg = cpoly("D15").distance(cpoly("J18"))
        res["J2_J3"] = dict(Q20_drain_pad=[round(qd[0], 3), round(qd[1], 3)], Q20_drain_vs_J18_direction_deg=round(ang, 1),
                            D15_J18_courtyard_gap_mm=round(dg, 3))
        if ang > 60.0:
            j23["J-2 Q20 drain land does not face J18"] = round(ang, 1)
        if dg > 1.0 + 1e-6:
            j23["J-3 D15 courtyard > 1 mm from J18"] = round(dg, 3)
    res["hard"] = dict(courtyard_overlaps=over, zone_violations=zone, plate_violations=plate, bshadow_violations=bsh, ecg_violations=ecg,
                       anchor_violations=anch, pad_gap_violations=padgap, critical_pair_violations=crit, no_legal_spot=unplaced, j2_j3_violations=j23)
    res["legal"] = not (over or zone or plate or bsh or ecg or anch or padgap or unplaced or j23)
    res["legal_and_critical_pairs_within_limits"] = res["legal"] and not crit
    by = {}
    for a, b, ca, cb, d in jlc_full:
        k = "-".join(sorted((str(ca), str(cb)))); by.setdefault(k, [0, 9.9]); by[k][0] += 1; by[k][1] = min(by[k][1], d)
    res["jlc_spacing_table"] = dict(source="jlcpcb.com/help/article/minimum-spacing-for-smd-components (updated 2026-09-09; read 2026-11-12 and 2026-11-15)",
                                    mode_enforced=P.JLC_MODE, pairs_below_the_recommended_table=len(jlc_full),
                                    by_class_pair={k: dict(pairs=v[0], smallest_envelope_gap_mm=v[1]) for k, v in sorted(by.items())},
                                    pairs=jlc_full[:400])
    res["info"] = dict(centre_line_courtyard_overlaps=cl_over, ecg_min_distance_movable_mm=round(dmin, 2), ecg_fixed_feature_conflicts=ecg_fixed,
                       min_pad_gap_mm=round(pmin[0], 3), min_pad_gap_pair=pmin[1], anchors=anch_info)

    # ---- gate-1 metric (area_check.py + the CAD lane's stage-1 convention)
    def A(refs, bb=False):
        return sum((obj[r].area_bb() if bb else (parts[r].get("courtyard_area_mm2") or obj[r].area())) for r in refs)
    placed = [r for r in sky if parts[r].get("jlc_placed")]
    hand = [r for r in sky if r in HAND_LANDS]
    dnp = [r for r in sky if parts[r].get("dnp")]
    fid = [r for r in sky if parts[r]["kind"] == "fid"]
    fixed_refs = [r for r in FIXED_REFS if r in parts]
    ufpc_fixed = [r for r in fixed_refs if r in P.UFPC_REFS]            # under the FPC run: no placement area used
    ufpc_fid = [r for r in fid if r in P.UFPC_REFS]
    fixed = sum(parts[r]["courtyard_area_mm2"] for r in fixed_refs if r not in ufpc_fixed) + LID_POSTS_V2
    ca = G.cad_areas(fixed)
    pa = ca["placement_stage1_convention_mm2"]
    cy = A(placed) + A(hand)
    cy_pcb = cy + A(dnp) + A([r for r in fid if r not in ufpc_fid])
    cy_bb = A(placed, True) + A(hand, True)
    cy_pcb_bb = cy_bb + A(dnp, True) + A([r for r in fid if r not in ufpc_fid], True)
    tall = sum(parts[r]["courtyard_area_mm2"] for r in placed if (parts[r].get("height_max_mm") or 0) > 0.70)
    za = pa + ca["cad_only_mm2"] - PANEL
    def row(c):
        return dict(courtyard_mm2=round(c, 1), utilisation_project=round(c / pa, 3), utilisation_v1=round(c / pa * V1, 3),
                    pass_project=c / pa <= LIMIT, pass_v1=c / pa * V1 <= LIMIT,
                    courtyard_that_fits_at_0p62_project_mm2=round(pa * LIMIT, 1), courtyard_that_fits_at_0p62_v1_mm2=round(pa * LIMIT / V1, 1),
                    slack_to_0p62_project_mm2=round(pa * LIMIT - c, 1), slack_to_0p62_v1_mm2=round(pa * LIMIT / V1 - c, 1))
    res["gate1_metric"] = dict(
        convention="placement = board - 0.5 mm edge band - antenna 15 - fixed features - motor cut-out - 6 post feet - CAD-only no-part features "
                   "(v3/cad/src/options_table.py areas(), v3/design/tools/area_check.py); utilisation = courtyard / placement; v1 = x 399.5 / 360.7; limit 0.62",
        placement_mm2=pa, fixed_features_mm2=round(fixed, 1), cad=ca, under_fpc_refs=sorted(P.UFPC_REFS),
        project_count=row(cy), pcb_count_with_dnp_lands_and_fiducials=row(cy_pcb),
        v1_measured_directly=dict(note="sum of pcbnew courtyard bounding boxes / placement (this part mix: x %.3f instead of x 1.108)" % (cy_bb / cy),
                                  project_count=round(cy_bb / pa, 3), pcb_count=round(cy_pcb_bb / pa, 3)),
        tall_zone_baseline_convention=dict(tall_courtyard_mm2=round(tall, 1), tall_zone_mm2=round(za, 1), utilisation_project=round(tall / za, 3),
                                           utilisation_v1=round(tall / za * V1, 3)),
        pass_both_project_count=bool(cy / pa * V1 <= LIMIT), pass_both_pcb_count=bool(cy_pcb / pa * V1 <= LIMIT))

    # ---- geometric utilisation per height zone, from the real placement
    anch_boxes = unary_union([box(*obj[r].cl()) for r in anchors if obj[r].side == "F"])
    base = G.INNER.difference(zero_u)
    levels = sorted({h for h, _ in hl.values()})
    regs, taken = {}, Polygon()
    for h in levels:
        g = unary_union([p for (hh, p) in hl.values() if abs(hh - h) < 1e-9]).difference(taken).intersection(base)
        regs["%.2f" % h] = g; taken = taken.union(unary_union([p for (hh, p) in hl.values() if abs(hh - h) < 1e-9]))
    regs["%.2f" % G.H_GENERAL] = base.difference(taken)
    if P.UFPC_REFS:
        regs["under_fpc_run"] = unary_union([ZP[n] for n in G.FPC_RUN]).intersection(G.INNER)
    zrep = {}
    mov = [r for r in sky if r not in anchors and r not in unplaced]
    for k, reg in regs.items():
        free = reg.difference(anch_boxes)
        occ = sum(box(*obj[r].cl()).intersection(reg).area for r in mov)
        occ_bb = sum(box(*obj[r].bb()).intersection(reg).area for r in mov)
        anc = sum(box(*obj[r].cl()).intersection(reg).area for r in anchors if obj[r].side == "F")
        zrep[k] = dict(region_mm2=round(reg.area, 1), anchors_mm2=round(anc, 1), free_for_movable_mm2=round(free.area, 1),
                       movable_courtyard_mm2=round(occ, 1), movable_bbox_mm2=round(occ_bb, 1),
                       utilisation_project=round(occ / free.area, 3) if free.area > 0 else None,
                       utilisation_v1_bbox=round(occ_bb / free.area, 3) if free.area > 0 else None,
                       remaining_mm2=round(free.area - occ, 1),
                       parts=len([r for r in mov if box(*obj[r].cl()).centroid.within(reg)]))
    tf = sum(v["free_for_movable_mm2"] for k, v in zrep.items()); to = sum(v["movable_courtyard_mm2"] for v in zrep.values())
    tb = sum(v["movable_bbox_mm2"] for v in zrep.values())
    res["zones_geometric"] = dict(note="free = zone inside the edge band minus keep-outs, no-part zones and anchor courtyards; movable = every sky-side "
                                       "courtyard the annealer places (JLC parts, DNP lands, test pads, SWD group, fiducials)",
                                  by_h_max=zrep, total=dict(free_for_movable_mm2=round(tf, 1), movable_courtyard_mm2=round(to, 1),
                                                            utilisation_project=round(to / tf, 3), utilisation_v1_bbox=round(tb / tf, 3)))
    # ---- inventory
    over_plate = sorted(r for r in mov if parts[r].get("jlc_placed") and box(*obj[r].cl()).intersection(G.PLATE_U).area > 0.05)
    res["over_plates"] = dict(n=len(over_plate), not_in_plate_ok=sorted(r for r in over_plate if r not in P.PLATE_OK))
    res["counts"] = dict(sky=len(sky), movable=len(mov), anchors_sky=len([r for r in anchors if obj[r].side == "F"]), jlc_placed_sky=len(placed))
    res["wl_hpwl_mm"] = round(sum((max(p[0] for p in pts) - min(p[0] for p in pts)) + (max(p[1] for p in pts) - min(p[1] for p in pts))
                                  for pts in ([obj[r].pad(n) for r, n in v] for v in nets.values())), 1)
    if len(sys.argv) > 2:
        json.dump(res, open(sys.argv[2], "w"), indent=1)
    h = res["hard"]
    print("LEGAL" if res["legal"] else "NOT LEGAL", "| overlaps %d zone %d plate %d bshadow %d ecg %d anchor %d padgap %d critical-pair %d unplaced %d %s" % (
        len(h["courtyard_overlaps"]), len(h["zone_violations"]), len(h["plate_violations"]), len(h["bshadow_violations"]), len(h["ecg_violations"]),
        len(h["anchor_violations"]), len(h["pad_gap_violations"]), len(crit), len(unplaced), unplaced))
    for k in ("courtyard_overlaps", "zone_violations", "plate_violations", "anchor_violations", "pad_gap_violations", "ecg_violations", "critical_pair_violations"):
        if h[k]:
            print("  ", k, str(h[k])[:600])
    g = res["gate1_metric"]
    print("gate-1 metric: placement %.1f mm2 | project count %.1f mm2 -> %.3f / %.3f | PCB count (DNP lands + fiducials) %.1f mm2 -> %.3f / %.3f | v1 measured directly %.3f / %.3f | tall zone %.3f / %.3f" % (
        pa, g["project_count"]["courtyard_mm2"], g["project_count"]["utilisation_project"], g["project_count"]["utilisation_v1"],
        g["pcb_count_with_dnp_lands_and_fiducials"]["courtyard_mm2"], g["pcb_count_with_dnp_lands_and_fiducials"]["utilisation_project"],
        g["pcb_count_with_dnp_lands_and_fiducials"]["utilisation_v1"], g["v1_measured_directly"]["project_count"], g["v1_measured_directly"]["pcb_count"],
        g["tall_zone_baseline_convention"]["utilisation_project"], g["tall_zone_baseline_convention"]["utilisation_v1"]))
    for k, v in zrep.items():
        print("  zone h<=%s: free %.1f, movable %.1f (bbox %.1f) -> %s / %s, remaining %.1f mm2, parts %d" % (
            k, v["free_for_movable_mm2"], v["movable_courtyard_mm2"], v["movable_bbox_mm2"], v["utilisation_project"], v["utilisation_v1_bbox"],
            v["remaining_mm2"], v["parts"]))
    j = res["jlc_spacing_table"]
    print("  JLC spacing table (mode %s): %d pairs below the recommended minimum %s" % (j["mode_enforced"], j["pairs_below_the_recommended_table"], j["by_class_pair"]))
    print("  info: centre-line overlaps %d, min pad gap %.3f mm %s, ECG min (movable) %.2f mm, fixed-feature ECG conflicts %s, over plates %d (not PLATE_OK %d)" % (
        len(cl_over), pmin[0], pmin[1], dmin, ecg_fixed, res["over_plates"]["n"], len(res["over_plates"]["not_in_plate_ok"])))


if __name__ == "__main__":
    main()
