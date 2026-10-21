// Solar Vest Explorer — interactive 3D walkthrough of the self-powered solar-harvesting wearable.
// Worn system, bench rig and both PCBs; X-ray shells, exploded view, labels, live energy flow (3D particles + SVG
// graph driven by the CN3791 simulation sweep) and a guided presentation.
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { MeshoptDecoder } from "three/examples/jsm/libs/meshopt_decoder.module.js";
import { EffectComposer } from "three/examples/jsm/postprocessing/EffectComposer.js";
import { UnrealBloomPass } from "three/examples/jsm/postprocessing/UnrealBloomPass.js";
import { OutputPass } from "three/examples/jsm/postprocessing/OutputPass.js";
import { ShaderPass } from "three/examples/jsm/postprocessing/ShaderPass.js";
import { GTAOPass } from "three/examples/jsm/postprocessing/GTAOPass.js";
import { Pass, FullScreenQuad } from "three/examples/jsm/postprocessing/Pass.js";
import { CopyShader } from "three/examples/jsm/shaders/CopyShader.js";
import { ripstopNormal, webbingNormal, printNormal, oakTexture, cellsTexture, backdropTexture, studioEnvironment, makeFloor, contactShadow,
  addBoxUV, splitMesh, boardClassifier, buildDressForm, bitalinoCoreTexture, bitalinoCoreBottomTexture, btModuleTexture, boardKitTexture, mcuBlockTexture, bleCanTexture, boardKitArt } from "./realism.js";
import { RoundedBoxGeometry } from "three/examples/jsm/geometries/RoundedBoxGeometry.js";
import EXTRAS from "../models/extras.json";
import { mergeGeometries, toCreasedNormals } from "three/examples/jsm/utils/BufferGeometryUtils.js";
import { computeBoundsTree, acceleratedRaycast } from "three-mesh-bvh";
import { CATS, PARTS, partOf, SHELLS, LABELS_WORN, LABELS_BENCH, EXPLODE, COMP, BOARD_LABELS, BOARD_OVERVIEW, SIM, SELF_MA, BATT_MAH,
  MODES, FLOW_NODES, FLOW_EDGES, TOUR } from "./data.js";

const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];
const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const clamp = (v, a, b) => Math.min(b, Math.max(a, v));
const fmt = (v, d = 0) => (Math.abs(v) >= 1000 && d === 0 ? v.toLocaleString("en-US") : v.toFixed(d));

// ======================================================================================== renderer / scene
const canvas = $("#gl");
// Hover picking and label occlusion raycast into ~740 k triangles; a BVH makes each ray ~0.05 ms instead of ~10 ms.
THREE.BufferGeometry.prototype.computeBoundsTree = computeBoundsTree;
THREE.Mesh.prototype.raycast = acceleratedRaycast;
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: "high-performance" });
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));   // with 4× MSAA this stays crisp and keeps Retina laptops near 60 fps
renderer.toneMapping = THREE.AgXToneMapping;          // photographic highlight roll-off
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.shadowMap.autoUpdate = false;   // the light is fixed per scene: re-render shadows only when geometry moves
renderer.outputColorSpace = THREE.SRGBColorSpace;
const scene = new THREE.Scene();
scene.background = backdropTexture();
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = studioEnvironment(pmrem);
const camera = new THREE.PerspectiveCamera(32, 1, 0.01, 60);
camera.position.set(1.32, 1.86, -2.12);
const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true; controls.dampingFactor = 0.08; controls.target.set(0, 1.4, -0.05);
controls.minDistance = 0.12; controls.maxDistance = 6;
const hemi = new THREE.HemisphereLight(0xdde6f2, 0x15171a, 0.25); scene.add(hemi);
const sunLight = new THREE.DirectionalLight(0xffe2b0, 2.5); scene.add(sunLight); scene.add(sunLight.target);
sunLight.castShadow = true; sunLight.shadow.mapSize.set(2048, 2048); sunLight.shadow.bias = -0.0003; sunLight.shadow.normalBias = 0.002;
const fill = new THREE.DirectionalLight(0xd2e0ff, 1.1); fill.position.set(-1.6, 2.2, 3); scene.add(fill);   // front key, so the chest side is not lost in silhouette

const pointsUniformPR = { value: 1 };
// Only the scene pass is multisampled: it draws into a 4× MSAA target that keeps its depth (ambient occlusion reuses
// it instead of drawing the scene twice), then one copy hands the colour to the plain targets the effects run on.
const sceneTarget = new THREE.WebGLRenderTarget(1, 1, { type: THREE.HalfFloatType, samples: 4 });
sceneTarget.depthTexture = new THREE.DepthTexture(1, 1);
class SceneMSAAPass extends Pass {
  constructor() {
    super(); this.needsSwap = false;
    this.quad = new FullScreenQuad(new THREE.ShaderMaterial({ uniforms: THREE.UniformsUtils.clone(CopyShader.uniforms), vertexShader: CopyShader.vertexShader, fragmentShader: CopyShader.fragmentShader, depthTest: false, depthWrite: false }));
  }
  setSize(w, h) { sceneTarget.setSize(w, h); }
  render(r, writeBuffer, readBuffer) {
    r.setRenderTarget(sceneTarget); r.clear(); r.render(scene, camera);
    this.quad.material.uniforms.tDiffuse.value = sceneTarget.texture; r.setRenderTarget(readBuffer); this.quad.render(r);
  }
}
const composer = new EffectComposer(renderer);
composer.addPass(new SceneMSAAPass());
// contact shadows in folds, pockets and under parts. Depth comes from the frame just drawn (particles, sprites,
// see-through shells and the floor write no depth, so they stay out of it); normals are rebuilt from depth.
const gtao = new GTAOPass(scene, camera, 1, 1);
gtao.setGBuffer(sceneTarget.depthTexture);
gtao.blendIntensity = 1.0;
gtao.updateGtaoMaterial({ radius: 0.05, distanceExponent: 1.4, thickness: 1.0, scale: 1.15, samples: 12 });
gtao.updatePdMaterial({ lumaPhi: 10, depthPhi: 2, normalPhi: 3, radius: 5, rings: 2, samples: 8 });
// AO depends only on the camera and the geometry (particles and glows write no depth), so while neither moves the
// last result is blended again instead of recomputed. `geomVersion` is bumped wherever parts move or change.
let geomVersion = 0; const aoStats = { full: 0 };
const aoCam = new Float64Array(33).fill(NaN);
const gtaoRender = gtao.render.bind(gtao);
gtao.render = function (renderer, writeBuffer, readBuffer, dt, mask) {
  const e = camera.matrixWorld.elements, pr = camera.projectionMatrix.elements;
  let same = aoCam[32] === geomVersion;
  for (let i = 0; i < 16 && same; i++) if (aoCam[i] !== e[i] || aoCam[16 + i] !== pr[i]) same = false;
  if (same) {
    this.copyMaterial.uniforms.tDiffuse.value = readBuffer.texture; this.copyMaterial.blending = THREE.NoBlending;
    this.renderPass(renderer, this.copyMaterial, writeBuffer);
    this.blendMaterial.uniforms.intensity.value = this.blendIntensity; this.blendMaterial.uniforms.tDiffuse.value = this.pdRenderTarget.texture;
    this.renderPass(renderer, this.blendMaterial, writeBuffer);
    return;
  }
  aoStats.full++;
  for (let i = 0; i < 16; i++) { aoCam[i] = e[i]; aoCam[16 + i] = pr[i]; } aoCam[32] = geomVersion;
  gtaoRender(renderer, writeBuffer, readBuffer, dt, mask);
};
const gtaoSetSize = gtao.setSize.bind(gtao);
gtao.setSize = (w, h) => { gtaoSetSize(Math.max(1, Math.round(w / 2)), Math.max(1, Math.round(h / 2))); geomVersion++; };   // AO is soft: half resolution is plenty
composer.addPass(gtao);
// Bloom blurs every pixel into its neighbours, so a single NaN / negative / infinite pixel becomes a flickering
// black block. Clean the HDR frame before bloom; #nan in the URL paints such pixels instead (magenta NaN,
// cyan negative, yellow huge) for diagnosis.
const sanitize = new ShaderPass({
  uniforms: { tDiffuse: { value: null }, uDebug: { value: location.hash.includes("nan") ? 1 : 0 } },
  vertexShader: "varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0); }",
  fragmentShader: `uniform sampler2D tDiffuse; uniform float uDebug; varying vec2 vUv;
    void main(){ vec4 c = texture2D(tDiffuse, vUv);
      bool bad = any(isnan(c)) || any(isinf(c)); bool neg = any(lessThan(c.rgb, vec3(0.0))); bool big = any(greaterThan(c.rgb, vec3(64.0)));
      if (uDebug > 0.5) { gl_FragColor = bad ? vec4(1.0,0.0,1.0,1.0)*8.0 : neg ? vec4(0.0,1.0,1.0,1.0)*8.0 : big ? vec4(1.0,1.0,0.0,1.0)*8.0 : c; return; }
      gl_FragColor = bad ? vec4(0.0) : clamp(c, 0.0, 64.0); }`,
});
composer.addPass(sanitize);
if (location.hash.includes("nan")) setTimeout(() => (bloom.enabled = false));
const bloom = new UnrealBloomPass(new THREE.Vector2(256, 256), 0.6, 0.5, 1.0);
composer.addPass(bloom);
composer.addPass(new OutputPass());

// layout insets so the model sits in the free area between the panels
const insets = { l: 0, r: 0, t: 0, b: 0 };
function resize() {
  for (const L of labelEls.values()) L.bw = 0;   // re-measure label widths (font size changes at narrow widths)
  const w = innerWidth, h = innerHeight;
  renderer.setSize(w, h, false); composer.setSize(w, h);
  bloom.resolution.set(w / 2, h / 2);
  camera.aspect = w / h;
  const dx = (insets.l - insets.r) / 2, dy = (insets.t - insets.b) / 2;
  if (dx || dy) camera.setViewOffset(w, h, -dx, -dy, w, h); else camera.clearViewOffset();
  camera.updateProjectionMatrix();
  pointsUniformPR.value = renderer.getPixelRatio();
}
function updateInsets() {
  const wide = innerWidth > 900;
  const touring = document.body.classList.contains("touring");
  insets.l = !wide ? 0 : touring ? $("#tour").offsetWidth + 16 : !$("#modes").hidden ? $("#modes").offsetWidth + 16 : 0;
  insets.r = wide && !$("#dossier").hidden ? $("#dossier").offsetWidth + 16 : 0;
  insets.t = Math.max(56, Math.round($("header").getBoundingClientRect().bottom) + 4);   // the header wraps on phones
  insets.b = !$("#dock").classList.contains("min") ? $("#dock").offsetHeight + 16 : 40;
  resize();
}
addEventListener("resize", updateInsets);

