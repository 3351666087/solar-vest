"""Deterministic simulated-annealing placer for the sky side of the SolarBand V3-F main board
(the v1 / V2-B annealer of v2/layout/tools/autoplace.py with the V3-F zones of lgeom.py / place_main.py).

Anchors (place_main.ANCHORS) are fixed. Every other sky-side part gets (x, y, rot in 0/90/180/270).
Cost = net half-perimeter wirelength (weighted, GND / VDD_1V8 skipped) + proximity-pair distances
     + W x courtyard overlap area + W x courtyard area in cells the part may not use (rastered CAD zones, 0.05 mm)
     + soft terms (plate avoidance, hints) + ECG distance penalty.
Hard rules (reported as violations):
  - courtyard overlap. gap=v1: pcbnew courtyard bounding boxes kept 0.05 mm apart (v1 rule); gap=dru: F.CrtYd centre-line boxes may touch;
  - the F.CrtYd centre-line box lies inside the board minus the 0.5 mm edge band and only on cells whose height limit covers the
    part (body + 0.05 mm solder): keep-outs, no-part zones, cut-out, post / rail feet, K and J11 zones are -1; ufpc: FID1 / FID2 / J12 may
    use the display FPC return run;
  - NO_PLATE parts outside the plates; NO_BSHADOW parts not above skin-face pads; R-ECG-1 >= 8 mm.
usage: G1_ZONES=.. G1_VARIANT=.. [G1_OPTS=..] venv-python autoplace.py [--iters N] [--seed S] [--init J] [--out J]
"""
import argparse, json, math, os, random, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np
import lgeom as G
import place_main as P

GAP = P.BASE_GAP                              # centre-line gap of the courtyard rule; pairs may need more (P.pair_gap, JLC table)
BIG = 1000.0
WT = {'ov': 1000.0, 'zone': 1000.0}
WB = {}                                        # per-part weight on overlap / zone cost (big and tall parts settle first)


def rot_pt(x, y, r):
    c, s = round(math.cos(math.radians(r))), round(math.sin(math.radians(r)))
    return x * c - y * s, x * s + y * c


def rect_rot(b, r):
    x0, y0, x1, y1 = b
    pts = [rot_pt(x, y, r) for x, y in ((x0, y0), (x1, y0), (x0, y1), (x1, y1))]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def ov(a, b):
    w = min(a[2], b[2]) - max(a[0], b[0])
    h = min(a[3], b[3]) - max(a[1], b[1])
    return w * h if (w > 0 and h > 0) else 0.0


class Part:
    def __init__(self, ref, fg, need):
        self.ref = ref
        self.side = fg["side"]
        m = -1 if self.side == "B" else 1               # skin-face parts are mirrored about the local Y axis (flip left-right)
        def conv(k):                                    # KiCad local (y down) -> board local (y up)
            return (min(m * k[0], m * k[2]), -k[3], max(m * k[0], m * k[2]), -k[1])
        self.bb0 = conv(fg["crt"])                      # pcbnew courtyard bounding box (v1's measure)
        self.cl0 = conv(P.clbox(ref))                   # F.CrtYd centre line (project measure, zone rule)
        self.ov0 = self.cl0                             # overlap test on the centre-line boxes with a pairwise gap
        self.pads0 = {}
        self.padlist = []
        for p in fg["pads"]:
            self.padlist.append((p["num"], m * p["x"], -p["y"], p["w"], p["h"]))
            if p["num"]:
                self.pads0.setdefault(p["num"], (m * p["x"], -p["y"]))
        self.need = need                                # zone height this part needs (0 = copper-only feature)
        self.x = self.y = 0.0
        self.r = 0

    def _box(self, b0, x, y, r, g):
        x = self.x if x is None else x; y = self.y if y is None else y; r = self.r if r is None else r
        b = rect_rot(b0, -r if self.side == "B" else r)     # KiCad: orientation, then flip left-right
        return (x + b[0] - g, y + b[1] - g, x + b[2] + g, y + b[3] + g)

    def crt(self, x=None, y=None, r=None, gap=0.0):
        """centre-line box grown by gap / 2"""
        return self._box(self.ov0, x, y, r, gap / 2)

    def cl(self, x=None, y=None, r=None):
        """F.CrtYd centre-line box (zone rule)"""
        return self._box(self.cl0, x, y, r, 0.0)

    def bb(self, x=None, y=None, r=None):
        return self._box(self.bb0, x, y, r, 0.0)

    def pad(self, num, x=None, y=None, r=None):
        x = self.x if x is None else x; y = self.y if y is None else y; r = self.r if r is None else r
        px, py = self.pads0[num]
        dx, dy = rot_pt(px, py, -r if self.side == "B" else r)
        return x + dx, y + dy

    def area(self):                                     # project measure
        c = self.cl0
        return (c[2] - c[0]) * (c[3] - c[1])

    def area_bb(self):                                  # v1's bounding-box measure
        c = self.bb0
        return (c[2] - c[0]) * (c[3] - c[1])


