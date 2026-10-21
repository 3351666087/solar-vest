// Build: bundle the app with esbuild and embed the GLB models as base64 so the page also works from file://.
// dist/index.html → offline/local use (double-click); dist/artifact.html → body-only page for publishing.
import { build } from "esbuild";
import fs from "node:fs";

const out = "dist";
fs.mkdirSync(out, { recursive: true });
await build({ entryPoints: ["src/app.js"], bundle: true, minify: true, format: "iife", target: "es2020", outfile: `${out}/app.js`, legalComments: "eof" });

const b64 = (f) => fs.readFileSync(`models/${f}`).toString("base64");
const index = JSON.parse(fs.readFileSync("models/assembly_index.json", "utf8"));
fs.writeFileSync(`${out}/models-core.js`, `window.SV_MODELS=${JSON.stringify({ "assembly.mo.glb": b64("assembly.mo.glb"), "bench.mo.glb": b64("bench.mo.glb") })};window.SV_INDEX=${JSON.stringify(index)};`);
const align = fs.readFileSync("models/board_align.json", "utf8");
fs.writeFileSync(`${out}/models-boards.js`, `window.SV_BOARDS=${JSON.stringify({ "pmbh.mo.glb": b64("pmbh.mo.glb"), "libb.mo.glb": b64("libb.mo.glb"), "core.mo.glb": b64("core.mo.glb"), "heartbit.mo.glb": b64("heartbit.mo.glb") })};window.SV_ALIGN=${align};`);

const page = fs.readFileSync("src/page.html", "utf8");
const cut = page.indexOf("<canvas");
const head = page.slice(0, cut), body = page.slice(cut);
const scripts = `<script src="models-core.js"></script>\n<script src="app.js"></script>\n`;
fs.writeFileSync(`${out}/index.html`, `<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n${head}</head>\n<body>\n${body}\n${scripts}</body>\n</html>\n`);
fs.writeFileSync(`${out}/artifact.html`, `${head}\n${body}\n${scripts}`);
for (const f of fs.readdirSync(out)) console.log(f, (fs.statSync(`${out}/${f}`).size / 1e6).toFixed(2), "MB");
