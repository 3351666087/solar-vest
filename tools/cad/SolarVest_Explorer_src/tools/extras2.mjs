// REF2 cell + 22 M2 screws in body (world) coordinates, using the same frames as assembly.py / harness.py.
import fs from "node:fs";
const [plPath, slPath, outPath] = process.argv.slice(2);
const PL = JSON.parse(fs.readFileSync(plPath, "utf8")), SL = JSON.parse(fs.readFileSync(slPath, "utf8"));
const add = (a, b) => a.map((x, i) => x + b[i]), sc = (a, s) => a.map((x) => x * s), dot = (a, b) => a[0] * b[0] + a[1] * b[1] + a[2] * b[2];
const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]], norm = (a) => sc(a, 1 / Math.hypot(...a));
// frame: local mm -> body m; local x,y,z = right, up, normal; local origin offset (mm) applied first
const frame = (p, off = [0, 0, 0]) => ({ o: p.origin, x: p.right, y: p.up, z: p.normal, off });
const W = (F, q) => { const l = add(q, F.off); return add(F.o, add(add(sc(F.x, l[0] / 1000), sc(F.y, l[1] / 1000)), sc(F.z, l[2] / 1000))); };
const D = (F, v) => norm(add(add(sc(F.x, v[0]), sc(F.y, v[1])), sc(F.z, v[2])));
const BP = frame(PL.back_pod, [-38.5, 62.8, 2.0]), CP = frame(PL.chest_pod, [-28.0, -12.5, 2.0]), CC = frame(SL.C_board, [-54.0, -33.6, 2.0]), R2 = frame(PL.ref2);
const screws = [];
const S = (F, part, x, y, zHead, len) => screws.push({ part, pos: W(F, [x, y, zHead]), axis: D(F, [0, 0, -1]), len: len / 1000 });
for (const [x, y] of [[2.6, -2.6], [2.6, -57.4], [83.4, -57.4], [83.4, -30.0]]) S(BP, "pmbh", x, y, 4.0 + 1.6, 6);                 // PMB-H on its bosses
for (const hx of [19.0, 58.0]) for (const dy of [-12.0, -26.0]) S(BP, "back_pod", hx, 3.0 - 15.0 + dy, 0.0, 6);                   // webbing hooks, from inside
for (const [x, y] of [[-7.0, -25.0], [-7.0, -122.1], [84.0, -122.1], [84.0, -76.0]]) S(BP, "back_pod_lid", x, y, 24.5 + 2.0 - 1.2, 8);
for (const [x, y] of [[53.4, -5.6], [2.6, -5.6]]) S(CP, "lib", x, y, 3.0 + 1.6, 6);
for (const [x, y] of [[-5.25, 70.25], [61.25, 70.25], [-13.5, -45.25], [61.25, -45.25]]) S(CP, "chest_pod_lid", x, y, 15.6 + 2.0 - 1.2, 8);
for (const [x, y] of [[-5.25, 72.5], [113.25, 72.5], [-5.25, -5.25], [113.25, -5.25]]) S(CC, "c_case", x, y, 14.0 + 0.8, 8);
// REF2: pocket plane at z' = h0 along g = body-up in the holder frame (enclosures.ref2_holder)
const g = norm([dot(R2.x, [0, 1, 0]), dot(R2.y, [0, 1, 0]), dot(R2.z, [0, 1, 0])]);
let h0 = -Infinity; for (const x of [-25, 25]) for (const y of [-20, 20]) h0 = Math.max(h0, (g[0] * x + g[1] * y) / g[2]); h0 += 3.0 + 3.5;
const xL = norm(add([1, 0, 0], sc(g, -g[0]))), yL = cross(g, xL), T = 2.8;
const cenL = add([0, 0, h0], sc(g, -(T / 2 + 0.1)));                                  // plane origin is (0, 0, h0)
const ref2 = { center: W(R2, cenL), x: D(R2, xL), y: D(R2, yL), n: D(R2, g), size: [0.040, 0.028, T / 1000], lead: W(R2, add(cenL, sc(yL, -(14 + 2)))) };
fs.writeFileSync(outPath, JSON.stringify({ note: "REF2 cell (AK 40x28 mm) and the 22 M2 self-tapping screws, body frame (m), from enclosures.py + placement.json", screws, ref2 },
  (k, v) => (typeof v === "number" ? +v.toFixed(6) : v)));
console.log("screws", screws.length, "| ref2 centre", ref2.center.map((v) => v.toFixed(4)), "n", ref2.n.map((v) => v.toFixed(3)), "| tilt from horizontal", (Math.acos(Math.abs(ref2.n[1])) * 180 / Math.PI).toFixed(2), "°");
for (const s of screws.slice(0, 3)) console.log(s.part, s.pos.map((v) => v.toFixed(4)));
