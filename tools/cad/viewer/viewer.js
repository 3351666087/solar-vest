// Solar-vest 3D viewer component — shared by the local viewer (zh) and the vice-dean brief (en).
// mountViewer(root, opts) builds canvas + overlay UI inside `root`. Models come from window.SV_MODELS (base64, for
// file:// use) or are fetched over HTTP. Group membership comes from an index {nodeName: group}.
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";
import { MeshoptDecoder } from "three/examples/jsm/libs/meshopt_decoder.module.js";

const CSS = `
.sv{position:relative;overflow:hidden;isolation:isolate;color:var(--sv-ink);font:13px/1.45 var(--sv-font);
  background:radial-gradient(120% 90% at 50% 0%,var(--sv-bg-hi) 0%,var(--sv-bg) 62%,var(--sv-bg-lo) 100%)}
.sv canvas{position:absolute;inset:0;width:100%;height:100%;display:block;outline:none;touch-action:none}
.sv-glass{background:var(--sv-glass);border:1px solid var(--sv-line);backdrop-filter:blur(14px) saturate(1.3);-webkit-backdrop-filter:blur(14px) saturate(1.3);
  box-shadow:0 1px 0 var(--sv-hl) inset,0 10px 30px -12px var(--sv-shadow);border-radius:14px}
.sv-btn{appearance:none;border:0;background:transparent;color:var(--sv-ink);font:inherit;cursor:pointer;border-radius:9px;
  transition:background .15s,color .15s,transform .15s}
.sv-btn:hover{background:var(--sv-hover)}.sv-btn:active{transform:scale(.97)}
.sv-btn:focus-visible{outline:2px solid var(--sv-acc);outline-offset:1px}
.sv-tools{position:absolute;top:14px;right:14px;display:flex;gap:2px;padding:4px;z-index:3}
.sv-tools .sv-btn{width:34px;height:34px;display:grid;place-items:center}
.sv-tools .sv-btn.on{color:var(--sv-acc);background:var(--sv-acc-soft)}
.sv-tools svg{width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round}
.sv-panel{position:absolute;top:14px;left:14px;width:268px;max-height:calc(100% - 96px);display:flex;flex-direction:column;z-index:3;transition:transform .25s,opacity .25s}
.sv-panel.hide{transform:translateX(-12px);opacity:0;pointer-events:none}
.sv-ph{display:flex;align-items:center;justify-content:space-between;padding:12px 14px 8px}
.sv-ph b{font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--sv-mute);font-weight:600}
.sv-ph .sv-btn{font-size:12px;padding:3px 8px;color:var(--sv-mute)}
.sv-layers{overflow:auto;padding:0 6px 8px;scrollbar-width:thin}
.sv-layer{display:flex;align-items:center;gap:10px;padding:6px 8px;border-radius:9px;cursor:pointer;user-select:none}
.sv-layer:hover{background:var(--sv-hover)}
.sv-dot{width:9px;height:9px;border-radius:50%;flex:none;box-shadow:0 0 0 2px var(--sv-glass)}
.sv-layer span{flex:1;min-width:0}
.sv-layer.off span,.sv-layer.off .sv-dot{opacity:.38}
.sv-solo{opacity:0;font-size:11px;padding:2px 6px!important;color:var(--sv-mute)!important}
.sv-layer:hover .sv-solo{opacity:1}
.sv-sw{width:28px;height:16px;border-radius:9px;background:var(--sv-track);position:relative;flex:none;transition:background .2s}
.sv-sw:after{content:"";position:absolute;top:2px;left:2px;width:12px;height:12px;border-radius:50%;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.3);transition:transform .2s}
.sv-layer:not(.off) .sv-sw{background:var(--sv-acc)}.sv-layer:not(.off) .sv-sw:after{transform:translateX(12px)}
.sv-facts{border-top:1px solid var(--sv-line);margin:2px 8px 0;padding:8px 6px 10px;display:grid;gap:5px}
.sv-fact{display:flex;justify-content:space-between;gap:10px;font-size:12px}.sv-fact i{font-style:normal;color:var(--sv-mute)}.sv-fact b{font-weight:600;text-align:right}
.sv-bottom{position:absolute;left:50%;bottom:14px;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;gap:8px;z-index:3;max-width:calc(100% - 28px)}
.sv-seg{display:flex;padding:3px;gap:2px}
.sv-seg .sv-btn{padding:6px 14px;font-weight:600;font-size:12.5px;color:var(--sv-mute)}
.sv-seg .sv-btn.on{background:var(--sv-acc);color:#fff;box-shadow:0 4px 12px -4px var(--sv-acc)}
.sv-views{display:flex;gap:2px;padding:3px;overflow-x:auto;max-width:100%;scrollbar-width:none}
.sv-views .sv-btn{padding:6px 11px;white-space:nowrap;font-size:12.5px}
.sv-views .sv-btn.on{color:var(--sv-acc);background:var(--sv-acc-soft)}
.sv-tip{position:absolute;z-index:4;pointer-events:none;padding:7px 10px;font-size:12px;border-radius:10px;opacity:0;transform:translate(12px,12px);transition:opacity .12s;max-width:260px}
.sv-tip b{display:block;font-size:12.5px}.sv-tip i{font-style:normal;color:var(--sv-mute);font-size:11.5px}
.sv-load{position:absolute;inset:0;display:grid;place-items:center;z-index:5;transition:opacity .4s}
.sv-load.done{opacity:0;pointer-events:none}
.sv-load div{width:220px;text-align:center;color:var(--sv-mute);font-size:12px}
.sv-bar{height:3px;border-radius:2px;background:var(--sv-track);margin-top:10px;overflow:hidden}
.sv-bar i{display:block;height:100%;width:0;background:var(--sv-acc);transition:width .2s}
.sv-hint{position:absolute;right:18px;top:64px;font-size:11.5px;color:var(--sv-mute);z-index:2;text-align:right;line-height:1.7}
.sv-hint kbd{font:inherit;font-size:10.5px;padding:0 5px;border:1px solid var(--sv-line);border-radius:4px;background:var(--sv-glass)}
@media (max-width:980px){.sv-hint{display:none}}
@media (max-width:720px){.sv-panel{top:auto;bottom:108px;left:10px;right:10px;width:auto;max-height:40%}.sv-hint{display:none}
  .sv-tools{top:10px;right:10px}}
`;
const ICON = {
  layers: '<svg viewBox="0 0 24 24"><path d="M12 3 3 8l9 5 9-5-9-5Z"/><path d="m3 13 9 5 9-5"/></svg>',
  reset: '<svg viewBox="0 0 24 24"><path d="M3 12a9 9 0 1 0 3-6.7"/><path d="M3 4v5h5"/></svg>',
  spin: '<svg viewBox="0 0 24 24"><path d="M21 12a9 9 0 0 1-15.5 6.2"/><path d="M3 12A9 9 0 0 1 18.5 5.8"/><path d="M18 2v4h-4"/><path d="M6 22v-4h4"/></svg>',
  shot: '<svg viewBox="0 0 24 24"><rect x="3" y="6" width="18" height="14" rx="3"/><circle cx="12" cy="13" r="3.5"/><path d="M9 6l1.5-2h3L15 6"/></svg>',
  full: '<svg viewBox="0 0 24 24"><path d="M4 9V4h5M20 9V4h-5M4 15v5h5M20 15v5h-5"/></svg>',
};
const PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948", "#5b8def", "#9a6b3f", "#3aa6b9", "#8a8f98"];
const TRANSLUCENT = new Set(["back_pod_lid", "chest_pod_lid", "C_lid", "cover"]);

