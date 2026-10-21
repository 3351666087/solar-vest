// Rigid alignment of a detailed source model onto a placeholder mesh in the assembly:
// best of 24 axis rotations by symmetric chamfer distance, then ICP (Horn's quaternion method).
import { NodeIO } from "@gltf-transform/core";
import fs from "node:fs";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { MeshoptDecoder } from "meshoptimizer";
import { fileURLToPath as __f2p } from "node:url";
const MODELS = __f2p(new URL("../models", import.meta.url)), REPO = __f2p(new URL("../../../../", import.meta.url));   // paths relative to this script
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ "meshopt.decoder": MeshoptDecoder });
const W = `${REPO}建模教程`;
const M = MODELS;
const mul = (m, v) => [m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12], m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13], m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14]];
function points(doc, filter, maxN = 6000) {
  const out = [];
  for (const n of doc.getRoot().listNodes()) {
    if (!n.getMesh() || !filter(n)) continue;
    const m = n.getWorldMatrix();
    for (const p of n.getMesh().listPrimitives()) { const a = p.getAttribute("POSITION"), v = [0,0,0]; for (let i = 0; i < a.getCount(); i++) { a.getElement(i, v); out.push(mul(m, v)); } }
  }
  const step = Math.max(1, Math.floor(out.length / maxN)); return out.filter((_, i) => i % step === 0);
}
const centroid = (P) => P.reduce((a, p) => [a[0]+p[0]/P.length, a[1]+p[1]/P.length, a[2]+p[2]/P.length], [0,0,0]);
function grid(P, cell) { const g = new Map(); for (const p of P) { const k = p.map((x) => Math.floor(x / cell)).join(","); (g.get(k) || g.set(k, []).get(k)).push(p); } return { g, cell }; }
function nearest(G, p) { const c = p.map((x) => Math.floor(x / G.cell)); let best = Infinity, bp = null;
  for (let dx = -1; dx <= 1; dx++) for (let dy = -1; dy <= 1; dy++) for (let dz = -1; dz <= 1; dz++) { const l = G.g.get(`${c[0]+dx},${c[1]+dy},${c[2]+dz}`); if (!l) continue;
    for (const q of l) { const d = (p[0]-q[0])**2 + (p[1]-q[1])**2 + (p[2]-q[2])**2; if (d < best) { best = d; bp = q; } } }
  return [Math.sqrt(best), bp]; }
const apply = (R, t, p) => [R[0]*p[0]+R[1]*p[1]+R[2]*p[2]+t[0], R[3]*p[0]+R[4]*p[1]+R[5]*p[2]+t[1], R[6]*p[0]+R[7]*p[1]+R[8]*p[2]+t[2]];
function rotations() { const out = []; const perms = [[0,1,2],[0,2,1],[1,0,2],[1,2,0],[2,0,1],[2,1,0]];
  for (const pm of perms) for (let s = 0; s < 8; s++) { const R = new Array(9).fill(0); const sg = [s&1?-1:1, s&2?-1:1, s&4?-1:1];
    for (let r = 0; r < 3; r++) R[r*3+pm[r]] = sg[r];
    const det = R[0]*(R[4]*R[8]-R[5]*R[7]) - R[1]*(R[3]*R[8]-R[5]*R[6]) + R[2]*(R[3]*R[7]-R[4]*R[6]); if (det > 0) out.push(R); } return out; }
