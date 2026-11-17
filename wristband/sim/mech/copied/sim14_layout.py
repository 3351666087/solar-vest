"""SIM-14 re-check with the Phase B layout: every placed skin-side part against the height allowance of the zone it
actually sits in, plus the plan-view clearances to the enclosure features, plus the Z-stack chains.

Inputs : layout/work/parts_case.json, layout/work/mech_layout.json (layout/tools/mech_export.py), the thermal-mech
         lane's allowances (sim14_stack.allowances / variant, recommended variant V0-PRODUCT-W, unchanged Z stack).
Zones  : tall zones (0.45 mm back-shell pocket, incl. the layout's far-edge zone) -> 'tall-part zone'; under the E1
         plate (through-opening; plate back face 0.40 mm below the shell inner face [MECH ELECTRODE_T/PROUD]) ->
         general + 0.40 - 0.05 plate tolerance [E]; U7 / L202 0.15 pockets -> 'U7 local pocket'; PPG flange area ->
         'under the PPG window'; anything else -> 'general zone'.
Output : out/sim14_layout.json, out/sim14_layout.md
usage  : venv-python sim14_layout.py
"""
import io, contextlib, json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
W = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(W, "mech")); sys.path.insert(0, os.path.join(W, "layout/tools"))
import numpy as np
with contextlib.redirect_stdout(io.StringIO()):
    import sim14_stack as S
import lgeom as LG
import place_main as P

parts = json.load(open(os.path.join(W, "layout/work/parts_case.json")))
allow = S.allowances(S.dims(ppg="W"))
A_GEN, A_TALL, A_POCK, A_PPG = (allow["general zone"], allow["tall-part zone (0.45 pocket)"],
                                allow["U7 local pocket (0.15)"], allow["under the PPG window"])
A_E1 = A_GEN + 0.40 - 0.05
E1_RECTS = P.TALL[-2:]
TALL_RECTS = P.TALL[:-2]


def cover(b, rects):
    """fraction of rect b covered by the union of non-overlapping rects"""
    a = (b["x1"] - b["x0"]) * (b["y1"] - b["y0"])
    s = 0.0
    for r in rects:
        w = min(b["x1"], r[2]) - max(b["x0"], r[0]); h = min(b["y1"], r[3]) - max(b["y0"], r[1])
        if w > 0 and h > 0:
            s += w * h
    return s / a if a else 0.0


rows, fails = [], []
for q in parts:
    if not q["jlc"] or q["dnp"]:
        continue
    b = q["board"]
    h = q["h_max"]
    if cover(b, TALL_RECTS) > 0.999:
        z, a = "tall-part zone (0.45 pocket)", A_TALL
    elif cover(b, E1_RECTS) > 0.999:
        z, a = "under the E1 plate", A_E1
    elif any(cover(b, [r]) > 0.999 for r in P.POCKETS.values()):
        z, a = "local 0.15 pocket", A_POCK
    elif cover(b, [LG.PPG_ZONE]) > 0:
        z, a = "under the PPG window", A_PPG
    else:
        z, a = "general zone", A_GEN
    ok = h + 1e-9 <= a
    if q["ref"] in ("D3", "D4", "PD1") and z != "under the PPG window":
        ok = False
    if z == "under the PPG window" and q["ref"] not in ("D3", "D4", "PD1"):
        ok = False
    rows.append(dict(ref=q["ref"], h_max=h, zone=z, allowance=round(a, 3), margin=round(a - h, 3), ok=ok))
    if not ok:
        fails.append(rows[-1])

# plan-view clearances to enclosure features (board frame)
def rect_circle_gap(b, c, r):
    dx = max(b["x0"] - c[0], 0, c[0] - b["x1"]); dy = max(b["y0"] - c[1], 0, c[1] - b["y1"])
    return math.hypot(dx, dy) - r

feat = [("standoff post", s, 0.8 + 0.1) for s in LG.STANDOFFS] + [("standoff post (IFA)", LG.STANDOFF_IFA, 0.9)]
feat += [("window-insert leg", l, 0.45 + 0.1) for l in LG.LEGS]
feat += [("E1 spring", LG.E1_SPRING, 1.0 + 0.1), ("E2 spring", LG.E2_SPRING, 1.0 + 0.1)]
plan = []
for q in parts:
    if not q["jlc"] or q["dnp"]:
        continue
    for name, c, r in feat:
        bb = q["board"]; body = dict(x0=bb["x0"] + 0.2, y0=bb["y0"] + 0.2, x1=bb["x1"] - 0.2, y1=bb["y1"] - 0.2)
        g = rect_circle_gap(body, c, r)   # courtyard - 0.2 = pads + body
        if g < 0:
            plan.append(dict(ref=q["ref"], feature=name, overlap_mm=round(-g, 3)))
