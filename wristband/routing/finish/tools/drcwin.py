"""[finish] keep only the dangling-copper violations inside the rip windows (so the dangling strip stays local).
usage: drcwin.py DRC.json "x0,y0,x1,y1;..." OUT.json   -> prints the count kept"""
import json, sys
d = json.load(open(sys.argv[1])); W = [tuple(map(float, w.split(","))) for w in sys.argv[2].split(";")]
inw = lambda p: any(w[0] - 0.3 <= p["x"] <= w[2] + 0.3 and w[1] - 0.3 <= p["y"] <= w[3] + 0.3 for w in W)
d["violations"] = [v for v in d["violations"] if v["type"] in ("track_dangling", "via_dangling") and all(inw(i["pos"]) for i in v["items"])]
d["unconnected_items"] = []
json.dump(d, open(sys.argv[3], "w")); print(len(d["violations"]))