// ======================================================================================== visual helpers
function radialTexture(stops, size = 256) {
  const c = document.createElement("canvas"); c.width = c.height = size;
  const g = c.getContext("2d"), grd = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  for (const [o, col] of stops) grd.addColorStop(o, col);
  g.fillStyle = grd; g.fillRect(0, 0, size, size);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
let formGhost = null;
const xrayMat = new THREE.ShaderMaterial({
  uniforms: { uColor: { value: new THREE.Color(0x4fd1e8) }, uOpacity: { value: 0.55 } },
  vertexShader: `varying vec3 vN; varying vec3 vV;
    void main(){ vec4 mv = modelViewMatrix*vec4(position,1.0); vN = normalMatrix*normal; vV = -mv.xyz; gl_Position = projectionMatrix*mv; }`,
  fragmentShader: `uniform vec3 uColor; uniform float uOpacity; varying vec3 vN; varying vec3 vV;
    void main(){ float ln = length(vN); vec3 n = ln > 1e-6 ? vN / ln : vec3(0.0, 0.0, 1.0);
      float f = pow(clamp(1.0 - abs(dot(n, normalize(vV))), 0.0, 1.0), 2.4);   // clamp: pow() of a tiny negative is NaN
      gl_FragColor = vec4(uColor*(0.25 + 1.3*f), uOpacity*(0.05 + 0.75*f)); }`,
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide,
});

formGhost = xrayMat.clone(); formGhost.uniforms.uColor.value = new THREE.Color(0xb8c4d4); formGhost.uniforms.uOpacity.value = 0.16;
const redGhost = xrayMat.clone(); redGhost.uniforms.uColor.value = new THREE.Color(0xff3a3a); redGhost.uniforms.uOpacity.value = 0.75;

// Base materials (the vest GLBs carry none). Real-world finishes: ripstop fabric with sheen, FDM-printed PETG,
// black PVC leads, white foam electrodes, aluminium and nickel. `name` refines a part (bindings, zips, studs…).
const TEX = {};
const tex = (k, make) => TEX[k] || (TEX[k] = make());
const N2 = (v) => new THREE.Vector2(v, v);
const phys = (o) => new THREE.MeshPhysicalMaterial({ envMapIntensity: 0.9, ...o });
const std = (o) => new THREE.MeshStandardMaterial({ envMapIntensity: 0.9, ...o });
const fabric = (color, sheenColor) => phys({ color, roughness: 0.86, sheen: 0.7, sheenColor, sheenRoughness: 0.5, normalMap: tex("rip", ripstopNormal), normalScale: N2(0.5), envMapIntensity: 0.6 });
const printedMat = (color = 0xd3d4cf) => phys({ color, roughness: 0.5, normalMap: tex("print", printNormal), normalScale: N2(0.22) });
const metal = (color, roughness = 0.3) => std({ color, metalness: 1, roughness });
const plastic = (color, roughness = 0.45) => std({ color, roughness });
const soldermask = (color) => phys({ color, roughness: 0.38, clearcoat: 0.5, clearcoatRoughness: 0.25 });
const foil = () => std({ color: 0xbfc3c9, metalness: 0.75, roughness: 0.4 });
const UV_TILE = { rip: 0.024, print: 0.009, web: 0.025, oak: 0.55 };
function matFor(key, name = "") {
  switch (key) {
    case "vest":
      if (/zip_puller/.test(name)) return metal(0x8f959d, 0.28);
      if (/zip_/.test(name)) return plastic(0x141619, 0.35);
      if (/binding/.test(name)) return fabric(0x2a2f37, 0x5a6472);
      if (/carrier_patch/.test(name)) return fabric(0x181b20, 0x434b56);
      return fabric(0x1c2027, 0x4c5562);
    case "pockets": return fabric(0x252a31, 0x56606c);
    case "tunnels": return /eyelet/.test(name) ? metal(0xaab0b7, 0.25) : fabric(0x20242b, 0x4c5562);
    case "webbing":
      if (/ladderlock|adjuster/.test(name)) return plastic(0x131417, 0.38);
      return phys({ color: 0x17191c, roughness: 0.7, sheen: 0.8, sheenColor: 0x5b6470, sheenRoughness: 0.4, normalMap: tex("web", webbingNormal), normalScale: N2(0.5) });
    case "panel": return metal(0xc5c9ce, 0.32);
    case "battery": return foil();
    case "xiao":
      if (/shield|usb/.test(name)) return metal(0xc3c8ce, 0.26);
      if (/hdr/.test(name)) return plastic(0x101113, 0.5);
      return soldermask(0x14202f);
    case "c_board":                       // BITalino (r)evolution Board Kit: white ENIG panel, gold UC-E6 sockets
      if (/battery/.test(name)) return foil();
      if (/pcb/.test(name)) return soldermask(0xf3f3ef);
      if (/C_core/.test(name)) return soldermask(0xf0f0ec);
      if (/C_ble/.test(name)) return metal(0xc6cad0, 0.34);
      if (/led/.test(name)) return plastic(0xf3f3f3, 0.3);
      if (/sock/.test(name)) return metal(0xd9b55e, 0.3);
      if (/usb/.test(name)) return metal(0xc3c8ce, 0.26);
      if (/pwr_conn/.test(name)) return plastic(0xf1eee6, 0.55);
      return plastic(0x141518, 0.4);
    case "unit_a": return printedMat(0xb3121a);
    case "phone": return phys({ color: 0x0b0c0f, roughness: 0.22, metalness: 0.3, clearcoat: 1, clearcoatRoughness: 0.05 });
    case "ecg_b": case "ecg_c":
      if (/^electrode_.*stud/.test(name)) return metal(0xd0d4d9, 0.22);
      if (/^electrode_/.test(name)) return std({ color: 0xf0efe9, roughness: 0.93 });          // foam pad
      if (/tongue/.test(name)) return metal(0xc8ccd2, 0.3);
      if (/^ecg_sensor/.test(name)) return printedMat(0xb3121a);                            // PLUX ECG sensor: red printed box
      return plastic(0xe9e9e5, 0.45);                                                       // PLUX leads and snaps are white
    case "ppg": return plastic(0x121315, 0.45);
    case "W01": case "W06": case "W_misc":
      if (/tongue/.test(name)) return metal(0xc8ccd2, 0.3);
      if (/waterproof/.test(name)) return plastic(0x111214, 0.4);
      if (/conn/.test(name)) return plastic(0xe8e1cf, 0.55);                                 // JST housings
      if (/^W(09|13)/.test(name)) return plastic(0xe9e9e5, 0.45);                            // PLUX UC-E6 and PulseSensor cables are white
      return plastic(0x141518, 0.42);                                                        // black PVC sheath
    case "thermocouples": return metal(0xb9965f, 0.35);
    case "ref_cells": return phys({ color: 0x101a30, roughness: 0.35, metalness: 0.2, clearcoat: 1, clearcoatRoughness: 0.05 });
    case "bench_table": return std({ map: tex("oak", oakTexture), roughness: 0.55 });
    case "bench_stand": return /^bolt/.test(name) ? metal(0xb4bac1, 0.3) : printedMat();
    case "bench_cover": return std({ color: 0x20242a, roughness: 0.9, transparent: true, opacity: 0.5 });
    default: return PARTS[key] && PARTS[key].cat === "printed" ? printedMat() : plastic(0x9aa4b0, 0.5);
  }
}
// shadows, plus box-projected UVs wherever a material carries a texture
function prepMesh(o) {
  o.castShadow = true; o.receiveShadow = true;
  if (!o.geometry.attributes.normal) o.geometry.computeVertexNormals();
  const m = o.material;
  if ((m.normalMap || m.map) && !o.geometry.attributes.uv) {
    const k = m.normalMap === TEX.rip ? "rip" : m.normalMap === TEX.print ? "print" : m.normalMap === TEX.web ? "web" : "oak";
    addBoxUV(o, UV_TILE[k]);
  }
}
// The panel export is one mesh (frame, backsheet, junction box and a stub of its lead) plus a glass slab.
// Work in the glass's own frame: u along the long side, v across, n out of the glass.
function dressPanel(panel, glass) {
  const gp = glass.geometry.attributes.position, idx = glass.geometry.index, mw = glass.matrixWorld;
  const P = (i) => new THREE.Vector3().fromBufferAttribute(gp, i).applyMatrix4(mw);
  const area = new THREE.Vector3(), tri = (a, b, c) => new THREE.Vector3().subVectors(b, a).cross(new THREE.Vector3().subVectors(c, a));
  const nTri = idx ? idx.count / 3 : gp.count / 3, best = [];
  for (let t = 0; t < nTri; t++) {
    const [a, b, c] = [0, 1, 2].map((k) => P(idx ? idx.getX(t * 3 + k) : t * 3 + k)), n = tri(a, b, c);
    if (n.lengthSq() > 0) best.push(n);
  }
  best.sort((x, y) => y.lengthSq() - x.lengthSq());
  const n = best[0].clone().normalize();
  const gc = new THREE.Box3().setFromObject(glass).getCenter(new THREE.Vector3());
  const pc = new THREE.Box3().setFromObject(panel).getCenter(new THREE.Vector3());
  if (n.dot(new THREE.Vector3().subVectors(gc, pc)) < 0) n.negate();
  const u = new THREE.Vector3(1, 0, 0).addScaledVector(n, -n.x).normalize(), v = new THREE.Vector3().crossVectors(n, u);
  const loc = (w) => { const d = new THREE.Vector3().subVectors(w, gc); return [d.dot(u), d.dot(v), d.dot(n)]; };
  let gw = 0, gh = 0; for (let i = 0; i < gp.count; i++) { const [a, b] = loc(P(i)); gw = Math.max(gw, Math.abs(a)); gh = Math.max(gh, Math.abs(b)); }
  // glass: planar UVs and the cell texture under a clear coat
  const uv = new Float32Array(gp.count * 2);
  for (let i = 0; i < gp.count; i++) { const [a, b] = loc(P(i)); uv[i * 2] = (a + gw) / (2 * gw); uv[i * 2 + 1] = (b + gh) / (2 * gh); }
  glass.geometry.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  glass.material = phys({ map: cellsTexture(gw * 2, gh * 2), roughness: 0.4, metalness: 0.15, clearcoat: 1, clearcoatRoughness: 0.03, envMapIntensity: 1.3 });
  // frame / backsheet / junction box / lead, from where each triangle sits relative to the glass
  const fw = gw + 0.0012, fh = gh + 0.0012, pm = panel.matrixWorld, w = new THREE.Vector3();
  const pp = panel.geometry.attributes.position; let cu = 0, cn = 0;
  for (let i = 0; i < pp.count; i += 7) { const [a, b] = loc(w.fromBufferAttribute(pp, i).applyMatrix4(pm)); if (Math.abs(b) > fh + 0.002) { cu += a; cn++; } }
  const leadU = cn ? cu / cn : 0.0195;   // the lead leaves the junction box off-centre; find which side in this pose
  return splitMesh(panel, (c) => {
    const [a, b, d] = loc(w.copy(c).applyMatrix4(pm)), edge = Math.min(fw - Math.abs(a), fh - Math.abs(b));
    if (edge < -0.0004) return "lead";
    if (Math.abs(a - leadU) < 0.0036 && d < -0.004 && d > -0.0105) return "lead";
    if (edge < 0.0085) return "frame";
    if (d < -0.0103) return "jbox";
    return "back";
  }, { frame: metal(0xc5c9ce, 0.32), back: std({ color: 0xeceeef, roughness: 0.6 }), jbox: plastic(0x141516, 0.5), lead: plastic(0x121315, 0.42) });
}
// ------------------------------------------------------------------ real models in place of the stand-ins
// PMB-H and LIB come from the KiCad exports, the BITalino Core from the model traced from PLUX's manual, the HeartBIT
// case from BITalinoWorld's print files. Each is placed by a rigid fit to the stand-in (≤ 0.2 mm, models/board_align.json).
function parseBoard(name) { const src = (window.SV_BOARDS || {})[name]; return src ? new Promise((res, rej) => loader.parse(b64(src), "", res, rej)) : null; }
function mergeByMaterial(root, pick) {
  root.updateMatrixWorld(true);
  const inv = root.matrixWorld.clone().invert(), rel = new THREE.Matrix4(), groups = new Map();
  root.traverse((o) => {
    if (!o.isMesh) return; const p = pick(o); if (!p) return;
    if (!groups.has(p.key)) groups.set(p.key, { p, geos: [] });
    groups.get(p.key).geos.push(plainGeometry(o.geometry, rel.multiplyMatrices(inv, o.matrixWorld)));
  });
  const out = [];
  for (const { p, geos } of groups.values()) {
    let g = mergeGeometries(geos, false); geos.forEach((x) => x.dispose());
    if (p.crease) { const c = toCreasedNormals(g, Math.PI / 6); g.dispose(); g = c; }   // print-file meshes: keep hard edges hard
    if (p.uv) p.uv(g);
    const m = new THREE.Mesh(g, p.make()); m.name = p.key; if (p.shell) m.userData.shell = true; if (p.xray) m.userData.xray = p.xray; out.push(m);
  }
  return out;
}
const planarXZ = (x0, w, z0, h) => (g) => {
  const pos = g.attributes.position, uv = new Float32Array(pos.count * 2);
  for (let i = 0; i < pos.count; i++) { uv[i * 2] = (pos.getX(i) - x0) / w; uv[i * 2 + 1] = (pos.getZ(i) - z0) / h; }
  g.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
};
// does this face mesh point along +y (the component side) in its model's frame?
function faceUp(o) {
  const nr = o.geometry.attributes.normal; if (!nr) return false;
  const q = new THREE.Quaternion(); o.getWorldQuaternion(q); const v = new THREE.Vector3();
  let sy = 0; for (let i = 0; i < nr.count; i++) sy += v.fromBufferAttribute(nr, i).applyQuaternion(q).normalize().y;
  return sy / nr.count > 0.6;
}
const kicadPick = (o) => { const m = o.material; return { key: `${m.color.getHexString()}|${m.opacity}|${m.metalness}|${m.roughness}`, make: () => boardMaterial(m) }; };
// BITalino Core parts by name (sockets are the unnamed boxes); the PCB and the BT module get their artwork
const corePickFor = (variant) => (o) => {
  // the traced model stores each part as a group of face meshes: the part's name is on the parent node
  const n = /^casing/.test(o.name) ? o.name : (o.parent && o.parent.name) || "";
  if (variant === "BLE" && n === "bt_module") return null;       // Core BLE has no HC-05 (its module is added separately)
  if (/^casing/.test(n)) return null;
  // each CAD face is its own mesh: the component face (+y) carries the artwork, the underside its own, edges plain
  const up = faceUp(o);
  if (n === "pcb") return up ? { key: "pcb", make: () => phys({ map: tex(`bitcore_${variant}`, () => bitalinoCoreTexture(variant)), roughness: 0.42, clearcoat: 0.35, clearcoatRoughness: 0.3 }), uv: planarXZ(-0.028, 0.056, -0.0325, 0.065) }
    : { key: "pcb_under", make: () => phys({ map: tex("bitcore_b", bitalinoCoreBottomTexture), roughness: 0.42, clearcoat: 0.35, clearcoatRoughness: 0.3 }), uv: planarXZ(-0.028, 0.056, -0.0325, 0.065) };
  if (n === "bt_module") return up ? { key: "bt", make: () => phys({ map: tex("bt", btModuleTexture), roughness: 0.45, clearcoat: 0.3, clearcoatRoughness: 0.3 }), uv: planarXZ(-0.0171, 0.0139, 0.005, 0.0275) }
    : { key: "bt_edge", make: () => soldermask(0x1e7a3c) };
  if (n === "mcu") return { key: "mcu", make: () => plastic(0x15161a, 0.5) };
  if (n === "micro_usb") return { key: "usb", make: () => metal(0xc9cdd2, 0.25) };
  if (n === "switch") return { key: "sw", make: () => plastic(0x18191c, 0.4) };
  if (n === "bat_jst") return { key: "jst", make: () => plastic(0xf2efe6, 0.55) };
  return null;                                                    // sockets: replaced by the detailed UC-E6 model
};
// UC-E6 receptacle as on the user's boards (photos): gold shell with the stamped arch-shaped spring on top, trapezoid mouth
// with a dark tongue, five fine solder pins behind and two side legs. Size from the official HeartBIT case, whose pockets
// hold it: 6.5 × 6.5 mm pockets ending 0.5 mm past the board edge, windows 6 × 2.4 mm → shell 6.0 long × 6.0 wide × 3.0 high.
// Canonical frame: x = out of the board edge (front face at x = 0), y = up from the board top, z = across; placed by
// `placeAt(out, up, pos)`; returns geometries grouped by material.
function uce6(groups, M) {
  const add = (k, g) => { g.applyMatrix4(M); (groups[k] ||= []).push(g.index ? g.toNonIndexed() : g); };
  const box = (k, x0, x1, y0, y1, z0, z1, r = 0) => { const g = r ? new RoundedBoxGeometry(x1 - x0, y1 - y0, z1 - z0, 1, r) : new THREE.BoxGeometry(x1 - x0, y1 - y0, z1 - z0); g.translate((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2); add(k, g); };
  const mm = 0.001;
  box("gold", -6.0 * mm, 0, 0, 3.0 * mm, -3.0 * mm, 3.0 * mm, 0.3 * mm);                             // shell
  for (const z of [-1.4, 1.4]) box("gold", -5.0 * mm, -1.6 * mm, 3.0 * mm, 3.11 * mm, (z - 0.2) * mm, (z + 0.2) * mm);   // spring legs
  box("gold", -5.35 * mm, -5.0 * mm, 3.0 * mm, 3.11 * mm, -1.6 * mm, 1.6 * mm);                      // arch top
  box("gold", -3.2 * mm, -2.9 * mm, 3.0 * mm, 3.11 * mm, -1.2 * mm, 1.2 * mm);                       // cross bar
  for (let i = 0; i < 5; i++) box("pin", -6.9 * mm, -5.8 * mm, 0, 0.18 * mm, (-1.6 + i * 0.8 - 0.15) * mm, (-1.6 + i * 0.8 + 0.15) * mm);
  for (const z of [-3.1, 3.1]) box("gold", -4.6 * mm, -2.6 * mm, 0, 0.9 * mm, (z - 0.1) * mm, (z + 0.1) * mm);   // side legs
  const sh = new THREE.Shape(); sh.moveTo(-2.5 * mm, 2.55 * mm); sh.lineTo(2.5 * mm, 2.55 * mm); sh.lineTo(1.8 * mm, 0.5 * mm); sh.lineTo(-1.8 * mm, 0.5 * mm); sh.closePath();
  const mouth = new THREE.ExtrudeGeometry(sh, { depth: 0.9 * mm, bevelEnabled: false }); mouth.rotateY(Math.PI / 2); mouth.translate(-0.88 * mm, 0, 0); add("mouth", mouth);   // trapezoid opening
  box("tongue", -0.95 * mm, -0.15 * mm, 1.2 * mm, 1.7 * mm, -1.7 * mm, 1.7 * mm);
}
const uce6Mats = { gold: () => metal(0xe8c76c, 0.22), pin: () => metal(0xd9dde2, 0.3), mouth: () => plastic(0x0b0c0e, 0.7), tongue: () => plastic(0x3a3c40, 0.5) };
const placeAt = (out, up, pos) => new THREE.Matrix4().makeBasis(out, up, new THREE.Vector3().crossVectors(out, up)).setPosition(pos);
function meshesFromGroups(groups, mats, prefix) { return Object.entries(groups).map(([k, list]) => { const m = new THREE.Mesh(mergeGeometries(list, false), mats[k]()); m.name = `${prefix}_${k}`; return m; }); }
// the Core's ten sockets in its traced frame: board top y = 1.6 mm, strips' outer edges at x = ±28 mm, fronts 0.4 mm proud
function coreSockets() {
  const g = {};
  for (const [, sd, z] of CORE_SOCKETS) uce6(g, placeAt(new THREE.Vector3(sd, 0, 0), new THREE.Vector3(0, 1, 0), new THREE.Vector3(sd * 0.0284, 0.0016, z)));
  return meshesFromGroups(g, uce6Mats, "uce6");
}
// the UC-E6 sockets' openings (black) on the outer faces of the Core's two strips
function coreSocketMouths() {
  const geos = [];
  for (const x of [-0.0282, 0.0282]) for (const z of [-0.0273, -0.0139, -0.0004, 0.0131, 0.0266]) { const g = new THREE.BoxGeometry(0.0004, 0.0021, 0.0050); g.translate(x, 0.00335, z); geos.push(g); }
  return new THREE.Mesh(mergeGeometries(geos, false), plastic(0x0d0e10, 0.6));
}
// Core BLE's radio: a blue module at the far end of the old HC-05 footprint (figure x 12–25, y 49–64 mm), shield can on top
function bleModuleMeshes() {
  const X = (mm) => mm / 1000 - 0.028, Z = (mm) => mm / 1000 - 0.0325, top = 0.0016;
  const pcb = new THREE.Mesh(new RoundedBoxGeometry(0.0130, 0.0009, 0.0152, 1, 0.0003), soldermask(0x2456a8));
  pcb.position.set(X(18.5), top + 0.00045, Z(56.4));
  const canG = new RoundedBoxGeometry(0.011, 0.0019, 0.011, 1, 0.0003);
  const cp = canG.attributes.position, uv = new Float32Array(cp.count * 2);
  for (let i = 0; i < cp.count; i++) { uv[i * 2] = (cp.getX(i) + 0.0055) / 0.011; uv[i * 2 + 1] = (cp.getZ(i) + 0.0055) / 0.011; }
  canG.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  const can = new THREE.Mesh(canG, std({ map: tex("blecan", bleCanTexture), metalness: 0.55, roughness: 0.35 }));
  can.position.set(X(18.5), top + 0.0009 + 0.00095, Z(58.3));
  return [pcb, can];
}
// ------------------------------------------------------------------ connection ports (for placement and checks)
// BITalino Core sockets in the traced model's frame (PLUX manual Fig. 8): left column I1 A4 A3 A2 A1, right O1 O2/I2 PWM A6 A5
const CORE_SOCKETS = [];
[5.2, 18.6, 32.1, 45.6, 59.1].forEach((y, i) => { const z = y / 1000 - 0.0325; CORE_SOCKETS.push([["I1", "A4", "A3", "A2", "A1"][i], -1, z], [["O1", "O2/I2", "PWM", "A6", "A5"][i], 1, z]); });
function addCorePorts(sc, tag, M) {
  for (const [nm, sd, z] of CORE_SOCKETS) sc.ports[`${tag}:${nm}`] = { at: new THREE.Vector3(sd * 0.0279, 0.0032, z).applyMatrix4(M),
    mouth: new THREE.Vector3(sd * 0.0284, 0.0032, z).applyMatrix4(M), out: new THREE.Vector3(sd, 0, 0).applyMatrix3(new THREE.Matrix3().setFromMatrix4(M)).normalize() };
  sc.ports[`${tag}:BAT`] = { at: new THREE.Vector3(0.0084, 0.004, 0.0167).applyMatrix4(M) };
}
function addKicadPorts(sc, tag, root, M) {
  root.updateMatrixWorld(true);
  root.traverse((o) => { if (/^J\d+$/.test(o.name)) sc.ports[`${tag}:${o.name}`] = { at: new THREE.Box3().setFromObject(o).getCenter(new THREE.Vector3()).applyMatrix4(M) }; });
}
// The Core B stand-in was mounted parts-to-body; the cables say otherwise: with the board turned 180° about its long axis
// the battery lead meets the JST (6.7 mm), the sync lead's tongue sits in I1 and the ECG lead's in A2.
const FLIP_LONG = new THREE.Matrix4().set(-1, 0, 0, 0, 0, -1, 0, 0.0016, 0, 0, 1, 0, 0, 0, 0, 1);
// Move a plug (body + tongue) into a socket and bend the cable's last few centimetres after it.
function seatPlug(sc, cable, plug, tongue, port) {
  const find = (nm) => sc.meshes.find((m) => m.userData.srcName === nm) || null;
  const P = find(plug), T = find(tongue), C = find(cable); if (!P || !T || !port.mouth) return null;
  const c = (m) => new THREE.Box3().setFromObject(m).getCenter(new THREE.Vector3());
  const P0 = c(P), T0 = c(T), len = P0.distanceTo(T0), a0 = T0.clone().sub(P0).normalize(), a1 = port.out.clone().negate();
  const T1 = port.mouth.clone().addScaledVector(a1, 0.0028), P1 = T1.clone().addScaledVector(a1, -len);
  const R = new THREE.Matrix4().makeRotationFromQuaternion(new THREE.Quaternion().setFromUnitVectors(a0, a1));
  const X = new THREE.Matrix4().makeTranslation(P1.x, P1.y, P1.z).multiply(R).multiply(new THREE.Matrix4().makeTranslation(-P0.x, -P0.y, -P0.z));
  for (const m of [P, T]) moveMesh(m, X);
  if (C) bendCable(C, P0, P1.clone().sub(P0));
  return P1.distanceTo(P0);
}
function moveMesh(m, X) { const w = X.clone().multiply(m.matrixWorld), loc = m.parent.matrixWorld.clone().invert().multiply(w); loc.decompose(m.position, m.quaternion, m.scale); m.userData.orig = m.position.clone(); m.updateMatrixWorld(true); }
// smooth bend: full displacement D at the plug end P0, fading out over 12 cm of cable
function bendCable(C, P0, D) {
  const g = C.geometry, pos = g.attributes.position, mw = C.matrixWorld, inv = mw.clone().invert(), out = new Float32Array(pos.count * 3), v = new THREE.Vector3();
  for (let i = 0; i < pos.count; i++) { v.fromBufferAttribute(pos, i).applyMatrix4(mw); const d = v.distanceTo(P0), w = d < 0.012 ? 1 : d > 0.12 ? 0 : 1 - THREE.MathUtils.smoothstep(d, 0.012, 0.12); v.addScaledVector(D, w).applyMatrix4(inv); out.set([v.x, v.y, v.z], i * 3); }
  g.setAttribute("position", new THREE.BufferAttribute(out, 3)); g.computeVertexNormals(); g.computeBoundingBox(); g.computeBoundingSphere(); g.computeBoundsTree();
}
// move a plug without a tongue (the battery JST) by D, cable bending after it
function shiftPlug(sc, cable, plug, D) {
  const find = (nm) => sc.meshes.find((m) => m.userData.srcName === nm) || null;
  const P = find(plug), C = find(cable); if (!P) return null;
  const P0 = new THREE.Box3().setFromObject(P).getCenter(new THREE.Vector3());
  moveMesh(P, new THREE.Matrix4().makeTranslation(D.x, D.y, D.z)); if (C) bendCable(C, P0, D);
  return D.length();
}
async function upgradeBoards(sc) {
  if (sc.upgraded || !window.SV_BOARDS || !window.SV_ALIGN || sc.name === "boards") return;
  sc.upgraded = true; sc.ports = sc.ports || {};
  const A = window.SV_ALIGN, jobs = sc.name === "worn"
    ? [["pmbh", "pmbh.mo.glb", A.pmbh_worn, kicadPick], ["lib", "libb.mo.glb", A.libb_worn, kicadPick], ["core_b", "core.mo.glb", A.core_worn, corePickFor("BLE")], ["unit_a", null, A.heartbit_worn, null]]
    : [["pmbh", "pmbh.mo.glb", A.pmbh_bench, kicadPick]];
  for (const [key, file, matrix, pick] of jobs) {
    const part = sc.parts[key]; if (!part || !matrix) continue;
    const holder = new THREE.Group(); holder.matrixAutoUpdate = false; holder.matrix.fromArray(matrix); sc.root.add(holder);
    if (key === "core_b" && !location.hash.includes("noflip")) holder.matrix.multiply(FLIP_LONG);
    let meshes;
    if (key === "unit_a") {
      const hb = await parseBoard("heartbit.mo.glb"), core = await parseBoard("core.mo.glb");
      // the user's HeartBIT case: white tray, red lid (the lid's snap tab is part of the official print file)
      meshes = mergeByMaterial(hb.scene, (o) => (o.name === "casing_lid" ? { key: "lid", make: () => printedMat(0xb3121a), shell: true, crease: true, xray: redGhost }
        : o.name === "casing_tray" ? { key: "tray", make: () => printedMat(0xe9e9e5), shell: true, crease: true } : null));
      const up = new THREE.Vector3(0, 1, 0).applyMatrix3(new THREE.Matrix3().setFromMatrix4(holder.matrix)).normalize();
      for (const m of meshes) if (m.name === "lid") m.userData.explodeExtra = up.multiplyScalar(0.05).toArray();   // explode lifts the lid off
      const inner = new THREE.Group(); inner.matrixAutoUpdate = false; inner.matrix.fromArray(A.core_in_hb); holder.add(inner);
      const alt = (location.hash.match(/-a(\d)/) || [])[1];
      // the traced Core sat 2 mm low in the case: raised 2.0 mm, all ten sockets face the case windows (checked: fitCheck)
      const raise = +((location.hash.match(/-raise([\d.]+)/) || [])[1] || 2.0) / 1000;
      inner.matrix.premultiply(new THREE.Matrix4().makeTranslation(0, raise, 0));
      // and 0.68 mm along the board: the case's ten pockets sit −0.15…+1.45 mm from the manual's socket positions (pitch
      // 13.85 vs 13.45 mm, trace tolerance), mean +0.68 mm — this centres them (checked: fitCheck)
      inner.matrix.multiply(new THREE.Matrix4().makeTranslation(0, 0, +((location.hash.match(/-hbz(-?[\d.]+)/) || [])[1] || 0.68) / 1000));
      if (alt) inner.matrix.multiply([new THREE.Matrix4(), new THREE.Matrix4().set(-1, 0, 0, 0, 0, 1, 0, 0, 0, 0, -1, 0, 0, 0, 0, 1), FLIP_LONG, new THREE.Matrix4().set(1, 0, 0, 0, 0, -1, 0, 0.0016, 0, 0, -1, 0, 0, 0, 0, 1)][+alt]);
      for (const m of mergeByMaterial(core.scene, corePickFor("BT"))) inner.add(m);
      coreSockets().forEach((m) => inner.add(m));
      holder.updateMatrixWorld(true); addCorePorts(sc, "A", inner.matrixWorld);
    } else {
      const gl = await parseBoard(file);
      holder.updateMatrixWorld(true);
      if (pick === kicadPick) addKicadPorts(sc, key === "lib" ? "LIB" : "PMB-H", gl.scene, holder.matrixWorld);
      meshes = mergeByMaterial(gl.scene, pick);
      if (key === "core_b") { meshes.push(...bleModuleMeshes(), ...coreSockets()); addCorePorts(sc, "B", holder.matrixWorld); }
    }
    meshes.forEach((m) => holder.add(m));
    // retire the stand-in, register the real parts under the same key (labels, dossier, explode keep working)
    for (const m of part.meshes) { m.parent && m.parent.remove(m); m.geometry.dispose(); }
    const old = new Set(part.meshes); sc.meshes = sc.meshes.filter((m) => !old.has(m)); part.meshes = [];
    holder.updateMatrixWorld(true);
    holder.traverse((o) => { if (o.isMesh) { prepMesh(o); registerMesh(sc, o, key); } });
  }
  // the PulseSensor lead (W13) ended at the case's notched edge, where the Core has no socket: seat it in an analog input
  // of unit A (any of A1–A6 works for PPG; OpenSignals is set to match)
  if (sc.name === "worn" && sc.ports["A:A1"]) {
    const plug = sc.meshes.find((m) => m.userData.srcName === "W13_conn0");
    if (plug) {
      const p0 = new THREE.Box3().setFromObject(plug).getCenter(new THREE.Vector3());
      // the lead arrives from the ear above: use an analog socket in the row that faces up, nearest to where the lead ends
      const up = ["A1", "A2", "A3", "A4", "A5", "A6"].filter((k) => sc.ports[`A:${k}`].out.y > 0.3);
      const best = (up.length ? up : ["A1", "A2", "A3", "A4", "A5", "A6"]).map((k) => [k, sc.ports[`A:${k}`].mouth.distanceTo(p0)]).sort((a, b) => a[1] - b[1])[0];
      sc.ppgPort = best[0]; sc.ppgMove = seatPlug(sc, "W13_pulsesensor", "W13_conn0", "W13_conn0_tongue", sc.ports[`A:${best[0]}`]);
    }
  }
  if (active === sc) { setXray(ui.xray); applyExplode(); buildLabels(); }
  renderer.shadowMap.needsUpdate = true; geomVersion++;
}
// Board Kit (unit C): the panel of break-away modules from the user's photo, laid out around the positions the vest design
// fixed for its parts (the electrode lead, battery lead and case windows were made for them): every socket, the battery
// JST, USB, switch, BLE, MCU, button, LED, LUX and ACC sits exactly on its anchor; modules, tabs and spine are built around.
function buildBoardKit(sc, pcb, parts) {
  [pcb, ...parts].forEach((c) => c.updateMatrixWorld(true));
  // The stand-in board is a box whose geometry is baked tilted (its node has no rotation), so take the board plane from
  // the geometry itself: normal of its largest face, long edge within that face, extents measured along those axes.
  const gp = pcb.geometry.attributes.position, gi = pcb.geometry.index, V = [];
  for (let i = 0; i < gp.count; i++) V.push(new THREE.Vector3().fromBufferAttribute(gp, i).applyMatrix4(pcb.matrixWorld));
  let nBest = null, aBest = 0;
  for (let t = 0; t < (gi ? gi.count : gp.count) / 3; t++) {
    const [a, b, c] = [0, 1, 2].map((k) => V[gi ? gi.getX(t * 3 + k) : t * 3 + k]), cr = new THREE.Vector3().subVectors(b, a).cross(new THREE.Vector3().subVectors(c, a));
    if (cr.length() > aBest) { aBest = cr.length(); nBest = cr.normalize(); }
  }
  // the box's own edge directions: from one corner, its three nearest distinct corners (a face diagonal is never among them)
  const uniq = []; for (const v of V) if (!uniq.some((u) => u.distanceToSquared(v) < 1e-12)) uniq.push(v);
  // three mutually perpendicular edges from one corner (a thin face's diagonal is nearly as short as an edge, so test angles)
  const cand = uniq.slice(1).map((v) => v.clone().sub(uniq[0])).sort((a, b) => a.length() - b.length()), edges = [];
  for (const e of cand) if (edges.every((f) => Math.abs(e.clone().normalize().dot(f.clone().normalize())) < 0.05)) { edges.push(e); if (edges.length === 3) break; }
  const eLongRaw = edges.filter((e) => Math.abs(e.clone().normalize().dot(nBest)) < 0.2).sort((a, b) => b.length() - a.length())[0];
  const eLong = eLongRaw.clone().addScaledVector(nBest, -eLongRaw.dot(nBest)).normalize();   // exactly in-plane
  const eShort = new THREE.Vector3().crossVectors(nBest, eLong).normalize();
  const span = (e) => { let lo = Infinity, hi = -Infinity; for (const v of V) { const d = v.dot(e); lo = Math.min(lo, d); hi = Math.max(hi, d); } return [lo, hi]; };
  const [l0, l1] = span(eLong), [s0, s1] = span(eShort), [n0, n1] = span(nBest);
  const W = (l1 - l0) * 1000, H = (s1 - s0) * 1000, T = n1 - n0;
  const centre = uniq.reduce((t, v) => t.add(v), new THREE.Vector3()).multiplyScalar(1 / uniq.length);
  const boxOf = (c) => new THREE.Box3().setFromObject(c);
  const side = Math.sign(parts.reduce((t, c) => t + boxOf(c).getCenter(new THREE.Vector3()).sub(centre).dot(nBest), 0)) || 1;
  const eN = nBest.clone().multiplyScalar(side);
  const eV = eShort.clone(); if (eV.y > 0) eV.negate();                 // artwork runs down the body
  const eU = new THREE.Vector3().crossVectors(eN, eV).normalize();       // right × down = into the board: reads unmirrored from the parts' side
  const eZ = new THREE.Vector3().crossVectors(eU, eN), s = Math.sign(eZ.dot(eV)) || 1;
  const toMM = (w) => { const d = w.clone().sub(centre); return [d.dot(eU) * 1000 + W / 2, d.dot(eV) * 1000 + H / 2]; };
  // In the vest design the board rides on its battery at the parts' height; the stand-in slab is the case floor.
  const hOf = (w) => w.clone().sub(centre).dot(eN) + T / 2;
  const sockH = parts.filter((c) => /C_sock_/.test(c.userData.srcName)).map((c) => hOf(boxOf(c).getCenter(new THREE.Vector3()))).sort((a, b) => a - b);
  const lift = sockH.length ? sockH[Math.floor(sockH.length / 2)] - 0.0018 - 0.0016 : 0;   // board bottom above the stand-in's bottom
  const A = {}, D = {};                                                   // anchors: name → [u, v] in mm; D: extents [along u, along v, height]
  const extent = (c) => { const g = c.geometry, p = g.attributes.position, lo = [Infinity, Infinity, Infinity], hi = [-Infinity, -Infinity, -Infinity], v = new THREE.Vector3();
    for (let i = 0; i < p.count; i++) { v.fromBufferAttribute(p, i).applyMatrix4(c.matrixWorld).sub(centre); const a = [v.dot(eU), v.dot(eV), v.dot(eN)]; for (let k = 0; k < 3; k++) { lo[k] = Math.min(lo[k], a[k]); hi[k] = Math.max(hi[k], a[k]); } }
    return { size: hi.map((h, k) => (h - lo[k]) * 1000), c: hi.map((h, k) => (h + lo[k]) * 500), lo: lo.map((x) => x * 1000), hi: hi.map((x) => x * 1000) }; };
  for (const c of parts) { A[c.userData.srcName] = toMM(boxOf(c).getCenter(new THREE.Vector3())); D[c.userData.srcName] = extent(c); }
  const socks = ["EEG", "EDA", "ECG", "EMG"].filter((k) => A[`C_sock_${k}`]);
  const out = socks.reduce((t, k) => t + A[`C_sock_${k}`][0], 0) / socks.length < W / 2 ? -1 : 1;   // sockets face out of this side
  // ---- the panel exactly as in the user's photo (kit.jpg, 1400 × 840 px), turned 180° in the board plane: then the four
  // sockets face the case windows and the silkscreen (upside down in the photo) reads upright. Pixel → mm: least-squares
  // fit of the photo's sockets, JST, USB, switch, BLE, button, LED and LUX to the positions the vest design gave them,
  // 12.54 px/mm across and 12.08 px/mm down (the camera was slightly tilted) — which also makes the panel 100 × 65 mm,
  // PLUX's datasheet size. Nothing below is placed by rule: every slab, hole, part and label is a measured photo position.
  const KX = 12.54, KY = 12.08, U0 = 107.53, V0 = 66.24;
  const PU = (x) => (out < 0 ? U0 - x / KX : W - U0 + x / KX), PV = (y) => (out < 0 ? V0 - y / KY : H - V0 + y / KY);
  const RX = ([x0, y0, x1, y1]) => ({ x: Math.min(PU(x0), PU(x1)), z: Math.min(PV(y0), PV(y1)), w: Math.abs(x1 - x0) / KX, h: Math.abs(y1 - y0) / KY });
  const P2 = (x, y) => [PU(x), PV(y)];
  const SENS = [[97, 176.5], [260, 341.5], [423, 505.5], [587, 670.5]];      // sensor module top edge, socket centre (gold blob) in px
  const LEFT = [[33, 110, 257], [35, 273, 423], [39, 440, 587], [41, 603, 750]];   // left modules: x0, y0, y1
  const slabsPx = [
    ...LEFT.flatMap(([x0, y0, y1]) => [[x0, y0, 252, y1], [250, y0 + 23, 316, y1 - 24]]),            // ACC, BUZ, BTN, pad array + necks
    [313, 40, 423, 813],                                                                              // left rail
    [435, 37, 657, 330], [435, 350, 657, 423], [670, 37, 880, 270], [673, 290, 880, 417], [437, 437, 880, 657],   // PWR, logo, BLE, 3×3, MCU
    [457, 655, 550, 737], [437, 735, 563, 810], [610, 655, 713, 737], [580, 735, 730, 810], [767, 655, 863, 737], [747, 735, 880, 810],   // LUX, +/−, LED
    [885, 30, 987, 800],                                                                              // right rail
    ...SENS.flatMap(([y0]) => [[985, y0 + 26, 1052, y0 + 117], [1050, y0, 1277, y0 + 143]]),          // sensor necks + modules
    // break-away tabs across the slits
    [421, 160, 437, 200], [421, 280, 437, 312], [421, 368, 437, 402], [421, 470, 439, 510], [421, 600, 439, 632],
    [655, 130, 672, 170], [878, 130, 887, 170], [878, 335, 887, 372], [878, 520, 887, 560], [878, 615, 887, 650],
    [525, 328, 570, 352], [525, 421, 570, 439], [752, 268, 800, 292], [752, 415, 800, 439]];
  const L = { holes: [], texts: [], hatches: [], pads: [], silk: [], logo: null }, items = [], ports = {};
  let tagNow = "";
  // item: centre (u, v) mm, size along u / v / height mm; th = rotation in the board plane (u → v)
  const item = (u, v, w, d, h, mat, th = 0, y0 = 0.0016, shape = "box") => items.push({ x: u, z: v, w, d, h, mat, rotY: -s * th, y0, tag: tagNow, shape });
  const at = (x, y, w, d, h, mat, th, y0, shape) => { const [u, v] = P2(x, y); item(u, v, w, d, h, mat, th, y0, shape); return [u, v]; };
  const hole = (x, y, r = 0.55) => L.holes.push([...P2(x, y), r]);
  const text = (t, x, y, size) => L.texts.push([t, ...P2(x, y), size]);
  // gull-wing leads on two opposite sides (along v) or all four (QFP), in the part's own frame turned by th
  const leads = (u, v, bw, bd, n, pitch, th = 0, four = false) => {
    const c = Math.cos(th), sn = Math.sin(th), put = (a, b, lw, ld) => item(u + a * c - b * sn, v + a * sn + b * c, lw, ld, 0.28, "lead", th);
    for (let k = 0; k < n; k++) { const o = (k - (n - 1) / 2) * pitch;
      for (const sg of [-1, 1]) { put(o, sg * (bd / 2 + 0.4), 0.28, 0.8); if (four) put(sg * (bw / 2 + 0.4), o, 0.8, 0.28); } } };
  const ic = (x, y, bw, bd, h, n, pitch, th = 0, four = false) => { const [u, v] = at(x, y, bw, bd, h, "black", th); if (n) leads(u, v, bw, bd, n, pitch, th, four); return [u, v]; };
  // 0603 passive: body + tinned ends; o = "h" long across (photo x), "v" long down (photo y)
  const rc = (x, y, o = "h", kind = "c") => { const [u, v] = P2(x, y), hz = o === "h", Lb = 1.6, Wb = 0.8;
    item(u, v, hz ? Lb - 0.6 : Wb, hz ? Wb : Lb - 0.6, 0.5, kind === "c" ? "tan" : "black");
    for (const sg of [-1, 1]) item(u + (hz ? sg * (Lb / 2 - 0.15) : 0), v + (hz ? 0 : sg * (Lb / 2 - 0.15)), hz ? 0.3 : Wb, hz ? Wb : 0.3, 0.52, "lead");
    L.pads.push([u, v, hz ? Lb + 0.4 : Wb + 0.3, hz ? Wb + 0.3 : Lb + 0.4]); };
  const hatch = (x, y, w, h) => L.hatches.push([...P2(x, y), w, h]);
  // ---- left column
  const mid = (y0, y1) => (y0 + y1) / 2;
  LEFT.forEach(([, y0, y1], i) => { const yc = mid(y0, y1);
    for (const d of [-36, -12, 12, 36]) hole(220, yc + d, 0.5);                       // module header
    hatch(247, yc - 22, 1.1, 3.2); hatch(247, yc + 22, 1.1, 3.2); hole(286, yc - 30, 0.3); hole(286, yc + 30, 0.3);
    L.silk.push([...P2(236, y0 + 12), 1], [...P2(236, y1 - 12), 1]); });
  tagNow = "acc";
  ic(59, 181, 3.2, 3.2, 0.9, 0); const acc = ic(133, 177, 5.0, 4.4, 1.1, 7, 0.65);           // ACC module: QFN + TSSOP-14
  rc(92, 176, "v", "c"); rc(52, 230, "h", "r"); rc(81, 230, "h", "r"); rc(160, 137, "h", "c"); hole(50, 140, 0.75);
  for (const d of [-26, 0, 23]) hole(177, 183.5 + d, 0.45);
  tagNow = "buz";
  at(70, 343, 6.7, 6.7, 3.0, "black");                                                       // buzzer
  at(122, 345, 2.4, 2.4, 1.3, "trim", 0, 0.0016, "cyl");                                      // trimmer
  ic(177, 347, 4.9, 3.9, 1.5, 4, 1.27);                                                       // SOIC-8
  ic(67, 403, 1.6, 2.9, 1.0, 0); rc(130, 292, "h", "r"); rc(160, 407, "h", "c");
  tagNow = "btn";
  const btn = at(133, 513, 5.2, 5.2, 1.8, "silver");                                          // tact switch, cream cap
  at(133, 513, 2.6, 2.6, 0.9, "cream", 0, 0.0016 + 0.0018, "cyl"); rc(200, 510, "v", "c");
  for (const x of [59, 89, 119, 149]) for (const y of [629, 660, 695, 730]) hole(x, y, 0.75);   // pad-array module
  for (const y of [629, 654, 679, 704, 729]) hole(185, y, 0.65);
  // ---- rails
  for (const y of [60, 220, 400, 553, 717]) for (let k = 0; k < 4; k++) hole(403, y + 23 * k, 0.5);
  for (const y of [90, 258, 425, 590, 745]) hatch(370, y, 1.4, 4.1);
  hole(373, 687, 1.2);
  for (const y of [57, 213, 380, 543]) for (let k = 0; k < 4; k++) hole(900, y + 24 * k, 0.5);
  for (const y of [87, 247, 407, 573, 740]) hatch(937, y, 1.4, 4.1);
  hole(937, 677, 1.2);
  // ---- PWR
  tagNow = "switch";
  const sw = at(493, 52, 8.5, 3.6, 2.8, "silver"); at(480, 33, 1.4, 1.6, 1.4, "black", 0, 0.0016 + 0.0007);
  tagNow = "usb";
  const usb = at(608, 57, 7.2, 4.6, 2.6, "silver"); at(608, 33, 5.8, 0.25, 1.6, "mouth", 0, 0.0016 + 0.0005);
  tagNow = "pwr_conn";
  const jst = at(561, 230, 6.2, 8.1, 4.8, "white"); at(561, 279.5, 4.6, 0.3, 3.0, "mouth", 0, 0.0016 + 0.0009);
  ports["C:PWR"] = { at: localToWorldMM(jst[0], jst[1], 0.004) };
  tagNow = "pwr";
  ic(513, 143, 2.9, 1.3, 1.0, 3, 0.95); ic(460, 243, 1.6, 2.9, 1.0, 0); ic(620, 200, 2.9, 1.6, 1.0, 3, 0.95); ic(620, 273, 2.9, 1.6, 1.0, 3, 0.95);
  for (const y of [185, 215, 247, 280]) rc(650, y, "v", "c");
  rc(540, 103, "h", "r"); rc(447, 270, "h", "r"); rc(447, 290, "h", "c");
  for (const y of [120, 147, 177]) hole(450, y); for (const y of [120, 147]) hole(483, y);
  for (const x of [570, 600, 633]) for (const y of [120, 148]) { hole(x, y, 0.75); L.silk.push([...P2(x, y), 1.15, "ring"]); }
  text("OFF", 447, 93, 1.4); text("ON", 507, 88, 1.4); text("+", 533, 170, 1.9); text("−", 563, 170, 1.9); text("PWR", 457, 313, 1.7);
  // ---- logo plate
  L.logo = [...P2(545, 385), 4.4];
  // ---- BLE
  tagNow = "ble";
  const blePcb = at(777, 120, 11.2, 13.7, 0.8, "pcbw"); const bleCan = P2(777, 140);
  at(717, 60, 0.8, 1.6, 0.6, "led"); at(760, 50, 3.2, 1.5, 0.8, "brown"); rc(733, 230, "h", "r"); rc(780, 230, "h", "c");
  for (let k = 0; k < 6; k++) hole(693 + 30.8 * k, 253, 0.7); hole(683, 210, 0.9); hole(857, 210, 0.9);
  text("BLE", 852, 230, 1.7);
  // ---- 3 × 3 module
  for (const x of [740, 770, 800]) for (const y of [327, 357]) hole(x, y, 0.65);
  for (let k = 0; k < 6; k++) hole(697 + 30 * k, 400, 0.7); rc(690, 325, "v", "c");
  // ---- MCU
  tagNow = "core";
  const mcu = P2(657, 543); item(mcu[0], mcu[1], 7, 7, 1.2, "black", Math.PI / 4); leads(mcu[0], mcu[1], 7, 7, 8, 0.8, Math.PI / 4, true);
  at(753, 533, 3.2, 5.0, 1.1, "silver"); rc(843, 507, "v", "c"); rc(843, 567, "v", "c"); rc(500, 553, "h", "r");
  for (let k = 0; k < 10; k++) rc(487 + 34 * k, 615, "h", k % 3 ? "r" : "c");
  for (let k = 0; k < 12; k++) hole(520 + 30.3 * k, 455, 0.65);
  for (let k = 0; k < 13; k++) hole(490 + 30.25 * k, 640, 0.65);
  for (let k = 0; k < 6; k++) hole(457, 473 + 30.8 * k, 0.55);
  text("MCU", 540, 550, 2.3);
  // ---- small modules under the MCU: LUX, a +/− module, LED
  tagNow = "lux"; const lux = at(503, 793, 3.0, 1.6, 0.8, "amber"); rc(553, 790, "v", "c");
  tagNow = "pm"; ic(597, 793, 1.6, 2.9, 1.0, 0); rc(723, 790, "v", "r"); hole(640, 793, 0.6); hole(670, 793, 0.6); text("+", 640, 772, 1.8); text("−", 670, 772, 1.8);
  tagNow = "led"; const led = at(807, 787, 3.7, 1.9, 0.9, "led"); for (const x of [795, 819]) at(x, 787, 0.9, 0.9, 0.06, "black", 0, 0.0016 + 0.0009); rc(857, 783, "v", "c");
  for (const x0 of [467, 610, 767]) for (let k = 0; k < 4; k++) hole(x0 + (x0 === 610 ? 34 : 24) * k, 760, 0.45);
  hole(467, 680, 0.45); hole(540, 680, 0.45);
  // ---- sensor modules: amplifier chips, passives, headers and the UC-E6 socket overhanging each module's end
  tagNow = "sens";
  const sockG = {}, sockAt = {}, names = ["EMG", "ECG", "EDA", "EEG"];   // top to bottom in the photo = the design's order
  const pas = [[60, -31.5, "h"], [83, -61.5, "v"], [97, 48.5, "h"], [133, 51.5, "h"], [153, 18.5, "v"], [167, 1.5, "v"], [193, -61.5, "h"], [173, 31.5, "v"], [57, 24.5, "v"], [120, -45, "h"]];
  SENS.forEach(([y0, ys], i) => { const yc = y0 + 71.5;
    if (i < 2) ic(1169, yc, 4.3, 4.0, 0.9, 0); else if (i === 2) ic(1170, yc - 4, 1.6, 1.6, 0.9, 0); else { ic(1133, yc - 10, 3.6, 3.6, 0.9, 0); ic(1193, yc - 10, 3.6, 3.6, 0.9, 0); }
    pas.forEach(([dx, dy, o], k) => rc(1050 + dx, yc + dy * (i % 2 ? -1 : 1), o, k % 2 ? "r" : "c"));
    for (const d of [-36, -11, 12, 36]) hole(1082, yc + d, 0.55);
    for (const d of [-26, -2, 24]) hole(1233, yc + d, 0.5);
    hole(1010, yc - 20, 0.3); hole(1010, yc + 20, 0.3); hatch(1003, yc, 1.1, 3.2);
    const [uf, vs] = P2(1348, ys), k = names[i];
    uce6(sockG, placeAt(new THREE.Vector3(out, 0, 0), new THREE.Vector3(0, 1, 0), new THREE.Vector3((uf - W / 2) / 1000, 0.0016, s * (vs - H / 2) / 1000)));
    sockAt[k] = [uf - out * 3, vs];
    ports[`C:${k}`] = { at: localToWorldMM(uf - out * 0.5, vs, 0.0034), mouth: localToWorldMM(uf, vs, 0.0033), out: eU.clone().multiplyScalar(out) };
  });
  // photo vs the positions the vest design (case windows, leads) was made for
  const photoVsDesign = Object.fromEntries([["C_sock_EMG", sockAt.EMG], ["C_sock_ECG", sockAt.ECG], ["C_sock_EDA", sockAt.EDA], ["C_sock_EEG", sockAt.EEG], ["C_pwr_conn", jst], ["C_usb", usb],
    ["C_switch", sw], ["C_ble", bleCan], ["C_btn", btn], ["C_led", led], ["C_lux", lux], ["C_acc", acc], ["C_core", mcu]].filter(([k]) => A[k]).map(([k, p]) =>
    [k, { photo: p.map((x) => +x.toFixed(1)), design: A[k].map((x) => +x.toFixed(1)), d_mm: +Math.hypot(p[0] - A[k][0], p[1] - A[k][1]).toFixed(1) }]));
  function localToWorldMM(u, v, y) { return centre.clone().addScaledVector(eN, -T / 2 + lift + y).addScaledVector(eU, (u - W / 2) / 1000).addScaledVector(eV, (v - H / 2) / 1000); }
  // ---- PCB slabs with the artwork on their top faces
  const slabs = slabsPx.map(RX).map((r) => {
    const g = new RoundedBoxGeometry(r.w / 1000, 0.0016, r.h / 1000, 1, Math.min(0.0005, r.w / 4000, r.h / 4000));
    g.translate((r.x + r.w / 2 - W / 2) / 1000, 0.0008, s * (r.z + r.h / 2 - H / 2) / 1000); return g.index ? g.toNonIndexed() : g;
  });
  const board = mergeGeometries(slabs, false);
  { const p = board.attributes.position, nr = board.attributes.normal, uv = new Float32Array(p.count * 2);
    for (let i = 0; i < p.count; i++) { const top = nr.getY(i) > 0.5; uv[i * 2] = top ? (p.getX(i) * 1000 + W / 2) / W : 0.0002; uv[i * 2 + 1] = top ? (s * p.getZ(i) * 1000 + H / 2) / H : 0.0002; }
    board.setAttribute("uv", new THREE.BufferAttribute(uv, 2)); }
  const meshes = [new THREE.Mesh(board, phys({ map: boardKitArt(W, H, L), roughness: 0.42, clearcoat: 0.35, clearcoatRoughness: 0.3 }))];
  const mats = { gold: () => metal(0xe8c76c, 0.22), mouth: () => plastic(0x0d0e10, 0.6), black: () => plastic(0x15161a, 0.5), silver: () => metal(0xc9cdd2, 0.28), lead: () => metal(0xd4d7db, 0.3),
    white: () => plastic(0xf2efe6, 0.55), pcbw: () => soldermask(0xe2e4e7), led: () => plastic(0xfafafa, 0.25), tan: () => plastic(0xb8976a, 0.5), cream: () => plastic(0xe0cf9c, 0.45),
    trim: () => metal(0xd9c48a, 0.35), brown: () => plastic(0x5a4034, 0.5), amber: () => plastic(0xa8782c, 0.35) };
  const groups = {};
  for (const it of items) {
    const g = it.shape === "cyl" ? new THREE.CylinderGeometry(it.w / 2000, it.w / 2000, it.h / 1000, 24) : new RoundedBoxGeometry(it.w / 1000, it.h / 1000, it.d / 1000, 1, Math.min(0.0003, it.h / 3000, it.w / 3000, it.d / 3000));
    if (it.rotY) g.rotateY(it.rotY);
    g.translate((it.x - W / 2) / 1000, it.y0 + it.h / 2000, s * (it.z - H / 2) / 1000);
    (groups[location.hash.includes("debug") ? `${it.mat}_${it.tag}` : it.mat] ||= []).push(g.index ? g.toNonIndexed() : g);
  }
  for (const [k, list] of Object.entries(groups)) { const m = new THREE.Mesh(mergeGeometries(list, false), mats[k.split("_")[0]]()); m.name = `kit_${k}`; meshes.push(m); }
  meshes[0].name = "kit_pcb";
  meshes.push(...meshesFromGroups(sockG, uce6Mats, "kit_uce6"));
  { const [x, z] = bleCan, cg = new RoundedBoxGeometry(0.0093, 0.0019, 0.0099, 1, 0.0003), cp = cg.attributes.position, uv = new Float32Array(cp.count * 2);
    for (let i = 0; i < cp.count; i++) { uv[i * 2] = (cp.getX(i) + 0.00465) / 0.0093; uv[i * 2 + 1] = (cp.getZ(i) + 0.00495) / 0.0099; }
    cg.setAttribute("uv", new THREE.BufferAttribute(uv, 2)); cg.translate((x - W / 2) / 1000, 0.0016 + 0.0008 + 0.00095, s * (z - H / 2) / 1000);
    meshes.push(new THREE.Mesh(cg, std({ map: tex("blecan", bleCanTexture), metalness: 0.55, roughness: 0.35 }))); }
  const grp = new THREE.Group(); grp.matrixAutoUpdate = false;
  grp.matrix.makeBasis(eU, eN, eZ).setPosition(centre.clone().addScaledVector(eN, -T / 2 + lift));
  sc.root.add(grp); meshes.forEach((m) => grp.add(m)); grp.updateMatrixWorld(true);
  const gone = new Set([pcb, ...parts.filter((c) => !/battery/.test(c.userData.srcName))]);
  gone.forEach((m) => { m.parent && m.parent.remove(m); });
  sc.meshes = sc.meshes.filter((m) => !gone.has(m)); sc.parts.c_board.meshes = sc.parts.c_board.meshes.filter((m) => !gone.has(m));
  for (const m of meshes) { prepMesh(m); registerMesh(sc, m, "c_board"); }
  sc.ports = Object.assign(sc.ports || {}, ports);
  // the leads follow the real connectors: the ECG lead's plug goes into the ECG socket, the battery plug moves with the JST
  const seat = { W11: seatPlug(sc, "W11_C_electrode_cable", "W11_conn0", "W11_conn0_tongue", ports["C:ECG"]),
    W12: A.C_pwr_conn ? shiftPlug(sc, "W12_C_battery", "W12_conn1", localToWorldMM(jst[0], jst[1], 0).sub(localToWorldMM(A.C_pwr_conn[0], A.C_pwr_conn[1], 0))) : null };
  const h3 = (w) => { const d = w.clone().sub(centre); return [+(d.dot(eU) * 1000 + W / 2).toFixed(1), +(d.dot(eV) * 1000 + H / 2).toFixed(1), +(d.dot(eN) * 1000 + T * 500).toFixed(1)]; };
  const plugsUVH = {}; for (const nm of ["W11_conn0", "W11_conn0_tongue", "W12_conn1", "W11_C_electrode_cable", "W12_C_battery"]) { const m = sc.meshes.find((x) => x.userData.srcName === nm); if (m) { const b = boxOf(m); plugsUVH[nm] = { c: h3(b.getCenter(new THREE.Vector3())), min: h3(b.min), max: h3(b.max) }; } }
  const partsUVH = Object.fromEntries(parts.map((c) => { const b = boxOf(c); return [c.userData.srcName, { c: h3(b.getCenter(new THREE.Vector3())) }]; }));
  sc.kitInfo = { T_mm: +(T * 1000).toFixed(2), plugsUVH, partsUVH, W: +W.toFixed(1), H: +H.toFixed(1), out, anchors: Object.fromEntries(Object.entries(A).map(([k, v]) => [k, v.map((x) => +x.toFixed(1))])) };
  sc.kitInfo.lift_mm = +(lift * 1000).toFixed(2);
  sc.kitInfo.photoVsDesign = photoVsDesign; sc.kitInfo.plugMoved_mm = Object.fromEntries(Object.entries(seat).map(([k, v]) => [k, v == null ? null : +(v * 1000).toFixed(1)]));
  sc.kitInfo.extents = Object.fromEntries(Object.entries(D).map(([k, d]) => [k, { size: d.size.map((x) => +x.toFixed(1)), h: [+(d.lo[2] + T * 500).toFixed(1), +(d.hi[2] + T * 500).toFixed(1)] }]));
  sc.kitInfo.box = { corners: uniq.map((v) => v.toArray().map((x) => +(x * 1000).toFixed(1))), edges: edges.map((e) => +(e.length() * 1000).toFixed(1)), normal: nBest.toArray().map((x) => +x.toFixed(3)), eLong: eLong.toArray().map((x) => +x.toFixed(3)), tris: (gi ? gi.count : gp.count) / 3 };
}
const hash2 = (a, b) => { const v = Math.sin(a * 91.7 + b * 47.3) * 43758.5453; return v - Math.floor(v); };
function dressBoard(mesh, maskColor) {
  const cls = boardClassifier(mesh);
  return splitMesh(mesh, cls, { board: soldermask(maskColor), comp: plastic(0x1b1c1f, 0.42) });
}

// ======================================================================================== model loading
const loader = new GLTFLoader(); loader.setMeshoptDecoder(MeshoptDecoder);
const b64 = (s) => { const bin = atob(s); const a = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i); return a.buffer; };
function loadGLB(name) {
  const src = (window.SV_MODELS || {})[name];
  if (src) return new Promise((res, rej) => loader.parse(b64(src), "", res, rej));
  return new Promise((res, rej) => loader.load(`models/${name}`, res, undefined, rej));
}
function loadScript(src) {
  return new Promise((res, rej) => { const s = document.createElement("script"); s.src = src; s.onload = res; s.onerror = rej; document.head.appendChild(s); });
}

// ======================================================================================== scene registry
const SCENES = {};      // name → { root, parts: {key: Part}, meshes: [], labels: [...], views: {}, stage }
let active = null;
class Part {
  constructor(key) { this.key = key; this.meshes = []; this.center = new THREE.Vector3(); }
  worldCenter(out = new THREE.Vector3()) {
    const box = new THREE.Box3();
    for (const m of this.meshes) if (m.visible !== false) box.expandByObject(m);
    return box.isEmpty() ? out.set(0, 0, 0) : box.getCenter(out);
  }
  box() { const b = new THREE.Box3(); for (const m of this.meshes) b.expandByObject(m); return b; }
}

function registerMesh(sc, mesh, key) {
  if (!sc.parts[key]) sc.parts[key] = new Part(key);
  const p = sc.parts[key];
  p.meshes.push(mesh);
  mesh.userData.part = key;
  if (!mesh.geometry.attributes.normal) mesh.geometry.computeVertexNormals();
  if (!mesh.geometry.boundsTree) mesh.geometry.computeBoundsTree();
  mesh.userData.orig = mesh.position.clone();
  sc.meshes.push(mesh);
}

// Parts placed from the enclosure CAD + placement data (models/extras.json, made by brief/extras2.mjs): the REF2 cell in its
// shoulder holder (AK 40 x 28 mm, top 0.1 mm below the holder, level) and the 22 M2 self-tapping screws (PA pan head):
// PMB-H x4, webbing hooks x4, LIB x2 (M2x6); back, chest and C lids x4 each (M2x8). Each screw follows its host on explode.
function addExtras(sc) {
  const V = (a) => new THREE.Vector3(...a), r = EXTRAS.ref2;
  const cg = new THREE.BoxGeometry(...r.size); cg.applyMatrix4(new THREE.Matrix4().makeBasis(V(r.x), V(r.y), V(r.n)).setPosition(V(r.center)));
  const cell = new THREE.Mesh(cg, matFor("ref_cells", "ref2_cell")); cell.name = cell.userData.srcName = "ref2_cell";
  cell.userData.explodeExtra = [0, 0, 0.03];                                   // ride with its holder (ref_holders), not with REF1
  sc.root.add(cell); prepMesh(cell); registerMesh(sc, cell, "ref_cells");
  const groups = {}, Y = new THREE.Vector3(0, 1, 0), one = new THREE.Vector3(1, 1, 1);
  for (const sw of EXTRAS.screws) {
    const T = new THREE.Matrix4().compose(V(sw.pos), new THREE.Quaternion().setFromUnitVectors(Y, V(sw.axis).negate()), one);   // +y = out of the hole
    const head = new THREE.CylinderGeometry(0.0017, 0.0019, 0.0013, 20); head.translate(0, 0.00065, 0);
    const shank = new THREE.CylinderGeometry(0.001, 0.0008, sw.len, 12); shank.translate(0, -sw.len / 2, 0);
    const slot = new THREE.BoxGeometry(0.0022, 0.0004, 0.00042); slot.translate(0, 0.00125, 0); const slot2 = slot.clone().rotateY(Math.PI / 2);
    for (const [k, g] of [["metal", head], ["metal", shank], ["recess", slot], ["recess", slot2]]) { g.applyMatrix4(T); (((groups[sw.part] ||= {})[k]) ||= []).push(g.toNonIndexed()); }
  }
  for (const [host, gs] of Object.entries(groups)) for (const [k, list] of Object.entries(gs)) {
    const m = new THREE.Mesh(mergeGeometries(list, false), k === "metal" ? metal(0xc4c8cd, 0.32) : plastic(0x2a2c30, 0.6));
    m.name = m.userData.srcName = `screws_${host}_${k}`; m.userData.explodeExtra = (EXPLODE[host] || [0, 0, 0]).slice();
    sc.root.add(m); prepMesh(m); registerMesh(sc, m, "screws");
  }
}
async function buildWorn() {
  const gltf = await loadGLB("assembly.mo.glb");
  const index = window.SV_INDEX || {};
  const root = gltf.scene; root.updateMatrixWorld(true);
  const sc = { name: "worn", root: new THREE.Group(), parts: {}, meshes: [], labels: LABELS_WORN };
  const toRemove = [], swaps = [], vestPanels = [], kitParts = []; let kitPcb = null;
  let panel = null, glass = null;
  // GLTFLoader strips "/", "." and ":" from node names; map them back to the names the index and rules use
  const original = {}; for (const k of Object.keys(index)) original[THREE.PropertyBinding.sanitizeNodeName(k)] = k;
  root.traverse((o) => {
    if (!o.isMesh) return;
    const name = original[o.name] || o.name;
    if (/PRIVATE/.test(name) || index[name] === "torso") { toRemove.push(o); return; }
    const key = partOf(name, index[name]);
    if (/^vest\/vest_/.test(name)) vestPanels.push(o);
    if (name === "panel") { panel = o; return; }
    if (name === "panel_glass") glass = o;
    if (key === "pmbh" || key === "lib" || key === "core_b") { swaps.push([o, key, dressBoard(o, key === "core_b" ? 0x1d3d7a : 0x0f5a3a)]); return; }
    o.material = matFor(key, name); o.userData.srcName = name; prepMesh(o);
    if (key === "c_board") (name === "C_board_pcb" ? (kitPcb = o) : kitParts.push(o));
    registerMesh(sc, o, key);
  });
  if (kitPcb && !location.hash.includes("nokit")) buildBoardKit(sc, kitPcb, kitParts);
  if (panel && glass) swaps.push([panel, "panel", dressPanel(panel, glass)]);
  for (const [o, key, parts] of swaps) { for (const m of parts) { o.parent.add(m); prepMesh(m); registerMesh(sc, m, key); } toRemove.push(o); }
  toRemove.forEach((o) => o.parent.remove(o));
  sc.root.add(root);
  // a dress form fills the vest, standing on a weighted base on the studio floor
  sc.form = buildDressForm(vestPanels); sc.root.add(sc.form);
  const floor = makeFloor(0, 2.4); floor.receiveShadow = false;   // the figure's long shadow would leave the shadow map
  sc.root.add(floor, contactShadow(sc.form.userData.footXZ[0], 0, sc.form.userData.footXZ[1], 0.32));
  sc.shadow = { center: new THREE.Vector3(0, 1.32, -0.02), radius: 0.58 };
  addExtras(sc);
  upgradeBoards(sc);
  sc.ao = 0.05;
  sc.views = {
    iso: ["Rear ¾", [1.32, 1.86, -2.12], [0, 1.4, -0.05]], back: ["Back", [0, 1.45, -2.5], [0, 1.4, 0]], front: ["Front", [0, 1.45, 2.4], [0, 1.4, 0]],
    side: ["Side", [-2.5, 1.45, 0], [0, 1.4, 0]], pod: ["Back unit", [0.32, 1.42, -0.95], [0, 1.22, -0.2]],
    chest: ["Chest unit", [-0.42, 1.5, 0.62], [-0.115, 1.38, 0.15]], cunit: ["Unit C", [0.45, 1.5, 0.62], [0.12, 1.38, 0.13]],
    skin: ["Electrodes", [0.18, 1.42, 1.05], [0, 1.36, 0.08]],
  };
  sc.defaultView = "iso";
  return sc;
}
async function buildBench() {
  const gltf = await loadGLB("bench.mo.glb");
  const root = gltf.scene; root.updateMatrixWorld(true);
  const sc = { name: "bench", root: new THREE.Group(), parts: {}, meshes: [], labels: LABELS_BENCH };
  const swaps = []; let panel = null, glass = null;
  root.traverse((o) => {
    if (!o.isMesh) return;
    let key = partOf(o.name, null);
    if (o.name === "PMB-H") key = "pmbh";
    if (o.name === "W01_bench") key = "W01";
    if (o.name === "panel") { panel = o; return; }
    if (o.name === "panel_glass") glass = o;
    if (key === "pmbh") { swaps.push([o, key, dressBoard(o, 0x0f5a3a)]); return; }
    o.material = matFor(key, o.name); prepMesh(o);
    registerMesh(sc, o, key);
  });
  if (panel && glass) swaps.push([panel, "panel", dressPanel(panel, glass)]);
  for (const [o, key, parts] of swaps) { for (const m of parts) { o.parent.add(m); prepMesh(m); registerMesh(sc, m, key); } o.parent.remove(o); }
  sc.root.add(root);
  const box = new THREE.Box3().setFromObject(root);
  sc.shadow = { center: box.getCenter(new THREE.Vector3()), radius: 0.62 };
  upgradeBoards(sc);
  sc.ao = 0.03;
  sc.views = { iso: ["¾ view", [0.82, 0.62, -0.98], [0, 0.06, -0.04]], side: ["Side · tilt", [1.25, 0.18, 0.0], [0, 0.07, 0]], top: ["Top", [0.0, 1.3, 0.01], [0, 0, 0]] };
  sc.defaultView = "iso";
  return sc;
}
const COMP_RE = /^(U|Q|M|D|C|R|RS|J|L|F|SC)\d+[A-Z]?$/;
// Float32 position/normal copy of a (possibly quantised, meshopt-decoded) geometry, baked into holder space.
function plainGeometry(src, m) {
  const out = new THREE.BufferGeometry();
  for (const name of ["position", "normal"]) {
    const a = src.attributes[name]; if (!a) continue;
    const f = new Float32Array(a.count * 3);
    for (let i = 0; i < a.count; i++) { f[i * 3] = a.getX(i); f[i * 3 + 1] = a.getY(i); f[i * 3 + 2] = a.getZ(i); }
    out.setAttribute(name, new THREE.BufferAttribute(f, 3));
  }
  if (!out.attributes.normal) out.computeVertexNormals();
  out.setIndex(src.index ? Array.from(src.index.array) : [...Array(out.attributes.position.count).keys()]);
  out.applyMatrix4(m);
  return out;
}
// KiCad's colours, tuned to read like the green JLC boards on order (and to stay under the bloom threshold).
function boardMaterial(src) {
  const m = src.clone(), hex = src.color.getHex();
  m.envMapIntensity = 0.5;
  if (hex === 0x507c69) { m.color.set(0x0f5a3a); m.opacity = 0.92; m.roughness = 0.45; }   // solder mask
  else if (hex === 0xadb393) m.color.set(0x8c8a6a);                                        // FR4 edge
  else if (hex === 0xffffff && m.transparent) { m.color.set(0xe8ece8); m.opacity = 1; m.transparent = false; } // silkscreen
  else if (m.metalness > 0.5) m.roughness = Math.max(m.roughness, 0.35);
  return m;
}
async function buildBoards() {
  if (!window.SV_BOARDS) await loadScript("models-boards.js").catch(() => {});
  const sc = { name: "boards", root: new THREE.Group(), parts: {}, meshes: [], labels: [], comps: [] };
  const place = { pmbh: [-0.24, 0], libb: [0.27, 0.0] };
  for (const b of ["pmbh", "libb"]) {
    let gltf;
    const src = (window.SV_BOARDS || {})[`${b}.mo.glb`];
    if (src) gltf = await new Promise((res, rej) => loader.parse(b64(src), "", res, rej));
    else gltf = await new Promise((res, rej) => loader.load(`models/${b}.mo.glb`, res, undefined, rej));
    const g = gltf.scene;
    let bb = new THREE.Box3().setFromObject(g), sz = bb.getSize(new THREE.Vector3());
    if (sz.y > Math.min(sz.x, sz.z) * 1.5) { g.rotation.x = -Math.PI / 2; g.updateMatrixWorld(true); bb = new THREE.Box3().setFromObject(g); sz = bb.getSize(new THREE.Vector3()); }
    const s = 5 / Math.max(sz.x, sz.z) * (b === "pmbh" ? 0.086 : 0.056);
    const holder = new THREE.Group(); holder.add(g); holder.scale.setScalar(s);
    const c = bb.getCenter(new THREE.Vector3());
    g.position.sub(c);
    holder.position.set(place[b][0], 0, place[b][1]);
    sc.root.add(holder);
    holder.updateMatrixWorld(true);
    const boardKey = b === "pmbh" ? "pmbh" : "lib";
    // KiCad exports every pad and pin as its own mesh (~6 000 per board). Merge them per part and material,
    // so the scene costs a few hundred draw calls instead of twelve thousand.
    const groups = new Map();           // part key -> Map(material signature -> {mat, meshes})
    const nodeOf = {};
    g.traverse((o) => {
      if (!o.isMesh) return;
      let n = o, ref = null;
      while (n && n !== g) { if (COMP_RE.test(n.name)) { ref = n.name; break; } n = n.parent; }
      const key = ref ? `${b}:${ref}` : boardKey;
      if (ref) nodeOf[key] = ref;
      const m = o.material, sig = `${m.color.getHexString()}|${m.opacity}|${m.metalness}|${m.roughness}`;
      if (!groups.has(key)) groups.set(key, new Map());
      const gm = groups.get(key); if (!gm.has(sig)) gm.set(sig, { mat: m, meshes: [] });
      gm.get(sig).meshes.push(o);
    });
    const inv = holder.matrixWorld.clone().invert(), rel = new THREE.Matrix4();
    for (const [key, gm] of groups) {
      const isComp = key !== boardKey;
      const part = sc.parts[key] || (sc.parts[key] = new Part(key));
      const host = isComp ? new THREE.Group() : holder;
      if (isComp) { holder.add(host); part.ref = nodeOf[key]; part.board = b; part.node = host; host.userData.orig = host.position.clone(); sc.comps.push(part); }
      for (const { mat, meshes } of gm.values()) {
        const geos = meshes.map((o) => plainGeometry(o.geometry, rel.multiplyMatrices(inv, o.matrixWorld)));
        const merged = new THREE.Mesh(mergeGeometries(geos, false), boardMaterial(mat));
        merged.geometry.computeBoundsTree();
        geos.forEach((x) => x.dispose());
        merged.userData.part = key; host.add(merged);
        part.meshes.push(merged); sc.meshes.push(merged);
      }
    }
    holder.remove(g);
    g.traverse((o) => { if (o.isMesh) o.geometry.dispose(); });
  }
  const bbx = new THREE.Box3(); for (const m of sc.meshes) bbx.expandByObject(m);
  sc.root.add(makeFloor(bbx.min.y - 0.0005, 1.3, 0x202328));
  for (const m of sc.meshes) { m.castShadow = true; m.receiveShadow = true; }
  sc.shadow = { center: bbx.getCenter(new THREE.Vector3()), radius: 0.5 };
  sc.ao = 0.012;
  sc.views = { boards: ["Both boards", [-0.015, 1.08, 0.92], [-0.015, 0, 0.0]], pmbh: ["PMB-H", [-0.24, 0.84, 0.47], [-0.24, 0, 0.01]], libb: ["LIB", [0.27, 0.55, 0.31], [0.27, 0, 0.0]] };
  sc.defaultView = "boards";
  // the overview names the headline parts only; zooming into one board names all of its key parts
  const has = (b) => (r) => sc.parts[`${b}:${r}`], keys = (b, list) => list.filter(has(b)).map((r) => `${b}:${r}`);
  sc.labelSets = { boards: [...keys("pmbh", BOARD_OVERVIEW.pmbh), ...keys("libb", BOARD_OVERVIEW.libb)],
    pmbh: keys("pmbh", BOARD_LABELS.pmbh), libb: keys("libb", BOARD_LABELS.libb) };
  sc.labels = sc.labelSets.boards;
  return sc;
}

// ======================================================================================== energy model
function simAt(g) {
  if (g <= 0) return { p: 0, ibat: -SELF_MA, chg: 0, cap: 0 };
  for (let i = 1; i < SIM.length; i++) {
    const [g0, p0, i0, c0] = SIM[i - 1], [g1, p1, i1, c1] = SIM[i];
    if (g <= g1) { const t = (g - g0) / (g1 - g0); const ibat = i0 + (i1 - i0) * t; return { p: p0 + (p1 - p0) * t, ibat, chg: Math.max(0, ibat + SELF_MA), cap: c0 + (c1 - c0) * t }; }
  }
  const l = SIM[SIM.length - 1]; return { p: l[1], ibat: l[2], chg: l[2] + SELF_MA, cap: l[3] };
}
function breakEven(need) {          // irradiance where charger output covers `need` mA
  for (let i = 1; i < SIM.length; i++) {
    const a = SIM[i - 1][2] + SELF_MA, b = SIM[i][2] + SELF_MA;
    if (b >= need && a < need) return SIM[i - 1][0] + (SIM[i][0] - SIM[i - 1][0]) * (need - a) / (b - a);
  }
  return need <= SIM[0][2] + SELF_MA ? 0 : Infinity;
}
const state = { mode: "sun", g: 1000, load: 65, glitchT: 0 };
function energy() {
  const s = simAt(state.g), glitch = state.mode === "glitch";
  const load = glitch ? 0 : state.load;
  const net = s.chg - SELF_MA - load;
  const need = SELF_MA + state.load;
  return { ...s, glitch, load, net, share: clamp(s.chg / need, 0, 1), alone: BATT_MAH / need, atLight: net < 0 ? BATT_MAH / -net : Infinity, be: breakEven(need) };
}

// ======================================================================================== 3D energy flows
class Flow {
  constructor(curve, color, n = 28, size = 0.012) {
    this.curve = curve; this.n = n; this.t = Math.random();
    const geo = new THREE.BufferGeometry();
    this.pos = new Float32Array(n * 3); this.alpha = new Float32Array(n);
    geo.setAttribute("position", new THREE.BufferAttribute(this.pos, 3));
    geo.setAttribute("aAlpha", new THREE.BufferAttribute(this.alpha, 1));
    this.mat = new THREE.ShaderMaterial({
      uniforms: { uColor: { value: new THREE.Color(color) }, uSize: { value: size }, uPR: pointsUniformPR, uGain: { value: 1 } },
      vertexShader: `attribute float aAlpha; uniform float uSize; uniform float uPR; varying float vA;
        void main(){ vec4 mv = modelViewMatrix*vec4(position,1.0); gl_PointSize = uSize*900.0*uPR/max(0.05,-mv.z); vA = aAlpha; gl_Position = projectionMatrix*mv; }`,
      fragmentShader: `uniform vec3 uColor; uniform float uGain; varying float vA;
        void main(){ float d = length(gl_PointCoord-0.5); float a = 1.0 - smoothstep(0.0,0.5,d); if (a <= 0.0) discard; a = a*a; gl_FragColor = vec4(uColor*(1.5+2.5*a)*uGain, a*vA); }`,
      transparent: true, depthWrite: false, depthTest: false, blending: THREE.AdditiveBlending,
    });
    this.obj = new THREE.Points(geo, this.mat); this.obj.renderOrder = 10; this.obj.frustumCulled = false;
    this.speed = 0.2; this.level = 0; this.target = 0;
  }
  set(level, speed) { this.target = level; this.speed = speed; }
  update(dt) {
    this.level += (this.target - this.level) * Math.min(1, dt * 4);
    this.t = (this.t + dt * this.speed) % 1;
    const v = new THREE.Vector3();
    for (let i = 0; i < this.n; i++) {
      const u = (i / this.n + this.t) % 1;
      this.curve.getPointAt(u, v);
      this.pos[i * 3] = v.x; this.pos[i * 3 + 1] = v.y; this.pos[i * 3 + 2] = v.z;
      this.alpha[i] = this.level * Math.sin(Math.PI * u) ** 0.35;
    }
    this.obj.geometry.attributes.position.needsUpdate = true; this.obj.geometry.attributes.aAlpha.needsUpdate = true;
    this.obj.visible = this.level > 0.01;
  }
}
// rough centreline of a tube mesh: voxel-average its vertices, then chain the cells from `start`
function centreline(meshes, start, end, cell = 0.02) {
  const cells = new Map(), v = new THREE.Vector3();
  for (const m of meshes) {
    const pa = m.geometry.attributes.position; m.updateMatrixWorld(true);
    const step = Math.max(1, Math.floor(pa.count / 3000));
    for (let i = 0; i < pa.count; i += step) {
      v.fromBufferAttribute(pa, i).applyMatrix4(m.matrixWorld);
      const k = `${Math.round(v.x / cell)},${Math.round(v.y / cell)},${Math.round(v.z / cell)}`;
      const c = cells.get(k) || cells.set(k, [0, 0, 0, 0]).get(k); c[0] += v.x; c[1] += v.y; c[2] += v.z; c[3]++;
    }
  }
  const pts = [...cells.values()].map((c) => new THREE.Vector3(c[0] / c[3], c[1] / c[3], c[2] / c[3]));
  if (pts.length < 3) return new THREE.CatmullRomCurve3([start, end]);
  const ordered = []; let cur = start.clone();
  while (pts.length) {
    let bi = 0, bd = Infinity;
    for (let i = 0; i < pts.length; i++) { const d = pts[i].distanceToSquared(cur); if (d < bd) { bd = d; bi = i; } }
    cur = pts.splice(bi, 1)[0]; ordered.push(cur);
  }
  const smooth = ordered.map((p, i) => { const a = ordered[Math.max(0, i - 2)], b = ordered[Math.min(ordered.length - 1, i + 2)]; return p.clone().add(a).add(b).multiplyScalar(1 / 3); });
  const keep = [start];
  for (const p of [...smooth.filter((_, i) => i % 2 === 0), end]) if (p.distanceTo(keep[keep.length - 1]) > 0.003) keep.push(p);
  if (keep.length < 2) keep.push(end.clone().add(new THREE.Vector3(0, 0.001, 0)));
  return new THREE.CatmullRomCurve3(keep, false, "centripetal");
}
const arc = (a, b, lift) => { const m = a.clone().add(b).multiplyScalar(0.5).add(lift); return new THREE.QuadraticBezierCurve3(a, m, b); };

let sunSprite = null;
function buildFlows(sc) {
  const P = sc.parts, C = (k) => (P[k] ? P[k].worldCenter() : null);
  const flows = {};
  const add = (name, curve, color, n, size) => { if (!curve) return; const f = new Flow(curve, color, n, size); sc.root.add(f.obj); flows[name] = f; };
  if (sc.name === "worn") {
    const panel = C("panel"), pod = C("back_pod"), chest = C("chest_pod"), core = C("core_b"), lib = C("lib"), batt = C("battery"),
      pmb = C("pmbh"), phone = C("phone"), cB = C("c_board"), uA = C("unit_a"), xiao = C("xiao"), ecg = C("ecg_b"), ref = C("ref_cells");
    sc.sunPos = panel.clone().add(new THREE.Vector3(0.9, 2.4, -2.6));
    // light rays onto the panel
    const pb = P.panel.box(), rays = [];
    for (let i = 0; i < 7; i++) {
      const tgt = new THREE.Vector3(THREE.MathUtils.lerp(pb.min.x, pb.max.x, 0.12 + 0.76 * ((i * 0.37) % 1)), THREE.MathUtils.lerp(pb.min.y, pb.max.y, 0.15 + 0.7 * ((i * 0.61) % 1)), pb.min.z);
      rays.push(new THREE.LineCurve3(sc.sunPos.clone().add(new THREE.Vector3((i - 3) * 0.05, 0, 0)), tgt));
    }
    rays.forEach((r, i) => add(`ray${i}`, r, 0xffc861, 10, 0.016));
    add("pv", centreline(P.W01 ? P.W01.meshes : [], panel, pod), 0xffb547, 30, 0.013);
    add("chg", arc(pmb, batt, new THREE.Vector3(0, 0.03, -0.03)), 0x7cf29a, 14, 0.011);
    add("load", centreline(P.W06 ? P.W06.meshes : [], pod, chest), 0xffb547, 46, 0.012);
    add("hold", arc(lib, core, new THREE.Vector3(0, 0.02, 0.03)), 0xffb547, 10, 0.011);
    add("ecg", arc(ecg, core, new THREE.Vector3(-0.02, 0.03, 0.05)), 0xff6b8b, 16, 0.01);
    add("bleB", arc(core, phone, new THREE.Vector3(0.0, 0.05, 0.22)), 0x4fd1e8, 22, 0.011);
    add("bleC", arc(cB, phone, new THREE.Vector3(0.0, 0.05, 0.22)), 0x4fd1e8, 22, 0.011);
    add("bleA", arc(uA, phone, new THREE.Vector3(0.0, 0.02, 0.16)), 0x4fd1e8, 18, 0.011);
    add("bleX", arc(xiao, phone, new THREE.Vector3(-0.42, 0.12, 0.05)), 0x4fd1e8, 34, 0.011);
    if (ref) add("ref", arc(ref, pod, new THREE.Vector3(0, 0.05, -0.08)), 0xff6b8b, 18, 0.009);
  } else if (sc.name === "bench") {
    const panel = C("panel"), pod = C("back_pod") || C("pmbh");
    sc.sunPos = panel.clone().add(new THREE.Vector3(0.4, 1.6, -0.9));
    const pb = P.panel.box();
    for (let i = 0; i < 7; i++) {
      const tgt = new THREE.Vector3(THREE.MathUtils.lerp(pb.min.x, pb.max.x, 0.1 + 0.8 * ((i * 0.37) % 1)), pb.max.y, THREE.MathUtils.lerp(pb.min.z, pb.max.z, 0.15 + 0.7 * ((i * 0.61) % 1)));
      add(`ray${i}`, new THREE.LineCurve3(sc.sunPos.clone().add(new THREE.Vector3((i - 3) * 0.03, 0, 0)), tgt), 0xffc861, 10, 0.012);
    }
    if (P.W01 && pod) add("pv", centreline(P.W01.meshes, panel, pod, 0.015), 0xffb547, 30, 0.01);
  }
  sc.flows = flows;
}
function applyFlows(dt) {
  if (!active || !active.flows) return;
  const e = energy(), F = active.flows, on = ui.flow;
  const lv = (x) => (on ? x : 0);
  const pw = clamp(Math.log10(1 + e.p * 10) / Math.log10(48), 0, 1);       // 0..1 for 0..4.7 W
  for (const k in F) if (k.startsWith("ray")) F[k].set(lv(state.g > 0 ? 0.25 + 0.75 * clamp(state.g / 1000, 0, 1) : 0), 0.35 + 0.5 * pw);
  if (F.pv) F.pv.set(lv(e.p > 0.001 ? 0.35 + 0.65 * pw : 0), 0.08 + 0.35 * pw);
  if (F.chg) F.chg.set(lv(e.chg > 0.5 ? 0.3 + 0.7 * pw : 0), 0.1 + 0.5 * pw);
  if (F.load) { F.load.set(lv(e.glitch ? 0 : 0.75), 0.12); F.load.mat.uniforms.uColor.value.set(0xffb547); }
  if (F.hold) { F.hold.set(lv(1), 0.25); F.hold.mat.uniforms.uColor.value.set(e.glitch ? 0xb69cff : 0xffb547); }
  for (const k of ["ecg", "bleB", "bleC", "bleA", "bleX", "ref"]) if (F[k]) F[k].set(lv(k === "ref" ? (state.g > 0 ? 0.7 : 0.15) : 0.8), k.startsWith("ble") ? 0.35 : 0.3);
  for (const k in F) F[k].update(dt);
  if (sunSprite) {
    sunSprite.visible = !!active.sunPos && state.g > 0;
    if (active.sunPos) sunSprite.position.copy(active.sunPos);
    const s = 0.25 + 0.55 * clamp(state.g / 1000, 0, 1); sunSprite.scale.setScalar(s);
    sunSprite.material.opacity = 0.35 + 0.65 * clamp(state.g / 1000, 0, 1);
  }
}

// ======================================================================================== interaction state
const ui = { xray: false, explode: 0, explodeTarget: 0, labels: true, flow: true, hover: null, sel: null };
const tmpV = new THREE.Vector3(), tmpV2 = new THREE.Vector3();

function setXray(on) {
  ui.xray = on; $("#t-xray").classList.toggle("on", on); $("#t-xray").setAttribute("aria-pressed", on);
  for (const sc of Object.values(SCENES)) for (const m of sc.meshes) {
    if (!SHELLS.has(m.userData.part) && !m.userData.shell) continue;
    if (!m.userData.base) m.userData.base = m.material;
    m.material = on ? m.userData.xray || xrayMat : m.userData.base;
    m.renderOrder = on ? 5 : 0;
    m.castShadow = !on;                       // a see-through shell must not darken what it reveals
  }
  renderer.shadowMap.needsUpdate = true; geomVersion++;
  // the dress form turns into a faint ghost
  for (const sc of Object.values(SCENES)) if (sc.form) sc.form.traverse((o) => {
    if (!o.isMesh) return;
    if (!o.userData.base) o.userData.base = o.material;
    o.material = on ? formGhost : o.userData.base; o.castShadow = !on; o.renderOrder = on ? 4 : 0;
  });
  // in X-ray, cables become faint so the boards read clearly
  for (const sc of Object.values(SCENES)) for (const k of ["W01", "W06", "W_misc"]) {
    const p = sc.parts[k]; if (!p) continue;
    for (const m of p.meshes) { m.material.transparent = on; m.material.opacity = on ? 0.45 : 1; m.material.needsUpdate = true; }
  }
}
function applyExplode() {
  if (!active) return;
  const e = ease(clamp(ui.explode, 0, 1));
  if (active.name === "boards") {
    for (const p of active.comps) {
      const n = p.node; if (!n.userData.orig) continue;
      n.position.copy(n.userData.orig);
      const lift = 0.012 + 0.006 * ((p.ref.charCodeAt(0) * 7 + p.ref.length) % 5);
      const parent = n.parent; parent.updateMatrixWorld(true);
      const wp = n.getWorldPosition(new THREE.Vector3());
      const tgt = wp.clone().add(new THREE.Vector3(0, lift * e, 0));
      parent.worldToLocal(wp); parent.worldToLocal(tgt);
      n.position.add(tgt.sub(wp));
    }
    return;
  }
  for (const m of active.meshes) {
    const b = EXPLODE[m.userData.part] || [0, 0, 0], x = m.userData.explodeExtra, d = x ? [b[0] + x[0], b[1] + x[1], b[2] + x[2]] : b;
    m.position.copy(m.userData.orig);
    if (!d[0] && !d[1] && !d[2]) continue;
    const parent = m.parent; parent.updateMatrixWorld(true);
    const wp = m.getWorldPosition(tmpV.set(0, 0, 0)).clone();
    const target = wp.clone().add(tmpV2.set(d[0], d[1], d[2]).multiplyScalar(e));
    parent.worldToLocal(wp); parent.worldToLocal(target);
    m.position.add(target.sub(wp));
  }
  // cables fade out while exploded
  for (const k of ["W01", "W06", "W_misc"]) {
    const p = active.parts[k]; if (!p) continue;
    for (const m of p.meshes) m.visible = e < 0.35;
  }
}
function setLabels(on) { ui.labels = on; $("#t-labels").classList.toggle("on", on); $("#t-labels").setAttribute("aria-pressed", on); $("#labels").hidden = !on; $("#leaders").style.display = on ? "" : "none"; }
function setFlow(on) { ui.flow = on; $("#t-flow").classList.toggle("on", on); $("#t-flow").setAttribute("aria-pressed", on); }

// ---------------- camera tween
let tween = null;
function flyTo(pos, tgt, dur = 1.2) {
  if (reduceMotion) dur = 0.01;
  tween = { p0: camera.position.clone(), t0: controls.target.clone(), p1: new THREE.Vector3(...pos), t1: new THREE.Vector3(...tgt), k: 0, dur };
}
function setView(name) {
  if (!active || !active.views[name]) return;
  const [, p, t] = active.views[name];
  flyTo(p, t);
  if (active.labelSets && active.labelSets[name] && active.labels !== active.labelSets[name]) { active.labels = active.labelSets[name]; buildLabels(); }
  $$("#views button").forEach((b) => b.classList.toggle("on", b.dataset.v === name));
}
function frameBox(box, dirHint) {
  const c = box.getCenter(new THREE.Vector3()), r = Math.max(active && active.name === "boards" ? 0.07 : 0.03, box.getSize(new THREE.Vector3()).length() / 2);
  const dist = r / Math.sin(THREE.MathUtils.degToRad(camera.fov / 2)) * 1.25;
  const dir = dirHint ? dirHint.clone().normalize() : camera.position.clone().sub(controls.target).normalize();
  flyTo(c.clone().addScaledVector(dir, dist).toArray(), c.toArray());
}

// ======================================================================================== labels
const labelEls = new Map();
if (document.fonts) document.fonts.ready.then(() => { for (const L of labelEls.values()) L.bw = 0; });
function buildLabels() {
  const box = $("#labels"); box.innerHTML = ""; labelEls.clear();
  if (!active) return;
  for (const key of active.labels) {
    const p = active.parts[key]; if (!p) continue;
    let name, cat;
    if (active.name === "boards") { const info = COMP[p.board][p.ref]; name = info ? `${p.ref} · ${info[0]}` : p.ref; cat = "elec"; }
    else { name = PARTS[key].name; cat = PARTS[key].cat; }
    const el = document.createElement("button");
    el.className = "lbl"; el.type = "button";
    el.innerHTML = `<i style="background:${CATS[cat].color}"></i><span>${name}</span>`;
    el.addEventListener("click", () => select(key, true));
    el.addEventListener("mouseenter", () => setHover(key));
    el.addEventListener("mouseleave", () => setHover(null));
    box.appendChild(el);
    labelEls.set(key, { el, occ: 0 });
  }
}
let occTimer = 0;
const ray = new THREE.Raycaster(); ray.firstHitOnly = true;
function updateLabels(dt) {
  const svg = $("#leaders");
  if (!ui.labels || !active || !innerWidth || !innerHeight) { svg.innerHTML = ""; return; }   // a 0 x 0 window (hidden tab) has no layout
  const w = innerWidth, h = innerHeight, cx = w / 2 + (insets.l - insets.r) / 2, cy = h / 2 + (insets.t - insets.b) / 2;
  occTimer -= dt; const doOcc = occTimer <= 0; if (doOcc) occTimer = 0.25;
  const placed = []; let lines = "";
  for (const [key, L] of labelEls) {
    const p = active.parts[key];
    const wc = p.worldCenter(tmpV);
    const camDist = wc.distanceTo(camera.position);
    const sp = wc.clone().project(camera);
    if (sp.z > 1 || Math.abs(sp.x) > 1.1 || Math.abs(sp.y) > 1.1) { L.el.style.opacity = 0; L.el.style.pointerEvents = "none"; continue; }
    const x = (sp.x * 0.5 + 0.5) * w, y = (-sp.y * 0.5 + 0.5) * h;
    if (doOcc) {
      ray.set(camera.position, wc.clone().sub(camera.position).normalize());
      const hits = ray.intersectObjects(active.meshes.filter((m) => m.visible && !(ui.xray && (SHELLS.has(m.userData.part) || m.userData.shell))), false);
      L.occ = hits.length && hits[0].distance < camDist - 0.02 && hits[0].object.userData.part !== key ? 1 : 0;
    }
    let dx = x - cx, dy = y - cy; const len = Math.hypot(dx, dy) || 1; dx /= len; dy /= len;
    let lx = x + dx * 70, ly = y + dy * 46;
    const bw = L.bw || (L.bw = L.el.offsetWidth || 120), bh = 26;
    lx = dx < 0 ? lx - bw : lx;
    // clamp first, then slide to the nearest free row (alternating away from / towards the centre)
    const minY = insets.t + (innerWidth > 900 ? 46 : 6), maxY = h - insets.b - bh - 4;   // stay below the view chips (desktop)
    lx = clamp(lx, 8 + (innerWidth > 900 ? insets.l : 0), w - bw - 8 - (innerWidth > 900 ? insets.r : 0));
    const y0 = clamp(ly, minY, maxY), dir = dy >= 0 ? 1 : -1;
    const free = (yy) => !placed.some((q) => lx < q[0] + q[2] + 4 && lx + bw + 4 > q[0] && yy < q[1] + q[3] + 2 && yy + bh + 2 > q[1]);
    ly = y0;
    for (let k = 1; k <= 16 && !free(ly); k++) {
      const step = Math.ceil(k / 2) * (bh + 3) * (k % 2 ? dir : -dir);
      ly = clamp(y0 + step, minY, maxY);
    }
    placed.push([lx, ly, bw, bh]);
    lx = Math.round(lx); ly = Math.round(ly);   // whole pixels keep the label text crisp
    L.el.style.transform = `translate(${lx}px,${ly}px)`;
    const op = L.occ ? 0.42 : 1, isSel = ui.sel === key, isHov = ui.hover === key;
    L.el.style.opacity = op; L.el.style.pointerEvents = "auto";
    L.el.classList.toggle("sel", isSel || isHov);
    const ax = lx + (dx < 0 ? bw : 0), ay = ly + bh / 2;
    lines += `<line x1="${x.toFixed(1)}" y1="${y.toFixed(1)}" x2="${ax.toFixed(1)}" y2="${ay.toFixed(1)}" opacity="${op * (isSel ? 1 : 0.6)}"/><circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${isSel ? 4 : 2.6}" opacity="${op}"/>`;
  }
  svg.innerHTML = lines;
}

// ======================================================================================== picking / highlight
const pointer = new THREE.Vector2(); let pointerDirty = false, downAt = null;
const setPointer = (ev) => pointer.set((ev.clientX / innerWidth) * 2 - 1, -(ev.clientY / innerHeight) * 2 + 1);
canvas.addEventListener("pointermove", (ev) => { setPointer(ev); pointerDirty = true; tip.style.transform = `translate(${ev.clientX + 14}px,${ev.clientY + 14}px)`; });
canvas.addEventListener("pointerleave", () => { setHover(null); });
canvas.addEventListener("pointerdown", (ev) => { downAt = [ev.clientX, ev.clientY]; });
canvas.addEventListener("pointerup", (ev) => {
  if (!downAt || Math.hypot(ev.clientX - downAt[0], ev.clientY - downAt[1]) > 5) return;
  setPointer(ev); // taps and clicks without a preceding move still pick at the right spot
  const k = pick(); if (k) select(k, false); else if (ui.sel) select(null);
});
const tip = $("#tip");
function pick() {
  if (!active) return null;
  ray.setFromCamera(pointer, camera);
  const cand = active.meshes.filter((m) => m.visible && !(ui.xray && (SHELLS.has(m.userData.part) || m.userData.shell)));
  const hits = ray.intersectObjects(cand, false);
  return hits.length ? hits[0].object.userData.part : null;
}
function partInfo(key) {
  if (!key) return null;
  if (key.includes(":")) {
    const [b, ref] = key.split(":"); const c = COMP[b][ref];
    return { name: c ? c[0] : ref, sub: `${ref} on ${b === "pmbh" ? "PMB-H" : "LIB"}`, cat: "elec", what: c ? c[1] : "Passive component.", why: c ? c[2] : "", specs: [], flow: [] , ref };
  }
  return PARTS[key];
}
function setHover(key) {
  if (ui.hover === key) return;
  ui.hover = key;
  canvas.style.cursor = key ? "pointer" : "";
  const info = partInfo(key);
  if (info) { tip.innerHTML = `<b>${info.ref ? info.ref + " · " : ""}${info.name}</b><span>${info.sub || ""}</span>`; tip.classList.add("on"); }
  else tip.classList.remove("on");
  highlightFlowNodes(key);
}
function highlightFlowNodes(key) {
  const info = partInfo(key || ui.sel);
  const nodes = new Set(info && info.flow ? info.flow : []);
  if (key && key.includes(":")) { const ref = key.split(":")[1]; for (const [id, n] of Object.entries(FLOW_NODES)) if (n.comp === ref || (key.startsWith("libb") && id === "lib")) nodes.add(id); }
  $$("#flow g.node").forEach((g) => g.classList.toggle("hl", nodes.has(g.dataset.id)));
}
function applyHighlight(time) {
  if (!active) return;
  const pulse = 0.55 + 0.35 * Math.sin(time * 4.2);
  for (const m of active.meshes) {
    const k = m.userData.part, mat = m.material;
    if (!mat || mat === xrayMat || !mat.emissive) continue;
    let target = 0, col = null;
    if (k === ui.sel) { target = pulse; col = catColor(k); }
    else if (k === ui.hover || hoverFromFlow.has(k)) { target = 0.45; col = catColor(k); }
    if (target) { mat.emissive.copy(col); mat.emissiveIntensity = target; }
    else if (mat.emissiveIntensity) { mat.emissiveIntensity = 0; }
  }
  // battery glows with its net current
  const bat = active.parts.battery;
  if (bat && ui.sel !== "battery" && ui.hover !== "battery") {
    const e = energy(), lvl = clamp(Math.abs(e.net) / 600, 0.15, 1);
    for (const m of bat.meshes) { m.material.emissive.set(e.net >= 0 ? 0x3ddc97 : 0xff8a4c); m.material.emissiveIntensity = ui.flow ? (0.15 + 0.35 * lvl) * (0.7 + 0.3 * Math.sin(time * 3)) : 0; }
  }
  // the chest cable flashes when it is "pulled"
  const w6 = active.parts.W06;
  if (w6) for (const m of w6.meshes) { if (state.mode === "glitch") { m.material.emissive.set(0xff3b5c); m.material.emissiveIntensity = 0.6 + 0.4 * Math.sin(time * 9); } else if (ui.sel !== "W06" && ui.hover !== "W06") m.material.emissiveIntensity = 0; }
}
const catColor = (k) => new THREE.Color(CATS[(partInfo(k) || {}).cat || "elec"].color);
const hoverFromFlow = new Set();

// ======================================================================================== dossier
function select(key, fly) {
  ui.sel = key;
  const d = $("#dossier");
  if (!key) { d.hidden = true; updateInsets(); highlightFlowNodes(null); return; }
  const info = partInfo(key); if (!info) return;
  const cat = CATS[info.cat];
  const flowChips = (info.flow || []).map((id) => `<button type="button" class="chip" data-flow="${id}">${FLOW_NODES[id].t}</button>`).join("");
  const specs = (info.specs || []).map(([a, b]) => `<div><dt>${a}</dt><dd>${b}</dd></div>`).join("");
  const boardBtn = info.board && active.name !== "boards" ? `<button type="button" class="act" data-board="${info.board}">Look inside the board →</button>` : "";
  d.innerHTML = `
    <button type="button" class="x" aria-label="Close" data-close>×</button>
    <p class="eyebrow"><i style="background:${cat.color}"></i>${cat.label}${info.ref ? " · " + info.ref : ""}</p>
    <h2>${info.name}</h2><p class="sub">${info.sub || ""}</p>
    <section><h3>What it is</h3><p>${info.what}</p></section>
    ${info.why ? `<section class="why"><h3>Problem it solves</h3><p>${info.why}</p></section>` : ""}
    ${specs ? `<dl>${specs}</dl>` : ""}
    ${flowChips ? `<div class="chips"><span>In the flow</span>${flowChips}</div>` : ""}
    ${boardBtn}`;
  d.hidden = false;
  d.querySelector("[data-close]").onclick = () => select(null);
  d.querySelectorAll("[data-flow]").forEach((b) => (b.onclick = () => flashFlowNode(b.dataset.flow)));
  const bb = d.querySelector("[data-board]"); if (bb) bb.onclick = () => switchScene("boards").then(() => setView(bb.dataset.board === "libb" ? "libb" : "pmbh"));
  updateInsets();
  highlightFlowNodes(key);
  if (fly && active.parts[key]) {
    const box = active.parts[key].box();
    const c = box.getCenter(new THREE.Vector3());
    const hint = active.name === "boards" ? new THREE.Vector3(0, 1.2, 0.8) : new THREE.Vector3(c.x * 1.5, 0.25, c.z >= 0 ? 1 : -1);
    frameBox(box, hint);
  }
}
function flashFlowNode(id) { const g = $(`#flow g.node[data-id="${id}"]`); if (!g) return; g.classList.remove("flash"); void g.getBBox(); g.classList.add("flash"); if ($("#dock").classList.contains("min")) toggleDock(); }

// ======================================================================================== flow graph (SVG)
const NW = 104, NH = 56;
function edgePath(a, b, kind) {
  const A = FLOW_NODES[a], B = FLOW_NODES[b];
  if (kind === "c") {                         // control: from the XIAO's top up to the bottom of the target
    const x1 = A.x, y1 = A.y - NH / 2, x2 = B.x, y2 = B.y + NH / 2, my = (y1 + y2) / 2;
    return `M${x1},${y1} C${x1},${my} ${x2},${my} ${x2},${y2}`;
  }
  if (Math.abs(A.x - B.x) < 30) {             // vertical
    const y1 = A.y + (B.y > A.y ? NH / 2 : -NH / 2), y2 = B.y - (B.y > A.y ? NH / 2 : -NH / 2), my = (y1 + y2) / 2;
    return `M${A.x},${y1} C${A.x},${my} ${B.x},${my} ${B.x},${y2}`;
  }
  const right = B.x > A.x, x2 = right ? B.x - NW / 2 : B.x + NW / 2, y2 = B.y;
  if (Math.abs(A.y - B.y) > 10) {             // diagonal: leave from top or bottom, arrive from the side
    const x1 = A.x, y1 = A.y + (B.y > A.y ? NH / 2 : -NH / 2);
    return `M${x1},${y1} C${x1},${y2} ${(x1 + x2) / 2},${y2} ${x2},${y2}`;
  }
  const x1 = right ? A.x + NW / 2 : A.x - NW / 2, y1 = A.y, mx = (x1 + x2) / 2;
  return `M${x1},${y1} C${mx},${y1} ${mx},${y2} ${x2},${y2}`;
}
function buildFlowGraph() {
  const svg = $("#flow");
  let edges = "", nodes = "", labels = "";
  FLOW_EDGES.forEach(([a, b, k], i) => {
    const d = edgePath(a, b, k);
    edges += `<path class="e ${k}" id="e-${a}-${b}" d="${d}"/><path class="ef ${k}" id="ef-${a}-${b}" d="${d}"/>`;
  });
  for (const [id, n] of Object.entries(FLOW_NODES)) {
    nodes += `<g class="node ${n.kind || ""}" data-id="${id}" transform="translate(${n.x - NW / 2},${n.y - NH / 2})" tabindex="0" role="button" aria-label="${n.t}">
      <rect width="${NW}" height="${NH}" rx="10"/><text class="t" x="10" y="19">${n.t}</text><text class="s" x="10" y="33">${n.s}</text><text class="v" id="v-${id}" x="10" y="48"></text></g>`;
  }
  labels = `<text class="el" id="l-pv" x="280" y="100" text-anchor="middle"></text><text class="el" id="l-chg" x="560" y="100" text-anchor="middle"></text>
    <text class="el" id="l-load" x="840" y="100" text-anchor="middle"></text><text class="el" id="l-hold" x="1120" y="100" text-anchor="middle"></text>
    <text class="el note" id="l-night" x="350" y="128" text-anchor="middle"></text>`;
  svg.innerHTML = `<defs><linearGradient id="g-e" x1="0" x2="1"><stop offset="0" stop-color="#ffc861"/><stop offset="1" stop-color="#ff9f3d"/></linearGradient></defs>
    <g class="edges">${edges}</g>${labels}<g class="nodes">${nodes}</g>`;
  $$("#flow g.node").forEach((g) => {
    const id = g.dataset.id, n = FLOW_NODES[id];
    const enter = () => { hoverFromFlow.clear(); if (n.part && active && active.parts[n.part]) hoverFromFlow.add(n.part);
      if (active && active.name === "boards" && n.comp) { const k = `${n.part === "lib" ? "libb" : "pmbh"}:${n.comp}`; if (active.parts[k]) hoverFromFlow.add(k); } };
    g.addEventListener("mouseenter", enter); g.addEventListener("focus", enter);
    g.addEventListener("mouseleave", () => hoverFromFlow.clear()); g.addEventListener("blur", () => hoverFromFlow.clear());
    const go = () => {
      if (!n.part) return;
      if (active.name === "boards" && n.comp) { const k = `${n.part === "lib" ? "libb" : "pmbh"}:${n.comp}`; if (active.parts[k]) return select(k, true); }
      if (active.parts[n.part]) select(n.part, true); else if (PARTS[n.part]) select(n.part, false);
    };
    g.addEventListener("click", go); g.addEventListener("keydown", (ev) => { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); go(); } });
  });
}
function edgeSet(a, b, on, speed, width, extraCls) {
  const e = document.getElementById(`ef-${a}-${b}`), base = document.getElementById(`e-${a}-${b}`); if (!e) return;
  e.style.opacity = on ? 1 : 0; base.style.opacity = on ? 0.5 : 0.18;
  e.style.animationDuration = `${(1.6 / Math.max(0.15, speed)).toFixed(2)}s`;
  if (width) e.style.strokeWidth = width;
  base.classList.toggle("broken", extraCls === "broken"); e.classList.toggle("violet", extraCls === "violet");
}
function updateFlowGraph() {
  const e = energy(), lit = state.g > 0 && e.chg > 0.5;
  const pw = clamp(Math.log10(1 + e.p * 10) / Math.log10(48), 0, 1), w = (x) => (1.6 + 4.2 * x).toFixed(2);
  edgeSet("sun", "panel", state.g > 0, 0.4 + pw, w(clamp(state.g / 1000, 0.1, 1)));
  edgeSet("panel", "prot", lit, 0.3 + pw, w(pw));
  edgeSet("prot", "mppt", lit, 0.3 + pw, w(pw));
  edgeSet("mppt", "batt", lit, 0.3 + pw, w(pw));
  const ld = clamp(state.load / 120, 0.15, 1);
  edgeSet("batt", "loadsw", !e.glitch, 0.5, w(ld * 0.6));
  edgeSet("loadsw", "j6", !e.glitch, 0.5, w(ld * 0.6));
  edgeSet("j6", "lib", !e.glitch, 0.5, w(ld * 0.6), e.glitch ? "broken" : "");
  edgeSet("lib", "coreb", true, 0.5, w(ld * 0.6), e.glitch ? "violet" : "");
  for (const [a, b, k] of FLOW_EDGES) if (k !== "e") {
    let on = true; if (a === "refs") on = state.g > 0;
    const ctrl = k === "c" ? ((state.mode === "night" && b === "prot") || (state.mode === "glitch" && b === "lib")) : true;
    edgeSet(a, b, on && ctrl, k === "c" ? 0.6 : 0.7, null);
  }
  const set = (id, t) => { const el = document.getElementById(id); if (el) el.textContent = t; };
  set("l-pv", lit ? `${fmt(e.p, e.p < 1 ? 2 : 1)} W` : "");
  set("l-chg", lit ? `${fmt(e.chg)} mA` : "");
  set("l-load", e.glitch ? "cable pulled" : `${fmt(state.load)} mA`);
  set("l-hold", e.glitch ? `supercaps · ${Math.max(0, 60 - state.glitchT).toFixed(0)} s` : "");
  set("l-night", state.mode === "night" ? "PV_EN: panel switched off · back-feed 51 µA" : "");
  set("v-panel", state.g > 0 ? `${fmt(state.g)} W/m²` : "dark");
  set("v-batt", `${e.net >= 0 ? "+" : "−"}${fmt(Math.abs(e.net))} mA`);
  const vb = document.getElementById("v-batt"); if (vb) vb.setAttribute("class", `v ${e.net >= 0 ? "pos" : "neg"}`);
  set("v-mppt", lit ? `${fmt(e.cap, 1)} %` : "idle");
  set("v-coreb", e.glitch ? "on hold-up" : "recording");
}

