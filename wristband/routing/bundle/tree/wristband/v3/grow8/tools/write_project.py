"""Write the KiCad project around the main board: .kicad_pro (net classes from design/netclasses.json, JLC 6-layer
board minimums), .kicad_dru (custom rules), fp/sym lib tables, and a copy of the schematic sheets (so ERC/parity and
the 3D viewer work from one project). Plain python.
JLC numbers [V: research/pv-mechanics.md §7, JLC capabilities page]: multilayer track/space 0.09/0.09 (3.5 mil),
via 0.15/0.25 min (preferred 0.2), via-in-pad POFV 0.15-0.55, castellated hole >= 0.5. Hole-to-hole 0.2 and
copper-to-edge 0.3 are this design's margins over JLC's minimum [E]."""
import json, os, shutil

W = "@SVROOT@/wristband"
OUT = W + "/layout/main"
NC = json.load(open(W + "/design/netclasses.json"))


def cls(name, track, clear, via=(0.4, 0.2), dp=(0.15, 0.2), prio=0):
    return {"name": name, "clearance": clear, "track_width": track, "via_diameter": via[0], "via_drill": via[1],
            "diff_pair_width": dp[0], "diff_pair_gap": dp[1], "diff_pair_via_gap": 0.25,
            "microvia_diameter": 0.2, "microvia_drill": 0.1, "wire_width": 6, "bus_width": 12, "line_style": 0,
            "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)", "priority": prio,
            "tuning_profile": ""}


