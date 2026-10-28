"""(1) interference of the real board models with the printed solids: surface points inside a solid (must be 0; control = pushed 1 mm);
(2) free travel of each loose item (exact boolean intersection of box models with the printed solids, bisection to 0.05 mm)."""
import os, sys, json, numpy as np, trimesh, manifold3d as mf
P, MF, OLD = sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None   # MF = the repository's hardware/ directory
G2C = np.array([[1, 0, 0, 0], [0, 0, -1, 0], [0, 1, 0, 0], [0, 0, 0, 1.0]]) @ np.diag([1000, 1000, 1000, 1])
def glb(path):
    sc = trimesh.load(path, force="scene"); ms = []
    for n in sc.graph.nodes_geometry:
        T, g = sc.graph[n]; m = sc.geometry[g].copy(); m.apply_transform(T); ms.append(m)
    m = trimesh.util.concatenate(ms); m.apply_transform(G2C); return m
def load(d, n): return trimesh.load(os.path.join(d, n + ".stl"))
def M(m): return mf.Manifold(mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32), tri_verts=np.asarray(m.faces, np.uint32)))
def box(x0, x1, y0, y1, z0, z1): return mf.Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])
R180 = np.diag([-1.0, -1.0, 1.0, 1.0]); Z_BRD, ZLIB, ZCORE, CBZ = 4.0, 3.0, 2.5, 7.0
pm = glb(f"{MF}/pcb/pmbh/pmbh.glb"); pm.apply_translation((-100, 100, Z_BRD))
lb = glb(f"{MF}/pcb/libb/libb.glb"); lb.apply_transform(R180); lb.apply_translation((156.0, -140.0, ZLIB))
core = glb(f"{MF}/../modeling/bitalino_core_LOD1.glb"); core.apply_transform(R180); core.apply_translation((28.0, 32.5, ZCORE))
def report(d, tag):
    out = {}
    solids = {k: [load(d, a), load(d, b)] for k, (a, b) in dict(back=("back_pod_base", "back_pod_lid"), chest=("chest_pod_base", "chest_pod_lid"), c=("c_case_base", "c_case_lid")).items()}
    for nm, m, k in (("PMB-H", pm, "back"), ("LIB", lb, "chest"), ("Core B (LOD1)", core, "chest")):
        pts = np.vstack([trimesh.sample.sample_surface(m, 6000)[0], m.vertices[:: max(1, len(m.vertices) // 6000)]])
        cnt = lambda q: int(sum(s.contains(q).sum() for s in solids[k]))
        out[nm] = dict(points=len(pts), inside=cnt(pts), inside_lifted_0p05=cnt(pts + [0, 0, 0.05]), control_pushed_1mm=max(cnt(pts + d) for d in np.eye(3).tolist() + (-np.eye(3)).tolist()))
    MS = {k: [M(s) for s in v] for k, v in solids.items()}
    items = {"104050 battery (40x50+3x10)": ("back", box(23.0, 63.0, -125.6, -72.6, 0.0, 10.0)),
             "104050 battery, bumps excluded (39.4 wide)": ("back", box(23.3, 62.7, -125.6, -72.6, 0.0, 10.0)),
             "Core B (56x65 + 3.5 sockets)": ("chest", box(0.0, 56.0, 0.0, 65.0, ZCORE, ZCORE + 1.6 + 3.5)),
             "Board Kit 108x65 (official)": ("c", box(0.0, 108.0, 0.0, 65.0, CBZ, CBZ + 1.6)),
             "523450 battery": ("c", box(21.0, 71.0, 16.0, 50.0, 0.0, 5.2))}
    def vol(k, it): return sum((it ^ s).volume() for s in MS[k])
    for nm, (k, it) in items.items():
        tr = {}
        for ax, d in (("+X", (1, 0, 0)), ("-X", (-1, 0, 0)), ("+Y", (0, 1, 0)), ("-Y", (0, -1, 0)), ("+Z", (0, 0, 1))):
            if vol(k, it) > 1e-3: tr[ax] = "already touching"; continue
            lo, hi = 0.0, None
            for step in np.arange(0.25, 20.01, 0.25):                         # march first (thin ribs must not be skipped)
                if vol(k, it.translate([c * step for c in d])) > 1e-3: hi = step; break
                lo = step
            if hi is None: tr[ax] = ">20"; continue
            while hi - lo > 0.05:
                mid = (lo + hi) / 2
                if vol(k, it.translate([c * mid for c in d])) < 1e-3: lo = mid
                else: hi = mid
            tr[ax] = round(lo, 2)
        out[nm] = dict(overlap_mm3=round(vol(k, it), 3), free_travel_mm=tr)
    print(f"== {tag}"); [print(f"  {k}: {v}") for k, v in out.items()]; return out
res = {"new": report(P, "NEW parts")}
if OLD: res["old"] = report(OLD, "OLD parts (before this change)")
json.dump(res, open(os.path.join(P, "fit_report.json"), "w"), indent=1, ensure_ascii=False)
