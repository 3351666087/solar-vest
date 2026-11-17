"""FIX lane: download a datasheet into its own folder cache/v2/ds_fix/<name>/<name>.pdf through curl (paced 3 s). LCSC viewer / redirect
pages are resolved to datasheet.lcsc.com/datasheet/pdf/<hash>.pdf?productCode=<C>. url, sha256, size and time go to cache/v2/ds_fix/index.json.
usage: python fetch_ds_fix.py name=url [name=url ...]"""
import hashlib, json, os, re, subprocess, sys, time, datetime
D = "/path/to/SolarVest_work/wristband/cache/v2/ds_fix"
IDX = os.path.join(D, "index.json")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
RX = re.compile(rb"https://datasheet\.lcsc\.com/datasheet/pdf/[0-9a-f]+\.pdf\?productCode=C\d+")
RXP = re.compile(rb"https://www\.lcsc\.com/product-detail/C\d+\.html")
os.makedirs(D, exist_ok=True)
idx = json.load(open(IDX)) if os.path.exists(IDX) else {}
def get(u, out):
    r = subprocess.run(["curl", "-sS", "-L", "-m", "90", "--retry", "2", "-A", UA, "-H", "Accept: application/pdf,*/*", "-o", out, u], capture_output=True)
    time.sleep(3)
    return r.returncode == 0 and os.path.exists(out) and open(out, "rb").read(5) == b"%PDF-"
for a in sys.argv[1:]:
    n, u = a.split("=", 1); d = os.path.join(D, n); os.makedirs(d, exist_ok=True); p = os.path.join(d, n + ".pdf")
    if os.path.exists(p) and open(p, "rb").read(5) == b"%PDF-": print(n, "cached"); continue
    part = p + ".part"; ok = get(u, part); hops = 0
    while not ok and os.path.exists(part) and hops < 3:
        raw = open(part, "rb").read(); m = RX.search(raw) or RXP.search(raw)
        if not m: break
        u = m.group(0).decode(); ok = get(u, part); hops += 1
    if not ok:
        if os.path.exists(part): os.replace(part, os.path.join(d, n + ".fail.html"))
        print(n, "FAIL"); continue
    os.replace(part, p); raw = open(p, "rb").read()
    idx[n] = dict(url=u, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw), fetched_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
    json.dump(idx, open(IDX, "w"), indent=1); print(n, "ok", len(raw), u)