// ======================================================================================== mode panel
function setMode(m, keepG) {
  state.mode = m; if (!keepG) state.g = MODES[m].g; state.glitchT = 0;
  $$("#modechips button").forEach((b) => b.classList.toggle("on", b.dataset.m === m));
  $("#g").value = gToSlider(state.g); refreshPanel();
}
const gToSlider = (g) => (g <= 0 ? 0 : Math.round(clamp(Math.log10(g) / 3, 0, 1) * 1000));
const sliderToG = (v) => (v <= 0 ? 0 : Math.round(Math.pow(10, (v / 1000) * 3)));
function refreshPanel() {
  const e = energy();
  $("#g-out").textContent = state.g > 0 ? `${fmt(state.g)} W/m²` : "dark";
  $("#load-out").textContent = `${state.load} mA`;
  const set = (id, v) => ($(id).textContent = v);
  set("#m-p", e.p > 0 ? `${fmt(e.p, e.p < 1 ? 2 : 2)} W` : "0 W");
  set("#m-chg", `${fmt(e.chg)} mA`);
  set("#m-use", e.glitch ? `${SELF_MA} mA` : `${SELF_MA + state.load} mA`);
  const net = $("#m-net"); net.textContent = `${e.net >= 0 ? "+" : "−"}${fmt(Math.abs(e.net))} mA`; net.className = e.net >= 0 ? "pos" : "neg";
  set("#m-share", `${Math.round(e.share * 100)} %`);
  $("#sharebar i").style.width = `${Math.round(e.share * 100)}%`;
  set("#m-alone", `${fmt(e.alone, 1)} h`);
  set("#m-light", e.net >= 0 ? "charging" : `${fmt(Math.min(e.atLight, 999), 1)} h`);
  set("#m-be", Number.isFinite(e.be) ? `${fmt(e.be)} W/m²` : "—");
  $("#modenote").textContent = MODES[state.mode].note;
  updateFlowGraph();
}

