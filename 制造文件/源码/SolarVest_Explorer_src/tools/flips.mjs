import fs from "node:fs";
import { fileURLToPath as __f2p } from "node:url";
const MODELS = __f2p(new URL("../models", import.meta.url)), REPO = __f2p(new URL("../../../../", import.meta.url));   // paths relative to this script
const A = JSON.parse(fs.readFileSync(`${MODELS}/board_align.json`, "utf8"));
const { plugs } = JSON.parse(fs.readFileSync(`${MODELS}/ports.json`, "utf8"));
const mul = (m, v) => [m[0]*v[0]+m[4]*v[1]+m[8]*v[2]+m[12], m[1]*v[0]+m[5]*v[1]+m[9]*v[2]+m[13], m[2]*v[0]+m[6]*v[1]+m[10]*v[2]+m[14]];
const mm4 = (a, b) => { const o = new Array(16).fill(0); for (let r = 0; r < 4; r++) for (let c = 0; c < 4; c++) for (let k = 0; k < 4; k++) o[c*4+r] += a[k*4+r] * b[c*4+k]; return o; };
const dist = (a, b) => Math.hypot(a[0]-b[0], a[1]-b[1], a[2]-b[2]) * 1000;
// flips about the board's own centre (x right, y up = component side, z along the long side; slab y ∈ [0, 1.6 mm])
const F = {
  as_is:     [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1],
  flip_long: [-1,0,0,0, 0,-1,0,0, 0,0,1,0, 0,0.0016,0,1],    // 180° about the long axis: left↔right columns, component side flips
  flip_short:[1,0,0,0, 0,-1,0,0, 0,0,-1,0, 0,0.0016,0,1],    // 180° about the short axis: top↔bottom, component side flips
  spin:      [-1,0,0,0, 0,1,0,0, 0,0,-1,0, 0,0,0,1],          // 180° in-plane
};
const SY = [5.2, 18.6, 32.1, 45.6, 59.1], L = ["I1", "A4", "A3", "A2", "A1"], R = ["O1", "O2/I2", "PWM", "A6", "A5"];
const portsOf = (mat) => { const p = {}; SY.forEach((y, i) => { const z = y / 1000 - 0.0325; p[L[i]] = mul(mat, [-0.0275, 0.0034, z]); p[R[i]] = mul(mat, [0.0275, 0.0034, z]); }); p["BAT"] = mul(mat, [0.0084, 0.004, 0.0167]); p["USB"] = mul(mat, [0.0048, 0.003, 0.0303]); return p; };
for (const [unit, base, checks] of [["Core B", A.core_worn, [["W07_conn1", "BAT"], ["W08_conn1", "I1"], ["W09_conn1", null]]], ["Core A (HeartBIT)", mm4(A.heartbit_worn, A.core_in_hb), [["W13_conn0", null]]]]) {
  console.log(`== ${unit}`);
  for (const [fname, f] of Object.entries(F)) {
    const p = portsOf(mm4(base, f));
    const parts = checks.map(([plug, want]) => {
      const near = Object.entries(p).map(([k, v]) => [k, dist(plugs[plug], v)]).sort((a, b) => a[1] - b[1])[0];
      return want ? `${plug}→${want} ${dist(plugs[plug], p[want]).toFixed(1)}mm (nearest ${near[0]} ${near[1].toFixed(1)})` : `${plug}→nearest ${near[0]} ${near[1].toFixed(1)}mm`;
    });
    console.log(`  ${fname.padEnd(10)} ${parts.join(" | ")}`);
  }
}
