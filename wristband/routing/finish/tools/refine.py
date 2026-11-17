"""Hard-legal annealing refinement of a legal V3-F placement (legalize.py output): every accepted state is legal
(pairwise courtyard gap rule incl. the JLC table if jlc=full, rastered zones / height limits / edge band, NO_PLATE, NO_BSHADOW,
R-ECG-1 >= 8 mm). Moves: local shift, rotation, swap of two parts, jump toward the centroid of the part's connections.
Cost: weighted HPWL + decoupling pairs + soft plate avoidance (place_main.py). After v1's layout/tools/refine.py.
usage: [env] venv-python refine.py IN.json OUT.json [--iters N] [--seed S] [--t0 T]
"""
import argparse, json, math, os, random, sys, time
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lgeom as G
import place_main as P
from autoplace import load, Zones, gap_matrix, ov


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("inp"); ap.add_argument("out")
    ap.add_argument("--iters", type=int, default=1500000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--t0", type=float, default=1.5)
    a = ap.parse_args()
    random.seed(a.seed)
    src = json.load(open(a.inp)); pl = src.get("parts", src)
    if any(v.get("no_legal_spot") for v in src.get("violations", {}).values()):
        print("refine: input has unplaced parts; copied unchanged"); json.dump(src, open(a.out, "w"), indent=1); return
    parts, obj, nets = load()
    for r, q in pl.items():
        if r in obj:
            obj[r].x, obj[r].y, obj[r].r = q["x"], q["y"], q["rot"]
    for r, (x, y, rr) in P.ANCHORS.items():
        obj[r].x, obj[r].y, obj[r].r = x, y, rr
    anchors = set(P.ANCHORS)
    ZN = Zones(obj)
    fside = [r for r in sorted(obj) if obj[r].side == "F"]
    idx = {r: i for i, r in enumerate(fside)}
    R = np.array([obj[r].crt() for r in fside])
    GM = gap_matrix(fside)
    movable = [r for r in fside if r not in anchors]
    sw = set(P.SWITCHERS); fixed_aggr = set(P.FIXED_AGGR)
    ecg_items = P.ECG_ITEMS
    ecg_refs = {it if not isinstance(it, tuple) else it[0] for it in ecg_items}
    part_nets = {r: [] for r in obj}
    for n, pins in nets.items():
        for r in {r for r, _ in pins}:
            part_nets[r].append(n)
    pairs_of = {r: [] for r in obj}
    ALLP = list(P.PAIRS) + [(pp, ic, pad, -d) for (pp, ic, pad, d) in P.CRIT]
    for t in ALLP:
        pairs_of[t[0]].append(t); pairs_of[t[1]].append(t)

    def ept(it):
        return obj[it[0]].pad(it[1]) if isinstance(it, tuple) else (obj[it].x, obj[it].y)

    def ecg_ok(r):
        if r in sw:
            for it in ecg_items:
                q = ept(it)
                if math.hypot(obj[r].x - q[0], obj[r].y - q[1]) < P.ECG_MIN:
                    return False
        if r in ecg_refs:
            for it in ecg_items:
                if (it if not isinstance(it, tuple) else it[0]) != r:
                    continue
                q = ept(it)
                for s in sw | fixed_aggr:
                    if s == "J16" and r in P.E3_TIED:
                        continue
                    if math.hypot(obj[s].x - q[0], obj[s].y - q[1]) < P.ECG_MIN:
                        return False
        return True

    def legal(r, skip=None):
        o = obj[r]
        if ZN.area(o) > 1e-9:
            return False
        c = o.crt(); g = GM[idx[r]]
        w = np.minimum(R[:, 2], c[2]) - np.maximum(R[:, 0], c[0]) + g
        h = np.minimum(R[:, 3], c[3]) - np.maximum(R[:, 1], c[1]) + g
        hit = (w > 1e-6) & (h > 1e-6)
        hit[idx[r]] = False
        if skip is not None:
            hit[idx[skip]] = False
        if hit.any():
            return False
        return ecg_ok(r)

    def net_cost(n):
        pts = [obj[r].pad(num) for r, num in nets[n]]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return P.NET_W.get(n, 1.0) * ((max(xs) - min(xs)) + (max(ys) - min(ys)))

    def pair_cost(t):
        pp, ic, pad, w = t
        tx, ty = obj[ic].pad(pad)
        d = min(math.hypot(px - tx, py - ty) for px, py in (obj[pp].pad(k) for k in obj[pp].pads0))
        if w < 0:
            return P.CRIT_W * max(0.0, d + w) ** 2
        return w * d

    def soft(r):
        c = obj[r].cl(); pen = 0.0
        if r in P.HINTS:
            pen += ((c[2] - c[0]) * (c[3] - c[1]) - sum(ov(c, z) for z in P.HINTS[r])) * P.HINT_W
        if r in P.PLATE_OK or r in P.NO_PLATE:
            return pen
        return pen + G.rect_count(ZN.plate, c) * ZN.cell * P.PLATE_AVOID_W

    def cost(r):
        return sum(net_cost(n) for n in part_nets[r]) + sum(pair_cost(t) for t in pairs_of[r]) + soft(r)

    def cost2(r, q):
        ns = set(part_nets[r]) | set(part_nets[q]); ps = set(pairs_of[r]) | set(pairs_of[q])
        return sum(net_cost(n) for n in ns) + sum(pair_cost(t) for t in ps) + soft(r) + soft(q)

    def total():
        return sum(net_cost(n) for n in nets) + sum(pair_cost(t) for t in ALLP) + sum(soft(r) for r in movable)

    def target(r):
        pts = []
        for (pp, ic, pad, w) in pairs_of[r]:
            other = ic if pp == r else pp
            pts += [(obj[other].x, obj[other].y)] * 3
        for n in part_nets[r]:
            for (q, num) in nets[n]:
                if q != r:
                    pts.append(obj[q].pad(num))
        if not pts:
            return obj[r].x, obj[r].y
        return sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts)

    bad0 = [r for r in movable if not legal(r)]
    if bad0:
        print("refine: input not legal for", bad0[:10], "- these parts stay where they are until a legal move is found")
    c0 = total(); cur = c0; critv = []; bad = set(bad0)
    T0, T1 = a.t0, 0.01
    N = a.iters; acc = 0; t_start = time.time()
    for it in range(N):
        T = T0 * (T1 / T0) ** (it / N)
        r = random.choice(sorted(bad)) if (bad and random.random() < 0.3) else random.choice(movable); o = obj[r]
        old = (o.x, o.y, o.r)
        mv = random.random()
        if it % 20000 == 0:                             # critical pairs still beyond their limit: targeted swaps into the neighbourhood of the IC pin
            critv = []
            for (pp, ic, pad, dm) in P.CRIT:
                if pp in anchors:
                    continue
                tx, ty = obj[ic].pad(pad)
                if min(math.hypot(px - tx, py - ty) for px, py in (obj[pp].pad(k) for k in obj[pp].pads0)) > dm:
                    critv.append((pp, tx, ty, dm))
        cs = None
        if critv and mv < 0.10:
            pp, tx, ty, dm = random.choice(critv)
            near = [q for q in movable if q != pp and math.hypot(obj[q].x - tx, obj[q].y - ty) < dm + 0.5 and obj[q].area() <= 2.5 * obj[pp].area() + 1.0]
            if near:
                r = pp; o = obj[r]; old = (o.x, o.y, o.r); cs = random.choice(near)
        if mv < 0.12 or cs:
            q = cs or random.choice(movable)
            if q == r:
                continue
            oq = obj[q]; oldq = (oq.x, oq.y, oq.r)
            before = cost2(r, q)
            o.x, o.y, oq.x, oq.y = oq.x, oq.y, o.x, o.y
            R[idx[r]] = o.crt(); R[idx[q]] = oq.crt()
            ok = legal(r) and legal(q)
            if ok:
                d = cost2(r, q) - before
                ok = d < 0 or random.random() < math.exp(-d / T)
            if ok:
                cur += d; acc += 1
            else:
                o.x, o.y, o.r = old; oq.x, oq.y, oq.r = oldq
                R[idx[r]] = o.crt(); R[idx[q]] = oq.crt()
            continue
        before = cost(r)
        if mv < 0.27:
            o.r = random.choice((0, 90, 180, 270))
        elif mv < 0.42:
            tx, ty = target(r)
            s = 0.3 + 2.0 * random.random()
            o.x = round((tx + random.gauss(0, s)) / 0.025) * 0.025; o.y = round((ty + random.gauss(0, s)) / 0.025) * 0.025
            if random.random() < 0.5:
                o.r = random.choice((0, 90, 180, 270))
        else:
            s = 0.05 + 1.2 * T / T0
            o.x = round((o.x + random.gauss(0, s)) / 0.025) * 0.025; o.y = round((o.y + random.gauss(0, s)) / 0.025) * 0.025
        R[idx[r]] = o.crt()
        ok = legal(r)
        if ok:
            d = cost(r) - before
            if r in bad:                                # repair: a part that was not legal takes the first legal position
                bad.discard(r)
            else:
                ok = d < 0 or random.random() < math.exp(-d / T)
        if ok:
            cur += d; acc += 1
        else:
            o.x, o.y, o.r = old
            R[idx[r]] = o.crt()
        if it % 250000 == 0:
            print("it %d T %.3f cost %.1f accepted %d (%.0f s)" % (it, T, cur, acc, time.time() - t_start), flush=True)
    c1 = total()
    still = [r for r in movable if not legal(r)]
    out = {r: dict(x=round(obj[r].x, 4), y=round(obj[r].y, 4), rot=obj[r].r, side=obj[r].side, need=obj[r].need, anchor=r in anchors) for r in obj}
    json.dump(dict(parts=out, cost=c1, violations={r: dict(not_legal=True) for r in still}, refined_from=os.path.basename(a.inp), seed=a.seed,
                   iters=N, variant=G.VARIANT, zones=G.ZTAG, opts=G.OPTS), open(a.out, "w"), indent=1)
    print("refine: cost %.1f -> %.1f (%.1f %%), accepted %d of %d, not legal %s -> %s" % (c0, c1, 100 * (c1 - c0) / c0, acc, N, still, a.out))


if __name__ == "__main__":
    main()
