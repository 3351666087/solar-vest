"""V3-G9 item 2: search every legal centre of the 8 mm ERM and its 8.6 mm board cut-out on the V3-F floor plan.

Plates are fixed first (geom_v3f.plate_outlines, no motor input). Constraints, each as a clearance that must be >= 0
(all in the case frame, mm; sources in geom_v3f):
  c_board   cut-out (r 4.3) inside the board outline with the 0.5 mm edge band            [B 7]
  c_posts   cut-out to each of the 6 rib-post foot pads (1.0 x 1.0) >= 0.3                [B 5.1; P CU_EDGE]
  c_landA   cut-out to the root-A entry lands (X 4.5-10.5, Y 29.0-30.5) >= 0.3            [B 7]
  c_kzone   cut-out to the J15 / K-block zone >= 0.3                                      [B 7]
  c_cap     cut-out to the optical-cap zone (skin-face optics) >= 0.3                     [B 7]
  c_rib     motor body (r 4.05 max) clear of the rib shelf (Y 21.0) by 0.10 in plan       [E: rib shelf at Z 2.15 < motor top 2.50]
  c_plates  motor body to E1 / E2 >= 1.0 in plan                                          [E]
  c_film    carrier-film cut-away (r 4.3) to E1 / E2 >= 0.5                               [E]
  c_ant     motor body to the antenna keep-out >= 10 mm                                   [B 13.1, eng_b]
  c_cavity  motor body inside the cavity wall by 0.1 (only binding for the notch variant) [E]
Two board variants: 'hole' (BASELINE: closed 8.6 mm cut-out, leaves a strip to the far board edge) and 'notch' (the cut-out
opened to the far edge, V3-G1 option). Writes out/motor_search.json and out/motor_search.png.
"""
import json, math, os, sys
import numpy as np
import shapely
from shapely.geometry import Point, box as sbox
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import geom_v3f as G   # noqa: E402

OUT = G.OUT_DIR                                             # [G1] out/ for plain outlines, out/options/<TAG>/ for option runs
TAG = G.TAG
R_CUT, R_MOT = G.MOTOR["cut_d"] / 2, G.MOTOR["d_max"] / 2


def obstacles():
    e1, e2 = G.plate_outlines()
    posts = [sbox(x - 0.5, G.POST_FOOT[0], x + 0.5, G.POST_FOOT[1]) for x in G.POST_X]
    la = G.LAND_A; kz = G.K_ZONE
    j6 = sbox(G.J6["x0"], G.LID_TAIL["y0"], G.J6["x1"], G.J6["y1"])          # [S1 C-6] lid flex tail + J6 land
    dots = shapely.union_all([Point(*d["centre"]).buffer(d["d"] / 2, quad_segs=32) for d in G.plate_dot_pads()])   # [S2d] plate-dot film openings
    return dict(e1=e1, e2=e2, dots=dots, posts=shapely.union_all(posts), landA=sbox(la[0], la[2], la[1], la[3]), j6=j6,
                kzone=sbox(kz[0], kz[2], kz[1], kz[3]), cap=G.cap_poly(), ant=G.keepout_poly(),
                board_in=G.board_outline().buffer(-G.BOARD_EDGE_BAND, quad_segs=32), cav=G.cavity())


