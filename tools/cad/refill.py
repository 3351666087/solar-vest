"""Re-apply zone settings and refill an already-routed board (keeps the routing). usage: kicad-python refill.py <b>"""
import os, sys, pcbnew
B = sys.argv[1]; p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", B, f"{B}.kicad_pcb")
brd = pcbnew.LoadBoard(p); MM = pcbnew.FromMM
for z in brd.Zones():
    z.SetThermalReliefGap(MM(0.3)); z.SetThermalReliefSpokeWidth(MM(0.5))
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
pcbnew.ZONE_FILLER(brd).Fill(brd.Zones()); brd.Save(p); print("refilled", B)
