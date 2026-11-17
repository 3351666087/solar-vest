"""V3-G6 / SIM-07 case 1a: capacitance from the display panel (COM + pixel stack) to a finger on E3 and to the E3 net.
2-D cross-section along X at the hand end of the V3-F pod (41 mm pod), lib/estat2d.py (finite differences).
x = 0: panel glass edge (COM taken to the glass edge: conservative, the TFT ledge is ignored), +x towards E3.
z = 0: window glass top. Stack (v3/cad CAD.md Z levels, panel raised 0.15 mm, decision c): window glass 0.70 (er 7.2),
film / stainless frame 0.25, air 0.10, panel top glass 0.30 (er 7.2), COM + pixels + TFT glass 0.50 (conductor, worst case:
white pixels follow COM), board GND 1.0 mm below the panel.
E3 net (C-9, 41 mm pod): strip from x 5.1 (2.4 mm on the rim), inner wrap / tab at x 4.1, down towards J11.
Frame: 0.25 mm stainless under the window edge, x 1.5-4.9 (CAD: bonded under the glass edge; its potential is not in
the netlist -> floating as built). Cases: frame floating, frame grounded, no frame.
Writes results/com_caps.json.  Run: python -B g6_com_caps.py   (a few minutes)"""
import sys, json, pathlib, time
import numpy as np
HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "lib"))
from estat2d import Grid

t0 = time.time()
ZG = -0.70; ZF = -0.95; ZA = -1.05; ZC = -1.35; ZP = -1.85; ZB = -2.85
X_GLASS_END = 5.0; X_STRIP = 5.1; X_TAB = 4.1
FR = (1.5, 4.9)
R_FINGER = 8.0
L_Y_FINGER = 14.0      # mm: panel extent in Y (5.7-19.7) under a 15 mm finger
L_Y_E3 = 16.8          # mm: E3 net facing the panel incl. fringe (14 mm x 1.2)


def model(h, xf, frame):
    g = Grid(-10.0, 14.0, ZB, 8.0, h)
    g.box_eps(-99, X_GLASS_END, ZG, 0.0, 7.2)                  # window glass
    g.box_eps(-99, FR[0], ZF, ZG, 3.0)                         # optical film over the panel
    g.box_eps(-99, 0.0, ZC, ZA, 7.2)                           # panel top glass
    g.box_eps(X_GLASS_END, 99, ZB, 0.0, 3.0)                   # PC rim / E3 block
    g.box_eps(X_TAB, X_GLASS_END, ZB, ZG, 3.0)
    g.box_cond(-99, 0.0, ZP, ZC, 1)                            # COM + pixel stack
    if xf is not None:
        def finger(X, Z):
            d = np.clip(xf - X, 0, None)
            zs = np.where(d < R_FINGER, R_FINGER - np.sqrt(np.clip(R_FINGER ** 2 - d ** 2, 0, None)), 1e9)
            return (Z >= zs) & (Z >= 0) & (X <= 13.0)
        g.mask_cond(finger, 2)
    g.box_cond(X_STRIP, X_STRIP + 2.4, -0.25, 0.0, 3)          # E3 strip
    g.box_cond(X_TAB, X_STRIP, -0.35, -0.25, 3)                # wrap
    g.box_cond(X_TAB, X_TAB + 0.3, ZB + 0.25, -0.25, 3)        # tab down to J11
    g.box_cond(-99, 99, ZB, ZB, 4)                             # board GND
    if frame != "none":
        g.box_cond(FR[0], FR[1], ZF, ZG, 4 if frame == "grounded" else 5)
    return g


def cmatrix(g):
    ks = sorted(set(np.unique(g.cond)) - {0, 4})
    K = np.zeros((len(ks), len(ks)))
    for a, ka in enumerate(ks):
        _, Qc = g.solve({k: (1.0 if k == ka else 0.0) for k in ks + [4]})
        for b, kb in enumerate(ks): K[b, a] = Qc[kb]
    if 5 in ks:                                                # floating frame: Q5 = 0
        i5 = ks.index(5); keep = [i for i in range(len(ks)) if i != i5]
        K = K[np.ix_(keep, keep)] - np.outer(K[keep, i5], K[i5, keep]) / K[i5, i5]
        ks = [k for k in ks if k != 5]
    m = lambda a, b: -K[ks.index(a), ks.index(b)] * 1e12 * 1e-3 if a in ks and b in ks else 0.0   # pF per mm
    return dict(com_finger=m(1, 2), com_e3=m(1, 3))


OUT = dict(geometry_mm=dict(z_glass=ZG, z_film=ZF, z_air=ZA, z_com=ZC, z_panel_bottom=ZP, z_board=ZB, glass_end=X_GLASS_END,
                            strip=X_STRIP, tab=X_TAB, frame=FR, r_finger=R_FINGER, Ly_finger=L_Y_FINGER, Ly_e3=L_Y_E3),
           note="pF = pF/mm x Ly; finger patch edge xf measured from the panel glass edge (negative = over the panel)")
print("mesh check (xf 1.0, frame floating):")
OUT["mesh"] = {}
for h in (0.05, 0.025):
    c = cmatrix(model(h, 1.0, "floating")); OUT["mesh"][str(h)] = c
    print("  h %.3f: COM-finger %.5f pF/mm, COM-E3 %.6f pF/mm" % (h, c["com_finger"], c["com_e3"]), flush=True)
H = 0.025
rows = []
for frame in ("floating", "grounded", "none"):
    for xf in (5.1, 3.0, 1.0, 0.0, -2.0, -5.0, None):
        c = cmatrix(model(H, xf, frame))
        r = dict(frame=frame, xf_mm=xf, finger_pF=c["com_finger"] * L_Y_FINGER, e3_pF=c["com_e3"] * L_Y_E3, **c)
        rows.append(r)
        print("  frame %-9s xf %5s  C(COM-finger) %.4f pF  C(COM-E3 net) %.5f pF   (%.0f s)" % (frame, xf, r["finger_pF"], r["e3_pF"], time.time() - t0), flush=True)
OUT["rows"] = rows
(HERE / "results").mkdir(exist_ok=True)
(HERE / "results" / "com_caps.json").write_text(json.dumps(OUT, indent=1))
print("done %.0f s" % (time.time() - t0))
