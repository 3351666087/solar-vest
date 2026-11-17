"""Download datasheets into cache/v2/ds/<name>.pdf through curl (paced 2 s); url, sha256, size and time are recorded in
cache/v2/ds/index.json. A non-PDF answer is kept as <name>.fail.html and reported.
usage: python fetch_ds2.py name=url [name=url ...]      (re-run safe: an existing PDF is not fetched again)
"""
import hashlib, json, os, re, subprocess, sys, time, datetime
D = "/path/to/SolarVest_work/wristband/cache/v2/ds"
IDX = os.path.join(D, "index.json")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
os.makedirs(D, exist_ok=True)
idx = json.load(open(IDX)) if os.path.exists(IDX) else {}
for a in sys.argv[1:]:
    n, u = a.split("=", 1); p = os.path.join(D, n + ".pdf")
    if os.path.exists(p) and open(p, "rb").read(5) == b"%PDF-":
        print(n, "cached"); continue
    r = subprocess.run(["curl", "-sS", "-L", "-m", "90", "--retry", "2", "-A", UA, "-H", "Accept: application/pdf,*/*", "-o", p + ".part", u], capture_output=True)
    time.sleep(2)
    ok = r.returncode == 0 and os.path.exists(p + ".part") and open(p + ".part", "rb").read(5) == b"%PDF-"
    if not ok and os.path.exists(p + ".part"):
        # LCSC answers with an HTML page that points to datasheet.lcsc.com/datasheet/pdf/<hash>.pdf?productCode=<C>
        m = re.search(rb"https://datasheet\.lcsc\.com/datasheet/pdf/[0-9a-f]+\.pdf\?productCode=C\d+", open(p + ".part", "rb").read())
        if m:
            u = m.group(0).decode()
            r = subprocess.run(["curl", "-sS", "-L", "-m", "90", "--retry", "2", "-A", UA, "-o", p + ".part", u], capture_output=True)
            time.sleep(2)
            ok = r.returncode == 0 and open(p + ".part", "rb").read(5) == b"%PDF-"
    if not ok:
        if os.path.exists(p + ".part"): os.replace(p + ".part", os.path.join(D, n + ".fail.html"))
        print(n, "FAIL", r.stderr.decode()[:120]); continue
    os.replace(p + ".part", p); raw = open(p, "rb").read()
    idx[n] = dict(url=u, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                  fetched_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
    json.dump(idx, open(IDX, "w"), indent=1)
    print(n, "ok", len(raw))