// ======================================================================================== scenes
let switching = null;
async function switchScene(name) {
  if (active && active.name === name) return;
  if (!SCENES[name]) {
    $("#busy").hidden = false; $("#busy span").textContent = name === "boards" ? "Loading the board models…" : "Loading…";
    try {
      SCENES[name] = name === "worn" ? await buildWorn() : name === "bench" ? await buildBench() : await buildBoards();
      scene.add(SCENES[name].root); buildFlows(SCENES[name]); setXray(ui.xray);
    } catch (err) { console.error(err); $("#busy span").textContent = "Could not load this view."; return; }
    $("#busy").hidden = true;
  }
  for (const [k, s] of Object.entries(SCENES)) s.root.visible = k === name;
  active = SCENES[name];
  $$("#scenes button").forEach((b) => b.classList.toggle("on", b.dataset.s === name));
  $("#views").innerHTML = Object.entries(active.views).map(([k, v], i) => `<button type="button" data-v="${k}" title="View ${i + 1}">${v[0]}</button>`).join("");
  $$("#views button").forEach((b) => (b.onclick = () => setView(b.dataset.v)));
  buildLabels(); select(null);
  controls.minDistance = name === "boards" ? 0.08 : 0.12;
  bloom.strength = name === "boards" ? 0.2 : 0.45;   // bare metal pads would glare under full bloom
  if (active.shadow) {
    const r = active.shadow.radius, sc = sunLight.shadow.camera;
    sc.left = -r; sc.right = r; sc.top = r; sc.bottom = -r; sc.near = 0.5; sc.far = 6; sc.updateProjectionMatrix();
  }
  gtao.updateGtaoMaterial({ radius: active.ao || 0.05 });
  renderer.shadowMap.needsUpdate = true; geomVersion++;
  setView(active.defaultView);
  applyExplode();
}