def clearances(xc, yc, ob, variant="hole", with_j6=True):
    P = shapely.points(np.c_[xc.ravel(), yc.ravel()])
    def dist(g): return shapely.distance(P, g).reshape(xc.shape)
    c = {}
    inside = shapely.contains(ob["board_in"], P).reshape(xc.shape)
    d_edge = shapely.distance(P, ob["board_in"].exterior).reshape(xc.shape)
    if variant == "hole":
        c["c_board"] = np.where(inside, d_edge - R_CUT, -d_edge - R_CUT)
    else:   # notch: the cut-out runs out through the far board edge; only the near side and the ends must stay in the board
        c["c_board"] = np.where(inside, np.minimum(d_edge - R_CUT, 0) * 0 + np.inf, -np.inf)
        c["c_board"] = np.where(inside | (yc > G.BOARD["y1"] - R_CUT - G.BOARD_EDGE_BAND), np.inf, -1.0)
        c["c_cavity"] = (shapely.distance(P, ob["cav"].exterior).reshape(xc.shape) - R_MOT - 0.1) * np.where(
            shapely.contains(ob["cav"], P).reshape(xc.shape), 1, -1)
    c["c_posts"] = dist(ob["posts"]) - R_CUT - G.CUT_EDGE_CLR
    c["c_landA"] = dist(ob["landA"]) - R_CUT - G.CUT_EDGE_CLR
    if with_j6:
        c["c_J6"] = dist(ob["j6"]) - R_CUT - G.CUT_EDGE_CLR
    c["c_kzone"] = dist(ob["kzone"]) - R_CUT - G.CUT_EDGE_CLR
    c["c_cap"] = dist(ob["cap"]) - R_CUT - G.CUT_EDGE_CLR
    c["c_rib"] = (yc - R_MOT) - (G.RIB["y1"] + G.RIB_MOTOR_CLR)
    if G.S2D:   # [S2d K-1] motor over plate E2 on the kept film: >= 1.0 mm to every plate-dot opening, cut-out wholly on E2's side of the strip,
        #   motor body clear of the E3 block's PV-half shelf (Z 2.15 < motor top) by 0.10 in plan (as the rib)
        c["c_dots"] = dist(ob["dots"]) - R_MOT - 1.0
        c["c_overE2"] = (xc - R_CUT) - ob["e2"].bounds[0]
        c["c_e3shelf"] = (G.E3_BLOCK["x0"] - G.RIB_MOTOR_CLR) - (xc + R_MOT)
    else:
        c["c_plates"] = np.minimum(dist(ob["e1"]), dist(ob["e2"])) - R_MOT - G.MOTOR_PLATE_CLR
        c["c_film"] = np.minimum(dist(ob["e1"]), dist(ob["e2"])) - R_CUT - 0.5
    c["c_ant"] = dist(ob["ant"]) - R_MOT - G.MOTOR_ANT_MIN
    return c


