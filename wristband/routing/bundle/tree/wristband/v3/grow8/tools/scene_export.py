"""Layout geometry for the SIM-10 re-run -> layout/work/rf_scene_layout.json (board frame; z relative to L6 for the
PV/battery items, scene z for electrodes: L1 = 0, L6 = 0.8, skin side negative). Plain python."""
import json
import lgeom as G
from shapely.geometry import box as sbox
from shapely.affinity import translate


def main():
    pv0 = G.pv_rect_to_board((0, 0, G.PV_W, G.PV_H))
    inset = sbox(*pv0).buffer(-0.3, join_style=2)
    bu, bv = G.PV_RF_BAND
    band = sbox(*G.pv_rect_to_board((bu, -1, G.PV_W + 1, bv)))
    pour = inset.difference(band)
    pads = [G.pv_rect_to_board(p) for c in G.PV_CELLS.values() for p in c["pads"]]
    cells = [dict(name=n, **dict(zip(("x0", "y0", "x1", "y1"), G.pv_rect_to_board(c["body"]))), z0=G.PV_CELL_Z[0],
                  z1=G.PV_CELL_Z[1]) for n, c in G.PV_CELLS.items()]
    leads = [G.pv_to_board(*xy) for xy in G.PV_LEADS.values()]
    b = G.BATTERY_L6
    L = dict(
        source="layout/tools/lgeom.py (Phase B); PV board L-07, battery L-06, electrodes L-03",
        pv=dict(x0=pv0[0], y0=pv0[1], x1=pv0[2], y1=pv0[3], gap_above_L6=G.PV_GAP_L6, thickness=G.PV_T,
                bcu_pour=list(pour.exterior.coords), pads=pads, cells=cells, leads=leads),
        battery=dict(x0=b[0], y0=b[1], x1=b[2], y1=b[3], z0=0.15, z1=0.15 + 3.5),
        battery_tab=dict(x0=0.9, y0=14.0, x1=3.0, y1=22.0, z1=0.4),
        electrodes=[
            dict(name="E1", x0=G.E1["x0"], y0=G.E1["y0"], x1=G.E1["x1"], y1=G.E1["y1"], z0=-2.3, z1=-1.8),
            dict(name="E1_spring", x0=G.E1_SPRING[0] - 0.5, y0=G.E1_SPRING[1] - 0.5, x1=G.E1_SPRING[0] + 0.5,
                 y1=G.E1_SPRING[1] + 0.5, z0=-1.8, z1=0.0),
            dict(name="E2", x0=G.E2["x0"], y0=G.E2["y0"], x1=G.E2["x1"], y1=G.E2["y1"], z0=-2.3, z1=-1.8),
            dict(name="E2_spring", x0=G.E2_SPRING[0] - 0.5, y0=G.E2_SPRING[1] - 0.5, x1=G.E2_SPRING[0] + 0.5,
                 y1=G.E2_SPRING[1] + 0.5, z0=-1.8, z1=0.0),
            dict(name="E2_pedestal", x0=G.TMP117[0] - 3, y0=G.TMP117[1] - 3, x1=G.TMP117[0] + 3, y1=G.TMP117[1] + 3,
                 z0=-1.8, z1=-0.2),
            dict(name="E3_spring", x0=13.0, y0=27.0, x1=14.0, y1=29.75, z0=0.8, z1=1.4)])
    json.dump(L, open(G.W + "/layout/work/rf_scene_layout.json", "w"), indent=1)
    print(json.dumps({k: (v if k != "pv" else {kk: vv for kk, vv in v.items() if kk != "bcu_pour"}) for k, v in L.items()}, indent=0)[:1500])


if __name__ == "__main__":
    main()
