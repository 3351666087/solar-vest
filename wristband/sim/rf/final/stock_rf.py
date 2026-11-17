"""[rf final] JLC stock today for the RF match candidates (same public parts API and rule as v3/package/tools/stock_today.py; raw answers not saved).
usage: venv python stock_rf.py C1 C2 ... -> stock_rf.json"""
import sys, json, time, datetime, urllib.request
URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
out = dict(queried_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"), rows=[])
for c in sys.argv[1:]:
    o = dict(lcsc=c)
    try:
        req = urllib.request.Request(URL, data=json.dumps({"keyword": c, "currentPage": 1, "pageSize": 10}).encode(),
                                     headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
        d = json.load(urllib.request.urlopen(req, timeout=40))
        lst = ((d.get("data") or {}).get("componentPageInfo") or {}).get("list") or []
        r = next((x for x in lst if x.get("componentCode") == c), None)
        if r:
            o.update(mpn=r.get("componentModelEn"), stock=r.get("stockCount"), can_presale=r.get("canPresaleNumber"),
                     library="Basic" if r.get("componentLibraryType") == "base" else "Extended", not_smt=r.get("assemblyComponentFlag"))
        else: o["error"] = "not found"
    except Exception as e:
        o["error"] = f"{type(e).__name__}: {e}"
    out["rows"].append(o); print(o, flush=True); time.sleep(0.3)
json.dump(out, open("stock_rf.json", "w"), indent=1)
