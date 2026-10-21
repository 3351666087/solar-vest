// Cable-end ↔ connector check. Ports come from the real models (KiCad component nodes; BITalino sockets from the
// traced Core, named per PLUX manual Fig. 8) placed with models/board_align.json; plugs are the assembly's W*_conn* parts.
import { NodeIO, getBounds } from "@gltf-transform/core";
import { ALL_EXTENSIONS } from "@gltf-transform/extensions";
import { MeshoptDecoder } from "meshoptimizer";
import fs from "node:fs";
import { fileURLToPath as __f2p } from "node:url";
const MODELS = __f2p(new URL("../models", import.meta.url)), REPO = __f2p(new URL("../../../../", import.meta.url));   // paths relative to this script
await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ "meshopt.decoder": MeshoptDecoder });
const M = MODELS, A = JSON.parse(fs.readFileSync(`${M}/board_align.json`, "utf8"));
const mul = (m, v) => [m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12], m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13], m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14]];
const mm4 = (a, b) => { const o = new Array(16).fill(0); for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) for (let k = 0; k < 4; k++) o[c*4+r] += a[k*4+r] * b[c*4+k]; return o; };
const ctr = (b) => b.min.map((v, i) => (v + b.max[i]) / 2);
const dist = (a, b) => Math.hypot(a[0]-b[0], a[1]-b[1], a[2]-b[2]);
const asm = await io.read(`${M}/assembly.mo.glb`);
const nodes = {}; for (const n of asm.getRoot().listNodes()) if (n.getMesh()) nodes[n.getName()] = ctr(getBounds(n));
const ports = {};
async function kicad(file, tag, mat, names) {
  const d = await io.read(`${M}/${file}`);
  for (const n of d.getRoot().listNodes()) if (names.includes(n.getName())) { const b = getBounds(n); if (isFinite(b.min[0])) ports[`${tag}:${n.getName()}`] = mul(mat, ctr(b)); }
}
await kicad("pmbh.mo.glb", "PMB-H", A.pmbh_worn, ["J1", "J2", "J3", "J4", "J5", "J6", "J7", "J8"]);
await kicad("libb.mo.glb", "LIB", A.libb_worn, ["J1", "J2", "J3"]);
// BITalino Core sockets (traced model frame): left column I1 A4 A3 A2 A1, right column O1 O2/I2 PWM A6 A5 (manual Fig. 8)
const SY = [5.2, 18.6, 32.1, 45.6, 59.1], L = ["I1", "A4", "A3", "A2", "A1"], R = ["O1", "O2/I2", "PWM", "A6", "A5"];
function core(tag, mat) {
  SY.forEach((y, i) => { const z = y / 1000 - 0.0325; ports[`${tag}:${L[i]}`] = mul(mat, [-0.0275, 0.0034, z]); ports[`${tag}:${R[i]}`] = mul(mat, [0.0275, 0.0034, z]); });
  ports[`${tag}:BAT(JST)`] = mul(mat, [0.0084, 0.004, 0.0167]); ports[`${tag}:USB`] = mul(mat, [0.0048, 0.003, 0.0303]);
}
core("CoreB", A.core_worn); core("CoreA", mm4(A.heartbit_worn, A.core_in_hb));
for (const k of ["C_sock_EEG", "C_sock_EDA", "C_sock_ECG", "C_sock_EMG", "C_pwr_conn", "C_usb"]) ports[`C(stand-in):${k.slice(2)}`] = nodes[k];
for (const k of Object.keys(nodes)) if (/^electrode_[BC]_[^_]+$/.test(k)) ports[`elec:${k.slice(10)}`] = nodes[k];
for (const k of ["ecg_sensor_B_ecg_top", "ear_clip", "ref1_holder", "ref2_holder", "battery_2500mAh", "C_battery_523450", "pocket_tc_pouch"]) if (nodes[k]) ports[k] = nodes[k];
const plugs = Object.keys(nodes).filter((k) => /^W\d+.*_conn\d$/.test(k));
const rows = [];
for (const p of plugs) {
  const near = Object.entries(ports).map(([k, v]) => [k, dist(nodes[p], v) * 1000]).sort((a, b) => a[1] - b[1]).slice(0, 2);
  rows.push(`${p.padEnd(20)} → ${near[0][0].padEnd(22)} ${near[0][1].toFixed(1).padStart(6)} mm   (next: ${near[1][0]} ${near[1][1].toFixed(1)} mm)`);
}
console.log(rows.join("\n"));
fs.writeFileSync(`${MODELS}/ports.json`, JSON.stringify({ ports, plugs: Object.fromEntries(plugs.map((p) => [p, nodes[p]])) }));
