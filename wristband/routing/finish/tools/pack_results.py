"""[grow G-4] Pack a run for the trip home: log, curve, config, best board, and the TOP best evaluations (enough to resume elsewhere).
  python pack_results.py RUNDIR OUT.tar.gz [--top 12]"""
import argparse, json, os, tarfile

ap = argparse.ArgumentParser(); ap.add_argument("rundir"); ap.add_argument("out"); ap.add_argument("--top", type=int, default=12)
a = ap.parse_args()
rd = os.path.abspath(a.rundir)
rows = [json.loads(l) for l in open(rd + "/results.jsonl")]
ok = sorted([r for r in rows if r["fitness"] < 1e9], key=lambda r: (r["fitness"], r.get("overused") or 1e9))
keep = {"results.jsonl", "curve.json", "config.json", "best"}
skip = ("fan.kicad_pcb", "routed.kicad_pcb", "dump.json", "drc_fan.json", "v3f_g1_fan.kicad_pcb", "tmp")
with tarfile.open(a.out, "w:gz") as t:
    for k in keep:
        if os.path.exists(rd + "/" + k):
            t.add(rd + "/" + k, arcname=os.path.basename(rd) + "/" + k)
    for r in ok[:a.top]:
        d = os.path.join(rd, r["dir"])
        t.add(d, arcname=os.path.basename(rd) + "/" + os.path.relpath(d, rd), filter=lambda ti: None if os.path.basename(ti.name) in skip else ti)
print("packed %d rows, best %s fitness %s -> %s" % (len(rows), ok[0]["id"] if ok else "-", ok[0]["fitness"] if ok else "-", a.out))
