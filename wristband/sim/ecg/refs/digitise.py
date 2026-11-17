"""Digitise the vendor curves used by SIM-06 from 400-dpi renders of the cached datasheets.

Method: the plot frame is found from the long dark rows/columns of the render, the axes are calibrated to the
frame (decade/linear ranges printed on the figure), and each curve is extracted by its legend colour
(column-wise median of matching pixels). Overlays (img/*_digitised.png) re-plot the extracted points on top of
the render so the result can be checked by eye. Output: curves.json (one entry per curve, with provenance).

Run with:  python3 refs/digitise.py      (from sim/ecg)
"""
import json, hashlib, pathlib
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.image as mpimg
import matplotlib.pyplot as plt

HERE = pathlib.Path(__file__).resolve().parent
DS = HERE.parents[2] / "cache" / "datasheets"


def sha(name):
    return hashlib.sha256((DS / f"{name}.pdf").read_bytes()).hexdigest()


def frame(im):
    dark = im.sum(axis=2) < 150
    cols = np.where(dark.mean(axis=0) > 0.55)[0]
    rows = np.where(dark.mean(axis=1) > 0.55)[0]

    # the frame is the outermost THICK (>= 3 px) line pair; thin page rules and grid lines are ignored
    def runs(idx):
        out, cur = [], [idx[0]]
        for v in idx[1:]:
            if v - cur[-1] == 1: cur.append(v)
            else: out.append(cur); cur = [v]
        out.append(cur)
        return [float(np.mean(r)) for r in out if len(r) >= 3]
    rc, rr = runs(cols), runs(rows)
    return rc[0], rc[-1], rr[0], rr[-1]


def extract(im, rgb, tol, box, exclude=(), split=None, min_px=3):
    """column-wise median row of pixels within tol of rgb; box = (x0,x1,y0,y1) pixel region searched.
    split: None, 'upper' or 'lower' to pick one of two same-colour curves in a column."""
    x0, x1, y0, y1 = box
    d = np.abs(im.astype(int) - np.array(rgb)[None, None, :]).max(axis=2) <= tol
    xs, ys = [], []
    for x in range(int(x0), int(x1)):
        if any(ex[0] <= x < ex[1] for ex in exclude if len(ex) == 2):
            continue
        r = np.where(d[int(y0):int(y1), x])[0] + int(y0)
        r = np.array([v for v in r if not any(len(ex) == 4 and ex[0] <= x < ex[1] and ex[2] <= v < ex[3] for ex in exclude)])
        if len(r) < min_px:
            continue
        if split:
            gaps = np.where(np.diff(r) > 6)[0]
            if len(gaps) == 0:
                continue          # cannot separate the two curves in this column
            g = gaps[0]
            r = r[:g + 1] if split == "upper" else r[g + 1:]
            if len(r) < min_px:
                continue
        xs.append(x); ys.append(float(np.median(r)))
    return np.array(xs), np.array(ys)


