"""Layout-only footprints for the SolarBand boards -> layout/lib/solarband_layout.pretty

None of these is a JLC-placed part (all are excluded from BOM and position files):
  Contact_Castellated_2.0x2.4_D1.0   C+/C- cradle contact, plated half-hole on the Y = 0 board edge
                                     (mech v0 conflict 6: the side-wall pins meet castellated edge pads)
  MechPad_D2.0                       back-shell standoff landing pad (bare ENIG, no paste, no net)
  LegPad_D1.3                        PPG window-insert leg landing pad (mech rev b, SIM-14 datum)
  HoldDown_D1.8                      frame hold-down post landing pad (placed on B.Cu)
  MechMark_D2.0_NoCu                 post location inside the IFA keep-out: courtyard + fab only, no copper
  IFA_B2_L6                          printed meander IFA (SIM-10 run B2_f_lb8) as a net-tie footprint:
                                     pad 1 = ANT_FEED at the feed via, pad 2 = GND at the short-leg root,
                                     copper polygon from sim/rf/sim10_ifa/export/ifa_L6.json. Drawn X-mirrored
                                     so that it is exact after the flip to B.Cu (origin = board corner 0,0).
Run with any python3 (no KiCad import needed).
"""
import json, os, uuid

W = "/path/to/SolarVest_work/wristband"
OUT = os.path.join(W, "layout/lib/solarband_layout.pretty")
IFA = os.path.join(W, "sim/rf/sim10_ifa/export/ifa_L6.json")


def u():
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "solarband-layout-%d" % next(_ctr)))


def _gen():
    i = 0
    while True:
        i += 1
        yield i


_ctr = _gen()


def head(name, descr, attr="smd exclude_from_pos_files exclude_from_bom", extra=""):
    return (f'(footprint "{name}" (version 20241229) (generator "solarband_layout_lib_gen") (layer "F.Cu")\n'
            f'  (descr "{descr}")\n  (attr {attr})\n{extra}'
            f'  (property "Reference" "REF**" (at 0 -1.8 0) (layer "F.SilkS") (hide yes) (uuid "{u()}")\n'
            f'    (effects (font (size 0.6 0.6) (thickness 0.1))))\n'
            f'  (property "Value" "{name}" (at 0 1.8 0) (layer "F.Fab") (hide yes) (uuid "{u()}")\n'
            f'    (effects (font (size 0.4 0.4) (thickness 0.06))))\n')


def circ_crtyd(r, layer="F.CrtYd"):
    return (f'  (fp_circle (center 0 0) (end {r:.3f} 0) (stroke (width 0.05) (type solid)) (fill no) '
            f'(layer "{layer}") (uuid "{u()}"))\n')


def write(name, body):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name + ".kicad_mod"), "w") as f:
        f.write(body + ")\n")