// ======================================================================================== tour
let tourI = -1;
function startTour() { tourI = 0; $("#tour").hidden = false; document.body.classList.add("touring"); updateInsets(); showStep(); }
function endTour() { tourI = -1; $("#tour").hidden = true; document.body.classList.remove("touring"); updateInsets(); }
async function showStep() {
  const s = TOUR[tourI]; if (!s) return endTour();
  $("#tour-n").textContent = `${tourI + 1} / ${TOUR.length}`;
  $("#tour-t").textContent = s.title; $("#tour-p").textContent = s.text;
  $("#tour-bar i").style.width = `${((tourI + 1) / TOUR.length) * 100}%`;
  $("#tour-prev").disabled = tourI === 0; $("#tour-next").textContent = tourI === TOUR.length - 1 ? "Finish" : "Next";
  $("#tour-asks").hidden = !s.finale;
  await switchScene(s.scene);
  setMode(s.mode); setXray(!!s.xray); setLabels(!!s.labels); setFlow(true);
  ui.explodeTarget = s.explode; $("#explode").value = Math.round(s.explode * 100);
  if (s.flow && $("#dock").classList.contains("min")) toggleDock();
  if (s.focus) { select(s.focus, false); } else select(null);
  setView(s.view);
}
function nextStep(d) { if (tourI < 0) return; tourI = clamp(tourI + d, 0, TOUR.length); if (tourI >= TOUR.length) return endTour(); showStep(); }