let cssDone = false;
function injectCSS() { if (cssDone) return; const s = document.createElement("style"); s.textContent = CSS; document.head.appendChild(s); cssDone = true; }
function b64ToBuffer(b64) { const bin = atob(b64); const u = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i); return u.buffer; }
const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };

export function mountViewer(root, opts) {
  injectCSS();
  const T = Object.assign({ layers: "Layers", all: "All", solo: "Only", loading: "Loading model…", hint: "Drag to orbit · Scroll to zoom · Right-drag to pan",
    reset: "Reset view", spin: "Auto-rotate", shot: "Save image", full: "Full screen", panel: "Layers",
    keys: "<kbd>1</kbd>–<kbd>9</kbd> views · <kbd>R</kbd> reset · <kbd>A</kbd> rotate · <kbd>F</kbd> full screen" }, opts.strings || {});
  root.classList.add("sv");
  const canvas = el("canvas"); canvas.tabIndex = 0; root.appendChild(canvas);
  const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(Math.min(2, devicePixelRatio));
  renderer.outputColorSpace = THREE.SRGBColorSpace; renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.05;
  renderer.setClearColor(0x000000, 0);
  const scene = new THREE.Scene();
  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  const key = new THREE.DirectionalLight(0xffffff, 1.1); key.position.set(1.5, 3, 2); scene.add(key);
  const rim = new THREE.DirectionalLight(0xdfe8ff, 0.6); rim.position.set(-2, 2, -2.5); scene.add(rim);
  const camera = new THREE.PerspectiveCamera(30, 1, 0.01, 30);
  const controls = new OrbitControls(camera, canvas);
  controls.enableDamping = true; controls.dampingFactor = 0.08; controls.autoRotateSpeed = 0.8; controls.autoRotate = !!opts.autoRotate;

  // ---------- overlay UI ----------
  const load = el("div", "sv-load", `<div><span class="sv-lt">${T.loading}</span><div class="sv-bar"><i></i></div></div>`); root.appendChild(load);
  const tools = el("div", "sv-tools sv-glass"); root.appendChild(tools);
  const mkTool = (k, title, fn) => { const b = el("button", "sv-btn", ICON[k]); b.title = title; b.setAttribute("aria-label", title); b.onclick = fn; tools.appendChild(b); return b; };
  const panel = el("div", "sv-panel sv-glass"); root.appendChild(panel);
  const bLayers = mkTool("layers", T.panel, () => { panel.classList.toggle("hide"); bLayers.classList.toggle("on", !panel.classList.contains("hide")); });
  bLayers.classList.add("on");
  mkTool("reset", T.reset, () => view(cfg.start));
  const bSpin = mkTool("spin", T.spin, () => { controls.autoRotate = !controls.autoRotate; bSpin.classList.toggle("on", controls.autoRotate); });
  bSpin.classList.toggle("on", controls.autoRotate);
  if (!opts.noShot) mkTool("shot", T.shot, screenshot);
  const goFull = () => { try { const p = document.fullscreenElement ? document.exitFullscreen() : root.requestFullscreen && root.requestFullscreen(); if (p && p.catch) p.catch(() => {}); } catch (e) {} };
  if (!opts.noFull) mkTool("full", T.full, goFull);
  if (opts.compact) { panel.classList.add("hide"); bLayers.classList.remove("on"); }
  const bottom = el("div", "sv-bottom"); root.appendChild(bottom);
  const seg = el("div", "sv-seg sv-glass"); const views = el("div", "sv-views sv-glass");
  if ((opts.sceneOrder || []).length > 1) bottom.appendChild(seg);
  bottom.appendChild(views);
  const tip = el("div", "sv-tip sv-glass"); root.appendChild(tip);
  if (!opts.compact && !opts.noHint) root.appendChild(el("div", "sv-hint", T.hint + "<br>" + T.keys));

  // ---------- scene loading ----------
  const loader = new GLTFLoader(); loader.setMeshoptDecoder(MeshoptDecoder);
  const cache = {}; let current = null, groups = {}, cfg = null, shadow = null, activeView = null;
  async function getModel(file, onProgress) {
    if (cache[file]) return cache[file];
    const emb = window.SV_MODELS && window.SV_MODELS[file];
    const gltf = emb ? await new Promise((res, rej) => loader.parse(b64ToBuffer(emb), "", res, rej)) : await loader.loadAsync(file, onProgress);
    return (cache[file] = gltf);
  }
  function blobShadow(box) {
    const c = document.createElement("canvas"); c.width = c.height = 256; const g = c.getContext("2d");
    const grd = g.createRadialGradient(128, 128, 0, 128, 128, 128); grd.addColorStop(0, "rgba(0,0,0,0.32)"); grd.addColorStop(1, "rgba(0,0,0,0)");
    g.fillStyle = grd; g.fillRect(0, 0, 256, 256);
    const s = box.getSize(new THREE.Vector3()), m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: new THREE.CanvasTexture(c), transparent: true, depthWrite: false }));
    m.rotation.x = -Math.PI / 2; m.scale.set(Math.max(s.x, s.z) * 1.6, Math.max(s.x, s.z) * 1.6, 1); m.position.set((box.min.x + box.max.x) / 2, box.min.y - 0.004, (box.min.z + box.max.z) / 2);
    m.renderOrder = -1; m.userData.skipPick = true; return m;
  }
  async function loadScene(kind) {
    cfg = opts.scenes[kind]; load.classList.remove("done"); load.querySelector(".sv-lt").textContent = T.loading;
    const bar = load.querySelector(".sv-bar i"); bar.style.width = "8%";
    [...seg.children].forEach(b => b.classList.toggle("on", b.dataset.k === kind));
    if (current) { scene.remove(current); if (shadow) scene.remove(shadow); }
    const index = typeof cfg.index === "string" ? (window.SV_INDEX && window.SV_INDEX[cfg.index]) || await (await fetch(cfg.index)).json() : cfg.index;
    let gltf = null, used = null;
    for (const f of cfg.files) {
      try { gltf = await getModel(f, e => { if (e.total) bar.style.width = (8 + 90 * e.loaded / e.total).toFixed(0) + "%"; }); used = f; break; } catch (e) { /* try next file */ }
    }
    if (!gltf) { load.querySelector(".sv-lt").textContent = "Model not found"; return; }
    bar.style.width = "100%";
    current = gltf.scene; groups = {};
    current.traverse(o => {
      if (!o.isMesh) return;
      const g = index[o.name] || index[(o.parent && o.parent.name) || ""] || "vest";
      (groups[g] = groups[g] || []).push(o); o.userData.group = g;
      if (!o.userData.prepared) {
        o.material = o.material.clone(); o.material.side = THREE.DoubleSide;
        if ("metalness" in o.material) { o.material.metalness = Math.min(o.material.metalness, 0.35); o.material.roughness = Math.max(o.material.roughness, 0.45); }
        if (TRANSLUCENT.has(g)) { o.material.transparent = true; o.material.opacity = 0.32; o.material.depthWrite = false; }
        if (g === "torso") { o.material.transparent = true; o.material.opacity = 0.85; }
        if (/glass/i.test(o.name)) { o.material.transparent = true; o.material.opacity = 0.22; o.material.depthWrite = false; }
        o.userData.baseEmissive = o.material.emissive ? o.material.emissive.clone() : null; o.userData.prepared = true;
      }
      o.visible = !(cfg.hidden || []).includes(g);
    });
    scene.add(current);
    shadow = blobShadow(new THREE.Box3().setFromObject(current)); scene.add(shadow);
    buildPanel(); buildViews(); view(cfg.start, true);
    setTimeout(() => load.classList.add("done"), 150);
    opts.onLoad && opts.onLoad(kind, used);
    window.__groups = groups;
  }
  function buildPanel() {
    panel.innerHTML = ""; const head = el("div", "sv-ph", `<b>${T.layers}</b>`); const all = el("button", "sv-btn", T.all); head.appendChild(all); panel.appendChild(head);
    const list = el("div", "sv-layers"); panel.appendChild(list); let i = 0; const rows = {};
    for (const g of Object.keys(cfg.names)) {
      if (!groups[g]) continue;
      const vis = groups[g][0].visible; const row = el("div", "sv-layer" + (vis ? "" : " off"));
      row.innerHTML = `<i class="sv-dot" style="background:${(cfg.colors && cfg.colors[g]) || PALETTE[i++ % PALETTE.length]}"></i><span>${cfg.names[g]}</span><button class="sv-btn sv-solo">${T.solo}</button><i class="sv-sw"></i>`;
      row.onclick = e => { if (e.target.classList.contains("sv-solo")) return; setGroup(g, row.classList.contains("off")); };
      row.querySelector(".sv-solo").onclick = () => Object.keys(rows).forEach(k => setGroup(k, k === g));
      rows[g] = row; list.appendChild(row);
    }
    all.onclick = () => Object.keys(rows).forEach(k => setGroup(k, true));
    function setGroup(g, on) { groups[g].forEach(o => (o.visible = on)); rows[g].classList.toggle("off", !on); }
    if (cfg.facts && cfg.facts.length) {
      const f = el("div", "sv-facts"); cfg.facts.forEach(([a, b]) => f.appendChild(el("div", "sv-fact", `<i>${a}</i><b>${b}</b>`))); panel.appendChild(f);
    }
  }
  function buildViews() {
    views.innerHTML = "";
    Object.entries(cfg.views).forEach(([k, v], i) => { const b = el("button", "sv-btn", v[0]); b.dataset.k = k; b.title = `${v[0]} (${i + 1})`; b.onclick = () => view(k); views.appendChild(b); });
  }
  // smooth camera flights
  let fly = null;
  function view(k, instant) {
    const v = cfg.views[k]; if (!v) return; activeView = k;
    [...views.children].forEach(b => b.classList.toggle("on", b.dataset.k === k));
    fly = { t: 0, p0: camera.position.clone(), t0: controls.target.clone(), p1: new THREE.Vector3(...v[1]), t1: new THREE.Vector3(...v[2]) };
    if (!current || instant) { camera.position.copy(fly.p1); controls.target.copy(fly.t1); fly = null; controls.update(); }
  }
  window.__cam = (p, t) => { fly = null; camera.position.set(...p); controls.target.set(...t); controls.update(); };
  window.__view = view;
  (opts.sceneOrder || []).forEach(k => { const b = el("button", "sv-btn", opts.sceneLabels[k]); b.dataset.k = k; b.onclick = () => loadScene(k); seg.appendChild(b); });

  // ---------- hover picking ----------
  const ray = new THREE.Raycaster(), ptr = new THREE.Vector2(); let hover = null, pending = false, lastEvt = null;
  canvas.addEventListener("pointermove", e => { lastEvt = e; if (!pending) { pending = true; requestAnimationFrame(pick); } });
  canvas.addEventListener("pointerleave", () => { setHover(null); tip.style.opacity = 0; });
  function pick() {
    pending = false; if (!current || !lastEvt || lastEvt.buttons) return;
    const r = canvas.getBoundingClientRect(); ptr.set(((lastEvt.clientX - r.left) / r.width) * 2 - 1, -((lastEvt.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ptr, camera);
    const hit = ray.intersectObject(current, true).find(h => h.object.visible && !h.object.userData.skipPick && !(h.object.material.transparent && h.object.material.opacity < 0.4));
    setHover(hit ? hit.object : null);
    if (hit) {
      const g = hit.object.userData.group; tip.innerHTML = `<b>${cfg.names[g] || g}</b><i>${prettyName(hit.object.name)}</i>`;
      tip.style.left = lastEvt.clientX - r.left + "px"; tip.style.top = lastEvt.clientY - r.top + "px"; tip.style.opacity = 1;
    } else tip.style.opacity = 0;
  }
  const prettyName = n => (n || "").replace(/^.*\//, "").replace(/_/g, " ").replace(/\s+\d+$/, "");
  function setHover(o) {
    if (hover === o) return;
    if (hover && hover.material.emissive) hover.material.emissive.copy(hover.userData.baseEmissive || new THREE.Color(0));
    hover = o; if (hover && hover.material.emissive) hover.material.emissive.set(opts.hoverColor || 0x1d4fb0).multiplyScalar(0.35);
    canvas.style.cursor = o ? "pointer" : "";
  }

  // ---------- misc ----------
  function screenshot() {
    renderer.render(scene, camera);
    const c = document.createElement("canvas"); c.width = canvas.width; c.height = canvas.height; const g = c.getContext("2d");
    g.fillStyle = getComputedStyle(root).getPropertyValue("--sv-bg").trim() || "#f4f5f2"; g.fillRect(0, 0, c.width, c.height); g.drawImage(canvas, 0, 0);
    const a = document.createElement("a"); a.download = `solar-vest-${activeView || "view"}.png`; a.href = c.toDataURL("image/png"); a.click();
  }
  root.addEventListener("keydown", e => {
    if (e.target.tagName === "INPUT") return;
    const keys = Object.keys(cfg ? cfg.views : {}); const n = parseInt(e.key, 10);
    if (n >= 1 && n <= keys.length) view(keys[n - 1]);
    else if (e.key === "r" || e.key === "R") view(cfg.start);
    else if (e.key === "a" || e.key === "A") { controls.autoRotate = !controls.autoRotate; bSpin.classList.toggle("on", controls.autoRotate); }
    else if ((e.key === "f" || e.key === "F") && !opts.noFull) goFull();
  });
  root.tabIndex = -1;
  let inset = 0;
  function resize() { const w = root.clientWidth, h = root.clientHeight; if (!w || !h) return; renderer.setSize(w, h, false); camera.aspect = w / h;
    if (inset > 0 && w > 720) camera.setViewOffset(w, h, -inset / 2, 0, w, h); else camera.clearViewOffset(); camera.updateProjectionMatrix(); }
  new ResizeObserver(resize).observe(root); resize();
  const clock = new THREE.Clock();
  renderer.setAnimationLoop(() => {
    const dt = clock.getDelta();
    if (fly) { fly.t = Math.min(1, fly.t + dt / 0.9); const s = fly.t < 0.5 ? 4 * fly.t ** 3 : 1 - (-2 * fly.t + 2) ** 3 / 2;
      camera.position.lerpVectors(fly.p0, fly.p1, s); controls.target.lerpVectors(fly.t0, fly.t1, s); if (fly.t >= 1) fly = null; }
    controls.update(); renderer.render(scene, camera);
  });
  controls.addEventListener("start", () => { fly = null; });
  loadScene(opts.start || (opts.sceneOrder || [])[0]);
  return { view, loadScene, get groups() { return groups; }, controls, camera, setInset(px) { inset = px; resize(); } };
}
if (typeof window !== "undefined") window.SolarVestViewer = { mountViewer };
