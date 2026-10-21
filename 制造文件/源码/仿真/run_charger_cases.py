import sys, json, multiprocessing as mp
sys.path.insert(0, ".")
def work(c):
    import tb_charger as T
    G, T_, vb = c
    try: return T.run(G, T_, vb, tstop=1.5e-3)
    except Exception as e: return dict(G=G, T=T_, vbat=vb, error=str(e))
if __name__ == "__main__":
    cases = [(1000, 25, 3.7), (1000, 0, 3.7), (400, 37, 3.7), (120, 29, 3.7), (1000, 55, 3.0), (1000, 55, 4.15), (30, 26, 3.7)]
    with mp.get_context("spawn").Pool(7) as p: res = p.map(work, cases)
    json.dump(res, open("tb_charger_cases.json", "w"), indent=1)
    for r in res: print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