// ======================================================================================== dock
function syncModesBtn() { const on = !$("#modes").hidden; $("#t-modes").classList.toggle("on", on); $("#t-modes").setAttribute("aria-pressed", on); }
function toggleDock() { $("#dock").classList.toggle("min"); $("#t-dock").setAttribute("aria-expanded", !$("#dock").classList.contains("min")); updateInsets(); }

// ======================================================================================== wiring of the static UI
function bindUI() {
  $("#modechips").innerHTML = Object.entries(MODES).map(([k, m]) => `<button type="button" data-m="${k}">${m.label}</button>`).join("");
  $$("#modechips button").forEach((b) => (b.onclick = () => setMode(b.dataset.m)));
  $("#g").addEventListener("input", (ev) => { state.g = sliderToG(+ev.target.value); if (state.mode === "night" && state.g > 0) state.mode = "cloud"; if (state.g === 0 && state.mode !== "glitch") state.mode = "night";
    $$("#modechips button").forEach((b) => b.classList.toggle("on", b.dataset.m === state.mode && MODES[state.mode].g === state.g)); refreshPanel(); });
  $("#load").addEventListener("input", (ev) => { state.load = +ev.target.value; refreshPanel(); });
  $("#t-xray").onclick = () => setXray(!ui.xray);
  $("#t-labels").onclick = () => setLabels(!ui.labels);
  $("#t-flow").onclick = () => setFlow(!ui.flow);
  $("#explode").addEventListener("input", (ev) => (ui.explodeTarget = +ev.target.value / 100));
  $("#t-explode").onclick = () => { ui.explodeTarget = ui.explodeTarget > 0.5 ? 0 : 1; $("#explode").value = Math.round(ui.explodeTarget * 100); };
  $("#t-present").onclick = () => (tourI >= 0 ? endTour() : startTour());
  $("#tour-prev").onclick = () => nextStep(-1); $("#tour-next").onclick = () => nextStep(1); $("#tour-x").onclick = endTour;
  $("#t-dock").onclick = toggleDock;
  $$("#scenes button").forEach((b) => (b.onclick = () => switchScene(b.dataset.s)));
  $("#t-modes").onclick = () => { $("#modes").hidden = !$("#modes").hidden; syncModesBtn(); updateInsets(); };
  addEventListener("keydown", (ev) => {
    if (ev.target.closest && ev.target.closest("input, textarea")) return;
    const k = ev.key.toLowerCase();
    if (tourI >= 0 && (k === "arrowright" || k === " " || k === "pagedown")) { ev.preventDefault(); return nextStep(1); }
    if (tourI >= 0 && (k === "arrowleft" || k === "pageup")) { ev.preventDefault(); return nextStep(-1); }
    if (k === "escape") { if (tourI >= 0) endTour(); else select(null); }
    if (k === "x") setXray(!ui.xray);
    if (k === "l") setLabels(!ui.labels);
    if (k === "e") $("#t-explode").click();
    if (k === "f") toggleDock();
    if (k === "p") $("#t-present").click();
    if (/^[1-9]$/.test(k) && active) { const v = Object.keys(active.views)[+k - 1]; if (v) setView(v); }
  });
}