def run():
    ob = obstacles()
    xs = np.arange(8.0, (G.POD_L if G.S2D else 32.0) + 1e-9, 0.05); ys = np.arange(20.0, 29.0 + 1e-9, 0.025)
    xc, yc = np.meshgrid(xs, ys)
    res = {}
    for variant in ("hole", "notch"):
        c = clearances(xc, yc, ob, variant, with_j6=not G.S2D)   # [S2d] J6 is placed beside the chosen motor, tested below
        ok = np.ones_like(xc, bool)
        for k, v in c.items():
            ok &= v >= -1e-9
        binding = {k: float(np.nanmax(np.where(ok, v, np.nan))) if ok.any() else None for k, v in c.items()}
        if ok.any():
            X, Y = xc[ok], yc[ok]
            # most central point: maximise the smallest clearance among the motor-specific constraints
            m = np.min(np.stack([np.where(ok, np.clip(c[k], 0, 5), -1) for k in c]), axis=0)
            i = np.unravel_index(np.argmax(np.where(ok, m, -1)), xc.shape)
            best = (float(xc[i]), float(yc[i]))
            ycols = sorted(set(np.round(Y, 3)))
            xmax = float(X.max()); ys_at = Y[np.abs(X - (xmax - 0.10)) < 1e-6]
            res[variant] = dict(s2d_rule_point=(round(xmax - 0.10, 2), round(float((ys_at.min() + ys_at.max()) / 2), 3)) if ys_at.size else None, feasible=True, n_points=int(ok.sum()), area_mm2=round(float(ok.sum()) * 0.05 * 0.025, 2),
                                x_range=(round(float(X.min()), 2), round(float(X.max()), 2)),
                                y_range=(round(float(Y.min()), 3), round(float(Y.max()), 3)),
                                x_range_at_y25p4=(lambda s: (round(float(s.min()), 2), round(float(s.max()), 2)) if s.size else None)(X[np.abs(Y - 25.4) < 1e-6]),
                                max_min_clearance_point=best, min_clearance_there=round(float(m[i]), 3))
        else:
            res[variant] = dict(feasible=False)
        res[variant]["constraints_at_baseline_point_20_25p4"] = {
            k: round(float(np.ravel(v)[0]), 3) for k, v in clearances(np.array([[20.0]]), np.array([[25.4]]), ob, variant).items()
            if np.isfinite(np.ravel(v)[0])}
        res[variant]["_ok"] = ok
        res[variant]["_c"] = c
    # chosen position: BASELINE's planning centre if it is legal for the hole variant (it keeps the spec), else the best
    hole = res["hole"]
    base_ok = all(v >= 0 for v in hole["constraints_at_baseline_point_20_25p4"].values())
    chosen = (20.0, 25.4) if base_ok else (hole.get("max_min_clearance_point") if hole["feasible"] else None)
    # [G1] the centre this run was asked to use (V3F_OPT mx / my / notch), tested on its own
    kv = "notch" if G.MOTOR_NOTCH else "hole"
    asked = {k: round(float(np.ravel(v)[0]), 3) for k, v in clearances(np.array([[G.MOTOR_C[0]]]), np.array([[G.MOTOR_C[1]]]), ob, kv).items()
             if np.isfinite(np.ravel(v)[0])}
    asked_ok = all(v >= -1e-9 for v in asked.values())
    if tuple(G.MOTOR_C) != (20.0, 25.4) or G.MOTOR_NOTCH:
        chosen = tuple(G.MOTOR_C)
    bridge = (G.BOARD["y1"] - (chosen[1] + R_CUT)) if chosen else None
    out = dict(pod_L=G.POD_L, pod_W=G.POD_W, tag=G.TAG, motor=G.MOTOR, asked_centre=list(G.MOTOR_C), asked_variant=kv, asked_centre_clearances=asked,
               asked_centre_legal=asked_ok, plates_first=dict(E1_mm2=round(ob["e1"].area, 1), E2_mm2=round(ob["e2"].area, 1),
                                                E1_contact_mm2=round(G.contact_area(ob["e1"]), 1), E2_contact_mm2=round(G.contact_area(ob["e2"]), 1),
                                                contact_strip_Y=G.CONTACT_STRIP, G7_min_mm2=G.G7_MIN_MM2,
                                                corridor_X=(G.PLATE_CORRIDOR[0], G.PLATE_CORRIDOR[1]), corridor_from_Y=G.PLATE_CORRIDOR[2]),
               variants={k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in res.items()},
               baseline_point_legal_hole=base_ok, chosen_centre=chosen,
               board_strip_beyond_hole_mm=round(bridge, 2) if bridge is not None else None,
               rules=dict(R_cut=R_CUT, R_motor_max=R_MOT, cut_edge_clr=G.CUT_EDGE_CLR, plate_clr=G.MOTOR_PLATE_CLR,
                          ant_min=G.MOTOR_ANT_MIN, rib_clr=G.RIB_MOTOR_CLR, edge_band=G.BOARD_EDGE_BAND),
               verdict=("a legal position exists" if hole["feasible"] else "NO legal position: the dia 8 ERM does not fit; decision 5 stays with the LED"))
    if chosen:
        cp = Point(*chosen)
        out["chosen_clearances_mm"] = {
            "motor body to E1": round(cp.distance(ob["e1"]) - R_MOT, 3), "motor body to E2": round(cp.distance(ob["e2"]) - R_MOT, 3),
            "cut-out to the nearest post foot": round(cp.distance(ob["posts"]) - R_CUT, 3),
            "cut-out to the root-A lands": round(cp.distance(ob["landA"]) - R_CUT, 3),
            "cut-out to the K zone": round(cp.distance(ob["kzone"]) - R_CUT, 3),
            "cut-out to the cap": round(cp.distance(ob["cap"]) - R_CUT, 3),
            "motor body to the rib shelf edge (Y 21.0)": round(chosen[1] - R_MOT - G.RIB["y1"], 3),
            "cut-out to the board edge band": round(G.BOARD["y1"] - G.BOARD_EDGE_BAND - chosen[1] - R_CUT, 3),
            "motor body to the antenna keep-out": round(cp.distance(ob["ant"]) - R_MOT, 2)}
    json.dump(out, open(os.path.join(OUT, f"motor_search_{TAG}.json"), "w"), indent=1)
    plot(ob, xc, yc, res, chosen)
    return out


