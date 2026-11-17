#!/usr/bin/env python3
"""V3-G3a run driver (from v2/gates/g3a/run_v2b.py): one printed radiator in the AE1 keep-out of the V3-F stage-2b pod,
on the wrist phantom or in free space.

  envs/emsim/bin/python -u run_v3f.py --tag PA --case body --level c --cand '{"kind":"fill"}' [--var '{"frame_gnd":false}']
        [--decay 1e-4] [--tmax 12] [--dry]
Writes runs/<tag>_<case>_<level>.npz and _meta.json.  Port: one-cell delta gap between the Y 4.5 (case) ground edge and
the feed leg on F.Cu (z = 1.0), 50-ohm lumped source resistor, Z from gap voltage and Ampere loop (common/fdtd.py).
Stop: touch runs/<tag>_<case>_<level>.STOP
"""
import argparse, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(HERE, "common"))
import numpy as np
from dataclasses import asdict
from scene_v3f import Cand, Var, build_scene, split_pec_polyz, BOARD_T
from mesh_v3f import v3f_mesh, flux_regions, PML_CELLS

LEVEL_GAP = {"c": 0.25, "f": 0.125}


def setup(case, level, cand_over=None, var_over=None):
    c = Cand(**(cand_over or {}))
    c.port_gap = LEVEL_GAP[level]
    v = Var(**(var_over or {}))
    v.phantom = (case == "body")
    mesh = v3f_mesh(v.phantom, level)
    gy = mesh.ax[1].phys_grid(); gz = mesh.ax[2].phys_grid()
    sy = lambda y: float(round(gy[np.argmin(np.abs(gy - y))], 6))
    sz = lambda z: float(round(gz[np.argmin(np.abs(gz - z))], 6))
    prims, port, ant = build_scene(c, v, (sy, sz))
    prims = split_pec_polyz(prims, mesh)
    return c, v, mesh, prims, port, ant


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", choices=["free", "body"], default="body")
    ap.add_argument("--level", choices=["c", "f"], default="c")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--cand", default="{}"); ap.add_argument("--var", default="{}")
    ap.add_argument("--tmax", type=float, default=12.0)
    ap.add_argument("--decay", type=float, default=1e-4)
    ap.add_argument("--dry", action="store_true")
    a = ap.parse_args()
    c, v, mesh, prims, port, ant = setup(a.case, a.level, json.loads(a.cand), json.loads(a.var))
    if not ant["info"]["fits"]:
        raise SystemExit(f"radiator copper outside the keep-out: {ant['info']}")
    import meep as mp
    from geom import GeometryBuilder
    from fdtd import run_port_sim
    gb = GeometryBuilder(mesh, mp)
    geo = gb.build(prims)
    my = mesh.ax[1]
    port = dict(port)
    port["y_loop"] = float(my.to_phys(float(my.to_comp(port["y_gap0"])) - 2.5 * mesh.dcomp))
    os.makedirs(os.path.join(HERE, "runs"), exist_ok=True)
    rtag = f"{a.tag}_{a.case}_{a.level}"
    out = os.path.join(HERE, "runs", rtag + ".npz")
    meta = dict(tag=a.tag, case=a.case, level=a.level, cand=asdict(c), var=asdict(v),
                mesh=[ax.describe() for ax in mesh.ax], ncells=mesh.ncells, courant=mesh.courant(),
                port=port, geometry_stats=gb.stats, ant_info=ant["info"], copper_F_wkt=ant["fcu"].wkt,
                copper_B_wkt=(ant["bcu"].wkt if ant["bcu"] is not None else None), vias=ant["vias"],
                prims=[(type(p).__name__, p.tag, p.mat.name) for p in prims],
                started=time.strftime("%Y-%m-%d %H:%M:%S"), decay=a.decay, tmax_ns=a.tmax)
    print(json.dumps({k: meta[k] for k in ("tag", "case", "level", "ncells", "courant", "geometry_stats", "ant_info", "port")},
                     default=str), flush=True)
    if a.dry:
        json.dump(meta, open(out.replace(".npz", "_dry_meta.json"), "w"), indent=1, default=str)
        return
    flux_f = np.array([2.30, 2.40, 2.44, 2.48, 2.58]) * 1e9
    run_port_sim(mp, mesh, geo, port, out, f_lo=2.0e9, f_hi=2.9e9, nf_port=181, f_src=2.45e9, fwidth_hz=3.0e9,
                 flux_freqs_hz=flux_f, flux_regions=flux_regions(v.phantom), pml_cells=PML_CELLS, decay_by=a.decay,
                 tmax_ns=a.tmax, extra_meta=meta, eps_averaging=False, log=lambda s: print(s, flush=True))


if __name__ == "__main__":
    main()