// ======================================================================================== main loop
const clock = new THREE.Clock();
function frame() {
  const dt = Math.min(0.05, clock.getDelta()), t = clock.elapsedTime;
  if (tween) {
    tween.k = Math.min(1, tween.k + dt / tween.dur); const k = ease(tween.k);
    camera.position.lerpVectors(tween.p0, tween.p1, k); controls.target.lerpVectors(tween.t0, tween.t1, k);
    if (tween.k >= 1) tween = null;
  }
  controls.update();
  if (Math.abs(ui.explode - ui.explodeTarget) > 0.001) { ui.explode += (ui.explodeTarget - ui.explode) * Math.min(1, dt * 3.2); applyExplode(); renderer.shadowMap.needsUpdate = true; geomVersion++; }
  if (state.mode === "glitch") { state.glitchT = (state.glitchT + dt) % 60; if (Math.floor(t * 4) % 4 === 0) updateFlowGraph(); }
  if (pointerDirty) { pointerDirty = false; setHover(pick()); }
  // light follows the irradiance
  const gl = clamp(state.g / 1000, 0, 1);
  sunLight.intensity = 0.25 + 2.6 * gl; sunLight.color.set(state.g > 0 ? 0xfff0de : 0x8fb3ff);
  if (active && active.shadow) {
    const c = active.shadow.center, dir = tmpV2.copy(active.sunPos || tmpV.set(c.x + 0.6, c.y + 2, c.z + 0.8)).sub(c).normalize();
    sunLight.position.copy(c).addScaledVector(dir, 3); sunLight.target.position.copy(c);
  }
  hemi.intensity = 0.18 + 0.12 * gl;
  applyFlows(dt); applyHighlight(t); updateLabels(dt);
  composer.render();
  if (sanitize.uniforms.uDebug.value && (nanFrame = (nanFrame + 1) % 20) === 0) countBadPixels();
  requestAnimationFrame(frame);
}
// ---------------------------------------------------------------- connection and fit checks (run from #debug)
// Every lead's plug against the connector it is meant for. Plug body ≤ 10 mm from the connector centre; a UC-E6 tongue
// ≤ 4 mm from its socket's mouth.
const CABLE_PLAN = [["W01_conn1", "PMB-H:J1"], ["W02_conn1", "PMB-H:J2"], ["W03_conn1", "PMB-H:J3"], ["W04_conn1", "PMB-H:J7"], ["W05_conn1", "PMB-H:J8"],
  ["W06_conn0", "PMB-H:J6"], ["W06_conn1", "LIB:J1"], ["W07_conn0", "LIB:J2"], ["W07_conn1", "B:BAT"], ["W08_conn0", "LIB:J3"], ["W08_conn1_tongue", "B:I1"],
  ["W09_conn1_tongue", "B:A2"], ["W11_conn0_tongue", "C:ECG"], ["W12_conn1", "C:PWR"], ["W13_conn0_tongue", "A:ppg"]];
