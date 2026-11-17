"""Export the as-built main-board geometry (KiCad board) in the mech/thermal case frame -> layout/work/mech_layout.json
(read by sim/thermal-mech/sim13_layout.py and sim14_layout.py) and layout/work/parts_case.json (per-part list).
Case frame (mech/geom_v0.py): X_case = 38.5 - X_board, Y_case = 1.5 + Y_board (F.Cu faces the skin).
usage: kicad-python mech_export.py
"""
import json, os, sys
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lgeom as G
import place_main as P

W = G.W
OX, OY = G.KICAD_ORIGIN
ADD = {"0402_RES": dict(h=(0.45, 0.50, 0.55), src="sim14_stack.py R0402 (0402 thick-film 0.55 max)", refs="0402 R"),
       "X2SON_DQN_TPS7A20": dict(h=(0.30, 0.35, 0.40), src="TI TPS7A20 SBVS338H p60", refs="U3"),
       "SC70-6_SIP32431": dict(h=(0.80, 0.95, 1.10), src="Vishay SiP32431 p12", refs="U12"),
       "SOT23_BAS21": dict(h=(0.90, 1.00, 1.10), src="Nexperia BAS21 p6", refs="D1"),
       "SOT23_MMBT3904": dict(h=(0.89, 1.00, 1.12), src="onsemi MMBT3904 p10 / Vishay 71196", refs="Q2 Q3")}


def rect_b2c(r):
    x0, y0 = G.board_to_case(r[0], r[1]); x1, y1 = G.board_to_case(r[2], r[3])
    return dict(x0=min(x0, x1), y0=min(y0, y1), x1=max(x0, x1), y1=max(y0, y1))


def main():
    brd = pcbnew.LoadBoard(W + "/layout/main/solarband_main.kicad_pcb")
    H = json.load(open(W + "/layout/work/heights.json"))
    parts, plist = [], []
    for f in brd.GetFootprints():
        ref = f.GetReference()
        if f.IsBoardOnly() or f.GetLayer() != pcbnew.F_Cu:
            continue
        cy = f.GetCourtyard(pcbnew.F_CrtYd)
        bb = cy.BBox() if cy.OutlineCount() else f.GetBoundingBox(False)
        x0 = pcbnew.ToMM(bb.GetLeft()) - OX; x1 = pcbnew.ToMM(bb.GetRight()) - OX
        y1 = OY - pcbnew.ToMM(bb.GetTop()); y0 = OY - pcbnew.ToMM(bb.GetBottom())
        cxb, cyb = (x0 + x1) / 2, (y0 + y1) / 2
        cxc, cyc = G.board_to_case(cxb, cyb)
        L, Wd = max(0.2, x1 - x0 - 0.5), max(0.2, y1 - y0 - 0.5)
        h = H.get(ref)
        rec = dict(ref=ref, board=dict(x0=x0, y0=y0, x1=x1, y1=y1), case_center=(cxc, cyc), L=L, W=Wd,
                   h_max=h["h"] if h else 0.0, hkey=h["key"] if h else None, dnp=f.IsDNP(),
                   jlc=not f.IsExcludedFromPosFiles())
        plist.append(rec)
        if h and ref not in ("D3", "D4", "PD1", "U8"):
            parts.append((ref, h["key"], round(cxc, 3), round(cyc, 3), round(L, 3), round(Wd, 3), "layout"))
    def pos(r):
        p = brd.FindFootprintByReference(r).GetPosition()
        return G.board_to_case(pcbnew.ToMM(p.x) - OX, OY - pcbnew.ToMM(p.y))
    e2 = rect_b2c((G.E2["x0"], G.E2["y0"], G.E2["x1"], G.E2["y1"]))
    e1 = rect_b2c((G.E1["x0"], G.E1["y0"], G.E1["x1"], G.E1["y1"]))
    ctr = lambda r: dict(cx=(r["x0"] + r["x1"]) / 2, cy=(r["y0"] + r["y1"]) / 2, L=r["x1"] - r["x0"], W=r["y1"] - r["y0"], R=1.0)
    u8 = [q for q in plist if q["ref"] == "U8"][0]
    pvc = []
    for n, c in G.PV_CELLS.items():
        b = c["body"]
        pvc.append(dict(name={"SC1": "KXOB121K04TF", "SC2": "KXOB25-03X4TF"}[n], x0=G.PV_CASE_ORIGIN[0] + b[0],
                        y0=G.PV_CASE_ORIGIN[1] + b[1], L=b[2] - b[0], W=b[3] - b[1]))
    tz = [rect_b2c(r) for r in P.TALL]
    out = dict(
        source="layout/main/solarband_main.kicad_pcb via layout/tools/mech_export.py",
        E1=ctr(e2), E2=ctr(e1),                      # model E1 = electrode with the TMP117 pedestal = layout E2
        TMP117_XY=G.board_to_case(*G.TMP117), E1_SPRING=G.board_to_case(*G.E2_SPRING), E2_SPRING=G.board_to_case(*G.E1_SPRING),
        STANDOFFS=[G.board_to_case(*s) for s in G.STANDOFFS] + [G.board_to_case(*G.STANDOFF_IFA)],
        TALL_ZONE=tz, LOCAL_POCKETS=[dict(**rect_b2c(r), depth=0.15) for r in P.POCKETS.values()],
        PV_BOARD=dict(x0=G.PV_CASE_ORIGIN[0], y0=G.PV_CASE_ORIGIN[1], L=G.PV_W, W=G.PV_H, R=G.PV_R),
        PV_CELLS=pvc, BATTERY=dict(x0=38.5 - G.BATTERY_L6[2], y0=1.5 + G.BATTERY_L6[1], L=G.BATTERY_L6[2] - G.BATTERY_L6[0],
                                   W=G.BATTERY_L6[3] - G.BATTERY_L6[1]),
        BOARD_R=4.5, PARTS=parts, TMP_SLOT_RING=G.TMP_SLOT_RING,
        PPG_PARTS=[dict(ref="D3", cx=21.0 - 2.75, cy=16.5, L=0.5, W=1.0, hkey="XL_1005UGC"),
                   dict(ref="PD1", cx=21.0, cy=16.5, L=2.5, W=4.8, hkey="VEMD8080"),
                   dict(ref="D4", cx=21.0 + 2.75, cy=16.5, L=0.5, W=1.0, hkey="XL_1005UGC"),
                   dict(ref="U8", cx=u8["case_center"][0], cy=u8["case_center"][1], L=2.05, W=1.85, hkey="MAX86141")],
        SOURCES={r: pos(r) for r in ("U1", "R111", "Q1", "U6")},
        HEIGHTS_ADD={k: dict(h=list(v["h"]), src=v["src"], refs=v["refs"]) for k, v in ADD.items()})
    json.dump(out, open(W + "/layout/work/mech_layout.json", "w"), indent=1)
    json.dump(plist, open(W + "/layout/work/parts_case.json", "w"), indent=1)
    print("parts", len(parts), "sources", out["SOURCES"])


if __name__ == "__main__":
    main()
