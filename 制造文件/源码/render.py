"""quick shaded orthographic renders of GLB scenes (matplotlib), for checking."""
import sys, numpy as np, trimesh, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
def render(paths, out, views=(("back", 180), ("front", 0), ("side", 90)), zoom=None, size=6):
    meshes = []
    for p in paths:
        sc = trimesh.load(p, force="scene")
        for name, g in sc.geometry.items():
            T = sc.graph.get(name)[0] if name in sc.graph.nodes else np.eye(4)
            g = g.copy(); 
            try: g.apply_transform(sc.graph[name][0])
            except Exception: pass
            c = g.visual.face_colors[:, :3] / 255.0 if hasattr(g.visual, "face_colors") else np.full((len(g.faces), 3), 0.7)
            meshes.append((g.vertices, g.faces, c))
    fig, axs = plt.subplots(1, len(views), figsize=(size * len(views), size * 1.3))
    L = np.array([0.4, 0.5, 0.75]); L /= np.linalg.norm(L)
    for ax, (vn, yaw) in zip(np.atleast_1d(axs), views):
        a = np.radians(yaw); R = np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])
        polys, cols, depth = [], [], []
        for V, F, C in meshes:
            W = V @ R.T; tri = W[F]
            n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0]); nn = np.linalg.norm(n, axis=1) + 1e-12; n /= nn[:, None]
            vis = n[:, 2] > 0
            shade = 0.35 + 0.65 * np.clip(n @ L, 0, 1)
            polys.append(tri[vis][:, :, :2]); cols.append(np.clip(C[vis] * shade[vis, None], 0, 1)); depth.append(tri[vis][:, :, 2].mean(1))
        P = np.concatenate(polys); Cc = np.concatenate(cols); D = np.concatenate(depth); o = np.argsort(D)
        ax.add_collection(PolyCollection(P[o], facecolors=Cc[o], edgecolors="none"))
        allp = P.reshape(-1, 2)
        if zoom: ax.set_xlim(*zoom[0]); ax.set_ylim(*zoom[1])
        else: ax.set_xlim(allp[:, 0].min() - 0.02, allp[:, 0].max() + 0.02); ax.set_ylim(allp[:, 1].min() - 0.02, allp[:, 1].max() + 0.02)
        ax.set_aspect("equal"); ax.set_title(vn); ax.axis("off")
    plt.tight_layout(); plt.savefig(out, dpi=70)
if __name__ == "__main__":
    render(sys.argv[2:], sys.argv[1])
