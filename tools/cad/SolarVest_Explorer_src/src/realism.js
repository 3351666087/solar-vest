// Photographic look: procedural textures, box-projected UVs, mesh splitting, the dress form and the studio.
// Everything is generated at load time, so the page stays a single offline bundle (no image downloads).
import * as THREE from "three";

// ---------------------------------------------------------------------------------------- small helpers
const canvas2d = (w, h) => { const c = document.createElement("canvas"); c.width = w; c.height = h; return [c, c.getContext("2d")]; };
function hash(x, y) { const s = Math.sin(x * 127.1 + y * 311.7) * 43758.5453; return s - Math.floor(s); }
function vnoise(x, y) {          // smooth value noise, period-free
  const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi;
  const u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
  const a = hash(xi, yi), b = hash(xi + 1, yi), c = hash(xi, yi + 1), d = hash(xi + 1, yi + 1);
  return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
}
// height field (Float32Array, w*h, wraps) → tangent-space normal map
function normalFromHeight(H, w, h, strength) {
  const [c, g] = canvas2d(w, h), img = g.createImageData(w, h), d = img.data;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const hl = H[y * w + ((x - 1 + w) % w)], hr = H[y * w + ((x + 1) % w)];
    const hu = H[((y - 1 + h) % h) * w + x], hd = H[((y + 1) % h) * w + x];
    let nx = (hl - hr) * strength, ny = (hu - hd) * strength, nz = 1;
    const l = Math.hypot(nx, ny, nz); nx /= l; ny /= l; nz /= l;
    const i = (y * w + x) * 4; d[i] = (nx * 0.5 + 0.5) * 255; d[i + 1] = (ny * 0.5 + 0.5) * 255; d[i + 2] = (nz * 0.5 + 0.5) * 255; d[i + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; return t;
}

// ---------------------------------------------------------------------------------------- textures
// 600D-style ripstop: a plain weave with a heavier reinforcing thread every 8th pick, as on outdoor gear.
export function ripstopNormal() {
  const w = 256, p = 8, H = new Float32Array(w * w);
  for (let y = 0; y < w; y++) for (let x = 0; x < w; x++) {
    const tx = (x % p) / p, ty = (y % p) / p, cx = Math.floor(x / p), cy = Math.floor(y / p);
    const over = (cx + cy) % 2 === 0;
    const across = Math.sin(Math.PI * (over ? tx : ty)), along = 0.75 + 0.25 * Math.sin(Math.PI * (over ? ty : tx));
    let h = across * along * (over ? 1 : 0.8);
    if (cx % 8 === 0 || cy % 8 === 0) h += 0.55 * Math.sin(Math.PI * (cx % 8 === 0 ? tx : ty));   // ripstop grid
    h += (hash(x, y) - 0.5) * 0.18;                                                                   // fibre fuzz
    H[y * w + x] = h;
  }
  return normalFromHeight(H, w, w, 2.2);
}
// nylon webbing: tight ribs along its length
export function webbingNormal() {
  const w = 128, H = new Float32Array(w * w);
  for (let y = 0; y < w; y++) for (let x = 0; x < w; x++) H[y * w + x] = Math.sin((x / w) * Math.PI * 2 * 16) * 0.5 + Math.sin((y / w) * Math.PI * 2 * 48) * 0.15 + (hash(x, y) - 0.5) * 0.1;
  return normalFromHeight(H, w, w, 2.5);
}
// FDM print: 0.2 mm layer lines plus a little surface grain
export function printNormal() {
  const w = 256, H = new Float32Array(w * w);
  for (let y = 0; y < w; y++) for (let x = 0; x < w; x++) H[y * w + x] = 0.55 * Math.sin((y / w) * Math.PI * 2 * 24) + 0.35 * vnoise(x / 9, y / 9) + (hash(x, y) - 0.5) * 0.12;
  return normalFromHeight(H, w, w, 1.6);
}
// light oak laminate, like the lab desk in the panel photos
export function oakTexture() {
  const [c, g] = canvas2d(1024, 512);
  g.fillStyle = "#d8c8b2"; g.fillRect(0, 0, 1024, 512);
  for (let i = 0; i < 520; i++) {
    const y0 = Math.random() * 512, amp = 2 + Math.random() * 7, f = 0.002 + Math.random() * 0.006, ph = Math.random() * 6.28;
    g.strokeStyle = `rgba(${150 + Math.random() * 30 | 0},${122 + Math.random() * 25 | 0},${92 + Math.random() * 20 | 0},${0.05 + Math.random() * 0.16})`;
    g.lineWidth = 0.5 + Math.random() * 2.2; g.beginPath();
    for (let x = -10; x <= 1034; x += 16) g.lineTo(x, y0 + amp * Math.sin(x * f + ph) + 3 * vnoise(x / 60, i));
    g.stroke();
  }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; return t;
}
// the vice dean's panel: 12 monocrystalline strips (≈32 × 67 mm) in 2 rows of 6 on a white backsheet,
// two busbars per strip, fine fingers, and the string ribbons in the end margins (sizes from the change list, §2)
export function cellsTexture(glassW, glassH) {
  const ppm = 8, W = Math.round(glassW * 1000 * ppm), H = Math.round(glassH * 1000 * ppm);
  const [c, g] = canvas2d(W, H), mm = (v) => v * ppm;
  g.fillStyle = "#dfe3e6"; g.fillRect(0, 0, W, H);
  const cw = 32, ch = 67, gapU = 3, gapV = 5, cols = 6, rows = 2;
  const u0 = (W / ppm - (cols * cw + (cols - 1) * gapU)) / 2, v0 = (H / ppm - (rows * ch + (rows - 1) * gapV)) / 2;
  for (let r = 0; r < rows; r++) for (let k = 0; k < cols; k++) {
    const x = mm(u0 + k * (cw + gapU)), y = mm(v0 + r * (ch + gapV)), w = mm(cw), h = mm(ch);
    const grd = g.createLinearGradient(x, y, x + w, y + h);
    grd.addColorStop(0, "#1a1c21"); grd.addColorStop(0.5, "#101216"); grd.addColorStop(1, "#1b1e24");   // near-black mono cells, as in the front photo
    g.fillStyle = grd; g.fillRect(x, y, w, h);
    g.fillStyle = "rgba(170,180,195,0.18)";                       // fingers across the strip
    for (let f = 1.2; f < cw; f += 1.6) g.fillRect(x + mm(f), y, 1, h);
    g.fillStyle = "#8e959e";                                      // two busbars along the string
    for (const b of [0.3, 0.7]) g.fillRect(x - mm(gapU / 2), y + mm(ch * b) - mm(0.4), w + mm(gapU), mm(0.8));
  }
  g.fillStyle = "#c3c8cf";                                        // end ribbons joining the strings
  for (const xe of [u0 - 4, u0 + cols * cw + (cols - 1) * gapU + 1.5]) g.fillRect(mm(xe), mm(v0), mm(2.5), mm(rows * ch + gapV));
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}
// ---------------------------------------------------------------------------------------- BITalino boards
// White ENIG boards as in the user's photo of the three BITalino boards and PLUX manual Fig. 8.
const MM = 12;   // px per mm
function boardCanvas(wmm, hmm) { const [c, g] = canvas2d(Math.round(wmm * MM), Math.round(hmm * MM)); g.scale(MM, MM); return [c, g]; }
function finishTex(c) { const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.flipY = false; t.anisotropy = 8; return t; }
const GOLD = "#d2a64a", SILK = "#3b3f46", MASK = "#f3f3ef";
function ring(g, x, y, r = 0.55) { g.fillStyle = GOLD; g.beginPath(); g.arc(x, y, r, 0, 7); g.fill(); g.fillStyle = "#6b5a2c"; g.beginPath(); g.arc(x, y, r * 0.48, 0, 7); g.fill(); }
function smd(g, x, y, w, h, body = "#1d1f24") { g.fillStyle = GOLD; g.fillRect(x - 0.15, y, 0.3, h); g.fillRect(x + w - 0.15, y, 0.3, h); g.fillStyle = body; g.fillRect(x + 0.15, y, w - 0.3, h); }
function chip(g, cx, cy, s, rot = 0) {
  g.save(); g.translate(cx, cy); g.rotate(rot);
  g.fillStyle = "#bfc3c9"; for (let k = -3; k <= 3; k++) { const o = (k / 3.5) * (s / 2); g.fillRect(o - 0.12, -s / 2 - 0.7, 0.24, s + 1.4); g.fillRect(-s / 2 - 0.7, o - 0.12, s + 1.4, 0.24); }
  g.fillStyle = "#16181c"; g.fillRect(-s / 2, -s / 2, s, s); g.fillStyle = "#2a2d33"; g.beginPath(); g.arc(-s / 2 + 1, -s / 2 + 1, 0.4, 0, 7); g.fill();
  g.restore();
}
function label(g, text, x, y, size = 2.2, color = SILK, align = "left") { g.fillStyle = color; g.font = `600 ${size}px "IBM Plex Sans", Arial, sans-serif`; g.textAlign = align; g.textBaseline = "middle"; g.fillText(text, x, y); }
function logo(g, x, y, size) {           // "bitalino" word mark, dark "bit" + grey "alino"
  g.font = `800 ${size}px Arial Rounded MT Bold, Arial, sans-serif`; g.textBaseline = "middle"; g.textAlign = "left";
  g.fillStyle = "#1c1e24"; g.fillText("bit", x, y); const w = g.measureText("bit").width; g.fillStyle = "#8d939b"; g.fillText("alino", x + w, y);
}
function traces(g, w, h, n, seed) {
  g.strokeStyle = "rgba(170,176,186,0.45)"; g.lineWidth = 0.18;
  for (let i = 0; i < n; i++) { const r = (k) => hash(i * 13.1 + seed, k * 7.7); const x0 = r(1) * w, y0 = r(2) * h, x1 = r(3) * w; g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y0); g.lineTo(x1, y0 + (r(4) - 0.5) * 10); g.stroke(); }
}
// BITalino (r)evolution Core, 56 × 65 mm, in the manual figure's frame (x right, y down from the top-left corner)
export function bitalinoCoreTexture(variant = "BT") {
  const W = 56, H = 65, [c, g] = boardCanvas(W, H);
  g.fillStyle = MASK; g.fillRect(0, 0, W, H);
  traces(g, W, H, 40, 3);
  const SY = [5.2, 18.6, 32.1, 45.6, 59.1];
  for (const sy of SY) for (const hx of [7.6, W - 7.6]) for (let k = 0; k < 4; k++) ring(g, hx, sy - 2.7 + 1.8 * k, 0.5);
  g.strokeStyle = "rgba(120,126,136,0.55)"; g.lineWidth = 0.22; g.setLineDash([0.8, 0.6]);       // break-away lines of the strips
  g.strokeRect(9, 12.5, W - 18, H - 13); g.setLineDash([]);
  g.strokeStyle = SILK; g.lineWidth = 0.25; g.strokeRect(10.2, 13.2, 35.6, 18.2);                  // MCU block
  for (const ry of [15.0, 29.5]) for (let k = 0; k < 13; k++) ring(g, 11.5 + 2.54 * k, ry, 0.6);
  label(g, "MCU", 37.5, 22.5, 2.4);
  for (const [x, y] of [[13, 19], [13, 23.5], [41.5, 19.5], [19, 25.5]]) smd(g, x, y, 1.6, 0.8);
  g.strokeRect(10.2, 34.2, 15.5, 30);
  if (variant === "BLE") {        // Core BLE: the HC-05 footprint stays empty, the BLE module sits at its far end
    label(g, "BLE", 11.2, 35.6, 2);
    for (let r = 0; r < 4; r++) for (let k = 0; k < 4; k++) ring(g, 13 + 2.6 * k, 39.5 + 2.4 * r, 0.42);
    g.strokeRect(11.6, 48.6, 13.4, 15.6);
  } else label(g, "BT", 11.2, 35.6, 2);
  for (let k = 0; k < 6; k++) ring(g, 13 + 2.54 * k, 36.2, 0.5);
  logo(g, 27.5, 37.5, 4.6);
  g.strokeRect(27, 41.2, 18.8, 23); label(g, "PWR", 41.2, 43, 1.8);
  for (const [x, y] of [[29, 44], [29, 48.5], [41.8, 49], [29, 55.5]]) chip(g, x + 1.2, y + 1, 1.8);
  for (const [x, y] of [[33, 44.2], [37.5, 56.5], [41, 53], [31.5, 59.5]]) smd(g, x, y, 1.5, 0.8);
  for (const [x, y] of [[28.8, 51.5], [31.3, 51.5], [28.8, 53.8], [31.3, 53.8]]) ring(g, x, y, 0.75);
  label(g, "+", 34, 45, 1.8); label(g, "−", 39.4, 45, 1.8);
  g.fillStyle = MASK; g.fillRect(0, 0, 0.6, 0.6);
  return finishTex(c);
}
// underside of the Core: the same through-hole rings and traces, no parts or lettering
export function bitalinoCoreBottomTexture() {
  const W = 56, H = 65, [c, g] = boardCanvas(W, H);
  g.fillStyle = MASK; g.fillRect(0, 0, W, H);
  traces(g, W, H, 30, 7);
  for (const sy of [5.2, 18.6, 32.1, 45.6, 59.1]) for (const hx of [7.6, W - 7.6]) for (let k = 0; k < 4; k++) ring(g, hx, sy - 2.7 + 1.8 * k, 0.5);
  for (const ry of [15.0, 29.5]) for (let k = 0; k < 13; k++) ring(g, 11.5 + 2.54 * k, ry, 0.6);
  for (let k = 0; k < 6; k++) ring(g, 13 + 2.54 * k, 36.2, 0.5);
  for (const [x, y] of [[28.8, 51.5], [31.3, 51.5], [28.8, 53.8], [31.3, 53.8]]) ring(g, x, y, 0.75);
  return finishTex(c);
}
// top of the BLE module's shield can: brushed silver, CE mark, small print and a 2-D code
export function bleCanTexture() {
  const W = 11, H = 11, [c, g] = boardCanvas(W, H);
  const grd = g.createLinearGradient(0, 0, W, H); grd.addColorStop(0, "#c9cdd2"); grd.addColorStop(1, "#aeb3ba");
  g.fillStyle = grd; g.fillRect(0, 0, W, H);
  g.fillStyle = "#f4f4f2"; g.fillRect(1, 1, 9, 9);
  g.strokeStyle = "#2b2e33"; g.lineWidth = 0.35; g.beginPath(); g.arc(3.2, 3.4, 1.3, 0.6, 5.7); g.stroke(); g.beginPath(); g.arc(5.6, 3.4, 1.3, 0.6, 5.7); g.stroke();
  g.beginPath(); g.moveTo(4.9, 3.4); g.lineTo(6.4, 3.4); g.stroke();
  g.fillStyle = "#2b2e33"; for (let r = 0; r < 3; r++) g.fillRect(1.8, 5.6 + r * 0.9, 4.2 - r * 0.8, 0.35);
  for (let i = 0; i < 25; i++) if (hash(i, 9) > 0.45) g.fillRect(6.6 + (i % 5) * 0.55, 6.2 + Math.floor(i / 5) * 0.55, 0.5, 0.5);
  return finishTex(c);
}
// HC-05-class Bluetooth module: green FR4, two shielded chips, gold meander antenna at the far end
export function btModuleTexture() {
  const W = 13.9, H = 27.5, [c, g] = boardCanvas(W, H);
  g.fillStyle = "#1e7a3c"; g.fillRect(0, 0, W, H);
  for (let k = 0; k < 13; k++) { g.fillStyle = GOLD; g.fillRect(0, 1 + k * 1.5, 0.9, 0.9); g.fillRect(W - 0.9, 1 + k * 1.5, 0.9, 0.9); }
  g.fillStyle = "#15171b"; g.fillRect(2, 2, 9.5, 7.5); g.fillRect(2, 10.6, 9.5, 7.2);
  g.fillStyle = "#2b2e34"; g.fillRect(3, 3, 3, 2); label(g, "BC417", 6.7, 5.8, 1.4, "#7b818a", "center");
  g.strokeStyle = GOLD; g.lineWidth = 0.55; g.beginPath(); let x = 1.6, y = 25.2; g.moveTo(x, y);
  for (let k = 0; k < 5; k++) { g.lineTo(x, 20.6); x += 1.05; g.lineTo(x, 20.6); g.lineTo(x, 25.2); x += 1.05; g.lineTo(x, 25.2); } g.stroke();
  smd(g, 3, 18.4, 1.4, 0.7, "#c9b48a"); smd(g, 7.5, 18.4, 1.4, 0.7);
  return finishTex(c);
}
// the MCU block of the Board Kit: white panel, ATmega328P (TQFP-32) at 45°, two header rows
export function mcuBlockTexture() {
  const W = 30, H = 30, [c, g] = boardCanvas(W, H);
  g.fillStyle = MASK; g.fillRect(0, 0, W, H); traces(g, W, H, 14, 5);
  for (const ry of [3, 27]) for (let k = 0; k < 10; k++) ring(g, 3.6 + 2.54 * k, ry, 0.6);
  chip(g, 15, 15, 7, Math.PI / 4);
  for (const [x, y] of [[5, 8], [5, 20], [23, 8], [23, 20]]) smd(g, x, y, 1.6, 0.8);
  return finishTex(c);
}
// BITalino (r)evolution Board Kit: the white panel with break-away modules. `mods` are rectangles in mm
// (from the 3D parts' positions) with a label; drawn as outlined modules joined by break-away tabs.
export function boardKitTexture(W, H, mods) {
  const [c, g] = boardCanvas(W, H);
  g.fillStyle = MASK; g.fillRect(0, 0, W, H);
  traces(g, W, H, 70, 11);
  for (let i = 0; i < 160; i++) { const x = hash(i, 1) * W, y = hash(i, 2) * H; ring(g, x, y, 0.28); }   // vias
  g.strokeStyle = "rgba(120,126,136,0.6)"; g.lineWidth = 0.25; g.setLineDash([0.9, 0.6]);
  for (const m of mods) g.strokeRect(m.x - 1.2, m.y - 1.2, m.w + 2.4, m.h + 2.4);
  g.setLineDash([]);
  for (const m of mods) {
    label(g, m.label, m.x + m.w / 2, Math.min(H - 1.5, m.y + m.h + 2.4), 2.1, SILK, "center");
    for (let k = 0; k < 3; k++) ring(g, m.x - 2.2, m.y + m.h * (0.25 + 0.25 * k), 0.45);
  }
  // the word mark goes to the first spot no module covers
  const lw = 19, lh = 5, hit = (x, y) => mods.some((m) => x < m.x + m.w + 3 && x + lw > m.x - 3 && y - lh / 2 < m.y + m.h + 4 && y + lh / 2 > m.y - 3);
  const spots = [[W * 0.62, H * 0.1], [W * 0.38, H * 0.1], [W * 0.62, H * 0.9], [W * 0.3, H * 0.9], [W * 0.66, H * 0.55], [W * 0.5, H * 0.5]];
  const [lx, ly] = spots.find(([x, y]) => !hit(x - lw / 2, y)) || spots[0];
  logo(g, lx - lw / 2, ly, 4.2);
  return finishTex(c);
}
// Board Kit artwork, everything at its position in the user's photo (mapped to mm in app.js, buildBoardKit):
// plated holes, SMD pads, resistor-array footprints, the silk marks, PWR / BLE / MCU / ON / OFF / ± and the word mark.
export function boardKitArt(W, H, L) {
  const [c, g] = boardCanvas(W, H);
  g.fillStyle = MASK; g.fillRect(0, 0, W, H);
  traces(g, W, H, 110, 21);
  for (let i = 0; i < 260; i++) { g.fillStyle = "rgba(150,156,166,0.55)"; g.beginPath(); g.arc(hash(i, 3) * W, hash(i, 4) * H, 0.18, 0, 7); g.fill(); }   // tented vias
  for (const [x, y, w, h] of L.pads) { g.fillStyle = GOLD; g.fillRect(x - w / 2, y - h / 2, w, h); }
  for (const [x, y, w, h] of L.hatches) {        // resistor-array / castellation footprints: rows of fine gold pads
    g.fillStyle = GOLD; const n = Math.max(3, Math.round(h / 0.5));
    for (let k = 0; k < n; k++) g.fillRect(x - w / 2, y - h / 2 + (k + 0.15) * (h / n), w, (h / n) * 0.6);
  }
  g.strokeStyle = SILK; g.lineWidth = 0.22;
  for (const [x, y, r, kind] of L.silk) {
    g.beginPath(); if (kind === "ring") g.arc(x, y, r, 0, 7); else { g.moveTo(x - r, y); g.lineTo(x, y); g.lineTo(x, y + r); } g.stroke();
  }
  for (const [x, y, r] of L.holes) ring(g, x, y, r);
  for (const [t, x, y, size] of L.texts) label(g, t, x, y, size, SILK, "center");
  if (L.logo) { const [x, y, size] = L.logo; g.font = `800 ${size}px Arial Rounded MT Bold, Arial, sans-serif`; logo(g, x - g.measureText("bitalino").width / 2, y, size); }
  g.fillStyle = MASK; g.fillRect(0, 0, 0.6, 0.6);
  return finishTex(c);
}
export function backdropTexture() {
  const [c, g] = canvas2d(1024, 1024);
  const grd = g.createRadialGradient(512, 430, 40, 512, 560, 760);
  grd.addColorStop(0, "#2a2e35"); grd.addColorStop(0.55, "#16191e"); grd.addColorStop(1, "#07080a");
  g.fillStyle = grd; g.fillRect(0, 0, 1024, 1024);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

// ---------------------------------------------------------------------------------------- studio lighting
// A dark studio with softboxes: big warm one above-behind (the sun side), cool strips left/right, a broad front fill.
export function studioEnvironment(pmrem) {
  const s = new THREE.Scene();
  s.add(new THREE.Mesh(new THREE.SphereGeometry(20, 32, 16), new THREE.MeshBasicMaterial({ color: 0x121417, side: THREE.BackSide })));
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.MeshBasicMaterial({ color: 0x1d2024 }));
  floor.rotation.x = -Math.PI / 2; floor.position.y = -2; s.add(floor);
  const box = (w, h, pos, k, tint = 0xffffff) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ color: new THREE.Color(tint).multiplyScalar(k), side: THREE.DoubleSide }));
    m.position.set(...pos); m.lookAt(0, 0, 0); s.add(m);
  };
  box(7, 3.5, [0, 7, -5], 4.2, 0xfff0dc);
  box(1.4, 7, [-8, 2, 2], 2.0, 0xdde8ff);
  box(1.4, 7, [8, 2, 2], 1.5);
  box(6, 2.2, [0, 2.5, 8], 1.0);
  const tex = pmrem.fromScene(s, 0.035).texture;
  s.traverse((o) => { if (o.isMesh) { o.geometry.dispose(); o.material.dispose(); } });
  return tex;
}
// floor disc that fades into the backdrop; receives the real shadows
export function makeFloor(y, radius, color = 0x1b1e22) {
  const [c, g] = canvas2d(256, 256), grd = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  grd.addColorStop(0, "#fff"); grd.addColorStop(0.55, "#bbb"); grd.addColorStop(1, "#000");
  g.fillStyle = grd; g.fillRect(0, 0, 256, 256);
  const m = new THREE.Mesh(new THREE.CircleGeometry(radius, 96),
    new THREE.MeshStandardMaterial({ color, roughness: 0.92, metalness: 0, alphaMap: new THREE.CanvasTexture(c), transparent: true, depthWrite: false }));
  m.rotation.x = -Math.PI / 2; m.position.y = y; m.receiveShadow = true; m.userData.noAO = true; m.renderOrder = -1;
  return m;
}
export function contactShadow(x, y, z, radius, opacity = 0.55) {
  const [c, g] = canvas2d(128, 128), grd = g.createRadialGradient(64, 64, 0, 64, 64, 64);
  grd.addColorStop(0, `rgba(0,0,0,${opacity})`); grd.addColorStop(1, "rgba(0,0,0,0)");
  g.fillStyle = grd; g.fillRect(0, 0, 128, 128);
  const m = new THREE.Mesh(new THREE.PlaneGeometry(radius * 2, radius * 2), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false }));
  m.rotation.x = -Math.PI / 2; m.position.set(x, y + 0.001, z); m.userData.noAO = true; return m;
}

