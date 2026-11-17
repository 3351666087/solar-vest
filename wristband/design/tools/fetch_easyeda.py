"""Fetch EasyEDA symbol + footprint + 3D model for each LCSC C-number and convert with easyeda2kicad.

Raw API answers are cached verbatim in cache/easyeda/<C>.json (+ <C>.meta.json: UTC time, HTTP status, sha256),
3D models in cache/easyeda/<uuid>.obj / .step. Requests are paced >= 1.5 s apart.
Output (per C-number, so JLC's own geometry is kept per part even when titles collide):
  design/lib/easyeda.kicad_sym        symbol  "<C>_<title>"
  design/lib/easyeda.pretty/<C>_<title>.kicad_mod
  design/lib/easyeda.3dshapes/<model>.wrl/.step
usage: python fetch_easyeda.py C123 C456 ...   (re-run safe: cached JSON is reused unless --refresh)
"""
import sys, os, json, time, hashlib, datetime, urllib.request, gzip, logging
from pathlib import Path
from easyeda2kicad.easyeda.easyeda_api import EasyedaApi, API_ENDPOINT
from easyeda2kicad.easyeda.easyeda_importer import EasyedaSymbolImporter, EasyedaFootprintImporter, Easyeda3dModelImporter
from easyeda2kicad.kicad.export_kicad_symbol import ExporterSymbolKicad
from easyeda2kicad.kicad.export_kicad_footprint import ExporterFootprintKicad
from easyeda2kicad.kicad.export_kicad_3d_model import Exporter3dModelKicad

CACHE = Path(os.environ.get("SB_RAW_EE", "/tmp/solarband_raw"))   # V3-F lane: raw answers stay outside the project
LIB = Path(__file__).resolve().parent.parent / "lib"   # V3-F lane: v3/design/lib
OUT = LIB / "easyeda"
logging.basicConfig(level=logging.INFO, format="%(message)s")
_last = [0.0]
def pace():
    dt = time.time() - _last[0]
    if dt < 1.5: time.sleep(1.5 - dt)
    _last[0] = time.time()

import subprocess
from easyeda2kicad.easyeda.easyeda_api import ENDPOINT_3D_MODEL, ENDPOINT_3D_MODEL_STEP
def curl_get(url, dest, ua):
    """curl with retries + resume (the network truncates long transfers); returns bytes or None."""
    tmp = str(dest) + ".part"
    for attempt in range(6):
        pace()
        r = subprocess.run(["curl", "-sS", "-L", "-C", "-", "--retry", "5", "--retry-all-errors", "--retry-delay", "3",
                            "--max-time", "120", "-A", ua, "-o", tmp, url], capture_output=True)
        if r.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 0:
            os.replace(tmp, dest); return Path(dest).read_bytes()
        time.sleep(5)
    if os.path.exists(tmp): os.remove(tmp)
    return None

class PacedApi(EasyedaApi):
    def get_raw_3d_model_obj(self, uuid):
        p = self.cache_dir / f"{uuid}.obj"
        if p.exists() and p.stat().st_size > 0: return p.read_text(errors="replace")
        b = curl_get(ENDPOINT_3D_MODEL.format(uuid=uuid), p, self.headers["User-Agent"])
        return b.decode(errors="replace") if b else None
    def get_step_3d_model(self, uuid):
        p = self.cache_dir / f"{uuid}.step"
        if p.exists() and p.stat().st_size > 0: return p.read_bytes()
        return curl_get(ENDPOINT_3D_MODEL_STEP.format(uuid=uuid), p, self.headers["User-Agent"])