def run():
    out = {}
    specs = [
        # name, pdf, page, figure, conditions, x-range (log decades), y-range, y-scale, curves
        dict(img="tps7a02_f643", pdf="tps7a02", page=15, fig="Figure 6-43 PSRR vs Frequency and IOUT",
             cond="VIN = 2.8 V, VOUT = 1.8 V, COUT = 1 uF, TJ = 25 C typ", fx=(10, 1e7), fy=(0, 100), ylog=False,
             unit="dB", curves={"tps7a02_psrr_0mA": dict(rgb=(255, 0, 0), tol=60),
                                "tps7a02_psrr_1mA": dict(rgb=(255, 152, 0), tol=50)},
             exclude=[(118, 840, 615, 790)]),       # legend box
        dict(img="tps7a02_f648", pdf="tps7a02", page=15, fig="Figure 6-48 Output Noise vs Frequency and IOUT",
             cond="VOUT = 1.8 V, VIN = 2.8 V, COUT = 1 uF", fx=(10, 1e7), fy=(0.05, 50), ylog=True,
             unit="uV/rtHz", curves={"tps7a02_noise_100uA": dict(rgb=(255, 0, 0), tol=60),
                                     "tps7a02_noise_1mA": dict(rgb=(0, 0, 0), tol=40, gridfree=True)},
             exclude=[(425, 1170, 50, 220)]),
        dict(img="ads1291_f8", pdf="ads1291", page=13, fig="Figure 8 PSRR vs Frequency",
             cond="TA = 25 C, AVDD = 3 V, DVDD = 1.8 V, data rate 8 kSPS (curve), gain as labelled",
             fx=(10, 1e3), fy=(50, 120), ylog=False, unit="dB",
             curves={"ads1291_psrr_g3": dict(rgb=(255, 0, 255), tol=40),
                     "ads1291_psrr_g4": dict(rgb=(255, 0, 0), tol=40, split="lower"),
                     "ads1291_psrr_g6": dict(rgb=(110, 138, 61), tol=30),
                     "ads1291_psrr_g8": dict(rgb=(255, 0, 0), tol=40, split="upper")},
             exclude=[(186, 815, 572, 810), (600, 1200, 125, 215)]),
    ]
    for s in specs:
        im = (mpimg.imread(HERE / "img" / f"{s['img']}.png")[:, :, :3] * 255).astype(int)
        xl, xr, yt, yb = frame(im)
        lx0, lx1 = np.log10(s["fx"][0]), np.log10(s["fx"][1])
        fig, ax = plt.subplots(figsize=(im.shape[1] / 100, im.shape[0] / 100), dpi=100)
        ax.imshow(im.astype(np.uint8)); ax.set_axis_off()
        for cid, c in s["curves"].items():
            box = (xl + 4, xr - 3, yt + 4, yb - 3)
            if c.get("gridfree"):
                # black curve on a black grid: drop rows/columns that are grid lines, keep thick runs only
                dark = np.abs(im - np.array(c["rgb"])[None, None, :]).max(axis=2) <= c["tol"]
                gridrows = set(np.where(dark[:, int(xl):int(xr)].mean(axis=1) > 0.25)[0])
                gridcols = set(np.where(dark[int(yt):int(yb), :].mean(axis=0) > 0.25)[0])
                xs, ys = [], []
                for x in range(int(box[0]), int(box[1])):
                    if x in gridcols or any(len(ex) == 4 and ex[0] <= x < ex[1] for ex in s["exclude"]):
                        if not any(len(ex) == 4 and ex[0] <= x < ex[1] for ex in s["exclude"]):
                            continue
                    r = [y for y in np.where(dark[int(box[2]):int(box[3]), x])[0] + int(box[2])
                         if y not in gridrows and not any(len(ex) == 4 and ex[0] <= x < ex[1] and ex[2] <= y < ex[3] for ex in s["exclude"])]
                    if len(r) >= 3:
                        xs.append(x); ys.append(float(np.median(r)))
                xs, ys = np.array(xs), np.array(ys)
            else:
                xs, ys = extract(im, c["rgb"], c["tol"], box, exclude=s["exclude"], split=c.get("split"))
            f = 10 ** (lx0 + (xs - xl) / (xr - xl) * (lx1 - lx0))
            if s["ylog"]:
                ly0, ly1 = np.log10(s["fy"][0]), np.log10(s["fy"][1])
                y = 10 ** (ly1 - (ys - yt) / (yb - yt) * (ly1 - ly0))
            else:
                y = s["fy"][1] - (ys - yt) / (yb - yt) * (s["fy"][1] - s["fy"][0])
            # resample on a log grid (median in each bin) to drop pixel noise
            grid = np.logspace(lx0, lx1, 121)
            fb, yb_ = [], []
            for a, b in zip(grid[:-1], grid[1:]):
                k = (f >= a) & (f < b)
                if k.sum():
                    fb.append(float(np.sqrt(a * b))); yb_.append(float(np.median(y[k])))
            out[cid] = dict(pdf=f"cache/datasheets/{s['pdf']}.pdf", sha256=sha(s["pdf"]), page=s["page"],
                            figure=s["fig"], conditions=s["cond"], unit=s["unit"],
                            frame_px=[xl, xr, yt, yb], n_px=int(len(xs)), f_hz=fb, y=yb_)
            ax.plot(xs, ys, ".", ms=1.2, color="cyan" if c["rgb"] != (0, 0, 0) else "lime")
            print(f"{cid:24s} {len(xs):5d} px  {len(fb):3d} bins  f {fb[0]:.3g}..{fb[-1]:.3g} Hz  "
                  f"y {min(yb_):.3g}..{max(yb_):.3g} {s['unit']}")
        fig.savefig(HERE / "img" / f"{s['img']}_digitised.png", dpi=100); plt.close(fig)
    (HERE / "curves.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    run()
