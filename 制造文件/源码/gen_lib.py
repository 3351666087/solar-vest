"""Custom symbols (CN3791, LM66100, XIAO nRF52840 Sense) and footprints (flat-mounted 10x25 supercap)."""
import uuid
def pin(num, name, typ, x, y, ang, length=2.54):
    return f'''      (pin {typ} line (at {x:.2f} {y:.2f} {ang}) (length {length})
        (name "{name}" (effects (font (size 1.27 1.27))))
        (number "{num}" (effects (font (size 1.27 1.27)))))'''
def box_symbol(name, ref, left, right, fp="", desc="", w=15.24, extra_props=""):
    """left/right: lists of (num, name, type); pins spaced 2.54, box auto-sized."""
    n = max(len(left), len(right)); h = (n + 1) * 2.54
    top = h/2
    pins = []
    for i, (num, nm, t) in enumerate(left):
        pins.append(pin(num, nm, t, -w/2 - 2.54, top - 2.54*(i + 1), 0))
    for i, (num, nm, t) in enumerate(right):
        pins.append(pin(num, nm, t, w/2 + 2.54, top - 2.54*(i + 1), 180))
    return f'''  (symbol "{name}" (exclude_from_sim no) (in_bom yes) (on_board yes)
    (property "Reference" "{ref}" (at 0 {top + 1.27:.2f} 0) (effects (font (size 1.27 1.27))))
    (property "Value" "{name}" (at 0 {-top - 1.27:.2f} 0) (effects (font (size 1.27 1.27))))
    (property "Footprint" "{fp}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
    (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
    (property "Description" "{desc}" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes))){extra_props}
    (symbol "{name}_0_1"
      (rectangle (start {-w/2:.2f} {top:.2f}) (end {w/2:.2f} {-top:.2f}) (stroke (width 0.254) (type default)) (fill (type background))))
    (symbol "{name}_1_1"
{chr(10).join(pins)}))
'''
syms = []
syms.append(box_symbol("CN3791", "U",
    [("9", "VCC", "power_in"), ("1", "VG", "passive"), ("6", "MPPT", "input"), ("5", "COM", "passive"), ("2", "GND", "power_in")],
    [("10", "DRV", "output"), ("8", "CSP", "input"), ("7", "BAT", "input"), ("3", "~{CHRG}", "open_collector"), ("4", "~{DONE}", "open_collector")],
    fp="Package_SO:SSOP-10_3.9x4.9mm_P1.00mm", desc="4A Li-ion charger with photovoltaic MPPT, Consonance, LCSC C154992"))
syms.append(box_symbol("LM66100", "U",
    [("1", "VIN", "power_in"), ("3", "~{CE}", "input"), ("2", "GND", "power_in")],
    [("6", "VOUT", "power_out"), ("5", "~{ST}", "open_collector"), ("4", "NC", "no_connect")],
    fp="Package_TO_SOT_SMD:SOT-363_SC-70-6", desc="5.5V 1.5A ideal diode, TI, LCSC C2869734", w=12.7))
syms.append(box_symbol("XIAO_nRF52840_Sense", "M",
    [("1", "D0/A0", "bidirectional"), ("2", "D1/A1", "bidirectional"), ("3", "D2/A2", "bidirectional"), ("4", "D3/A3", "bidirectional"),
     ("5", "D4/SDA", "bidirectional"), ("6", "D5/SCL", "bidirectional"), ("7", "D6/TX", "bidirectional")],
    [("14", "5V", "power_in"), ("13", "GND", "power_in"), ("12", "3V3", "power_in"), ("11", "D10/MOSI", "bidirectional"),
     ("10", "D9/MISO", "bidirectional"), ("9", "D8/SCK", "bidirectional"), ("8", "D7/RX", "bidirectional")],
    desc="Seeed XIAO nRF52840 Sense (pre-soldered), plugs into J4/J5 sockets; not placed on the PCB", w=17.78))
lib = "(kicad_symbol_lib (version 20241209) (generator \"hw_gen\") (generator_version \"1.0\")\n" + "".join(syms) + ")\n"
open("lib/hw.kicad_sym", "w").write(lib)

# --- footprint: 2.7 V 10 F supercap, D10 x L25, lying flat on the board, leads bent 90 deg into 2 holes at 5 mm pitch ---
def fp_supercap():
    L, D, gap = 25.0, 10.0, 2.5           # body length, diameter, body end -> hole row
    body_x0, body_x1 = -gap - L, -gap      # body lies along -X from the hole row
    t = f'''(footprint "SuperCap_D10_L25_Flat_P5.00mm"
  (version 20241229) (generator "hw_gen") (layer "F.Cu")
  (descr "2.7V 10F radial supercapacitor D10xL25 mounted flat: leads bent 90 deg at {gap} mm from the body")
  (attr through_hole)
  (property "Reference" "REF**" (at -15 -6.6 0) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.15))))
  (property "Value" "10F 2.7V" (at -15 6.6 0) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.15))))
  (fp_rect (start {body_x0} {-D/2}) (end {body_x1} {D/2}) (stroke (width 0.12) (type solid)) (fill no) (layer "F.SilkS"))
  (fp_text user "+" (at {body_x1 + 1.2} -3.6 0) (layer "F.SilkS") (effects (font (size 1.2 1.2) (thickness 0.18))))
  (fp_rect (start {body_x0 - 0.5} {-D/2 - 0.5}) (end 1.6 {D/2 + 0.5}) (stroke (width 0.05) (type solid)) (fill no) (layer "F.CrtYd"))
  (fp_rect (start {body_x0} {-D/2}) (end {body_x1} {D/2}) (stroke (width 0.1) (type solid)) (fill no) (layer "F.Fab"))
  (pad "1" thru_hole rect (at 0 -2.5) (size 1.8 1.8) (drill 1.0) (layers "*.Cu" "*.Mask"))
  (pad "2" thru_hole circle (at 0 2.5) (size 1.8 1.8) (drill 1.0) (layers "*.Cu" "*.Mask"))
)
'''
    open("lib/hw.pretty/SuperCap_D10_L25_Flat_P5.00mm.kicad_mod", "w").write(t)
fp_supercap()
print("ok")
