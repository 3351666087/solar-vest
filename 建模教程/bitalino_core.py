"""BITalino (r)evolution Core (BT) — LOD1 model traced from PLUX User Manual Fig. 8.

Source:   bitalino-revolution-user-manual.pdf §1.8, Fig. 8 ("65 mm x 56 mm x 2 mm")
Method:   the 65 mm / 56 mm dimension arrows give the scale (7.28 px/mm vertical, 6.87 px/mm horizontal;
          the 6 % mismatch is the figure's own distortion, so expect about ±1 mm on traced features).
Frame:    traced in image coords (x right, y down, origin = board top-left); converted to CAD below
          (X right, Y up, Z out of the component side, origin = board centre on the bottom face).
Unknowns: (📏) component heights; the Plugged kit is quoted at 6 mm overall, which bounds them.
"""
from build123d import *

# ---- parameters (mm) ------------------------------------------------------
W, H, T_PCB = 56.0, 65.0, 1.6          # outline (datasheet) and board thickness (📏 datasheet says 2 mm overall)
STRIP_W = 9.0                          # side strips that carry the UC-E6 sockets
NOTCH_D = 12.5                         # top-centre cut-out between the strips
SOCKET_Y = [5.2, 18.6, 32.1, 45.6, 59.1]   # socket centres from the top edge (left = I1 A4 A3 A2 A1, right = O1 O2/I2 PWM A6 A5)
SOCK = dict(depth=6.0, width=7.0, h=3.5)   # UC-E6 socket body (📏)
BT = dict(x0=10.9, x1=24.8, y0=37.5, y1=65.0, h=2.3)     # HC-05-class Bluetooth module
MCU = dict(cx=28.0, cy=22.2, s=7.0, h=1.0)               # ATmega328P TQFP-32, rotated 45°
USB = dict(cx=32.8, w=7.5, d=5.0, h=2.6)                  # micro-USB charging port on the bottom edge
SW = dict(x0=39.0, x1=46.0, d=3.5, h=3.0, knob=1.5)       # ON/OFF slide switch, knob sticks out of the edge
BAT_JST = dict(x0=33.5, x1=39.3, y0=45.4, y1=52.9, h=4.8) # JST-PH 2P battery socket (side entry)

def P(x, y, z=0.0):                    # image coords -> CAD coords
    return Pos(x - W/2, H/2 - y, T_PCB + z)

def box(x0, x1, y0, y1, h):
    return P((x0+x1)/2, (y0+y1)/2) * Box(x1-x0, y1-y0, h, align=(Align.CENTER, Align.CENTER, Align.MIN))

# ---- board outline: rectangle minus the top-centre notch --------------------
pcb = Box(W, H, T_PCB, align=(Align.CENTER, Align.CENTER, Align.MIN))
pcb -= Pos(0, H/2 - NOTCH_D/2, T_PCB/2) * Box(W - 2*STRIP_W, NOTCH_D + 0.01, T_PCB + 1)
for side in (0, 1):                    # 4 header holes beside every socket
    hx = 7.6 if side == 0 else W - 7.6
    for sy in SOCKET_Y:
        for k in range(4):
            pcb -= Pos(hx - W/2, H/2 - (sy - 2.7 + 1.8*k), T_PCB/2) * Cylinder(0.45, T_PCB + 1)
for row_y in (15.0, 29.5):             # MCU daughter-section header rows
    for k in range(13):
        pcb -= Pos(11.5 + 2.54*k - W/2, H/2 - row_y, T_PCB/2) * Cylinder(0.5, T_PCB + 1)

parts = {"pcb": pcb}
socks = []
for side in (0, 1):
    x0 = 0.0 if side == 0 else W - SOCK["depth"]
    for sy in SOCKET_Y:
        socks.append(box(x0, x0 + SOCK["depth"], sy - SOCK["width"]/2, sy + SOCK["width"]/2, SOCK["h"]))
parts["uce6_sockets"] = Compound(children=socks)
parts["bt_module"] = box(BT["x0"], BT["x1"], BT["y0"], BT["y1"], BT["h"])
parts["mcu"] = P(MCU["cx"], MCU["cy"]) * Rot(0, 0, 45) * Box(MCU["s"], MCU["s"], MCU["h"], align=(Align.CENTER, Align.CENTER, Align.MIN))
parts["micro_usb"] = box(USB["cx"] - USB["w"]/2, USB["cx"] + USB["w"]/2, H - USB["d"], H + 0.6, USB["h"])
parts["switch"] = box(SW["x0"], SW["x1"], H - SW["d"], H, SW["h"]) + \
                  box(42.0, 42.0 + SW["knob"], H, H + SW["knob"], SW["h"] * 0.6)
parts["bat_jst"] = box(BAT_JST["x0"], BAT_JST["x1"], BAT_JST["y0"], BAT_JST["y1"], BAT_JST["h"])

COLORS = {"pcb": (0.93, 0.93, 0.90), "uce6_sockets": (0.80, 0.68, 0.40), "bt_module": (0.20, 0.55, 0.25),
          "mcu": (0.12, 0.12, 0.14), "micro_usb": (0.75, 0.76, 0.78), "switch": (0.15, 0.15, 0.15), "bat_jst": (0.97, 0.97, 0.95)}
for k, v in parts.items():
    v.label = k; v.color = Color(*COLORS[k])
core = Compound(children=list(parts.values()), label="BITalino_Core_BT_LOD1")
if __name__ == "__main__":
    bb = core.bounding_box()
    print(f"bbox {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm  (datasheet: 56 x 65, Plugged ≈ 6 mm overall)")
    export_step(core, "bitalino_core_LOD1.step")
    export_gltf(core, "bitalino_core_LOD1.glb", binary=True)
    print("ok")
