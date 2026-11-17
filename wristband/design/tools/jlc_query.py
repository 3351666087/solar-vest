"""Query JLC's public parts API for each LCSC C-number (paced >= 1.5 s) - V3-F lane version.

usage: python jlc_query.py [--refresh] C123 C456 ...
Raw API answers are downloaded data and are kept OUTSIDE the project (session scratchpad, RAW below). The project keeps only the
fields that are used, per C-number, in data/jlc/<C>.json, in the same shape common.jlc_record() and make_outputs.py read
(response.data.componentPageInfo.list = [the exact-match record, reduced to the used fields]) plus fetched_utc and the sha256 of
the raw answer. orderable = min(stockCount, canPresaleNumber) (canPresaleNumber read as the quantity not yet committed, v2 FIX R-05).
"""
import json, os, sys, time, hashlib, datetime, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
DESIGN = os.path.dirname(HERE)
OUT = os.path.join(DESIGN, "data", "jlc")
RAW = os.environ.get("SB_RAW", "/tmp/solarband_raw")
URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
KEEP = ("componentCode", "componentLibraryType", "preferredComponentFlag", "stockCount", "canPresaleNumber", "preMinPurchaseNum",
        "componentModelEn", "componentBrandEn", "componentSpecificationEn", "componentPrices", "describe", "dataManualUrl",
        "assemblyComponentFlag", "componentTypeEn", "lcscGoodsUrl", "leastPatchNumber")
_last = [0.0]

def fetch(c, refresh=False):
    os.makedirs(OUT, exist_ok=True); os.makedirs(RAW, exist_ok=True)
    p = os.path.join(OUT, f"{c}.json")
    if os.path.exists(p) and not refresh:
        rec = json.load(open(p))
        if rec.get("http") == 200: return rec
    dt = time.time() - _last[0]
    if dt < 1.5: time.sleep(1.5 - dt)
    body = json.dumps({"keyword": c, "currentPage": 1, "pageSize": 10})
    t0 = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
    raw, status = b"", -1
    for attempt in range(4):
        r = subprocess.run(["curl", "-sS", "-m", "40", "-X", "POST", URL, "-H", "Content-Type: application/json",
                            "-A", "Mozilla/5.0", "-d", body], capture_output=True)
        raw = r.stdout or r.stderr
        if r.returncode == 0 and raw[:1] == b"{": status = 200; break
        time.sleep(5 * (attempt + 1))
    _last[0] = time.time()
    open(os.path.join(RAW, f"{c}.{t0.replace(':', '')}.json"), "wb").write(raw)
    rec = {"lcsc": c, "fetched_utc": t0, "http": status, "raw_sha256": hashlib.sha256(raw).hexdigest(), "source": URL + " (POST keyword=C-number)"}
    try:
        d = json.loads(raw)
        lst = d["data"]["componentPageInfo"]["list"]
        hit = [{k: x.get(k) for k in KEEP} for x in lst if x.get("componentCode") == c]
        rec["response"] = {"data": {"componentPageInfo": {"list": hit, "total_answer": len(lst)}}}
    except Exception as e:
        rec["http"] = -2; rec["error"] = f"{e!r}: {raw[:300]!r}"
    json.dump(rec, open(p, "w"), indent=1, ensure_ascii=False)
    return rec

def summary(rec):
    c = rec["lcsc"]
    try:
        lst = rec["response"]["data"]["componentPageInfo"]["list"]
    except Exception:
        return dict(lcsc=c, found=False, why=rec.get("error", "bad response"))
    if not lst: return dict(lcsc=c, found=False, why="no exact match")
    x = lst[0]; prices = x.get("componentPrices") or []
    def price_at(n):
        for pr in prices:
            if pr["startNumber"] <= n and (pr["endNumber"] in (-1, None) or n <= pr["endNumber"]): return pr["productPrice"]
        return prices[-1]["productPrice"] if prices else None
    st, cp = x.get("stockCount"), x.get("canPresaleNumber")
    return dict(lcsc=c, found=True, mpn=x.get("componentModelEn"), mfr=x.get("componentBrandEn"), pkg=x.get("componentSpecificationEn"),
                lib="Basic" if x.get("componentLibraryType") == "base" else ("Preferred" if x.get("preferredComponentFlag") else "Extended"),
                stock=st, can_presale=cp, orderable=None if st is None else max(min(st, cp if cp is not None else st), 0),
                hand_assembly_flag=x.get("assemblyComponentFlag"), p1=price_at(1), p100=price_at(100), desc=x.get("describe"),
                datasheet=x.get("dataManualUrl"), fetched=rec["fetched_utc"])

if __name__ == "__main__":
    refresh = "--refresh" in sys.argv
    for c in [a for a in sys.argv[1:] if a.startswith("C")]:
        print(json.dumps(summary(fetch(c, refresh)), ensure_ascii=False), flush=True)
