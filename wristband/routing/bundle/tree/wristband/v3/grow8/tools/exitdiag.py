"""[grow8 Q-4] Static pad-exit diagnosis: which connection ends have no legal exit at all, and what copper closes them.

  venv-python exitdiag.py DUMP.json OUT.json [PARAMS.json]      (PARAMS: pfroute parameters, e.g. {"neck": 1.4, "shield": [...]})

For every end group of every connection: breadth-first search over the cells the net's static rule mask allows (tracks on every
signal layer, vias where the via bit is set), from the group's copper, up to R_OPEN = 0.5 mm from it. An end that cannot get
R_OPEN away is "closed" (no weight or order can route it). For each closed end: the other-net fixed copper within 0.35 mm of the
reachable region (pads REF.N, vias, tracks; fan-out vias / stubs are the locked board copper of the plane nets), keep-outs, edge.
"""
import json, math, os, sys
from collections import deque
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pfroute

R_OPEN = 0.5


def main(dumpf, outf, prmf=None):
    prm = dict(pfroute.DEF)
    if prmf:
        prm.update(json.load(open(prmf)))
    D = json.load(open(dumpf))
    pfroute.SIG = list(D.get("sig", pfroute.SIG6))
    if prm.get("plane_nets") is None:
        prm["plane_nets"] = sorted(pfroute.PLANE_LAYER[D.get("nl", 6)])
    if prm.get("plane_fix") is None:
        prm["plane_fix"] = D.get("nl", 6) == 8
    R = pfroute.prep(D, prm)
    NX, NY, NL, G = R["NX"], R["NY"], R["NL"], R["GRID"]; P2 = NX * NY
    X0, Y0 = R["X0"], R["Y0"]
    inv = {v: k for k, v in R["nid"].items()}
    rad = int(R_OPEN / G)

    def mb(n, j, i):
        w = R["win"][n]
        if j < w[0] or j >= w[1] or i < w[2] or i >= w[3]:
            return 0
        return int(R["mask"][R["m_off"][n] + (j - w[0]) * (w[3] - w[2]) + (i - w[2])])

    # fixed copper objects for naming
    objs = []
    for pd in D.get("pads", []):
        for pg in pd["pts"]:
            objs.append(("pad %s.%s" % (pd["ref"], pd["num"]), pd["net"], np.array(pg)))
    for it in D["items"]:
        if it["k"] == "via":
            objs.append(("via%s" % ("" if it.get("rm") else " (locked: fan-out)"), it["net"], np.array([it["c"]]), it["r"]))
        elif it["k"] == "seg":
            objs.append(("track %s%s" % (it["layer"], "" if it.get("rm") else " (locked: fan-out)"), it["net"], np.array([it["a"], it["b"]]), it["r"]))

    def near_objs(pts_mm, net, dmax=0.35):
        res = {}
        for o in objs:
            if o[1] == net:
                continue
            q = o[2]; r = o[3] if len(o) > 3 else 0.0
            if len(q) == 2 and len(o) > 3:                       # segment
                a, b = q; d = np.inf
                ab = b - a; L2 = float(ab @ ab)
                t = np.clip(((pts_mm - a) @ ab) / L2, 0, 1) if L2 > 0 else np.zeros(len(pts_mm))
                d = np.hypot(*(pts_mm - (a + t[:, None] * ab)).T).min() - r
            else:
                d = np.min(np.hypot(pts_mm[:, None, 0] - q[None, :, 0], pts_mm[:, None, 1] - q[None, :, 1])) - r
            if d < dmax:
                k = "%s [%s]" % (o[0], o[1] or "netless")
                res[k] = min(res.get(k, 9), round(float(d), 3))
        return dict(sorted(res.items(), key=lambda kv: kv[1]))

    closed = []
    for k, c in enumerate(R["conns"]):
        n = c[0]; net = c[4]
        for side, g in (("a", c[1]), ("b", c[2])):
            cells = R["g_cells"][R["g_off"][g]:R["g_off"][g + 1]]
            if R["g_onplane"][g]:
                continue
            seen = set(int(v) for v in cells); dq = deque(seen)
            js = (cells % P2) // NX; is_ = cells % NX
            cj, ci = js.mean(), is_.mean(); r0 = math.hypot(js.max() - js.min(), is_.max() - is_.min()) / 2
            far = 0.0; ok = False
            while dq and len(seen) < 60000:
                v = dq.popleft(); l, r2 = divmod(v, P2); j, i = divmod(r2, NX)
                dist = math.hypot(j - cj, i - ci) - r0
                far = max(far, dist)
                if dist >= rad:
                    ok = True; break
                m = mb(n, j, i)
                for dj, di in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    jj, ii = j + dj, i + di
                    if 0 <= jj < NY and 0 <= ii < NX:
                        u = l * P2 + jj * NX + ii
                        if u not in seen and (mb(n, jj, ii) >> l) & 1:
                            seen.add(u); dq.append(u)
                if m & 64:
                    for l2 in range(NL):
                        u = l2 * P2 + r2
                        if u not in seen and (m >> l2) & 1:
                            seen.add(u); dq.append(u)
            if ok:
                continue
            reg = np.array(sorted(seen)); rj = (reg % P2) // NX; ri = reg % NX
            pts = np.c_[X0 + G * ri, Y0 + G * rj]
            ctr = (round(float(X0 + G * ci), 3), round(float(Y0 + G * cj), 3))
            pad = None
            best = 9
            for pd in D.get("pads", []):
                if pd["net"] == net:
                    d = math.dist(pd["c"], ctr)
                    if d < best:
                        best, pad = d, "%s.%s" % (pd["ref"], pd["num"])
            closed.append(dict(net=net, len=round(c[3], 2), end=side, at=ctr, pad=pad if best < 0.6 else None, reach_mm=round(far * G, 3),
                               layers_reached=sorted({pfroute.SIG[int(v) // P2] for v in reg}),
                               blockers=dict(list(near_objs(pts[:: max(1, len(pts) // 400)], net).items())[:8])))
    json.dump(dict(params={k: prm[k] for k in ("neck", "shield")}, closed=closed, n_closed_conns=len({(x["net"], x["len"]) for x in closed})),
              open(outf, "w"), indent=1)
    print("closed ends %d in %d connections" % (len(closed), len({(x["net"], x["len"]) for x in closed})))
    for x in closed:
        print(" ", x["net"], x["len"], x["end"], x["pad"], x["at"], "reach", x["reach_mm"], list(x["blockers"].items())[:4])


if __name__ == "__main__":
    main(*sys.argv[1:4])
