"""Hand-defined RF chain of the SolarBand main board (board frame, mm): nRF52832 ANT -> Nordic match
(C203 shunt 0.8 pF, L201 series 3.9 nH) -> RF node -> 3.0 mm CPWG -> pi-net (C213 shunt A DNP, C215 series 2.1 pF,
L204 shunt B 1.8 nH) -> 8.0 mm CPWG -> feed via (12.5, 5.95) -> L6 IFA feed leg.   [C-13, C-14, SIM-09/10/12]

CPWG on L1 over solid L2: W 0.170 / gap 0.150 (SIM-12, JLC06081H-2116). Lengths are measured along the centre line:
RF node (L201 RF_50R land centre) -> C213 junction = LEN_A; L204 ANT_FEED land centre -> feed-via centre = LEN_B.
The 8 mm line spirals inward between the nRF and the pi-net so the RF area stays inside X 10.6-16.3 (the BQ25570
cluster needs the tall zone right of it). Fence: GND vias 0.2/0.4 both sides, pitch <= 1.0 mm (R-RF-1: <= 2 mm).
usage: python rf_geom.py  -> prints the geometry and the two lengths (also imported by place_main / build_main)
"""
import math
import lgeom as G

ANT = (10.21, 9.2)          # U6 pin 30 land centre for U6 at (7.3, 9.4) rot 270 (checked against pcbnew in build_main)
U6_POS = (7.3, 9.4, 270)
Y_TOP = 11.0                # top leg (RF_50R); PPG zone starts at Y 11.5 [MECH]
X_C215 = 15.3               # right leg; C215 vertical on it
Y_MID = 7.45                # spiral middle leg
Y_BOT = 6.45                # bottom leg into the feed via
CHAMFER = 0.0               # 90 deg corners (CPWG 0.17 mm at 2.4 GHz: corner discontinuity negligible [E])


def parts():
    """RF part placements (ref: (x, y, rot)); rot = KiCad orientation (pad 1 = local -x)"""
    return {
        "C203": (11.85, ANT[1], 0),                       # pad1 RF_ANT left at 11.43, GND right
        "L201": (11.35, 10.57, 90),                       # pad1 RF_ANT bottom (10.15), pad2 RF_50R top (10.99)
        "C213": (14.35, 10.16, 270),                      # pad1 RF_50R top (10.58), GND bottom; DNP land
        "C215": (X_C215, 10.53, 270),                     # pad1 RF_50R top (10.95), pad2 ANT_FEED bottom (10.11)
        "L204": (14.80, 8.80, 180),                       # pad1 ANT_FEED right (15.22), GND left (14.38) inside
    }


def pad(ref, num):
    x, y, r = parts()[ref]
    dx = -0.42 if num == "1" else 0.42
    c, s = round(math.cos(math.radians(r))), round(math.sin(math.radians(r)))
    return (x + dx * c, y + dx * s)


def polylen(p):
    return sum(math.hypot(p[i + 1][0] - p[i][0], p[i + 1][1] - p[i][1]) for i in range(len(p) - 1))


def solve_x_left():
    """x of the spiral's left leg so that L204 land -> feed via = LEN_PINET_FEED exactly"""
    lx, ly = pad("L204", "1")
    fx, fy = G.FEED_VIA
    fixed = abs(X_C215 - lx) + (ly - Y_MID) + (Y_MID - Y_BOT) + (Y_BOT - fy)
    # 2 * (X_C215 - x_left) - (X_C215 - fx) ... horizontal: (X_C215 - xl) + (fx - xl)
    # total = fixed + (X_C215 - xl) + (fx - xl) = L  ->  xl = (fixed + X_C215 + fx - L) / 2
    return (fixed + X_C215 + fx - G.LEN_PINET_FEED) / 2


def tracks():
    """list of (net, [points]) centre lines on F.Cu, width CPWG_W"""
    a = ANT
    c203 = pad("C203", "1"); l1 = pad("L201", "1"); l2 = pad("L201", "2")
    c213 = pad("C213", "1"); c215a = pad("C215", "1"); c215b = pad("C215", "2"); l204 = pad("L204", "1")
    xl = solve_x_left()
    fx, fy = G.FEED_VIA
    T = [
        ("RF_ANT", [a, c203]),
        ("RF_ANT", [(l1[0], a[1]), l1]),
        ("RF_50R", [l2, (l2[0], Y_TOP), (X_C215, Y_TOP), c215a]),
        ("RF_50R", [(c213[0], Y_TOP), c213]),
        ("ANT_FEED", [c215b, (X_C215, l204[1]), (X_C215, Y_MID), (xl, Y_MID), (xl, Y_BOT), (fx, Y_BOT), (fx, fy)]),
        ("ANT_FEED", [(X_C215, l204[1]), l204]),
    ]
    return T


def lengths():
    l2 = pad("L201", "2"); c213 = pad("C213", "1")
    la = polylen([l2, (l2[0], Y_TOP), (c213[0], Y_TOP)])
    l204 = pad("L204", "1")
    xl = solve_x_left()
    fx, fy = G.FEED_VIA
    lb = polylen([l204, (X_C215, l204[1]), (X_C215, Y_MID), (xl, Y_MID), (xl, Y_BOT), (fx, Y_BOT), (fx, fy)])
    total = polylen([ANT, (l2[0], ANT[1])]) + 1.0 + la + polylen([(c213[0], Y_TOP), (X_C215, Y_TOP), pad("C215", "1")]) + 0.84 + lb
    return dict(rf_node_to_pinet_mm=round(la, 3), pinet_to_feed_via_mm=round(lb, 3), x_left=round(xl, 3),
                ant_to_feed_total_mm=round(total, 2))


def fence(pitch=1.0, off=0.5):
    """GND fence-via candidates both sides of the 50-ohm segments (filtered later against copper by build_main)"""
    pts = []
    for net, poly in tracks():
        if net == "RF_ANT":
            continue
        for i in range(len(poly) - 1):
            (x0, y0), (x1, y1) = poly[i], poly[i + 1]
            L = math.hypot(x1 - x0, y1 - y0)
            if L < 0.6:
                continue
            ux, uy = (x1 - x0) / L, (y1 - y0) / L
            nx, ny = -uy, ux
            n = max(1, int(L / pitch))
            for k in range(n + 1):
                t = k * L / n
                for sgn in (-1, 1):
                    pts.append((round(x0 + ux * t + sgn * nx * off, 3), round(y0 + uy * t + sgn * ny * off, 3)))
    return pts


if __name__ == "__main__":
    import json
    print(json.dumps(dict(parts=parts(), lengths=lengths(), tracks=tracks(), n_fence=len(fence())), indent=1))