// ---------------------------------------------------------------------------------------- geometry tools
// World-space box projection: each vertex takes the plane its normal faces most. `tile` is metres per texture repeat.
export function addBoxUV(mesh, tile) {
  const geo = mesh.geometry, pos = geo.attributes.position, nor = geo.attributes.normal;
  const m = mesh.matrixWorld, nm = new THREE.Matrix3().getNormalMatrix(m), p = new THREE.Vector3(), n = new THREE.Vector3();
  const uv = new Float32Array(pos.count * 2);
  for (let i = 0; i < pos.count; i++) {
    p.set(pos.getX(i), pos.getY(i), pos.getZ(i)).applyMatrix4(m);
    n.set(nor.getX(i), nor.getY(i), nor.getZ(i)).applyMatrix3(nm);
    const ax = Math.abs(n.x), ay = Math.abs(n.y), az = Math.abs(n.z);
    let u, v;
    if (ax >= ay && ax >= az) { u = p.z; v = p.y; } else if (ay >= az) { u = p.x; v = p.z; } else { u = p.x; v = p.y; }
    uv[i * 2] = u / tile; uv[i * 2 + 1] = v / tile;
  }
  geo.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
}
// Split one mesh into several that share its vertex buffers: classify(triangle centroid in local space, tri index) → group name.
export function splitMesh(mesh, classify, materials) {
  const geo = mesh.geometry, pos = geo.attributes.position;
  const idx = geo.index ? geo.index.array : null, triCount = idx ? idx.length / 3 : pos.count / 3;
  const groups = {}, c = new THREE.Vector3(), a = new THREE.Vector3(), b = new THREE.Vector3(), d = new THREE.Vector3();
  for (let t = 0; t < triCount; t++) {
    const i0 = idx ? idx[t * 3] : t * 3, i1 = idx ? idx[t * 3 + 1] : t * 3 + 1, i2 = idx ? idx[t * 3 + 2] : t * 3 + 2;
    a.fromBufferAttribute(pos, i0); b.fromBufferAttribute(pos, i1); d.fromBufferAttribute(pos, i2);
    c.copy(a).add(b).add(d).multiplyScalar(1 / 3);
    const k = classify(c, a, b, d);
    (groups[k] ||= []).push(i0, i1, i2);
  }
  const out = [];
  for (const [k, list] of Object.entries(groups)) {
    if (!materials[k]) continue;
    const g = new THREE.BufferGeometry();
    for (const [name, attr] of Object.entries(geo.attributes)) g.setAttribute(name, attr);
    g.setIndex(list);
    const m = new THREE.Mesh(g, materials[k]);
    m.name = `${mesh.name}#${k}`; m.position.copy(mesh.position); m.quaternion.copy(mesh.quaternion); m.scale.copy(mesh.scale);
    out.push(m);
  }
  return out;
}
// A PCB export as one mesh: triangles in the board slab are solder mask, everything else is a component.
// The slab is the most-area layer along the mesh's thinnest axis.
export function boardClassifier(mesh) {
  const geo = mesh.geometry; geo.computeBoundingBox();
  const s = geo.boundingBox.getSize(new THREE.Vector3()), ax = s.x <= s.y && s.x <= s.z ? "x" : s.y <= s.z ? "y" : "z";
  const pos = geo.attributes.position, idx = geo.index ? geo.index.array : null, n = idx ? idx.length / 3 : pos.count / 3;
  const lo = geo.boundingBox.min[ax], span = s[ax], bins = new Float64Array(200);
  const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3(), e1 = new THREE.Vector3(), e2 = new THREE.Vector3();
  for (let t = 0; t < n; t++) {
    a.fromBufferAttribute(pos, idx ? idx[t * 3] : t * 3); b.fromBufferAttribute(pos, idx ? idx[t * 3 + 1] : t * 3 + 1); c.fromBufferAttribute(pos, idx ? idx[t * 3 + 2] : t * 3 + 2);
    const area = e1.subVectors(b, a).cross(e2.subVectors(c, a)).length() / 2, k = Math.min(199, Math.floor(((a[ax] + b[ax] + c[ax]) / 3 - lo) / span * 200));
    bins[k] += area;
  }
  const peak = bins.indexOf(Math.max(...bins)), pv = lo + (peak + 0.5) / 200 * span;
  // the other face of a 1.6 mm board is the larger neighbour within ~2 mm (in local units, scale-free via span)
  const tol = Math.max(0.0022, span * 0.06);
  return (cen) => (Math.abs(cen[ax] - pv) <= tol ? "board" : "comp");
}

