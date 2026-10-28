import json, csv, math, os, sys, subprocess, urllib.request
HW = os.path.expandvars("$TMPDIR/hw/out")
U = 0.254  # EasyEDA unit = 10 mil

def bom(board):
    rows = list(csv.DictReader(open(f"{HW}/{board}/fab/{board}_BOM_JLC.csv")))
    m = {}
    for r in rows:
        for d in r["Designator"].split(","): m[d.strip()] = (r["LCSC Part #"], r["Footprint"], r["Comment"])
    return m

def easy(lcsc):
    fn = f"{lcsc}.json"
    if not os.path.exists(fn) or os.path.getsize(fn) < 1000:
        raise FileNotFoundError(lcsc)
    d = json.load(open(fn))["result"]
    ds = d["packageDetail"]["dataStr"]; hx, hy = float(ds["head"]["x"]), float(ds["head"]["y"])
    pads = {}
    for s in ds["shape"]:
        if s.startswith("PAD~"):
            f = s.split("~"); x, y, num = float(f[2]), float(f[3]), f[8]
            pads.setdefault(num, []).append(((x - hx) * U, (y - hy) * U))
    return d["packageDetail"]["title"], pads

def rot(p, deg):  # visual CCW rotation in y-down coordinates
    t = math.radians(deg); x, y = p
    return (x * math.cos(t) + y * math.sin(t), -x * math.sin(t) + y * math.cos(t))

kic = json.load(open(sys.argv[1]))  # ref -> {rot, pos, pads{num:[(x,y) fp-relative unrotated]}}
out = {}
for board in ("pmbh", "libb"):
    B = bom(board); cpl = {r["Designator"]: r for r in csv.DictReader(open(f"{HW}/{board}/fab/{board}_CPL_JLC.csv"))}
    for ref in sorted(cpl):
        if ref not in B or ref not in kic[board]: continue
        lcsc, fp, val = B[ref]
        try: title, ep = easy(lcsc)
        except FileNotFoundError: print(board, ref, val, lcsc, "-- footprint not fetched"); continue
        kp = kic[board][ref]["pads"]
        common = [n for n in kp if n in ep and n not in ("", "MP")]
        if len(common) < 2: print(board, ref, "few common pads", list(kp), list(ep)); continue
        res = []
        for th in (0, 90, 180, 270):
            # best translation = mean difference over first pad instance of each number
            pe = {n: rot(ep[n][0], th) for n in common}; pk = {n: kp[n][0] for n in common}
            dx = sum(pk[n][0] - pe[n][0] for n in common) / len(common); dy = sum(pk[n][1] - pe[n][1] for n in common) / len(common)
            err = math.sqrt(sum((pe[n][0] + dx - pk[n][0]) ** 2 + (pe[n][1] + dy - pk[n][1]) ** 2 for n in common) / len(common))
            res.append((err, th, dx, dy))
        res.sort(); err, th, dx, dy = res[0]
        amb = len(res) > 1 and res[1][0] < 0.05
        kr = kic[board][ref]["rot"]; cur = float(cpl[ref]["Rotation"]); need = (kr + th) % 360
        flag = "OK " if abs((cur - need) % 360) < 1 or (amb and abs((cur - need) % 180) < 1) else "BAD"
        print(f"{board:4} {ref:4} {val[:14]:14} {lcsc:9} {fp[:28]:28} kicad={kr:5.0f} cpl={cur:5.0f} need={need:5.0f} {'(0/180 symmetric)' if amb else ''} off=({dx:+.2f},{dy:+.2f})mm err={err:.2f} {flag}")
        out[f"{board}:{ref}"] = dict(need=need, cur=cur, amb=amb, off=(dx, dy), err=err, title=title)
json.dump(out, open("match.json", "w"), indent=1)
