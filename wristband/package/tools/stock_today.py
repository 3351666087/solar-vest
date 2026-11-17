"""Stock check of the JLC BOM lines today (public JLC parts API, no login; same endpoint and rule as v3/design/tools/jlc_query.py).
Reads OUT/assembly/BOM_JLC.csv and v3/design/BOM_v3f.csv (Qty_10_boards); writes OUT/assembly/stock_today.json and .md.
Rule (stock_report.md): flag when orderable = min(stockCount, canPresaleNumber) < 50 or < 5 x Qty_10_boards, or not SMT-placeable.
Raw answers are not saved. usage: python stock_today.py --out OUTDIR"""
import argparse, csv, datetime, json, os, time, urllib.request
URL = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList"
D = os.environ.get("V3_DESIGN", os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "design"))
ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
q10 = {r["LCSC"]: int(r["Qty_10_boards"]) for r in csv.DictReader(open(os.path.join(D, "BOM_v3f.csv")))}
rows = list(csv.DictReader(open(os.path.join(a.out, "assembly", "BOM_JLC.csv"))))
res, now = [], datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
for r in rows:
    c = r["LCSC Part #"]; rec = None; err = None
    for k in range(6):
        try:
            req = urllib.request.Request(URL, data=json.dumps({"keyword": c, "currentPage": 1, "pageSize": 10}).encode(),
                                         headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=40) as h:
                d = json.load(h)
            lst = ((d.get("data") or {}).get("componentPageInfo") or {}).get("list") or []
            rec = next((x for x in lst if x.get("componentCode") == c), None); err = None if rec else "not found"; break
        except Exception as e:
            err = f"{type(e).__name__}: {e}"; time.sleep(2 + 2 * k)
    o = dict(lcsc=c, refs=r["Designator"], comment=r["Comment"], qty10=q10.get(c), error=err)
    if rec:
        st, cp = rec.get("stockCount"), rec.get("canPresaleNumber")
        orderable = min(v for v in (st, cp) if v is not None) if (st is not None or cp is not None) else None
        lib = "Basic" if rec.get("componentLibraryType") == "base" else ("Preferred" if rec.get("preferredComponentFlag") else "Extended")
        low = orderable is None or orderable < 50 or (q10.get(c) and orderable < 5 * q10[c]) or bool(rec.get("assemblyComponentFlag"))
        o.update(stock=st, can_presale=cp, orderable=max(orderable, 0) if orderable is not None else None, library=lib,
                 not_smt=rec.get("assemblyComponentFlag"), low=bool(low))
    res.append(o); time.sleep(0.3)
ok = [x for x in res if not x["error"]]
out = dict(queried_utc=now, lines=len(res), answered=len(ok), errors=[x["lcsc"] + ": " + x["error"] for x in res if x["error"]],
           basic=sum(x.get("library") == "Basic" for x in ok), preferred=sum(x.get("library") == "Preferred" for x in ok),
           extended=sum(x.get("library") == "Extended" for x in ok), low=[x for x in ok if x["low"]], rows=res)
json.dump(out, open(os.path.join(a.out, "assembly", "stock_today.json"), "w"), indent=1)
L = [f"# JLC stock today ({now})", "", f"Lines {len(res)}, answered {len(ok)}, errors {len(out['errors'])}; Basic {out['basic']}, Preferred {out['preferred']}, Extended {out['extended']}.",
     "Rule: orderable = min(stock, canPresale) < 50 or < 5 x Qty for 10 boards, or not SMT-placeable.", "",
     "| LCSC | Refs | Part | Qty/10 boards | Stock | canPresale | Orderable |", "|---|---|---|---|---|---|---|"]
L += [f"| {x['lcsc']} | {x['refs']} | {x['comment']} | {x['qty10']} | {x['stock']} | {x['can_presale']} | {x['orderable']} |" for x in out["low"]] or ["| - | | | | | | |"]
open(os.path.join(a.out, "assembly", "stock_today.md"), "w").write("\n".join(L) + "\n")
print(json.dumps({k: out[k] for k in ("queried_utc", "lines", "answered", "basic", "preferred", "extended")} | {"low": [x["lcsc"] for x in out["low"]], "errors": len(out["errors"])}))
