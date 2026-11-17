"""[S1 C-7] unit tests of lgeom_v3f.height_limit_at (run after exports_v3f.py; V3F_POD_L selects the board).
usage: python3 -B test_lgeom_v3f.py   -> prints the cases, exit 1 on a failure"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import geom_v3f as G      # noqa: E402
os.environ.setdefault("V3F_ZONES", os.path.join(G.OUT_DIR, f"board_zones_{G.TAG}.json"))   # [G1] the zone file of this run (plain or option)
import lgeom_v3f as LG    # noqa: E402

def b(x, y): return G.to_board(x, y)
sw = G.sw1_land(); s0, s1, s2, s3 = sw["courtyard"]
cases = [
    ("SW1 centre (part zone 1.35)", b((s0 + G.BOARD["x1"]) / 2, G.SW1["cy"]), 1.35),
    ("J15 land centre (finger 1.5)", b(*G.PINS[0]["land"]), 1.5),
    ("J18 land centre (finger 1.5)", b(*G.PINS[1]["land"]), 1.5),
    ("J11 land centre (finger 1.5)", b(*G.J11["land"]), 1.5),
    ("antenna keep-out centre (0)", b((G.ANT_KEEPOUT[0] + G.ANT_KEEPOUT[1]) / 2, (G.ANT_KEEPOUT[2] + G.ANT_KEEPOUT[3]) / 2), 0.0),
    ("land_A centre (0)", b((G.LAND_A[0] + G.LAND_A[1]) / 2, (G.LAND_A[2] + G.LAND_A[3]) / 2), 0.0),
    ("K zone outside the fingers (0)", b(3.7, 25.0), 0.0),
    ("under the panel (0.75 + raise)", b(15.0, 9.0), round(G.Z.parts_low - G.Z.pcb1, 2)),
    ("under the rail (0.75 + raise)", b(7.0 if not getattr(G, "S2E", False) else 9.0, 5.2), round(G.Z.rail0 - getattr(G, "RAIL_P4_DEEPEN", 0.0) - 0.15 - G.Z.pcb1, 2)),   # [P-4] 0.70 with p4=1   # [mini-ECO F-4] was b(8.0, 5.2), now a post foot; [S2e] 7.0 is foot X6.7 now -> 9.0
    *([("[P-4] under the stainless rail, unchanged", b(19.5, 5.05), round(G.Z.rail0 - 0.15 - G.Z.pcb1, 2))] if getattr(G, "P4", False) else []),
    ("under the rib shelf (0.55)", b(15.0, 20.5), 0.55),
    ("general zone (1.05)", b(25.0, 3.5), 1.05),
    ("motor cut-out (0)", b(*G.MOTOR_C), 0.0 if G.HAS_MOTOR else 1.05),
    ("FPC corridor / tail (0, or the under-FPC limit of fpc=over)", b(30.0, 12.0),
     0.0 if G.FPC_MODEL not in ("over", "rear") else max(0.0, [z["h_max"] for z in G.board_zones() if z["name"] == "under_fpc_tail"][0])),
    ("far board edge strip, general zone (1.05) [G1 width]", b(25.0 if G.HAS_MOTOR else 30.0, G.BOARD["y1"] - 0.3), (1.20 if G.S2D else 1.05) if (G.DW >= 1 or not G.HAS_MOTOR) else None),   # [S2d K-3] PV half 1.20
    *([("[S2d K-3] PV half general (1.20)", b(20.0, 24.0), 1.20)] if G.S2D else []),
    ("D10 part zone (0.9)", b((G.D10["x0"] + G.D10["x1"]) / 2, (G.D10["y0"] + G.D10["y1"]) / 2), 0.9),
]
bad = 0
for name, pt, want in cases:
    if want is None:
        continue
    got = LG.height_limit_at(*pt)
    ok = abs(got - want) < 1e-6; bad += not ok
    print(f"{'OK  ' if ok else 'FAIL'} {name:34s} board {pt} -> {got} (expected {want})")
if G.S2D:   # [S2d J-1] the J40 part zone (inside the all-layer pocket, which the loader reports as 0) carries h 3.10
    hz = [z["h_max_mm"] for z in LG._D["zones"] if z["name"] == "J40_land"]
    ok = hz == [3.1]; bad += not ok; cases.append(("J40_land h_max", None, 3.1))
    print(f"{'OK  ' if ok else 'FAIL'} [S2d J-1] J40_land zone h_max -> {hz} (expected [3.1])")
n = sum(1 for c in cases if c[2] is not None)
print(f"{n - bad}/{n} passed")
sys.exit(1 if bad else 0)
