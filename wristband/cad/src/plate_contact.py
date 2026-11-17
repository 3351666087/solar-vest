"""[S1 C-14] plate skin-contact sensitivity (was published as out/plate_contact_L40.json without a script).
Method (as published): contact strip half-width w = sqrt(2 R d) at the dorsal vertex of the q 0.68 ellipse (R = a^2 / b, strap-lane model,
ellipse_axes of geom_v3f), d = floor indentation into the skin beyond the pressed-in mesa (0.4 / 0.6 / 1.0 mm, E); contact area of each plate =
plate outline (geom_v3f.plate_outlines) inside the strip Y 16 +- w; compared with the project's 14.9 mm strip convention (Lens D) and
G-7 (>= 150 mm2 per plate). All values are model output (E): the q 0.68 section ratio was measured at the distal flexor crease, 15-20 mm
distal of where the pod sits (review C-17), and the model is symmetric.
usage: V3F_POD_L=40|41 python3 -B plate_contact.py   -> out/plate_contact_L<..>.json"""
import json, math, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import geom_v3f as G   # noqa: E402
OUT = G.OUT_DIR; TAG = G.TAG
e1, e2 = G.plate_outlines()
res = dict(method="contact strip half-width w = sqrt(2 R d) at the dorsal vertex of the q 0.68 ellipse (R = a^2/b); d = floor indentation into the "
                  "skin beyond the pressed-in mesa (E); compared with the project's 14.9 mm strip convention (Lens D)",
           caveat="E: q 0.68 measured at the distal flexor crease, the pod sits 15-20 mm proximal of it (S1 C-17); symmetric wrist model",
           wrists={}, convention_14p9=dict(E1=round(G.contact_area(e1), 1), E2=round(G.contact_area(e2), 1)), G7_min_mm2=G.G7_MIN_MM2,
           plate_area_mm2=dict(E1=round(e1.area, 1), E2=round(e2.area, 1)))
for Cw in G.WRISTS:
    a, b = G.ellipse_axes(Cw)
    R = a * a / b
    row = dict(R_vertex_mm=round(R, 1))
    for d in (0.4, 0.6, 1.0):
        w = math.sqrt(2 * R * d)
        yc = G.POD_W / 2      # [G1] the pod centre line (16.0 at 32 mm)
        row[f"indent {d:.1f}"] = dict(strip_mm=round(2 * w, 1), E1=round(G.contact_area(e1, (yc - w, yc + w)), 1), E2=round(G.contact_area(e2, (yc - w, yc + w)), 1))
    res["wrists"][str(int(Cw))] = row
json.dump(res, open(os.path.join(OUT, f"plate_contact_{TAG}.json"), "w"), indent=1)
print(json.dumps(res["wrists"]["130"]), res["convention_14p9"])
