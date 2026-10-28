// Verifies the console's BLE decoder (the <script id="decoder"> block in console.html)
// against the shared protocol vectors. Run: node test_decoder.mjs
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import assert from "node:assert/strict";

const here = dirname(fileURLToPath(import.meta.url));
const html = readFileSync(join(here, "console.html"), "utf8");
const m = html.match(/<script id="decoder">([\s\S]*?)<\/script>/);
if (!m) { console.error("decoder block not found in console.html"); process.exit(1); }
const svDecode = new Function(`${m[1]}\nreturn svDecode;`)();

const vectors = JSON.parse(readFileSync(join(here, "..", "protocol", "vectors.json"), "utf8"));
const hex = (s) => Uint8Array.from(s.match(/../g), (h) => parseInt(h, 16));

let failed = 0;
for (const v of vectors) {
  try {
    const got = svDecode(hex(v.a_hex), hex(v.b_hex), v.ts);
    assert.deepStrictEqual(got, v.expected);
    // Key order must match too, so the JSON the relay posts is byte-identical to the gateway's.
    assert.deepStrictEqual(Object.keys(got), Object.keys(v.expected));
    // Must also work on a view into a larger buffer (Web Bluetooth hands out DataViews).
    const big = new Uint8Array(64); big.set(hex(v.a_hex), 7);
    assert.deepStrictEqual(svDecode(big.subarray(7, 27), hex(v.b_hex), v.ts), v.expected);
    console.log(`ok   ${v.name}`);
  } catch (e) {
    failed++;
    console.log(`FAIL ${v.name}\n${e.message}`);
  }
}
if (vectors.length < 3) { console.log("FAIL fewer than 3 vectors"); failed++; }
console.log(failed ? `${failed} failed` : `all ${vectors.length} vectors pass`);
process.exit(failed ? 1 : 0);
