"""Dump the layout geometry of lgeom.py for scripts that run in KiCad's python (no numpy / shapely there).
usage: [G1_ZONES=.. G1_VARIANT=.. G1_OPTS=..] venv-python dump_geom.py OUT.json"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import lgeom as G
out = dict(G=dict(ZTAG=G.ZTAG, VARIANT=G.VARIANT, OPTS=G.OPTS, DESIGN=G.DESIGN, KICAD_ORIGIN=G.KICAD_ORIGIN, CU_EDGE=G.CU_EDGE,
                  BOARD_W=G.BOARD_W, BOARD_H=G.BOARD_H, OUTLINE=G.OUTLINE, MOTOR_CENTER=G.MOTOR_CENTER, MOTOR_CUT_D=G.MOTOR_CUT_D,
                  ANT_KEEPOUT=G.ANT_KEEPOUT, ZRECTS={k: v.get("rect_board") for k, v in G.ZONES.items()}, SKIN=G.SKIN, PLATE_RECT=G.PLATE_RECT, CAP=G.CAP, DOTS=G.DOTS))
os.makedirs(os.path.dirname(os.path.abspath(sys.argv[1])), exist_ok=True)
json.dump(out, open(sys.argv[1], "w"))
print("wrote", sys.argv[1])
