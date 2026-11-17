"""Keyword search on JLC's public parts API (alternates / missing values). Paced >= 1.2 s, raw answers cached in
cache/jlc/search/<slug>.json.   usage: python jlc_search.py "keyword 1" "keyword 2" ...
Prints: C-number, MPN, Basic/Extended, stock, package, description (first 10 hits with stock > 0 first).
"""
import json, os, re, sys, time, hashlib, datetime, urllib.request
CACHE = "/path/to/SolarVest_work/wristband/cache/v2/jlc/search"
URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
def search(kw, n=25):
    os.makedirs(CACHE, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9.+-]+", "_", kw)
    body = json.dumps({"keyword": kw, "currentPage": 1, "pageSize": n}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    t0 = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    raw = b""
    for a in range(4):
        try: raw = urllib.request.urlopen(req, timeout=40).read(); break
        except Exception as e: raw = str(e).encode(); time.sleep(4 * (a + 1))
    time.sleep(1.2)
    rec = {"keyword": kw, "fetched_utc": t0, "sha256": hashlib.sha256(raw).hexdigest()}
    try: rec["response"] = json.loads(raw)
    except Exception: rec["response_text"] = raw[:2000].decode(errors="replace")
    json.dump(rec, open(os.path.join(CACHE, slug + ".json"), "w"), indent=1, ensure_ascii=False)
    try: lst = rec["response"]["data"]["componentPageInfo"]["list"] or []
    except Exception: lst = []
    return lst
if __name__ == "__main__":
    for kw in sys.argv[1:]:
        lst = search(kw)
        lst.sort(key=lambda x: -(x.get("stockCount") or 0))
        print(f"== {kw}: {len(lst)} hits")
        for x in lst[:12]:
            lib = "Basic" if x.get("componentLibraryType") == "base" else ("Preferred" if x.get("preferredComponentFlag") else "Extended")
            print(f"  {x['componentCode']:10s} {x.get('componentModelEn','')[:28]:28s} {lib:9s} {x.get('stockCount'):>9} {x.get('componentSpecificationEn','')[:14]:14s} {(x.get('describe') or '')[:70]}")