function score(src, Gt, R, t, cap) { let s = 0, n = 0; for (const p of src) { const [d] = nearest(Gt, apply(R, t, p)); s += Math.min(isFinite(d) ? d : cap, cap); n++; } return s / n; }
function horn(A, B) { // best R,t with B ≈ R A + t
  const ca = centroid(A), cb = centroid(B); const S = [0,0,0,0,0,0,0,0,0];
  for (let i = 0; i < A.length; i++) { const a = [A[i][0]-ca[0], A[i][1]-ca[1], A[i][2]-ca[2]], b = [B[i][0]-cb[0], B[i][1]-cb[1], B[i][2]-cb[2]]; for (let r = 0; r < 3; r++) for (let c = 0; c < 3; c++) S[r*3+c] += a[r]*b[c]; }
  const [Sxx,Sxy,Sxz,Syx,Syy,Syz,Szx,Szy,Szz] = S;
  const N = [[Sxx+Syy+Szz, Syz-Szy, Szx-Sxz, Sxy-Syx],[Syz-Szy, Sxx-Syy-Szz, Sxy+Syx, Szx+Sxz],[Szx-Sxz, Sxy+Syx, -Sxx+Syy-Szz, Syz+Szy],[Sxy-Syx, Szx+Sxz, Syz+Szy, -Sxx-Syy+Szz]];
  const shift = Math.abs(Sxx)+Math.abs(Syy)+Math.abs(Szz)+Math.abs(Sxy)+Math.abs(Sxz)+Math.abs(Syx)+Math.abs(Syz)+Math.abs(Szx)+Math.abs(Szy);
  let q = [1, 0.1, 0.1, 0.1]; for (let it = 0; it < 300; it++) { const nq = [0,0,0,0]; for (let r = 0; r < 4; r++) { for (let c = 0; c < 4; c++) nq[r] += N[r][c]*q[c]; nq[r] += shift*q[r]; } const l = Math.hypot(...nq); q = nq.map((x) => x / l); }
  const [w,x,y,z] = q; const R = [1-2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y), 2*(x*y+w*z), 1-2*(x*x+z*z), 2*(y*z-w*x), 2*(x*z-w*y), 2*(y*z+w*x), 1-2*(x*x+y*y)];
  const Rc = apply(R, [0,0,0], ca); return { R, t: [cb[0]-Rc[0], cb[1]-Rc[1], cb[2]-Rc[2]] };
}
async function align(label, srcFile, srcFilter, dstFile, dstName, dstFilter) {
  const src = points(await io.read(srcFile), srcFilter), dst = points(await io.read(dstFile), dstFilter || ((n) => n.getName() === dstName));
  const cs = centroid(src), cd = centroid(dst), Gt = grid(dst, 0.003), cap = 0.01;
  const cands = [];
  for (const R0 of rotations()) { const Rc = apply(R0, [0,0,0], cs), t0 = [cd[0]-Rc[0], cd[1]-Rc[1], cd[2]-Rc[2]]; cands.push({ R: R0, t: t0, s: score(src, Gt, R0, t0, cap) }); }
  cands.sort((a, b) => a.s - b.s);
  const coarse = cands[0].s; let bestFinal = null;
  for (const c of (process.env.MULTI ? cands : cands.slice(0, 1))) {
    let R = c.R, t = c.t;
    for (const thr of [0.006, 0.004, 0.002, 0.001]) for (let it = 0; it < 12; it++) { const A = [], B = []; for (const p of src) { const q = apply(R, t, p); const [d, bp] = nearest(Gt, q); if (bp && d < thr) { A.push(p); B.push(bp); } } if (A.length < 50) break; ({ R, t } = horn(A, B)); }
    const f = score(src, Gt, R, t, cap); if (!bestFinal || f < bestFinal.f) bestFinal = { R, t, f };
  }
  let { R, t } = bestFinal;
  const fine = score(src, Gt, R, t, cap);
  // reverse direction too (placeholder → source) for a fair residual
  const Gs = grid(src.map((p) => apply(R, t, p)), 0.003); const back = score(dst, Gs, [1,0,0,0,1,0,0,0,1], [0,0,0], cap);
  const m = [R[0], R[3], R[6], 0, R[1], R[4], R[7], 0, R[2], R[5], R[8], 0, t[0], t[1], t[2], 1];   // column-major (three.js Matrix4.fromArray)
  console.log(`${label}: coarse ${(coarse*1000).toFixed(2)} mm → icp ${(fine*1000).toFixed(2)} mm, back ${(back*1000).toFixed(2)} mm`);
  return m.map((v) => +v.toFixed(6));
}
const out = JSON.parse(fs.readFileSync(`${MODELS}/board_align.json`, "utf8"));
// out.pmbh_worn = await align("PMB-H worn", `${M}/pmbh.mo.glb`, () => true, `${M}/assembly.mo.glb`, "PMB-H");
// out.pmbh_bench = await align("PMB-H bench", `${M}/pmbh.mo.glb`, () => true, `${M}/bench.mo.glb`, "PMB-H");
// out.libb_worn = await align("LIB worn", `${M}/libb.mo.glb`, () => true, `${M}/assembly.mo.glb`, "LIB");
// out.core_worn = await align("Core B worn", `${W}/bitalino_core_LOD1.glb`, () => true, `${M}/assembly.mo.glb`, "BITalino_Core_B");
// out.heartbit_worn = await align("HeartBIT A worn", `${W}/HeartBIT套件模型/heartbit_main_unit.glb`, () => true, `${M}/assembly.mo.glb`, "A_heartbit_unit");
out.core_in_hb = await align("Core inside HeartBIT", `${W}/bitalino_core_LOD1.glb`, () => true, `${W}/HeartBIT套件模型/heartbit_main_unit.glb`, null, (n) => !/^casing/.test(n.getName()));
fs.writeFileSync(`${MODELS}/board_align.json`, JSON.stringify(out));
console.log(Object.keys(out));