def main():
    # ---------------------------------------------------------------- castellated contact
    b = head("Contact_Castellated_2.0x2.4_D1.0",
             "Cradle C+/C- contact: plated half-hole D1.0 on the board edge (footprint origin = edge), pad 2.0 x 2.4 on all layers. "
             "Order option: castellated holes (confirm in the live JLC form).", attr="through_hole exclude_from_pos_files exclude_from_bom")
    b += (f'  (pad "1" thru_hole rect (at 0 0) (size 2.0 2.4) (drill 1.0) (property pad_prop_castellated) '
          f'(layers "*.Cu" "*.Mask") (remove_unused_layers no) (uuid "{u()}"))\n')
    b += (f'  (fp_rect (start -1.25 -1.45) (end 1.25 0) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd") (uuid "{u()}"))\n')
    b += (f'  (fp_rect (start -1.0 -1.2) (end 1.0 0) (stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab") (uuid "{u()}"))\n')
    write("Contact_Castellated_2.0x2.4_D1.0", b)
    # ---------------------------------------------------------------- mechanical landing pads
    for name, d, descr in (("MechPad_D2.0", 2.0, "Back-shell standoff (D1.6 post) landing pad, bare ENIG, no paste, no net"),
                           ("LegPad_D1.3", 1.3, "PPG window-insert leg (D0.9) landing pad = SIM-14 Z datum, bare ENIG, no paste, no net"),
                           ("HoldDown_D1.8", 1.8, "Frame hold-down post landing pad (place on B.Cu / L6), bare ENIG, no paste, no net")):
        b = head(name, descr)
        b += (f'  (pad "" smd circle (at 0 0) (size {d} {d}) (layers "F.Cu" "F.Mask") (uuid "{u()}"))\n')
        b += circ_crtyd(d / 2 + 0.2)
        b += (f'  (fp_circle (center 0 0) (end {d/2:.3f} 0) (stroke (width 0.08) (type solid)) (fill no) (layer "F.Fab") (uuid "{u()}"))\n')
        write(name, b)
    b = head("MechMark_D2.0_NoCu", "Plastic post location inside the IFA keep-out: no copper (courtyard + fab marker only)")
    b += circ_crtyd(1.0)
    b += (f'  (fp_circle (center 0 0) (end 0.8 0) (stroke (width 0.08) (type solid)) (fill no) (layer "F.Fab") (uuid "{u()}"))\n')
    write("MechMark_D2.0_NoCu", b)
    # ---------------------------------------------------------------- IFA (net tie), X mirrored for the flip to B.Cu
    d = json.load(open(IFA))
    poly = d["copper_polygon"]
    fv = d["feed_via"]
    sl = d["short_leg"]
    m = lambda x, y: (-x, -y)          # board (x, y up) -> library (x mirrored, KiCad y down); flip restores x
    b = head("IFA_B2_L6", "Printed meander IFA, SIM-10 run B2_f_lb8 (sim/rf/sim10_ifa/export/ifa_L6.json); net tie FEED-GND; "
             "origin = board corner (0,0); place on B.Cu", extra='  (net_tie_pad_groups "1,2")\n')
    pts = " ".join("(xy %.4f %.4f)" % m(x, y) for x, y in poly[:-1])
    b += (f'  (fp_poly (pts {pts}) (stroke (width 0) (type solid)) (fill yes) (layer "F.Cu") (uuid "{u()}"))\n')
    fx, fy = m(fv["x"], fv["y"])
    b += (f'  (pad "1" smd circle (at {fx:.4f} {fy:.4f}) (size {fv["pad"]} {fv["pad"]}) (layers "F.Cu") (uuid "{u()}"))\n')
    gx, gy = m((sl["x0"] + sl["x1"]) / 2, sl["y_join"] + 0.15)
    b += (f'  (pad "2" smd rect (at {gx:.4f} {gy:.4f}) (size {sl["x1"] - sl["x0"]:.3f} 0.3) (layers "F.Cu") (uuid "{u()}"))\n')
    # courtyard = keep-out box (fab reference only)
    x0, y0 = m(0, 0); x1, y1 = m(15.5, 6.4)
    b += (f'  (fp_rect (start {x1:.3f} {y1:.3f}) (end {x0:.3f} {y0:.3f}) (stroke (width 0.05) (type solid)) (fill no) (layer "F.Fab") (uuid "{u()}"))\n')
    write("IFA_B2_L6", b)
    # ---------------------------------------------------------------- PV board variants (fab-only board, L-07)
    src = open(W + "/design/lib/pv.pretty/KXOB25-03X4TF.kicad_mod").read()
    p1 = [(-1.4, -3.7), (0.66, -3.7), (1.4, -2.3), (1.4, 3.7), (-1.4, 3.7)]      # top pad: outer-left corner chamfered
    p2 = [(-1.4, -2.3), (-0.664, -3.7), (1.4, -3.7), (1.4, 3.7), (-1.4, 3.7)]    # bottom pad: outer-left corner chamfered
    def cpad(num, x, poly):
        pts = " ".join("(xy %.3f %.3f)" % q for q in poly)
        return (f'(pad "{num}" smd custom (at {x} 0.000) (size 1.0 1.0) (layers "F.Cu" "F.Mask") '
                f'(options (clearance outline) (anchor rect)) (primitives (gr_poly (pts {pts}) (width 0) (fill yes))) '
                f'(uuid "{u()}"))')
    import re as _re
    v = _re.sub(r'\(pad "1" smd rect \(at 10\.900 0\.000\)[^\n]*', cpad("1", "10.900", p1), src)
    v = _re.sub(r'\(pad "2" smd rect \(at -10\.900 0\.000\)[^\n]*', cpad("2", "-10.900", p2), v)
    v = v.replace('(footprint "KXOB25-03X4TF"', '(footprint "KXOB25-03X4TF_C2"').replace(
        '(descr "', '(descr "Layout variant (L-07): outer pad-extension corners chamfered for the R2.0 PV-board corners at rot 90 on the u=0 side; ', 1)
    open(os.path.join(OUT, "KXOB25-03X4TF_C2.kicad_mod"), "w").write(v)
    b = head("WirePad_SMD_D1.6", "PV+/PV- 32 AWG lead pad, SMD (place on PV-board B.Cu; no hole under the cells), Kapton strain relief")
    b += (f'  (pad "1" smd circle (at 0 0) (size 1.6 1.6) (layers "F.Cu" "F.Mask") (uuid "{u()}"))\n')
    b += circ_crtyd(1.0)
    write("WirePad_SMD_D1.6", b)
    print("wrote", sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
