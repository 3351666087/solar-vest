Solar Vest 3D-printed parts (2026-10-17 revision)
=================================================

Every part comes in three formats with identical content; use whichever your slicer supports:
  .3mf  recommended (opens directly in Bambu Studio / PrusaSlicer / Cura, units cannot go wrong)
  .stl  generic mesh
  .step original CAD, use it when dimensions need changing

General settings: 0.2 mm layer height, 4 walls, 25–30 % gyroid infill.
Panel shoes: tree supports, 30 % infill, preferably ASA (UV-resistant); PETG also works.
The foot angles of the 6 panel shoes are computed individually for your back's curvature; they are NOT interchangeable, so label each one by its file name after printing.
All meshes have been checked to be closed (watertight); every part is a single solid.

18 distinct parts, 21 pieces in total: 17 worn on the body, 4 for the bench rig.

File name             Qty  Material                          Orientation        Envelope mm          Purpose / notes
back_pod_base         1    PETG white/light grey (reflects sunlight, runs cooler)    base down          101 × 131.6 × 26.5   Back pod (worn); PMB-H (M2×6 ×4) + 104050 battery (40.6 mm wide battery pocket + crush ribs; double-sided foam tape on the floor)
back_pod_lid          1    PETG white/light grey             top face down      101 × 131.6 × 18.5   Back pod lid (worn); M2×8 self-tapping ×4; a strip of 2 mm foam under each of the two hold-down ribs clamps the battery
webbing_hook          2    PETG                              on its side        24 × 34 × 7.7        Hangs the back pod on webbing C (worn); ×2 on the back of the back pod; M2×6 self-tapping screws driven from inside the pod
chest_pod_base        1    PETG                              base down          82.8 × 123.5 × 17.6  Chest pod (worn); LIB (bottom, M2×6 ×2) + BITalino Core B (top, four corner standoffs + two end stops)
chest_pod_lid         1    PETG                              top face down      82.8 × 123.5 × 9.5   Chest pod lid (worn); M2×8 self-tapping ×4; 2 mm foam under the two hold-down ribs presses on Core B's header row
c_case_base           1    PETG                              base down          126.5 × 85.8 × 16    C case (worn); C: BITalino Board (official 108 × 65) + 523450; board-edge stops + battery end stops; ECG lead plugs in through the left-side window
c_case_lid            1    PETG                              top face down      126.5 × 85.8 × 6.2   C case lid (worn); M2×8 ×4; 4 press posts (2 mm foam on each) hold down the board's two side rails; a flexure button actuates BTN
ear_clip_pulsesensor  1    PETG or TPU                       on its side        31.5 × 22 × 11       PulseSensor ear clip (worn); PulseSensor ear clip for A (left earlobe), 0.5 mm foam inside the jaws
panel_shoe_TL         1    ASA (UV-resistant) / PETG         tree supports      34.8 × 40.7 × 64.4   Panel shoe (worn); panel shoe top left (wearer's left/right), webbing face to panel back 42.0 mm, hangs on webbing A
panel_shoe_TR         1    ASA (UV-resistant) / PETG         tree supports      34.8 × 40.7 × 64.4   Panel shoe (worn); panel shoe top right (wearer's left/right), webbing face to panel back 42.0 mm, hangs on webbing A
panel_shoe_BL         1    ASA (UV-resistant) / PETG         tree supports      33.1 × 44.2 × 66.4   Panel shoe (worn); panel shoe bottom left (wearer's left/right), webbing face to panel back 42.6 mm, hangs on webbing B
panel_shoe_BR         1    ASA (UV-resistant) / PETG         tree supports      33.1 × 44.2 × 66.4   Panel shoe (worn); panel shoe bottom right (wearer's left/right), webbing face to panel back 42.6 mm, hangs on webbing B
panel_shoe_TM         1    ASA (UV-resistant) / PETG         tree supports      36 × 40.7 × 47.2     Panel shoe (worn); panel shoe top middle (wearer's left/right), webbing face to panel back 27.4 mm, hangs on webbing A
panel_shoe_BM         1    ASA (UV-resistant) / PETG         tree supports      36 × 43.2 × 40.6     Panel shoe (worn); panel shoe bottom middle (wearer's left/right), webbing face to panel back 20.2 mm, hangs on webbing B
ref1_holder           1    ASA/PETG                          —                  56 × 40 × 20         REF1 holder (worn); clips onto the middle of the panel's left short edge; 40.6 × 28.6 pocket for the AK 40×28 reference cell, foam tape underneath brings it flush with the glass
ref2_holder           1    ASA/PETG                          —                  50 × 40 × 24.8       REF2 holder (worn); left shoulder, 24.1° wedge levels the reference cell; 40.6 × 28.6 pocket; hook-side Velcro on the base
stand_base            2    PETG (bench rig, print 2)         —                  140 × 50 × 112       Test stand base (bench); panel test stand base, 0–90° in 15° steps, M4×25 + wing nut ×2
stand_cradle          2    PETG (print 2)                    —                  120 × 26 × 61.6      Test stand cradle (bench); U-channel gripping the panel's short edge; on the bench REF1 clips to the middle of the panel's top long edge

Actual filament use is about 350 g.

Screws (already in the JD.com shopping cart):
  M2×6 self-tapping ×10: PMB-H 4, hooks 4, LIB 2
  M2×8 self-tapping ×12: 4 each for the back pod lid, chest pod lid and C case lid
  M4×25 wing screw + wing nut ×4 sets: test stand

2026-10-17 update: revised to match the parts actually bought on JD.com + PLUX's official dimensions, so boards and batteries no longer rattle inside the pods
-----------------------------------------------------------------------------------------------------------------------------------------------------------
8 parts changed (the other 10 are unchanged):
  back_pod_base   battery pocket made specific to the 104050 (10×40×50): pocket width 40.6, three 0.3 mm crush ribs on each side,
                  1 mm stop rib at the end; the battery's lead end faces the divider rib (towards PMB-H)
  back_pod_lid    the two hold-down ribs lowered to 11 mm, clamping the battery through 2 mm foam
  chest_pod_base  two end stops added for Core B (x 30–36 and 44–52, clear of wire W07), so it can no longer slide towards LIB
  chest_pod_lid   (no geometry change, re-exported) 2 mm foam under each of the two hold-down ribs presses on Core B's header row
  c_case_base     board per Fig. 9 of the official manual: 108 × 65 mm; stops added on the opposite edge (clear of wire W12), end stop ribs added for the 523450 battery
  c_case_lid      4 press posts added, bearing on the board's two component-free side rails (a small piece of 2 mm foam on each)
  ref1_holder / ref2_holder  pocket changed to 40.6 × 28.6, an exact fit for the AK 40×28 reference cell (0.3 mm per side)

Foam needed during assembly (the 2 mm double-sided foam tape, 2 cm wide, in the JD.com cart):
  - 104050 battery underside: one strip, sticks it to the pod floor
  - Back pod lid, two hold-down ribs: one strip each
  - Chest pod lid, two hold-down ribs: one strip each
  - C lid, 4 press posts: a small piece each (about 5×5 mm)
  - 523450 battery top face: one strip (pressed down by the board)
  - Floors of the two reference-cell pockets: a small piece each, packing the cell up flush with the pocket rim
The NTC goes in the centre of the 104050 battery, between the two hold-down ribs (ribs at y = −88 and −110; the middle of the battery is left free).

Dimension sources: BITalino Core 65 × 56 mm, Board 65 × 108 mm (PLUX "BITalino (r)evolution User Manual", Fig. 8 and Fig. 9, PDF: https://support.pluxbiosignals.com/wp-content/uploads/2021/11/bitalino-revolution-user-manual.pdf);
  104050 battery and AK 40×28 reference cell per the JD.com product specifications; PMB-H / LIB per the KiCad board models.

Fit check (2026-10-17, script tools/cad/check_fit.py, results tools/cad/fit_report_2026-10-17.txt):
  Board-to-enclosure interference: 0 for PMB-H, LIB and Core B (with the board raised 0.05 mm, 0 points lie inside a solid; pushing it 1 mm into a wall is detected = the method works)
  Free travel (before → after): 104050 battery side-to-side 14 mm → clamped, up-down 3 → 1 mm (taken up by foam);
    Core B towards LIB 2.97 → 0.28 mm; Board Kit lateral 2.97 → 0.28 mm, up-down 3.38 → 1.19 mm (taken up by foam); 523450 front-back about 10 → 0.38 mm

For assembly instructions see docs/build-and-assembly-guide.md §3 and §5.