def main():
    os.makedirs(OUT, exist_ok=True)
    c = NC["netclasses"]
    classes = [cls("Default", 0.10, 0.10, via=(0.3, 0.15), prio=2147483647)]
    order = ["RF_50R", "ECG_PAIR", "ECG_ELECTRODE", "MOHM_KEEPOUT", "ECG_LOCAL", "XTAL", "PPG_ANALOG", "PWR_HIGH",
             "PWR_LOW", "GND"]
    patterns = []
    for i, k in enumerate(order):
        d = c[k]
        via = tuple(reversed(d["via_mm"])) if "via_mm" in d else (0.3, 0.15)
        via = (max(via), min(via)) if "via_mm" in d else via
        clear = d.get("clearance_mm", d.get("gap_mm", 0.1))
        dp = (d["track_mm"], d.get("clearance_mm", 0.2)) if d.get("diff_pair") else (0.15, 0.2)
        classes.append(cls(k, d["track_mm"], clear, via=via, dp=dp, prio=i))
        for n in d["nets"]:
            patterns.append({"netclass": k, "pattern": n})
    pro = {
        "board": {
            "design_settings": {
                "defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2, "copper_text_size_h": 1.0,
                             "copper_text_size_v": 1.0, "copper_text_thickness": 0.15, "silk_line_width": 0.15,
                             "silk_text_size_h": 0.8, "silk_text_size_v": 0.8, "silk_text_thickness": 0.12,
                             "zones": {"min_clearance": 0.15}},
                "rules": {"min_clearance": 0.09, "min_track_width": 0.09, "min_via_diameter": 0.25,
                          "min_via_annular_width": 0.05, "min_through_hole_diameter": 0.15, "min_hole_to_hole": 0.2,
                          "min_hole_clearance": 0.15, "min_copper_edge_clearance": 0.3, "min_microvia_diameter": 0.2,
                          "min_microvia_drill": 0.1, "min_silk_clearance": 0.0, "min_text_height": 0.6,
                          "min_text_thickness": 0.08, "min_resolved_spokes": 1, "min_groove_width": 0.0,
                          "solder_mask_to_copper_clearance": 0.0, "max_error": 0.005, "use_height_for_length_calcs": True,
                          "allow_blind_buried_vias": False, "allow_microvias": False},
                "track_widths": [0.0, 0.1, 0.15, 0.17, 0.2, 0.3, 0.5],
                "via_dimensions": [{"diameter": 0.0, "drill": 0.0}, {"diameter": 0.3, "drill": 0.15},
                                   {"diameter": 0.4, "drill": 0.2}],
                "diff_pair_dimensions": [{"gap": 0.0, "via_gap": 0.0, "width": 0.0}],
            },
            "layer_presets": [], "viewports": [],
        },
        "net_settings": {"classes": classes, "meta": {"version": 4}, "net_colors": None,
                         "netclass_assignments": None, "netclass_patterns": patterns},
        "meta": {"filename": "solarband_main.kicad_pro", "version": 3},
        "pcbnew": {"page_layout_descr_file": ""},
        "schematic": {"drawing": {}},
        "sheets": json.load(open(W + "/design/kicad/main/solarband_main.kicad_pro"))["sheets"],
    }
    json.dump(pro, open(OUT + "/solarband_main.kicad_pro", "w"), indent=2)
    dru = """(version 1)
# SolarBand main board custom rules (layout/tools/write_project.py). Board minimums = JLC multilayer capability.
(rule "WLP fan-out U8 (0.09 only here, ARCH 5.3)"
  (condition "A.intersectsCourtyard('U8') || B.intersectsCourtyard('U8')")
  (constraint clearance (min 0.09mm)) (constraint track_width (min 0.09mm)))
(rule "Default signals 0.10 / 0.10 (ARCH 5.3)"
  (condition "A.NetClass == 'Default' && !A.intersectsCourtyard('U8')")
  (constraint track_width (min 0.10mm)))
(rule "Feed via L2 antipad 0.60 mm (C-14)"
  (layer "In1.Cu") (condition "A.NetName == 'ANT_FEED' && A.Type == 'Via' && B.Type == 'Zone'")
  (constraint clearance (min 0.1mm)))
(rule "CPWG gap 0.150 to the L1 GND pour (SIM-12)"
  (layer "F.Cu") (condition "A.NetClass == 'RF_50R' && B.Type == 'Zone'")
  (constraint clearance (min 0.15mm)))
(rule "JLC via 0.15 / 0.25 min, annular 0.05"
  (condition "A.Type == 'Via'") (constraint hole_size (min 0.15mm)) (constraint via_diameter (min 0.25mm)))
(rule "JLC plated pad annular ring"
  (condition "A.Type == 'Pad' && A.isPlated()") (constraint annular_width (min 0.13mm)))
(rule "Castellated C+/C- pads on the board edge (JLC castellated-hole option)"
  (condition "A.Fabrication_Property == 'Castellated pad'") (constraint edge_clearance (min -5mm)))
"""
    open(OUT + "/solarband_main.kicad_dru", "w").write(dru)
    open(OUT + "/fp-lib-table", "w").write("""(fp_lib_table
  (version 7)
  (lib (name "easyeda_rev") (type "KiCad") (uri "${KIPRJMOD}/../../design/lib/easyeda_rev.pretty") (options "") (descr "reviewed EasyEDA footprints (copper = JLC)"))
  (lib (name "easyeda") (type "KiCad") (uri "${KIPRJMOD}/../../design/lib/easyeda.pretty") (options "") (descr "raw EasyEDA conversion (cplgate reference)"))
  (lib (name "solarband") (type "KiCad") (uri "${KIPRJMOD}/../../design/lib/solarband.pretty") (options "") (descr "copper-only pads"))
  (lib (name "pv") (type "KiCad") (uri "${KIPRJMOD}/../../design/lib/pv.pretty") (options "") (descr "PV board footprints"))
  (lib (name "solarband_layout") (type "KiCad") (uri "${KIPRJMOD}/../lib/solarband_layout.pretty") (options "") (descr "layout-only footprints"))
)
""")
    # schematic copy (sheets + symbol lib) so the project is complete
    src = W + "/design/kicad/main"
    for fn in os.listdir(src):
        if fn.endswith(".kicad_sch") or fn in ("solarband.kicad_sym", "sym-lib-table"):
            shutil.copy(os.path.join(src, fn), os.path.join(OUT, fn))
    print("project written:", OUT)


if __name__ == "__main__":
    main()
