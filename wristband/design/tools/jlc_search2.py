"""Keyword search on JLC's public parts API through curl (urllib drops connections behind this proxy). Paced 1.5 s.
Raw answers: cache/v2/jlc/search/<slug>.json.   usage: python jlc_search2.py [--pkg 0402] "kw1" "kw2" ...
Prints the hits with stock > 0, highest stock first: C-number, MPN, Basic/Extended, stock, package, description.
"""
import json, os, re, subprocess, sys, time, datetime
CACHE = "/path/to/SolarVest_work/wristband/cache/v2/jlc/search"
URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
def search(kw, n=30):
    os.makedirs(CACHE, exist_ok=True)
    slug = re.sub(r"[^A-Za-z0-9.+-]+", "_", kw)
    body = json.dumps({"keyword": kw, "currentPage": 1, "pageSize": n})
    raw = b""
    for a in range(4):
        r = subprocess.run(["curl", "-sS", "-m", "40", "-X", "POST", URL, "-H", "Content-Type: application/json", "-A", "Mozilla/5.0", "-d", body], capture_output=True)
        raw = r.stdout
        if r.returncode == 0 and raw[:1] == b"{": break
        time.sleep(4 * (a + 1))
    time.sleep(1.5)
    rec = {"keyword": kw, "fetched_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
    try: rec["response"] = json.loads(raw)
    except Exception: rec["response_text"] = raw[:2000].decode(errors="replace")
    json.dump(rec, open(os.path.join(CACHE, slug + ".json"), "w"), indent=1, ensure_ascii=False)
    try: return rec["response"]["data"]["componentPageInfo"]["list"] or []
    except Exception: return []
if __name__ == "__main__":
    args = sys.argv[1:]; pkg = None
    if args and args[0] == "--pkg": pkg = args[1]; args = args[2:]
    for kw in args:
        lst = [x for x in search(kw) if (x.get("stockCount") or 0) > 0 and (pkg is None or pkg in (x.get("componentSpecificationEn") or ""))]
        lst.sort(key=lambda x: -(x.get("stockCount") or 0))
        print(f"== {kw}: {len(lst)} stocked hits", flush=True)
        for x in lst[:7]:
            lib = "Basic" if x.get("componentLibraryType") == "base" else ("Preferred" if x.get("preferredComponentFlag") else "Extended")
            print(f"  {x['componentCode']:10s} {(x.get('componentModelEn') or '')[:30]:30s} {lib:9s} {x.get('stockCount'):>9} {(x.get('componentSpecificationEn') or '')[:16]:16s} {(x.get('describe') or '')[:80]}", flush=True)