function verifyCables() {
  const sc = SCENES.worn, cen = (nm) => { const m = sc.meshes.find((x) => x.userData.srcName === nm); return m ? new THREE.Box3().setFromObject(m).getCenter(new THREE.Vector3()) : null; };
  const rows = CABLE_PLAN.map(([plug, port]) => {
    if (port === "A:ppg") port = `A:${sc.ppgPort}`;
    const p = cen(plug), q = sc.ports && sc.ports[port]; if (!p || !q) return [plug, port, null, "MISSING"];
    if (/tongue/.test(plug)) {
      const rel = p.clone().sub(q.mouth), depth = -rel.dot(q.out) * 1000, off = rel.addScaledVector(q.out, rel.dot(q.out) * -1).length() * 1000;
      return [plug, port, `${depth.toFixed(1)} mm in, ${off.toFixed(1)} mm off-axis`, depth >= 0.5 && depth <= 6 && off <= 1.5 ? "PASS" : "FAIL"];
    }
    const d = p.distanceTo(q.at) * 1000;
    return [plug, port, +d.toFixed(1), d <= 10 ? "PASS" : "FAIL"];
  });
  for (const [h, j] of [["xiao_hdr_a", "PMB-H:J4"], ["xiao_hdr_b", "PMB-H:J5"]]) { const p = cen(h), q = sc.ports["PMB-H:" + j.split(":")[1]]; if (p && q) { const d = p.distanceTo(q.at) * 1000; rows.push([h, j, +d.toFixed(1), d <= 12 ? "PASS" : "FAIL"]); } }
  return rows;
}
// Every board against its housing, by signed distance: for each sampled board point, the closest point on the housing
// surface and that face's outward normal. Behind the surface by > 0.3 mm = cutting into the wall. "outside" = the point
// escapes the housing in ≥ 3 of 6 axis directions (sockets at their windows legitimately reach the opening).
function fitCheck() {
  const sc = SCENES.worn, rc = new THREE.Raycaster(); rc.firstHitOnly = true; rc.far = 0.3;
  const meshesOf = (keys, f = () => true) => sc.meshes.filter((m) => keys.includes(m.userData.part) && f(m));
  const sample = (ms, n = 900) => { const pts = []; for (const m of ms) { const p = m.geometry.attributes.position, st = Math.max(1, Math.floor(p.count / (n / ms.length))); for (let i = 0; i < p.count; i += st) { const v = new THREE.Vector3().fromBufferAttribute(p, i).applyMatrix4(m.matrixWorld); v.src = m.name || m.userData.srcName || "?"; pts.push(v); } } return pts; };
  const dirs = [[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]].map((d) => new THREE.Vector3(...d));
  const tri = [new THREE.Vector3(), new THREE.Vector3(), new THREE.Vector3()];
  const signedTo = (p, housing) => {     // most negative signed distance (mm) of p to the housing surfaces (closest face decides)
    let best = null;
    for (const m of housing) {
      const inv = m.matrixWorld.clone().invert(), hit = m.geometry.boundsTree.closestPointToPoint(p.clone().applyMatrix4(inv), {});
      if (!hit) continue;
      const g = m.geometry, ix = g.index, f = hit.faceIndex;
      for (let k = 0; k < 3; k++) tri[k].fromBufferAttribute(g.attributes.position, ix ? ix.getX(f * 3 + k) : f * 3 + k).applyMatrix4(m.matrixWorld);
      const nrm = new THREE.Vector3().subVectors(tri[1], tri[0]).cross(new THREE.Vector3().subVectors(tri[2], tri[0])).normalize();
      const cp = hit.point.clone().applyMatrix4(m.matrixWorld), d = p.distanceTo(cp);
      if (!best || d < best.d) best = { d, sgn: Math.sign(p.clone().sub(cp).dot(nrm)) || 1 };
    }
    return best ? best.d * best.sgn * 1000 : Infinity;
  };
  // inside the material? cast 6 rays; for each first hit, a face normal along the ray means the ray is leaving material.
  // Majority vote, robust where the closest-face sign is ambiguous (slot edges, open meshes).
  const rc6 = new THREE.Raycaster(); rc6.firstHitOnly = true; rc6.far = 0.05;
  const inMaterial = (p, housing) => { let ex = 0, en = 0;
    for (const d of dirs) { rc6.set(p, d); const h = rc6.intersectObjects(housing, false)[0]; if (!h || !h.face) continue;
      const nw = h.face.normal.clone().transformDirection(h.object.matrixWorld); if (nw.dot(d) > 0) ex++; else en++; }
    return ex > en; };
  const test = (label, board, housing) => {
    const pts = sample(board); let cut = 0, worst = 0, outside = 0; const who = {};
    for (const p of pts) {
      const sd = signedTo(p, housing); if (sd < -0.3 && inMaterial(p, housing)) { cut++; worst = Math.min(worst, sd); who[p.src] = Math.min(who[p.src] || 0, +sd.toFixed(2)); }
      let esc = 0; for (const d of dirs) { rc.set(p, d); if (!rc.intersectObjects(housing, false).length) esc++; }
      if (esc >= 3) outside++;
    }
    return [label, pts.length, +(100 * cut / pts.length).toFixed(1), +worst.toFixed(2), +(100 * outside / pts.length).toFixed(1), who];
  };
  // board ↔ board: unsigned closest approach (their meshes are open, so no inside/outside)
  const gap = (a, b) => { let best = Infinity; for (const p of sample(a, 1500)) for (const m of b) { const inv = m.matrixWorld.clone().invert(), hit = m.geometry.boundsTree.closestPointToPoint(p.clone().applyMatrix4(inv), {}); if (hit) best = Math.min(best, hit.point.applyMatrix4(m.matrixWorld).distanceTo(p)); } return +(best * 1000).toFixed(2); };
  // ray hits must not depend on what is being rendered: test every surface double-sided, then restore
  const sides = new Map(); sc.meshes.forEach((m) => { const mt = m.material; if (mt && !sides.has(mt)) { sides.set(mt, mt.side); mt.side = THREE.DoubleSide; } });
  const shellA = meshesOf(["unit_a"], (m) => m.userData.shell), coreA = meshesOf(["unit_a"], (m) => !m.userData.shell);
  const rows = [test("PMB-H in back pod", meshesOf(["pmbh"]), meshesOf(["back_pod", "back_pod_lid"])), test("Li-Po in back pod", meshesOf(["battery"]), meshesOf(["back_pod", "back_pod_lid"])),
    test("XIAO in back pod", meshesOf(["xiao"]), meshesOf(["back_pod", "back_pod_lid"])), test("LIB in chest pod", meshesOf(["lib"]), meshesOf(["chest_pod", "chest_pod_lid"])),
    test("Core B in chest pod", meshesOf(["core_b"]), meshesOf(["chest_pod", "chest_pod_lid"])), test("Board Kit in C case", meshesOf(["c_board"], (m) => !/battery/.test(m.userData.srcName || "")), meshesOf(["c_case"])),
    test("Core A in HeartBIT case", coreA, shellA), test("Core A vs tray", coreA, shellA.filter((m) => m.name === "tray")), test("Core A vs lid", coreA, shellA.filter((m) => m.name === "lid")),
    test("Core B vs chest pod base", meshesOf(["core_b"]), meshesOf(["chest_pod"])), test("Core B vs chest pod lid", meshesOf(["core_b"]), meshesOf(["chest_pod_lid"]))];
  // socket access through the housing: from each socket mouth, a 30 mm ray outward must leave without hitting the wall
  const access = (tag, housing) => Object.entries(sc.ports).filter(([k]) => k.startsWith(tag + ":") && sc.ports[k].mouth).map(([k, q]) => {
    rc.far = 0.03; rc.set(q.mouth.clone().addScaledVector(q.out, 0.0004), q.out); const h = rc.intersectObjects(housing, false); rc.far = 0.3;
    return `${k.split(":")[1]}${h.length ? "✗" + (h[0].distance * 1000).toFixed(1) : "✓"}`; }).join(" ");
  rows.push([`B socket windows: ${access("B", meshesOf(["chest_pod", "chest_pod_lid"]))}`, 0, 0, 0, 0, {}]);
  rows.push([`C socket windows: ${access("C", meshesOf(["c_case"]))}`, 0, 0, 0, 0, {}]);
  rows.push([`A socket windows: ${access("A", shellA)}`, 0, 0, 0, 0, {}]);
  for (const [nm, hk] of [["W08_conn1", ["chest_pod", "chest_pod_lid"]], ["W09_conn1", ["chest_pod", "chest_pod_lid"]], ["W07_conn1", ["chest_pod", "chest_pod_lid"]], ["W11_conn0", ["c_case"]], ["W12_conn1", ["c_case"]], ["W13_conn0", []]]) {
    const m = sc.meshes.find((x) => x.userData.srcName === nm); if (!m) continue;
    rows.push(test(`plug ${nm}`, [m], hk.length ? meshesOf(hk) : shellA));
  }
  sides.forEach((sd, mt) => { mt.side = sd; });
  const lines = rows.map(([l, n, cut, worst, out, who]) => n === 0 ? l : `${l}: n=${n}  cutting-into ${cut}% (deepest ${worst} mm)  outside ${out}%${cut ? "  by " + JSON.stringify(who) : ""}`);
  lines.push(`gap Core B ↔ LIB: ${gap(meshesOf(["core_b"]), meshesOf(["lib"]))} mm`, `gap Board Kit ↔ its Li-Po: ${gap(meshesOf(["c_board"], (m) => !/battery/.test(m.userData.srcName || "")), meshesOf(["c_board"], (m) => /battery/.test(m.userData.srcName || "")))} mm`,
    `gap PMB-H ↔ back-pod Li-Po: ${gap(meshesOf(["pmbh"]), meshesOf(["battery"]))} mm`);
  return lines;
}
// #debug exposes the live objects for inspection from the console
if (location.hash.includes("debug")) window.__SV = { THREE, EXTRAS, verify: () => verifyCables(), fit: () => fitCheck(), kit: () => SCENES.worn && SCENES.worn.kitInfo, jump: (p, t) => { tween = null; camera.position.set(...p); controls.target.set(...t); controls.update(); }, parseBoard: (n) => parseBoard(n), countBadPixels: () => countBadPixels(), aoStats, aoCam, get geomVersion() { return geomVersion; }, scene, camera, renderer, composer, gtao, bloom, sanitize, sunLight, fill, hemi, SCENES, get active() { return active; } };
// #nan diagnosis: count the marker colours painted by the sanitize pass (bloom is off in this mode)
let nanFrame = 0; window.__nan = { frames: 0, magenta: 0, cyan: 0, yellow: 0, last: null };
function countBadPixels() {
  const gl = renderer.getContext(), w = gl.drawingBufferWidth, h = gl.drawingBufferHeight, px = new Uint8Array(w * h * 4);
  gl.readPixels(0, 0, w, h, gl.RGBA, gl.UNSIGNED_BYTE, px);
  let m = 0, c = 0, y = 0, lit = 0;
  for (let i = 0; i < px.length; i += 4) { const r = px[i], g = px[i + 1], b = px[i + 2];
    if (r + g + b > 60) lit++;
    if (r > 250 && g < 5 && b > 250) m++; else if (r < 5 && g > 250 && b > 250) c++; else if (r > 250 && g > 250 && b < 5) y++; }
  const N = window.__nan; N.frames++; N.magenta += m; N.cyan += c; N.yellow += y; N.last = { m, c, y, lit, w, h };
}

// ======================================================================================== boot
(async function boot() {
  bindUI(); buildFlowGraph();
  if (innerWidth <= 900) { $("#modes").hidden = true; syncModesBtn(); }   // phones: model first, panel on demand
  sunSprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: radialTexture([[0, "rgba(255,240,200,1)"], [0.18, "rgba(255,200,110,0.9)"], [0.5, "rgba(255,150,60,0.25)"], [1, "rgba(0,0,0,0)"]]), transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
  sunSprite.renderOrder = 11; scene.add(sunSprite);
  updateInsets();
  requestAnimationFrame(frame);
  try { await switchScene("worn"); } catch (e) { console.error(e); }
  setMode("sun"); setXray(false); setLabels(true); setFlow(true);
  $("#boot").classList.add("done"); window.__bootMs = Math.round(performance.now());
  setTimeout(() => { $("#boot").hidden = true; }, 700);
  // warm the board models in the background so the board view opens instantly
  setTimeout(() => {
    const up = () => Object.values(SCENES).forEach((sc) => upgradeBoards(sc).catch((e) => console.error(e)));
    if (window.SV_BOARDS) up(); else loadScript("models-boards.js").then(up).catch(() => {});
  }, 1200);
})();