// ---------------------------------------------------------------------------------------- the dress form
// A tailor's dress form fitted inside the vest: per height slice, the smallest radius of the vest panels in each
// direction, smoothed to a few Fourier terms (a generic form, not a body likeness), with a neck, an egg head
// (the ear-clip sensor sits at its ear) and a pole and base.
export function buildDressForm(vestMeshes) {
  const pts = [], p = new THREE.Vector3();
  for (const m of vestMeshes) { const pos = m.geometry.attributes.position; for (let i = 0; i < pos.count; i += 2) { p.fromBufferAttribute(pos, i).applyMatrix4(m.matrixWorld); pts.push(p.x, p.y, p.z); } }
  const S = 36, K = 4, N = 72, y0 = 1.06, y1 = 1.58, dy = 0.02, band = 0.016;
  const slices = [];
  for (let y = y0; y <= y1 + 1e-6; y += dy) {
    let minX = 1e9, maxX = -1e9, minZ = 1e9, maxZ = -1e9;
    for (let i = 0; i < pts.length; i += 3) if (Math.abs(pts[i + 1] - y) < band) { minX = Math.min(minX, pts[i]); maxX = Math.max(maxX, pts[i]); minZ = Math.min(minZ, pts[i + 2]); maxZ = Math.max(maxZ, pts[i + 2]); }
    if (minX > maxX) continue;
    slices.push({ y, cx: (minX + maxX) / 2, cz: (minZ + maxZ) / 2, r: new Array(S).fill(Infinity) });
  }
  for (let j = 1; j < slices.length - 1; j++) for (const k of ["cx", "cz"]) slices[j][k + "s"] = (slices[j - 1][k] + 2 * slices[j][k] + slices[j + 1][k]) / 4;
  for (const sl of slices) { if (sl.cxs !== undefined) { sl.cx = sl.cxs; sl.cz = sl.czs; } }
  for (let i = 0; i < pts.length; i += 3) for (const sl of slices) {
    if (Math.abs(pts[i + 1] - sl.y) >= band) continue;
    const dx = pts[i] - sl.cx, dz = pts[i + 2] - sl.cz, s = Math.floor(((Math.atan2(dz, dx) + Math.PI) / (2 * Math.PI)) * S) % S;
    sl.r[s] = Math.min(sl.r[s], Math.hypot(dx, dz));
  }
  // fill the open sectors (armholes, neckline) around the circle, then keep the first K harmonics
  const coefs = [];
  for (const sl of slices) {
    const known = sl.r.map((v, i) => (isFinite(v) ? i : -1)).filter((i) => i >= 0);
    if (known.length < 8) { coefs.push(null); continue; }
    const r = sl.r.map((v, i) => {
      if (isFinite(v)) return v;
      let lo = i, hi = i; while (!isFinite(sl.r[(lo + S) % S])) lo--; while (!isFinite(sl.r[hi % S])) hi++;
      const t = (i - lo) / (hi - lo); return sl.r[(lo + S) % S] * (1 - t) + sl.r[hi % S] * t;
    });
    const c = [];
    for (let k = 0; k <= K; k++) { let a = 0, b = 0; for (let i = 0; i < S; i++) { const th = ((i + 0.5) / S) * 2 * Math.PI - Math.PI; a += r[i] * Math.cos(k * th); b += r[i] * Math.sin(k * th); } c.push([(a * 2) / S / (k ? 1 : 2), (b * 2) / S]); }
    coefs.push(c);
  }
  for (let j = 0; j < coefs.length; j++) if (!coefs[j]) coefs[j] = coefs[j - 1] || coefs.find(Boolean);
  for (let pass = 0; pass < 2; pass++) {
    const prev = coefs.map((c) => c.map((x) => x.slice()));
    for (let j = 1; j < coefs.length - 1; j++) for (let k = 0; k <= K; k++) for (const q of [0, 1]) coefs[j][k][q] = (prev[j - 1][k][q] + 2 * prev[j][k][q] + prev[j + 1][k][q]) / 4;
  }
  const evalR = (c, th, inset) => { let r = c[0][0]; for (let k = 1; k <= K; k++) r += c[k][0] * Math.cos(k * th) + c[k][1] * Math.sin(k * th); return Math.max(0.03, r - inset); };
  // rings: hips (below the vest), the fitted torso, shoulders into the neck
  const inset = 0.007, base = slices[0], top = slices[slices.length - 1];
  const ring = (y, cx, cz, fn) => ({ y, cx, cz, fn });
  const rings = [];
  const fit = (j, scale = 1) => (th) => evalR(coefs[j], th, inset) * scale;
  rings.push(ring(0.885, base.cx, base.cz, (th) => fit(0, 0.9)(th)));
  rings.push(ring(0.9, base.cx, base.cz, fit(0, 0.985)));
  rings.push(ring(0.94, base.cx, base.cz, fit(0, 1.03)));
  rings.push(ring(1.0, base.cx, base.cz, fit(0, 1.02)));
  slices.forEach((sl, j) => rings.push(ring(sl.y, sl.cx, sl.cz, fit(j))));
  const neck = (th) => Math.hypot(0.052 * Math.cos(th), 0.056 * Math.sin(th)) + 0.001;
  const lastFit = fit(slices.length - 1);
  rings.push(ring(top.y + 0.02, top.cx, top.cz - 0.004, (th) => 0.45 * lastFit(th) + 0.55 * neck(th) * 1.25));
  rings.push(ring(top.y + 0.04, top.cx, top.cz - 0.008, (th) => neck(th) * 1.06));
  rings.push(ring(top.y + 0.09, top.cx, top.cz - 0.01, neck));
  // mesh: N vertices per ring, quads between rings, a flat cap at the bottom
  const P = [], I = [];
  rings.forEach((rg) => { for (let i = 0; i < N; i++) { const th = (i / N) * 2 * Math.PI - Math.PI; const r = rg.fn(th); P.push(rg.cx + r * Math.cos(th), rg.y, rg.cz + r * Math.sin(th)); } });
  for (let j = 0; j < rings.length - 1; j++) for (let i = 0; i < N; i++) {
    const a = j * N + i, b = j * N + ((i + 1) % N), c = (j + 1) * N + i, d = (j + 1) * N + ((i + 1) % N);
    I.push(a, c, b, b, c, d);
  }
  const ci = P.length / 3; P.push(base.cx, 0.885, base.cz);
  for (let i = 0; i < N; i++) I.push(ci, i, (i + 1) % N);
  const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.Float32BufferAttribute(P, 3)); g.setIndex(I); g.computeVertexNormals();
  const mat = new THREE.MeshPhysicalMaterial({ color: 0xaaa59d, roughness: 0.5, clearcoat: 0.3, clearcoatRoughness: 0.45, envMapIntensity: 0.8 });
  const form = new THREE.Group(); form.name = "dress_form";
  const torso = new THREE.Mesh(g, mat); form.add(torso);
  // egg head: narrower at the chin, centred over the neck; the ear clip (x = 0.084, y = 1.70) hangs at its ear
  const hg = new THREE.SphereGeometry(1, 64, 40), hp = hg.attributes.position;
  for (let i = 0; i < hp.count; i++) { const y = hp.getY(i), k = y < 0 ? 1 - 0.16 * -y : 1; hp.setXYZ(i, hp.getX(i) * 0.072 * k, y * 0.108, hp.getZ(i) * 0.088 * k); }
  hg.computeVertexNormals();
  const head = new THREE.Mesh(hg, mat); head.position.set(top.cx, top.y + 0.16, top.cz - 0.004); form.add(head);
  // steel pole and a weighted round base on the floor
  const steel = new THREE.MeshStandardMaterial({ color: 0x9aa1a9, metalness: 1, roughness: 0.32 });
  const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.011, 0.011, 0.86, 24), steel); pole.position.set(base.cx, 0.885 - 0.43, base.cz); form.add(pole);
  const foot = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.165, 0.028, 64), new THREE.MeshStandardMaterial({ color: 0x23262b, metalness: 0.6, roughness: 0.38 }));
  foot.position.set(base.cx, 0.014, base.cz); form.add(foot);
  form.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  form.userData.material = mat; form.userData.footXZ = [base.cx, base.cz];
  return form;
}
