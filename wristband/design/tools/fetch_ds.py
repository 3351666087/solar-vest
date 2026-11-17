"""Download datasheets into cache/datasheets/<name>.pdf, record url + sha256 in cache/datasheets/index.json."""
import json, os, sys, hashlib, time, urllib.request, datetime
D = "/path/to/SolarVest_work/wristband/cache/datasheets"
IDX = os.path.join(D, "index.json")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
def get(name, url):
    os.makedirs(D, exist_ok=True)
    idx = json.load(open(IDX)) if os.path.exists(IDX) else {}
    p = os.path.join(D, name + ".pdf")
    if os.path.exists(p) and open(p, "rb").read(5) == b"%PDF-":
        return p
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/pdf,*/*"})
    try:
        raw = urllib.request.urlopen(req, timeout=60).read()
    except Exception as e:
        print(name, "FAIL", e); return None
    if raw[:5] != b"%PDF-":
        import re
        m = re.search(rb"https://datasheet\.lcsc\.com/datasheet/pdf/[0-9a-f]+\.pdf\?productCode=C\d+", raw)
        if m:
            url = m.group(0).decode(); time.sleep(1)
            try:
                raw = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60).read()
            except Exception as e:
                print(name, "FAIL2", e); return None
        if raw[:5] != b"%PDF-":
            print(name, "NOT PDF", raw[:120]); return None
    open(p, "wb").write(raw)
    idx[name] = dict(url=url, sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw),
                     fetched_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"))
    json.dump(idx, open(IDX, "w"), indent=1)
    print(name, "ok", len(raw)); return p
if __name__ == "__main__":
    for a in sys.argv[1:]:
        n, u = a.split("=", 1); get(n, u); time.sleep(1)