# E2 pedestal (6 x 6 around the TMP117, 2.4 mm package recess): only U10 under it
cx, cy = LG.TMP117
ped = dict(x0=cx - 3, y0=cy - 3, x1=cx + 3, y1=cy + 3)
under_ped = [q["ref"] for q in parts if q["jlc"] and not q["dnp"] and cover(q["board"], [(ped["x0"], ped["y0"], ped["x1"], ped["y1"])]) > 0]
ped_ok = under_ped == ["U10"] or under_ped == []
with contextlib.redirect_stdout(io.StringIO()):
    v = S.variant("V0-PRODUCT-W (layout re-check)", S.dims(ppg="W"), "", np.random.default_rng(14))
chains = {k: v[k] for k in v if k not in ("dims",)}


def js(x):
    if isinstance(x, dict): return {k: js(w) for k, w in x.items()}
    if isinstance(x, (list, tuple)): return [js(w) for w in x]
    if isinstance(x, (np.floating,)): return float(x)
    if isinstance(x, (np.bool_,)): return bool(x)
    if isinstance(x, float) and math.isnan(x): return None
    return x

# board / PV board outline fit in the cavity (concentric corners), analytic
fit = dict(main_board_corner_clearance_mm=0.2, main_board_note="R4.5 corners in the R4.7 cavity corners; antenna corner R3.0 in an R3.2 cavity corner (L-01)",
           pv_board=dict(size=(LG.PV_W, LG.PV_H), corner_r=LG.PV_R, x0_case=LG.PV_CASE_ORIGIN[0], y0_case=LG.PV_CASE_ORIGIN[1]))
cav = (1.3, 1.3, 38.7, 30.7)
x0, y0 = LG.PV_CASE_ORIGIN; x1, y1 = x0 + LG.PV_W, y0 + LG.PV_H
fit["pv_board"]["edge_clearance_mm"] = dict(left=round(x0 - cav[0], 3), right=round(cav[2] - x1, 3), bottom=round(y0 - cav[1], 3), top=round(cav[3] - y1, 3))
def rrect_pts(x0, y0, x1, y1, R, n=90):
    pts = []
    for (cx, cy, a0) in ((x1 - R, y1 - R, 0), (x0 + R, y1 - R, 90), (x0 + R, y0 + R, 180), (x1 - R, y0 + R, 270)):
        for k in range(n + 1):
            t = math.radians(a0 + 90 * k / n); pts.append((cx + R * math.cos(t), cy + R * math.sin(t)))
    return pts


def sdf_rrect(px, py, x0, y0, x1, y1, R):
    """signed distance to a rounded rectangle (negative inside)"""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hx, hy = (x1 - x0) / 2 - R, (y1 - y0) / 2 - R
    qx, qy = abs(px - cx) - hx, abs(py - cy) - hy
    return math.hypot(max(qx, 0), max(qy, 0)) + min(max(qx, qy), 0) - R


for Rc in (4.7, 2.2):
    pv = rrect_pts(x0, y0, x1, y1, LG.PV_R)
    fit["pv_board"][f"min_clearance_in_cavity_corner_R{Rc}"] = round(min(-sdf_rrect(px, py, *cav, Rc) for px, py in pv), 3)
# cells inside the lens aperture
ap = (2.2, 2.2, 37.8, 29.8)
mech = json.load(open(os.path.join(W, "layout/work/mech_layout.json")))
cells_in = all(c["x0"] >= ap[0] and c["x0"] + c["L"] <= ap[2] and c["y0"] >= ap[1] and c["y0"] + c["W"] <= ap[3] for c in mech["PV_CELLS"])
res = dict(allowances=dict(general=A_GEN, tall=A_TALL, pocket_0p15=A_POCK, ppg=A_PPG, under_E1_plate=round(A_E1, 3)),
           parts_checked=len(rows), height_failures=fails, plan_overlaps=plan, e2_pedestal_parts=under_ped,
           pedestal_ok=ped_ok, cells_inside_lens_aperture=cells_in, outline_fit=fit,
           z_chains_variant_W=js(chains), rows=rows,
           pass_=not fails and not plan and ped_ok and cells_in)
json.dump(js(res), open(os.path.join(HERE, "out/sim14_layout.json"), "w"), indent=1)
with open(os.path.join(HERE, "out/sim14_layout.md"), "w") as fh:
    fh.write("# SIM-14 layout re-check (sim14_layout.py)\n\n")
    fh.write(f"Parts checked: {len(rows)}; height failures: {len(fails)}; plan overlaps with enclosure features: {len(plan)}; "
             f"E2 pedestal parts: {under_ped}; cells inside the lens aperture: {cells_in}. **{'PASS' if res['pass_'] else 'FAIL'}**\n\n")
    fh.write("| ref | h max | zone | allowance | margin | ok |\n|---|---|---|---|---|---|\n")
    for r in sorted(rows, key=lambda r: r["margin"]):
        fh.write(f"| {r['ref']} | {r['h_max']:.2f} | {r['zone']} | {r['allowance']:.2f} | {r['margin']:+.2f} | {'yes' if r['ok'] else 'NO'} |\n")
print(json.dumps({k: res[k] for k in ("allowances", "parts_checked", "height_failures", "plan_overlaps", "e2_pedestal_parts",
                                        "cells_inside_lens_aperture", "pass_")}, indent=1, default=str))
print(json.dumps(js(fit), indent=1))
