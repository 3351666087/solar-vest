"""[grow8 Q-4] Clear the escape halos of a placement: move intruding parts out of the halo boxes of U7, U1, U6, U15, U17 (evolve.py
halo model; own decoupling exempt), each move checked LEGAL by check_placement.py and accepted only when the total intrusion falls.
  venv-python halo_clean.py IN_placement.json OUT_placement.json [HALO_MM=0.8]"""
import json, math, sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import evolve

src, dst = sys.argv[1], sys.argv[2]
halo = float(sys.argv[3]) if len(sys.argv) > 3 else evolve.HALO0
pl = json.load(open(src)); parts = pl["parts"]
tot0 = sum(evolve.halo_intrusion(parts, halo).values()); log = []
for rnd in range(3):
    intr = evolve.halo_intrusion(parts, halo)
    for ref in sorted(intr, key=lambda r: -intr[r]):
        q = parts[ref]
        if q.get("anchor"):
            continue
        hc = evolve.halo_center(parts, ref)
        if not hc:
            continue
        base = sum(evolve.halo_intrusion(parts, halo).values())
        x0, y0 = q["x"], q["y"]; a0 = math.atan2(y0 - hc[2], x0 - hc[1]); done = False
        for d in (0.15, 0.3, 0.45, 0.6, 0.8):
            for da in (0.0, 0.4, -0.4, 0.8, -0.8, 1.57, -1.57):
                q["x"], q["y"] = round(x0 + d * math.cos(a0 + da), 3), round(y0 + d * math.sin(a0 + da), 3)
                t = sum(evolve.halo_intrusion(parts, halo).values())
                if t < base - 1e-3:
                    json.dump(pl, open(dst, "w"), indent=1)
                    if evolve.check(dst, dst[:-5]):
                        log.append((ref, round(q["x"] - x0, 3), round(q["y"] - y0, 3), 0)); done = True; break
            if done:
                break
        if not done:
            q["x"], q["y"] = x0, y0
pl.pop("violations", None)
json.dump(pl, open(dst, "w"), indent=1)
tot1 = sum(evolve.halo_intrusion(parts, halo).values())
print("halo %.2f: intrusion %.3f -> %.3f mm2, moves %s" % (halo, tot0, tot1, log))
json.dump(dict(halo=halo, before=tot0, after=tot1, moves=log), open(dst[:-5] + "_halo.json", "w"), indent=1)