def load():
    parts, fg = P.PARTS, P.FPG
    obj = {r: Part(r, fg[r], P.need_h(r)) for r in parts}
    nets = {}
    for r, p in parts.items():
        for num, n in p["pins"].items():
            if n and n not in P.SKIP_NETS and num in obj[r].pads0:
                nets.setdefault(n, []).append((r, num))
    nets = {n: v for n, v in nets.items() if len({r for r, _ in v}) >= 2}
    for r, (x, y, rr) in P.ANCHORS.items():
        obj[r].x, obj[r].y, obj[r].r = x, y, rr
    return parts, obj, nets


def gap_matrix(refs):
    """required centre-line gap for every pair of refs (courtyard rule, JLC table if jlc=full)"""
    n = len(refs)
    M = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            M[i, j] = M[j, i] = P.pair_gap(refs[i], refs[j])
    return M


class Zones:
    """rastered legality of the centre-line courtyard of a movable part"""
    def __init__(self, obj):
        self.lim = G.limit_raster(False)
        self.lim_u = G.limit_raster(True) if P.UFPC_REFS else None
        self.S = {}
        self.plate = G.integral(G._touched(G.PLATE_U))
        self.offplate = G.integral(~G._allowed_all_corners(G.PLATE_U))      # cells not fully over a plate
        self.bshadow = [obj[r].cl() for r in obj if obj[r].side == "B"]
        self.cell = G.RES * G.RES

    def key(self, o):
        return ("u" if o.ref in P.UFPC_REFS else "n", round(o.need, 3))

    def integral(self, o):
        k = self.key(o)
        if k not in self.S:
            lim = self.lim_u if k[0] == "u" else self.lim
            thr = (o.need - 1e-9) if o.need > 0 else -0.5      # copper-only features: every cell that is not -1
            bad = lim < thr
            self.S[k] = G.integral(bad)
        return self.S[k]

    def area(self, o, c=None):
        """mm2 of the centre-line courtyard of o on cells it may not use (0 = legal)"""
        c = o.cl() if c is None else c
        pen = G.rect_count(self.integral(o), c) * self.cell
        out = max(0.0, G.X0 - c[0]) + max(0.0, c[2] - (G.X0 + G.NX * G.RES)) + max(0.0, G.Y0 - c[1]) + max(0.0, c[3] - (G.Y0 + G.NY * G.RES))
        if out > 0:                                     # beyond the raster: everything is forbidden, and the penalty grows with the distance
            pen += (c[2] - c[0]) * (c[3] - c[1]) + 5.0 * out
        if o.ref in P.NO_PLATE:
            pen += G.rect_count(self.plate, c) * self.cell
        if o.ref in P.NO_BSHADOW:
            pen += sum(ov(c, z) for z in self.bshadow)
        if o.ref in P.ON_PLATE:
            pen += G.rect_count(self.offplate, c) * self.cell
        return pen


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--iters", type=int, default=1200000)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--init", default=None, help="start from an existing placement json")
    ap.add_argument("--out", default=None)
    ap.add_argument("--t0", type=float, default=4.0)
    ap.add_argument("--no-skeleton", dest="skeleton", action="store_false", help="soft big parts (default: big / tall parts are hard-legal from a guided legal start)")
    a = ap.parse_args()
    random.seed(a.seed)
    parts, obj, nets = load()
    anchors = P.ANCHORS
    movable = [r for r in sorted(obj) if r not in anchors and obj[r].side == "F"]
    ZN = Zones(obj)
    part_nets = {r: [] for r in obj}
    for n, pins in nets.items():
        for r in {r for r, _ in pins}:
            part_nets[r].append(n)
    pairs_of = {r: [] for r in obj}
    ALLP = list(P.PAIRS) + [(pp, ic, pad, -d) for (pp, ic, pad, d) in P.CRIT]
    for (pp, ic, pad, w) in ALLP:
        pairs_of[pp].append((pp, ic, pad, w)); pairs_of[ic].append((pp, ic, pad, w))
    sw = set(P.SWITCHERS) | set(P.FIXED_AGGR)
    ecg_items = P.ECG_ITEMS
    plate_ok = P.PLATE_OK

    init = json.load(open(a.init)) if a.init else {}
    init = init.get("parts", init)
    for r in movable:
        if r in init:
            obj[r].x, obj[r].y, obj[r].r = init[r]["x"], init[r]["y"], init[r]["rot"]
            continue
        tgt = []
        for (pp, ic, pad, w) in pairs_of[r]:
            if pp == r and ic in anchors:
                tgt.append(obj[ic].pad(pad))
        for n in part_nets[r]:
            for (rr, num) in nets[n]:
                if rr in anchors:
                    tgt.append(obj[rr].pad(num))
        if tgt:
            obj[r].x = sum(t[0] for t in tgt) / len(tgt) + random.uniform(-1, 1)
            obj[r].y = sum(t[1] for t in tgt) / len(tgt) + random.uniform(-1, 1)
        else:
            obj[r].x, obj[r].y = random.uniform(2, G.BOARD_W - 2), random.uniform(2, G.BOARD_H - 2)
        obj[r].r = random.choice((0, 90, 180, 270))

    def net_cost(n):
        pts = [obj[r].pad(num) for r, num in nets[n]]
        xs, ys = [p[0] for p in pts], [p[1] for p in pts]
        return P.NET_W.get(n, 1.0) * ((max(xs) - min(xs)) + (max(ys) - min(ys)))

    def pair_cost(t):
        pp, ic, pad, w = t
        tx, ty = obj[ic].pad(pad)
        d = min(math.hypot(px - tx, py - ty) for px, py in (obj[pp].pad(k) for k in obj[pp].pads0))
        if w < 0:                                       # critical pair: -w = distance limit
            return P.CRIT_W * max(0.0, d + w) ** 2
        return w * d

    plate_S = ZN.plate

    def zone_cost(r, soft=True):
        o = obj[r]
        c = o.cl()
        pen = ZN.area(o, c) * WT['zone']
        if soft:
            if r not in plate_ok and r not in P.NO_PLATE:
                pen += G.rect_count(plate_S, c) * ZN.cell * P.PLATE_AVOID_W
            if r in P.HINTS:
                area = (c[2] - c[0]) * (c[3] - c[1])
                pen += (area - sum(ov(c, z) for z in P.HINTS[r])) * P.HINT_W
        return pen

    ecg_refs = {it if not isinstance(it, tuple) else it[0] for it in ecg_items}

    def _ecg_pt(it):
        return obj[it[0]].pad(it[1]) if isinstance(it, tuple) else (obj[it].x, obj[it].y)

    def ecg_cost(r):
        pen = 0.0
        if r in sw:
            pairs = [(r, it) for it in ecg_items]
        elif r in ecg_refs:
            pairs = [(s_, it) for s_ in sw for it in ecg_items if (it if not isinstance(it, tuple) else it[0]) == r]
        else:
            return 0.0
        for s_, it in pairs:
            if s_ == "J16" and (it if not isinstance(it, tuple) else it[0]) in P.E3_TIED:
                continue
            q = _ecg_pt(it)
            d = math.hypot(obj[s_].x - q[0], obj[s_].y - q[1])
            if d < P.ECG_MIN + 1.0:
                pen += (P.ECG_MIN + 1.0 - d) ** 2 * 200
        return pen

    fside = [q for q in sorted(obj) if obj[q].side == "F"]
    idx = {q: i for i, q in enumerate(fside)}
    R = np.array([obj[q].crt() for q in fside])
    GM = gap_matrix(fside)

    def sync(r):
        if r in idx:
            R[idx[r]] = obj[r].crt()

    def ov_cost(r):
        c = obj[r].crt()
        g = GM[idx[r]]
        w = np.minimum(R[:, 2], c[2]) - np.maximum(R[:, 0], c[0]) + g
        h = np.minimum(R[:, 3], c[3]) - np.maximum(R[:, 1], c[1]) + g
        a_ = np.where((w > 1e-9) & (h > 1e-9), w * h, 0.0)
        a_[idx[r]] = 0.0
        return float(a_.sum()) * WT['ov']

    def part_cost(r):
        s = sum(net_cost(n) for n in part_nets[r]) + sum(pair_cost(t) for t in pairs_of[r])
        s += (zone_cost(r) + ov_cost(r)) * WB.get(r, 1.0) + ecg_cost(r)
        return s

    def total():
        s = sum(net_cost(n) for n in nets) + sum(pair_cost(t) for t in ALLP)
        s += sum(zone_cost(r) for r in movable) + sum(ov_cost(r) for r in movable) / 2 + sum(ecg_cost(r) for r in sw)
        return s

    # ---- skeleton: big or tall parts are kept legal against the zones, the anchors and each other at every step [G1]
    big = [r for r in movable if obj[r].area() >= 5.0 or obj[r].need > 0.75 + 1e-9]
    bigset = set(big) if a.skeleton else set()
    wbig = {r: (4.0 if r in set(big) else 1.0) for r in movable}
    hard_idx = np.array([idx[q] for q in fside if q in bigset or q in anchors], dtype=int)

    def hard_ok(r):
        o = obj[r]
        if ZN.area(o) > 1e-9:
            return False
        c = o.crt(); g = GM[idx[r]][hard_idx]; Rh = R[hard_idx]
        w = np.minimum(Rh[:, 2], c[2]) - np.maximum(Rh[:, 0], c[0]) + g
        h = np.minimum(Rh[:, 3], c[3]) - np.maximum(Rh[:, 1], c[1]) + g
        hit = (w > 1e-6) & (h > 1e-6)
        hit[hard_idx == idx[r]] = False
        return not hit.any()

    def skeleton_start():
        """legal start of the big / tall parts: hinted blocks first (largest first), then the on-plate part, then the rest by area"""
        placed_big, failed = [], []
        for q in big:
            obj[q].x, obj[q].y = -50.0 - 10 * big.index(q), -50.0; sync(q)          # parked: not yet placed parts do not block
        home = {q: None for q in big}
        for r in sorted(big, key=lambda r: (0 if r in P.HINTS else 1 if r in P.ON_PLATE else 2, -obj[r].area(), r)):
            o = obj[r]; best = None
            for k in range(6000):
                o.x, o.y, o.r = random.uniform(0.5, G.BOARD_W - 0.5), random.uniform(0.5, G.BOARD_H - 0.5), random.choice((0, 90, 180, 270))
                sync(r)
                if hard_ok(r):
                    c_ = sum(pair_cost(t) for t in pairs_of[r] if (t[1] if t[0] == r else t[0]) in anchors or (t[1] if t[0] == r else t[0]) in placed_big)
                    c_ += sum(net_cost(n) for n in part_nets[r]) * 0.05
                    if r in P.HINTS:
                        cc = o.cl()
                        c_ += ((cc[2] - cc[0]) * (cc[3] - cc[1]) - sum(ov(cc, z) for z in P.HINTS[r])) * 200.0
                    c_ += ecg_cost(r)
                    if best is None or c_ < best[0]:
                        best = (c_, o.x, o.y, o.r)
            if best is None:
                failed.append(r)
                o.x, o.y = -50.0 - 10 * big.index(r), -50.0; sync(r)
            else:
                o.x, o.y, o.r = best[1], best[2], best[3]; sync(r)
                placed_big.append(r)
        return failed

    if a.skeleton and not a.init:
        for attempt in range(12):
            failed = skeleton_start()
            if not failed:
                break
            print("skeleton attempt %d: no legal start for %s - retry" % (attempt, failed), flush=True)
        if failed:                                     # give up: the parts start in the middle of the board and stay soft until they are legal
            for r in failed:
                obj[r].x, obj[r].y = G.BOARD_W / 2, G.BOARD_H / 2; sync(r)
            bigset.difference_update(failed)
        print("skeleton: %d big / tall parts, legal start for %d (attempts %d): %s" % (len(big), len(big) - len(failed), attempt + 1, " ".join(big)), flush=True)

    WB.update(wbig)
    T0, T1 = a.t0, 0.002
    cur = total()
    print("zones %s variant %s opts %s: start cost %.1f, movable %d, anchors %d, nets %d, pairs %d" % (
        G.ZTAG, G.VARIANT, G.OPTS, cur, len(movable), len(anchors), len(nets), len(P.PAIRS)), flush=True)
    t0 = time.time()
    N = a.iters
    for it in range(N):
        T = T0 * (T1 / T0) ** (it / max(N, 1))
        f = it / N
        WT['ov'] = (30.0 * (3000.0 / 30.0) ** min(1.0, f / 0.8)) if a.t0 >= 1.0 else 3000.0
        WT['zone'] = WT['ov']
        r = random.choice(movable)
        o = obj[r]
        old = (o.x, o.y, o.r)
        before = part_cost(r)
        mv = random.random()
        if mv < 0.15:
            o.r = random.choice((0, 90, 180, 270)); sync(r)
        elif mv < 0.25:
            cand = [q for q in movable if q != r and (obj[q].cl0 == o.cl0 or random.random() < 0.3)]
            if cand:
                q = random.choice(cand)
                oq = obj[q]
                bq = part_cost(q)
                oldq = (oq.x, oq.y, oq.r)
                o.x, o.y, oq.x, oq.y = oq.x, oq.y, o.x, o.y
                sync(r); sync(q)
                after = part_cost(r) + part_cost(q)
                d = after - (before + bq)
                if (r in bigset and not hard_ok(r)) or (q in bigset and not hard_ok(q)):
                    d = 1e18
                if d < 0 or (d < 1e17 and random.random() < math.exp(-d / T)):
                    cur += d
                else:
                    o.x, o.y, o.r = old; oq.x, oq.y, oq.r = oldq
                    sync(r); sync(q)
                continue
        elif mv < 0.27 and (f < 0.6 or (r in bigset and f < 0.85)):
            o.x, o.y = random.uniform(1, G.BOARD_W - 1), random.uniform(1, G.BOARD_H - 1); sync(r)
        else:
            s = max(0.05, 3.0 * T / 4.0 + 0.05)
            o.x += random.gauss(0, s); o.y += random.gauss(0, s)
            sync(r)
        if r in bigset and not hard_ok(r):
            o.x, o.y, o.r = old
            sync(r)
            continue
        after = part_cost(r)
        d = after - before
        if d < 0 or random.random() < math.exp(-d / T):
            cur += d
        else:
            o.x, o.y, o.r = old
            sync(r)
        if it % 100000 == 0:
            print("it %d T %.4f cost %.1f  (%.0f s)" % (it, T, cur, time.time() - t0), flush=True)
    for r in movable:
        obj[r].x = round(obj[r].x / 0.025) * 0.025
        obj[r].y = round(obj[r].y / 0.025) * 0.025
        sync(r)
    WT['ov'] = WT['zone'] = BIG
    final = total()
    out = {r: dict(x=round(obj[r].x, 4), y=round(obj[r].y, 4), rot=obj[r].r, side=obj[r].side, need=obj[r].need,
                   anchor=r in anchors) for r in obj}
    viol = {}
    for r in movable:
        z, o_ = ZN.area(obj[r]), ov_cost(r) / BIG
        if z > 1e-6 or o_ > 1e-6:
            viol[r] = dict(zone=round(z, 4), overlap=round(o_, 4))
    ecg = {}
    for s_ in sw:
        for it_ in ecg_items:
            if s_ == "J16" and (it_ if not isinstance(it_, tuple) else it_[0]) in P.E3_TIED:
                continue
            q = _ecg_pt(it_); d = math.hypot(obj[s_].x - q[0], obj[s_].y - q[1])
            if d < P.ECG_MIN:
                ecg[f"{s_}-{it_}"] = round(d, 2)
    dst = a.out or (G.WORK + f"/pl_{G.TAG}_s{a.seed}.json")
    json.dump(dict(parts=out, cost=final, violations=viol, ecg=ecg, seed=a.seed, iters=N, variant=G.VARIANT, zones=G.ZTAG,
                   opts=G.OPTS), open(dst, "w"), indent=1)
    print("final cost %.1f, violations %d %s, ecg %s -> %s" % (final, len(viol), list(viol)[:20], ecg, dst))


if __name__ == "__main__":
    main()
