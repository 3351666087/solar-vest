#!/usr/bin/env python3
"""Scout driver (copy of ../run_v3f.py): lid radiator kinds L1 / L2 (scene_lid.py), body or free, level c.
Mesh: v3f_mesh with the 0.25 mm radiator zone widened from X 0..8.5 to X 0..12 so the whole lid strip is on 0.25 mm.
  envs/emsim/bin/python -u run_lid.py --kind L1 --case body [--dry]   -> runs/<kind>_<case>_c.npz + _meta.json"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(HERE, "..", "common")); sys.path.insert(0, HERE)
import numpy as np
from dataclasses import asdict
import scene_lid as SL
from scene_v3f import Var, split_pec_polyz
from mesh_v3f import v3f_mesh, flux_regions, PML_CELLS


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", required=True); ap.add_argument("--case", choices=["free", "body"], default="body")
    ap.add_argument("--tmax", type=float, default=12.0); ap.add_argument("--decay", type=float, default=1e-4)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    v = Var(); v.phantom = (a.case == "body")
    mesh = v3f_mesh(v.phantom, "c", fine=(0.0, 12.0, 0.0, 6.0))
    gy = mesh.ax[1].phys_grid(); gz = mesh.ax[2].phys_grid()
    sy = lambda y: float(round(gy[np.argmin(np.abs(gy - y))], 6))
    sz = lambda z: float(round(gz[np.argmin(np.abs(gz - z))], 6))
    prims, port, info = SL.build(a.kind, v, (sy, sz))
    prims = split_pec_polyz(prims, mesh)
    import meep as mp
    from geom import GeometryBuilder
    from fdtd import run_port_sim
    gb = GeometryBuilder(mesh, mp)
    geo = gb.build(prims)
    my = mesh.ax[1]
    port["y_loop"] = float(my.to_phys(float(my.to_comp(port["y_gap0"])) - 2.5 * mesh.dcomp))
    rtag = f"{a.kind}_{a.case}_c"
    out = os.path.join(HERE, "runs", rtag + ".npz")
    meta = dict(tag=a.kind, case=a.case, level="c", var=asdict(v), mesh=[ax.describe() for ax in mesh.ax], ncells=mesh.ncells,
                courant=mesh.courant(), port=port, geometry_stats=gb.stats, lid_info=info,
                prims=[(type(p).__name__, p.tag, p.mat.name) for p in prims], started=time.strftime("%Y-%m-%d %H:%M:%S"),
                decay=a.decay, tmax_ns=a.tmax)
    print(json.dumps({k: meta[k] for k in ("tag", "case", "ncells", "courant", "geometry_stats", "port")}, default=str), flush=True)
    print(json.dumps({k: info[k] for k in ("kind", "z_lid", "lid_area_mm2", "lid_bounds")}), flush=True)
    if a.dry:
        json.dump(meta, open(out.replace(".npz", "_dry_meta.json"), "w"), indent=1, default=str)
        return
    flux_f = np.array([2.30, 2.40, 2.44, 2.48, 2.58]) * 1e9
    run_port_sim(mp, mesh, geo, port, out, f_lo=2.0e9, f_hi=2.9e9, nf_port=181, f_src=2.45e9, fwidth_hz=3.0e9,
                 flux_freqs_hz=flux_f, flux_regions=flux_regions(v.phantom), pml_cells=PML_CELLS, decay_by=a.decay,
                 tmax_ns=a.tmax, extra_meta=meta, eps_averaging=False, log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    main()
