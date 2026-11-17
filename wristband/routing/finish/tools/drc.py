"""Run KiCad DRC (kicad-cli, all severities, JSON) and summarise. usage: python drc.py <board.kicad_pcb> [report.json] [--parity] [--detail TYPE]"""
import collections, json, os, subprocess, sys
KCLI = "kicad-cli"
pcb = sys.argv[1]
rep = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("--") else os.path.splitext(pcb)[0] + "_drc.json"
cmd = [KCLI, "pcb", "drc", "--severity-all", "--format", "json", "--units", "mm", "-o", rep, pcb]
if "--parity" in sys.argv:
    cmd.insert(3, "--schematic-parity")
if "--refill" in sys.argv:
    cmd.insert(3, "--refill-zones")
env = dict(os.environ, KICAD_CONFIG_HOME=os.environ.get("TMPDIR", "/tmp") + "/solarband_kicfg")
os.makedirs(env["KICAD_CONFIG_HOME"] + "/10.0", exist_ok=True)
kc = env["KICAD_CONFIG_HOME"] + "/10.0/kicad_common.json"
if not os.path.exists(kc):
    src = os.path.expanduser("~/Library/Preferences/kicad/10.0/kicad_common.json")
    s = open(src).read() if os.path.exists(src) else '{"system": {"language": "English"}}'
    open(kc, "w").write(s.replace('"language": "Default"', '"language": "English"'))
r = subprocess.run(cmd, capture_output=True, text=True, env=env)
d = json.load(open(rep))
cnt = collections.Counter()
for sect in ("violations", "unconnected_items", "schematic_parity"):
    for v in d.get(sect, []):
        cnt[(sect, v["severity"], v["type"])] += 1
for k, v in sorted(cnt.items()):
    print(f"{v:5d}  {k[0]:18s} {k[1]:8s} {k[2]}")
det = sys.argv[sys.argv.index("--detail") + 1] if "--detail" in sys.argv else None
if det:
    n = 0
    for sect in ("violations", "unconnected_items", "schematic_parity"):
        for v in d.get(sect, []):
            if v["type"] == det and n < 40:
                n += 1
                print("-", v["description"], "|", "; ".join(i["description"] + " @(%.2f,%.2f)" % (i["pos"]["x"] - 100, 130 - i["pos"]["y"]) for i in v["items"]))
