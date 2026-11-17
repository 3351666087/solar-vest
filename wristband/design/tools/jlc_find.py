"""Keyword search on JLC's public parts API through curl (urllib drops connections behind this proxy). Paced >= 2 s, raw answers cached in
the session scratchpad (V3-F lane: downloads stay outside the project).   usage: python jlc_find.py [-n 30] "keyword 1" "keyword 2" ...
Prints: C-number, MPN, library class, stockCount, canPresaleNumber, assembly flag, package, description."""
import json, os, re, sys, time, hashlib, datetime, subprocess
CACHE = os.environ.get("SB_RAW_SEARCH", "/tmp/solarband_raw")   # V3-F lane: raw answers outside the project
URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
def search(kw, n=30):
    os.makedirs(CACHE, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9.+-]+", "_", kw)
    body = json.dumps({"keyword": kw, "currentPage": 1, "pageSize": n})
    t0 = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    raw = b""
    for a in range(3):
        r = subprocess.run(["curl", "-sS", "-m", "40", "-X", "POST", URL, "-H", "Content-Type: application/json", "-A", "Mozilla/5.0", "-d", body], capture_output=True)
        raw = r.stdout or r.stderr
        if r.returncode == 0 and raw[:1] == b"{": break
        time.sleep(5 * (a + 1))
    time.sleep(2.0)
    rec = {"keyword": kw, "fetched_utc": t0, "sha256": hashlib.sha256(raw).hexdigest()}
    try: rec["response"] = json.loads(raw)
    except Exception: rec["response_text"] = raw[:2000].decode(errors="replace")
    json.dump(rec, open(os.path.join(CACHE, slug + ".json"), "w"), indent=1, ensure_ascii=False)
    try: return rec["response"]["data"]["componentPageInfo"]["list"] or []
    except Exception: return []
if __name__ == "__main__":
    a = sys.argv[1:]; n = 30
    if a and a[0] == "-n": n = int(a[1]); a = a[2:]
    for kw in a:
        lst = search(kw, n); lst.sort(key=lambda x: -(x.get("stockCount") or 0))
        print(f"== {kw}: {len(lst)} hits")
        for x in lst[:n]:
            lib = "Basic" if x.get("componentLibraryType") == "base" else ("Preferred" if x.get("preferredComponentFlag") else "Extended")
            print(f"  {x['componentCode']:10s} {(x.get('componentModelEn') or '')[:30]:30s} {lib:9s} stock {x.get('stockCount'):>9} presale {str(x.get('canPresaleNumber')):>9} asm {str(x.get('assemblyComponentFlag'))[:1]} {(x.get('componentSpecificationEn') or '')[:16]:16s} {(x.get('describe') or '')[:80]}")