def fetch_raw(api, c, refresh=False):
    p = CACHE / f"{c}.json"
    if p.exists() and not refresh:
        try:
            d = json.loads(p.read_text())
            if d.get("success") is True: return d
        except Exception: pass
    for attempt in range(4):
        pace()
        t0 = datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
        status, raw = -1, b""
        try:
            req = urllib.request.Request(API_ENDPOINT.format(lcsc_id=c) + "?version=6.4.19.5", headers=api.headers)
            with urllib.request.urlopen(req, timeout=40, context=api.ssl_context) as r:
                status = r.status; raw = r.read()
        except urllib.error.HTTPError as e:
            status = e.code; raw = e.read() or b""
        except Exception as e:
            raw = str(e).encode()
        if raw[:2] == b"\x1f\x8b": raw = gzip.decompress(raw)
        meta = {"lcsc": c, "fetched_utc": t0, "http": status, "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw), "attempt": attempt + 1,
                "url": API_ENDPOINT.format(lcsc_id=c) + "?version=6.4.19.5"}
        try:
            d = json.loads(raw)
        except Exception:
            d = None
        if d is not None and d.get("success") is True:
            p.write_bytes(raw); (CACHE / f"{c}.meta.json").write_text(json.dumps(meta, indent=1))
            return d
        (CACHE / f"{c}.fail.json").write_text(json.dumps(dict(meta, body=raw[:500].decode(errors="replace")), indent=1))
        if d is not None and d.get("code") == 404:
            break                                   # "Component not found": a hard answer, not a network error
        time.sleep(10 * (attempt + 1))              # 403/429/5xx/truncated body: back off and retry
    return None

def convert(api, c, d):
    cad = d["result"]
    sym = EasyedaSymbolImporter(easyeda_cp_cad_data=cad).get_symbol()
    sym.info.name = f"{c}_{sym.info.name}"
    fp = EasyedaFootprintImporter(easyeda_cp_cad_data=cad).get_footprint()
    fpname = f"{c}_{fp.info.name}"
    fp.info.name = fpname
    sym.info.package = f"easyeda:{fpname}"
    ExporterSymbolKicad(symbol=sym, lib_path=str(OUT) + ".kicad_sym", custom_fields={}).save_to_lib(
        lib_path=str(OUT) + ".kicad_sym", footprint_lib_name="easyeda", overwrite=True)
    (Path(str(OUT) + ".pretty")).mkdir(parents=True, exist_ok=True)
    m3d = None
    if os.environ.get("SB_WITH3D") == "1":      # V3-F lane: 3D models are downloaded files and are not stored in the project (default off)
        try:
            m3d = Easyeda3dModelImporter(easyeda_cp_cad_data=cad, download_raw_3d_model=True, api=api).output
        except Exception as e:
            print(f"{c}: 3D model download failed: {e!r}"); m3d = None
    ExporterFootprintKicad(footprint=fp).export(footprint_full_path=str(Path(str(OUT) + ".pretty") / f"{fpname}.kicad_mod"),
                                               model_3d_path="${KIPRJMOD}/../../lib/easyeda.3dshapes")
    m3name = None
    if m3d:
        ex = Exporter3dModelKicad(model_3d=m3d)
        if ex.output:
            ex.export(output_dir=str(OUT) + ".3dshapes", overwrite=True); m3name = ex.output.name
    return dict(lcsc=c, title=cad.get("title"), footprint=f"easyeda:{fpname}", package_title=cad["packageDetail"]["title"],
                symbol=sym.info.name, model3d=m3name, mfr_part=cad.get("dataStr", {}).get("head", {}).get("c_para", {}).get("Manufacturer Part"))

if __name__ == "__main__":
    CACHE.mkdir(parents=True, exist_ok=True)
    refresh = "--refresh" in sys.argv
    api = PacedApi(use_cache=True); api.cache_dir = CACHE
    LIB.mkdir(parents=True, exist_ok=True)
    idx_p = LIB / "easyeda_index.json"
    idx = json.loads(idx_p.read_text()) if idx_p.exists() else {}
    for c in [a for a in sys.argv[1:] if a.startswith("C")]:
        d = fetch_raw(api, c, refresh)
        if d is None:
            print(f"{c}: FETCH FAILED"); idx[c] = {"lcsc": c, "error": "fetch failed"}; continue
        try:
            idx[c] = convert(api, c, d); print(f"{c}: ok {idx[c]['footprint']} 3D={idx[c]['model3d']}", flush=True)
        except Exception as e:
            idx[c] = {"lcsc": c, "error": f"convert: {e!r}"}; print(f"{c}: CONVERT FAILED {e!r}", flush=True)
        idx_p.write_text(json.dumps(idx, indent=1, ensure_ascii=False))