def plot(ob, xc, yc, res, chosen):
    import matplotlib; matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Polygon as MP, Circle
    fig, axs = plt.subplots(1, 2, figsize=(17, 8.2))
    for ax, variant in zip(axs, ("hole", "notch")):
        def draw(g, **kw):
            gs = g.geoms if hasattr(g, "geoms") else [g]
            for p in gs:
                ax.add_patch(MP(np.asarray(p.exterior.coords), closed=True, **kw))
        draw(G.case_outline(), fc="none", ec="0.3", lw=1)
        draw(G.cavity(), fc="none", ec="0.6", lw=0.8, ls="--")
        draw(G.board_outline(), fc="#e8f3e8", ec="g", lw=1)
        draw(ob["e1"], fc="#b8c2cc", ec="k", lw=0.8, alpha=0.9); draw(ob["e2"], fc="#b8c2cc", ec="k", lw=0.8, alpha=0.9)
        draw(ob["cap"], fc="#9fd3ff", ec="b", lw=0.8)
        draw(ob["posts"], fc="#ff9f40", ec="k", lw=0.5)
        draw(ob["landA"], fc="#ffd27f", ec="k", lw=0.5); draw(ob["kzone"], fc="#ffe9b0", ec="k", lw=0.5)
        draw(ob["ant"], fc="#ff8080", ec="r", lw=0.8)
        draw(ob["ant"].buffer(G.ANT_METAL_MIN), fc="none", ec="r", lw=0.6, ls=":")
        ax.axhspan(G.RIB["y0"], G.RIB["y1"], xmin=0, xmax=1, color="#c0a080", alpha=0.35)
        ok = res[variant]["_ok"]
        ax.contourf(xc, yc, ok.astype(float), levels=[0.5, 1.5], colors=["#2ca02c"], alpha=0.55)
        if chosen and variant == "hole":
            ax.add_patch(Circle(chosen, R_CUT, fc="none", ec="m", lw=1.5)); ax.add_patch(Circle(chosen, R_MOT, fc="none", ec="m", lw=1, ls="--"))
            ax.plot(*chosen, "m+", ms=12)
        ax.set_xlim(-1, G.POD_L + 1); ax.set_ylim(-1, 33); ax.set_aspect("equal"); ax.grid(alpha=0.3)
        r = res[variant]
        txt = (f"feasible centres: X {r['x_range'][0]}-{r['x_range'][1]}, Y {r['y_range'][0]}-{r['y_range'][1]} ({r['area_mm2']} mm2)"
               if r["feasible"] else "no feasible centre")
        ax.set_title(f"V3-F {G.POD_L:.0f} mm: motor centre search, board cut-out = {variant}\n{txt}", fontsize=10)
        ax.set_xlabel("X mm (elbow -> hand, left wrist)"); ax.set_ylabel("Y mm (root B / antenna -> root A)")
    fig.text(0.01, 0.01, "green = legal motor centres; grey = Ti plates E1/E2 (fixed first); blue = optical cap; orange = rib-post feet; "
                "yellow = root-A lands / K zone; red = antenna keep-out (dotted: 5 mm metal rule); brown band = rib Y 20-21; "
                "magenta = chosen cut-out (8.6) and motor (8.1 max)", fontsize=8)
    fig.tight_layout(rect=(0, 0.04, 1, 1)); fig.savefig(os.path.join(OUT, f"motor_search_{TAG}.png"), dpi=120); plt.close(fig)


if __name__ == "__main__":
    if not G.HAS_MOTOR:      # [G1 level 4] no motor: no cut-out, nothing to search
        e1, e2 = G.plate_outlines()
        o = dict(pod_L=G.POD_L, tag=G.TAG, no_motor=True, plates_first=dict(E1_mm2=round(e1.area, 1), E2_mm2=round(e2.area, 1),
                 E1_contact_mm2=round(G.contact_area(e1), 1), E2_contact_mm2=round(G.contact_area(e2), 1), contact_strip_Y=G.CONTACT_STRIP,
                 G7_min_mm2=G.G7_MIN_MM2), variants=dict(hole=dict(feasible=None)), chosen_centre=None, chosen_clearances_mm={})
        json.dump(o, open(os.path.join(OUT, f"motor_search_{TAG}.json"), "w"), indent=1)
        print(json.dumps(o, indent=1, default=str)); sys.exit(0)
    o = run()
    print(json.dumps({k: v for k, v in o.items()}, indent=1, default=str))
