"""Placement-review pictures (top, bottom) and the per-part checklist for every rotation-sensitive part
(the rows of v3/design/placement_proof.json that are JLC-placed in v3f).

usage: python review_pics.py --board B --gate GATEDIR --out REVIEWDIR
"""
import argparse, csv, json, math, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Polygon as MPoly  # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pk  # noqa: E402
from cplgate import pad_poly, centroids  # noqa: E402
from render_gate import to_board  # noqa: E402

COL = {"GREEN": "#1e8449", "PREVIEW": "#2e86c1", "YELLOW": "#d4ac0d", "RED": "#c0392b", "UNKNOWN": "#7d3c98"}


def compass(dx, dy):
    if math.hypot(dx, dy) < 0.05:
        return "centre"
    a = math.degrees(math.atan2(dy, dx)) % 360
    return ["right (+X)", "upper right", "top (+Y)", "upper left", "left (-X)", "lower left", "bottom (-Y)", "lower right"][int(((a + 22.5) % 360) // 45)]


def ref_pad(P, kp):
    pol = P.get("polarity") or ""
    if pol.startswith("reference terminal"):
        return pol.split("pad ")[1].split(" ")[0], pol.split("terminal ")[1].split(" ")[0]
    for n in ("1", "A1"):
        if any(p["num"] == n for p in kp):
            return n, "pin 1"
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--board", required=True); ap.add_argument("--gate", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args(); os.makedirs(a.out, exist_ok=True)
    B = pk.load_board(a.board); F = B["footprints"]; ox, oy = B["aux_origin"]
    prov = json.load(open(os.path.join(a.gate, "cpl_provenance.json")))
    parts = {p["ref"]: p for p in prov["parts"]}
    proof = json.load(open(os.path.join(pk.DESIGN, "placement_proof.json")))["parts"]
    sens = [r for r in proof if r["ref"] in parts]
    sref = {r["ref"] for r in sens}
    C = lambda x, y: (x - ox, -(y - oy))
    rows = []
    for side in ("top", "bottom"):
        fig, ax = plt.subplots(figsize=(17, 13.5), dpi=150)
        for kind, pts in B["edges"]:
            d = {k: (x, y) for k, x, y in pts}
            if kind == "gr_line":
                (x1, y1), (x2, y2) = C(*d["start"]), C(*d["end"]); ax.plot([x1, x2], [y1, y2], color="k", lw=1)
            elif kind == "gr_circle":
                c = C(*d["center"]); r = math.dist(d["center"], d["end"])
                ax.add_patch(plt.Circle(c, r, fill=False, color="k", lw=1, ls="--"))
        for ref, fp in F.items():
            if fp["side"] != side:
                continue
            P = parts.get(ref); hot = ref in sref
            kp = [p for p in pk.board_to_local(fp) if p["num"]]
            for p in kp:
                g = to_board(pad_poly(p), fp)
                if g.is_empty or not hasattr(g, "exterior"):
                    continue
                xy = [C(x, y) for x, y in g.exterior.coords]
                fc = COL[P["verdict"]] if (hot and P) else ("#bbbbbb" if P else "#e5e5e5")
                ax.add_patch(MPoly(xy, closed=True, fc=fc, ec="#555", lw=0.3, alpha=0.85 if hot else 0.6))
            if not (hot and P):
                continue
            n, what = ref_pad(P, kp)
            cen = centroids(kp); allc = [pk.local_to_board(fp, v) for v in cen.values()]
            mx = sum(v[0] for v in allc) / len(allc); my = sum(v[1] for v in allc) / len(allc)
            direction = "-"
            if n:
                bx, by = pk.local_to_board(fp, cen[n]); cx, cy = C(bx, by)
                ax.plot(cx, cy, "o", color="k", ms=4)
                direction = compass(bx - mx, -(by - my))
            if "cpl" in P:
                X, Y, R = P["cpl"]["x"], P["cpl"]["y"], math.radians(P["cpl"]["rot"])
                sg = 1 if side == "top" else -1
                ax.annotate("", xy=(X + sg * 0.9 * math.cos(R), Y + 0.9 * math.sin(R)), xytext=(X, Y),
                            arrowprops=dict(arrowstyle="->", color="#0e6655", lw=1.2))
            mxc, myc = C(mx, my)
            ax.text(mxc + 0.25, myc + 0.35, f"{ref} {P.get('cpl', {}).get('rot', '?')}°", fontsize=6.5, color="#111",
                    bbox=dict(boxstyle="round,pad=0.1", fc="white", ec=COL[P["verdict"]], lw=0.6, alpha=0.85))
            pr = next(r for r in sens if r["ref"] == ref)
            rows.append(dict(ref=ref, part=P.get("value", ""), lcsc=P["lcsc"], side=side, proof_class=pr["proof_class"], gate=P["verdict"],
                             cpl_rot=P.get("cpl", {}).get("rot", "-"), mark=f"{what or '-'} (pad {n}) at the {direction} of the part (board view)" if n else "-",
                             evidence=pr["deciding_evidence"], test=pr["g10_item"]))
        ax.set_aspect("equal"); ax.autoscale_view(); ax.grid(alpha=0.2)
        ax.set_title(f"SolarBand V3-F main board, {side} side as seen from the {'top' if side == 'top' else 'top (looking through the board)'}; "
                     "coloured = rotation-sensitive part by gate verdict (green / blue = preview / yellow / red / purple = unknown); "
                     "black dot = pin 1, cathode or +; arrow = CPL rotation (EasyEDA +X axis)", fontsize=8)
        ax.set_xlabel("X mm (place origin)"); ax.set_ylabel("Y mm")
        fig.tight_layout(); fig.savefig(os.path.join(a.out, f"placement_{side}.png")); plt.close(fig)
    rows.sort(key=lambda r: ({"RED": 0, "UNKNOWN": 1, "YELLOW": 2, "PREVIEW": 3, "GREEN": 4}[r["gate"]], r["ref"]))
    with open(os.path.join(a.out, "checklist.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, list(rows[0]) + ["checked_in_preview", "checked_in_2D_file"]); w.writeheader()
        for r in rows:
            w.writerow(dict(r, checked_in_preview="", checked_in_2D_file=""))
    L = ["# Order-time checklist: rotation-sensitive parts", "",
         "One row per rotation-sensitive JLC-placed part (`v3/design/placement_proof.json`). Before any payment: compare each row in JLC's "
         "placement preview AND in the 2D production file (原始贴片图) after engineer review; tick both boxes; any JLC change or any "
         "space-bar press = STOP (spec §6.5). Bottom-side rows: JLC shows the bottom mirrored; the direction here is the top view ⚠.", "",
         f"Rows: {len(rows)}. Gate verdicts: " + ", ".join(f"{k} {sum(1 for r in rows if r['gate'] == k)}" for k in COL) + ".", "",
         "| ☐ | Ref | Part (LCSC) | Side | Class | Gate | CPL rot | Check in the JLC preview | Electrical test (G10 / EOL) |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| ☐ | {r['ref']} | {r['part']} ({r['lcsc']}) | {r['side']} | {r['proof_class']} | {r['gate']} | {r['cpl_rot']} | "
                 f"{r['mark']}; {r['evidence']} | {r['test']} |".replace("\n", " "))
    open(os.path.join(a.out, "checklist.md"), "w").write("\n".join(L) + "\n")
    print(json.dumps(dict(rows=len(rows), pictures=["placement_top.png", "placement_bottom.png"])))


if __name__ == "__main__":
    main()
