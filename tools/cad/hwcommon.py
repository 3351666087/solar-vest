"""Shared SKiDL setup + the part catalogue (KiCad symbol, footprint, JLC/LCSC part number).

Every part placed on a board carries an LCSC number so the BOM goes straight into JLCPCB assembly.
'jlc' = 'base' (no loading fee) or 'ext' (extended library) — checked against the JLCPCB API on 2026-10-11.
"""
import json, os
from skidl import *

KICAD = os.path.expanduser("~/Applications/KiCad/KiCad/KiCad/KiCad.app/Contents/SharedSupport")
HERE = os.path.dirname(os.path.abspath(__file__))
set_default_tool(KICAD10)
lib_search_paths[KICAD10] = [os.path.join(KICAD, "symbols"), os.path.join(HERE, "lib")]
footprint_search_paths[KICAD10] = [HERE]

# key: (symbol lib, symbol, footprint, value, LCSC, jlc lib)
CAT = {
    # passives (0603 unless noted)
    "R10k":    ("Device", "R", "Resistor_SMD:R_0603_1608Metric", "10k", "C25804", "base"),
    "R100k":   ("Device", "R", "Resistor_SMD:R_0603_1608Metric", "100k", "C25803", "base"),
    "R1k":     ("Device", "R", "Resistor_SMD:R_0603_1608Metric", "1k", "C21190", "base"),
    "R4k7":    ("Device", "R", "Resistor_SMD:R_0603_1608Metric", "4.7k", "C23162", "base"),
    "R22k":    ("Device", "R", "Resistor_SMD:R_0603_1608Metric", "22k", "C31850", "base"),
    "R200k": ("Device", "R", "Resistor_SMD:R_0603_1608Metric", "200k", "C25811", "base"),
    "R51k": ("Device", "R", "Resistor_SMD:R_0603_1608Metric", "51k", "C23196", "base"),
    "R1M": ("Device", "R", "Resistor_SMD:R_0603_1608Metric", "1M", "C22935", "base"),
    "R5k1":    ("Device", "R", "Resistor_SMD:R_0603_1608Metric", "5.1k", "C23186", "base"),
    "R120":    ("Device", "R", "Resistor_SMD:R_0603_1608Metric", "120", "C22787", "base"),
    "R33_2512":("Device", "R", "Resistor_SMD:R_2512_6332Metric", "33 1W", "C53728", "ext"),
    "RS_50m":  ("Device", "R", "Resistor_SMD:R_1206_3216Metric", "0.05 1W 1%", "C2904224", "ext"),
    "RS_100m": ("Device", "R", "Resistor_SMD:R_1206_3216Metric", "0.1 1W 1%", "C2903496", "ext"),
    "RS_470m": ("Device", "R", "Resistor_SMD:R_1206_3216Metric", "0.47 1%", "C28320", "ext"),
    "RS_220m": ("Device", "R", "Resistor_SMD:R_1206_3216Metric", "0.22 1W 1%", "C6627428", "ext"),   # Yageo PE1206FRF470R22L
    "C100n":   ("Device", "C", "Capacitor_SMD:C_0603_1608Metric", "100n", "C14663", "base"),
    "C1u":     ("Device", "C", "Capacitor_SMD:C_0603_1608Metric", "1u 50V", "C15849", "base"),
    "C10u":    ("Device", "C", "Capacitor_SMD:C_0603_1608Metric", "10u 10V", "C19702", "base"),
    "C220n":   ("Device", "C", "Capacitor_SMD:C_0603_1608Metric", "220n", "C21120", "base"),
    "C22u":    ("Device", "C", "Capacitor_SMD:C_0805_2012Metric", "22u 25V", "C45783", "base"),
    "L22u":    ("Device", "L", "Inductor_SMD:L_Sunlord_SWPA6045S", "22uH 1.8A", "C83454", "ext"),
    "PPTC":    ("Device", "Polyfuse", "Fuse:Fuse_1812_4532Metric", "1.5A 16V", "C883152", "ext"),
    # semiconductors
    "AO3401A": ("Transistor_FET", "AO3401A", "Package_TO_SOT_SMD:SOT-23", "AO3401A", "C15127", "base"),
    "AO3400A": ("Transistor_FET", "AO3400A", "Package_TO_SOT_SMD:SOT-23", "AO3400A", "C20917", "base"),
    "SS34":    ("Diode", "SS34", "Diode_SMD:D_SMA", "SS34", "C8678", "base"),
    "B5819W":  ("Device", "D_Schottky", "Diode_SMD:D_SOD-123", "B5819W", "C8598", "base"),
    "Z10V":    ("Device", "D_Zener", "Diode_SMD:D_SOD-123", "BZT52C10", "C173431", "ext"),
    "SMAJ10A": ("Diode", "SMAJ10A", "Diode_SMD:D_SMA", "SMAJ10A", "C134939", "ext"),
    "SMF5V0A": ("Device", "D_TVS", "Diode_SMD:D_SOD-123F", "SMF5.0A", "C193402", "ext"),
    "BAT54S":  ("Diode", "BAT54S", "Package_TO_SOT_SMD:SOT-23", "BAT54S", "C47546", "ext"),
    "CN3791":  ("hw", "CN3791", "Package_SO:SSOP-10_3.9x4.9mm_P1.00mm", "CN3791", "C154992", "ext"),
    "INA226":  ("Sensor_Energy", "INA226", "Package_SO:MSOP-10_3x3mm_P0.5mm", "INA226AIDGSR", "C49851", "ext"),
    "LM66100": ("hw", "LM66100", "Package_TO_SOT_SMD:SOT-363_SC-70-6", "LM66100DCKR", "C2869734", "ext"),
    "ME6211":  ("Regulator_Linear", "ME6211C33M5", "Package_TO_SOT_SMD:SOT-23-5", "ME6211C33M5G-N", "C82942", "ext"),
    # connectors / mechanics
    "PH2":     ("Connector_Generic", "Conn_01x02", "Connector_JST:JST_PH_S2B-PH-SM4-TB_1x02-1MP_P2.00mm_Horizontal", "PH2.0 2P", "C295747", "ext"),
    "PH5":     ("Connector_Generic", "Conn_01x05", "Connector_JST:JST_PH_S5B-PH-SM4-TB_1x05-1MP_P2.00mm_Horizontal", "PH2.0 5P", "C265104", "ext"),
    "KF350":   ("Connector", "Screw_Terminal_01x02", "TerminalBlock_Phoenix:TerminalBlock_Phoenix_PT-1,5-2-3.5-H_1x02_P3.50mm_Horizontal", "KF350-3.5-2P", "C474892", "ext"),
    "SOCK7":   ("Connector_Generic", "Conn_01x07", "Connector_PinSocket_2.54mm:PinSocket_1x07_P2.54mm_Vertical", "PM254-1-07-Z-8.5", "C2897370", "ext"),
    "NETTIE":  ("Device", "NetTie_2", "NetTie:NetTie-2_SMD_Pad0.5mm", "NetTie", None, None),
    "TP":      ("Connector", "TestPoint", "TestPoint:TestPoint_Pad_D1.5mm", "TP", None, None),
    "HOLE":    ("Mechanical", "MountingHole", "MountingHole:MountingHole_2.2mm_M2", "M2", None, None),
    "SUPERCAP":("Device", "C_Polarized", "hw:SuperCap_D10_L25_Flat_P5.00mm", "10F 2.7V", None, "user"),
    "CP100u35":("Device", "C_Polarized", "Capacitor_SMD:CP_Elec_6.3x7.7", "100u 35V", "C2836437", "ext"),   # alu electrolytic, ESR 0.6 Ω@100 kHz
    "XIAO":    ("hw", "XIAO_nRF52840_Sense", "", "XIAO nRF52840 Sense", None, "user"),
}

def mk(key, block, value=None, **kw):
    lib, sym, fp, val, lcsc, jl = CAT[key]
    p = Part(lib, sym, footprint=fp, value=value or val, **kw)
    p.block = block; p.lcsc = lcsc; p.jlc = jl; p.catkey = key
    return p

def export_parts(path):
    rows = {}
    for p in default_circuit.parts:
        rows[p.ref] = dict(value=p.value, footprint=p.footprint, lcsc=getattr(p, "lcsc", None), jlc=getattr(p, "jlc", None),
                           block=getattr(p, "block", ""), sym=f"{p.lib.filename if hasattr(p.lib, 'filename') else ''}:{p.name}",
                           catkey=getattr(p, "catkey", ""),
                           pins={str(pin.num): (pin.net.name if pin.net else None) for pin in p.pins},
                           pinnames={str(pin.num): pin.name for pin in p.pins})
    json.dump(rows, open(path, "w"), indent=1, ensure_ascii=False)
