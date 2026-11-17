"""Tiny numpy z-buffer renderer (orthographic, flat Lambert shading, part-ID outlines, simple transparency).
No OpenGL needed. Used by enclosure_v0.py for the concept renders."""
import numpy as np


def _basis(elev, azim):
    el, az = np.radians(elev), np.radians(azim)
    d = np.array([np.cos(el) * np.cos(az), np.cos(el) * np.sin(az), np.sin(el)])   # towards the camera
    up = np.array([0.0, 0.0, 1.0]) if abs(np.sin(el)) < 0.999 else np.array([0.0, 1.0, 0.0])
    r = np.cross(up, d); r /= np.linalg.norm(r)
    u = np.cross(d, r)
    return r, u, d


def render(parts, fn, elev=30, azim=-60, size=(1400, 1000), title=None, light=(0.35, -0.45, 0.82), bg=(1, 1, 1),
           margin=0.06, outline=True, labels=None):
    """parts: list of (name, vertices[N,3], faces[M,3], rgba)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    r, u, d = _basis(elev, azim)
    L = np.array(light, float); L /= np.linalg.norm(L)
    allp = np.concatenate([p[1] for p in parts])
    su, sv = allp @ r, allp @ u
    W, H = size
    span = max(su.max() - su.min(), (sv.max() - sv.min()) * W / H) * (1 + 2 * margin)
    s = W / span
    cu, cv = (su.max() + su.min()) / 2, (sv.max() + sv.min()) / 2
    zbuf = np.full((H, W), -np.inf); img = np.ones((H, W, 3)) * np.array(bg); pid = np.full((H, W), -1, int)
    trans = []
    for k, (name, V, F, rgba) in enumerate(parts):
        if rgba[3] < 0.99:
            trans.append((k, name, V, F, rgba)); continue
        _raster(V, F, rgba, r, u, d, L, s, cu, cv, W, H, zbuf, img, pid, k)
    # transparent parts: front-most layer of each, blended over the opaque image
    for (k, name, V, F, rgba) in trans:
        zb = np.full((H, W), -np.inf); im2 = np.zeros((H, W, 3)); p2 = np.full((H, W), -1, int)
        _raster(V, F, rgba, r, u, d, L, s, cu, cv, W, H, zb, im2, p2, k, cull=False)
        m = (zb > zbuf)
        a = rgba[3]
        img[m] = (1 - a) * img[m] + a * im2[m]
    if outline:
        e = np.zeros((H, W), bool)
        e[:, 1:] |= pid[:, 1:] != pid[:, :-1]; e[1:, :] |= pid[1:, :] != pid[:-1, :]
        dz = np.zeros((H, W))
        zf = np.where(np.isfinite(zbuf), zbuf, -1e3)
        dz[:, 1:] = np.maximum(dz[:, 1:], np.abs(zf[:, 1:] - zf[:, :-1])); dz[1:, :] = np.maximum(dz[1:, :], np.abs(zf[1:, :] - zf[:-1, :]))
        e |= dz > 0.6
        img[e] = img[e] * 0.35
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100)
    ax = fig.add_axes([0, 0, 1, 1]); ax.imshow(img, origin="upper"); ax.axis("off")
    if title:
        ax.text(0.01, 0.985, title, transform=ax.transAxes, fontsize=13, va="top")
    # axis triad
    ox, oy = 70, H - 70
    for vec, lab, col in (((1, 0, 0), "X", "r"), ((0, 1, 0), "Y", "g"), ((0, 0, 1), "Z", "b")):
        v = np.array(vec, float)
        ax.annotate("", xy=(ox + 45 * (v @ r), oy - 45 * (v @ u)), xytext=(ox, oy), arrowprops=dict(arrowstyle="->", color=col, lw=2))
        ax.text(ox + 55 * (v @ r), oy - 55 * (v @ u), lab, color=col, fontsize=11, ha="center", va="center")
    if labels:
        for (txt, p3) in labels:
            p3 = np.array(p3, float)
            x = (p3 @ r - cu) * s + W / 2; y = H / 2 - (p3 @ u - cv) * s
            ax.annotate(txt, xy=(x, y), xytext=(x + 40, y - 40), fontsize=9, arrowprops=dict(arrowstyle="-", lw=0.8),
                        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="0.5", alpha=0.85))
    fig.savefig(fn, dpi=100); plt.close(fig)
    return fn


def _raster(V, F, rgba, r, u, d, L, s, cu, cv, W, H, zbuf, img, pid, k, cull=True):
    P = V[F]                                     # (M,3,3)
    n = np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0])
    nn = np.linalg.norm(n, axis=1); ok = nn > 1e-12
    n[ok] /= nn[ok, None]
    facing = n @ d
    keep = ok & ((facing > 0) if cull else True)
    P, n, facing = P[keep], n[keep], facing[keep]
    shade = 0.35 + 0.65 * np.clip(np.abs(n @ L), 0, 1)
    X = (P @ r - cu) * s + W / 2
    Y = H / 2 - (P @ u - cv) * s
    Zd = P @ d
    col = np.array(rgba[:3])
    x0 = np.clip(np.floor(X.min(1)).astype(int), 0, W - 1); x1 = np.clip(np.ceil(X.max(1)).astype(int), 0, W - 1)
    y0 = np.clip(np.floor(Y.min(1)).astype(int), 0, H - 1); y1 = np.clip(np.ceil(Y.max(1)).astype(int), 0, H - 1)
    for t in range(len(P)):
        if x1[t] < x0[t] or y1[t] < y0[t]:
            continue
        xs = np.arange(x0[t], x1[t] + 1) + 0.5; ys = np.arange(y0[t], y1[t] + 1) + 0.5
        gx, gy = np.meshgrid(xs, ys)
        (ax_, bx, cx), (ay, by, cy) = X[t], Y[t]
        den = (by - cy) * (ax_ - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        w0 = ((by - cy) * (gx - cx) + (cx - bx) * (gy - cy)) / den
        w1 = ((cy - ay) * (gx - cx) + (ax_ - cx) * (gy - cy)) / den
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        if not inside.any():
            continue
        z = w0 * Zd[t, 0] + w1 * Zd[t, 1] + w2 * Zd[t, 2]
        sl = (slice(y0[t], y1[t] + 1), slice(x0[t], x1[t] + 1))
        zb = zbuf[sl]
        m = inside & (z > zb)
        if m.any():
            zb[m] = z[m]
            img[sl][m] = col * shade[t]
            pid[sl][m] = k
