"""Scout: radiator on the lid's inner face (glass, z = Z_case(win0) - 0.35 -> grid 3.5), fed by a spring finger from the
board feed. Copied wrapper around ../common/scene_v3f.build_scene: every conductor of the V3-F scene is kept, only the
board radiator (ant_F / ant_B / ant_via) is removed; the 5 x 3 keep-out pocket stays copper-free FR-4 (except the feed leg
and the spring land). Port = the same delta gap as the board runs (Y 4.25..4.5 case, X 4.0..4.5, z 1.0).
kinds: 'L1' straight strip (open end), 'L2' inverted-F (L1 + shorting spring to the Y 4.5 ground at X 2.5..3.0)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "common"))
from shapely.geometry import box as sbox
from shapely.ops import unary_union
import scene_v3f as S
from geom import PEC, PolyZ, Box

Z_LID = 3.545          # glass inner face (ZC.win0 + DZ) -> snapped to the 0.25 z grid (3.5)
FX0, FX1 = 4.0, 4.5    # feed leg / spring X (as the board radiator's feed leg)
SPR_Y = (2.5, 3.0)     # feed spring land on the pocket (R <= 4.03 from the board arc centre: inside the 0.3 copper clearance)
BAND_Y = (1.5, 2.0)    # lid strip along the antenna-side long wall (cavity wall + 0.25 inset holds for X >= 4.0)
X_END = 10.5           # open end, 0.6 mm short of the grounded frame cut-back edge (X 11.1)
SHORT_X = (2.5, 3.0)   # L2 shorting spring X, land Y 4.5..5.0 on the board ground (rail starts Y 5.0)


def lid_parts(kind):
    lid = [sbox(FX0, BAND_Y[0], X_END, BAND_Y[1]), sbox(FX0, BAND_Y[1], FX1, SPR_Y[1])]
    springs = [("spring_feed", (FX0, SPR_Y[0], FX1, SPR_Y[1]))]
    if kind == "L2":
        lid += [sbox(SHORT_X[0], 2.75, FX1, 3.25), sbox(SHORT_X[0], 3.25, SHORT_X[1], 5.0)]   # bridge Y 2.75..3.25 (cavity wall + 0.3 at X 2.5)
        springs.append(("spring_short", (SHORT_X[0], 4.5, SHORT_X[1], 5.0)))
    elif kind != "L1":
        raise ValueError(kind)
    lidp = unary_union(lid).simplify(1e-9)
    legp = sbox(FX0, SPR_Y[0], FX1, 4.25)
    return lidp, legp, springs


def build(kind, v, snap):
    sy, sz = snap
    prims, port, ant = S.build_scene(S.Cand(), v, snap)
    prims = [p for p in prims if p.tag not in ("ant_F", "ant_B", "ant_via")]
    lidp, legp, springs = lid_parts(kind)
    zl = sz(Z_LID)
    prims.append(PolyZ(legp, S.BOARD_T, S.BOARD_T, PEC, "feed_leg_F"))
    for tag, (x0, y0, x1, y1) in springs:
        prims.append(Box((x0, y0, S.BOARD_T), (x1, y1, zl), PEC, tag))
    prims.append(PolyZ(lidp, zl, zl, PEC, "lid_strip"))
    port = dict(x0=FX0, x1=FX1, y_gap0=4.25, y_gap1=4.5, z=S.BOARD_T)
    info = dict(kind=kind, z_lid=zl, lid_area_mm2=round(lidp.area, 3), lid_bounds=lidp.bounds,
                path_short_or_feed_to_open_mm=None, lid_wkt=lidp.wkt, leg_wkt=legp.wkt, springs=springs)
    return prims, port, info
