#!/bin/bash
# Upload the ESP32 gateway: aioble library, main.py, and config.json built from
# ~/.config/solarvest/gateway.env (server URL + device token) and ~/.config/solarvest/wifi.json
# (written by the user: [{"ssid": "...", "password": "..."}, ...], tried in order).
set -euo pipefail
PORT=${1:-/dev/cu.usbserial-0001}
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="$HERE/../gateway-mac/.venv/bin/python"
CFG=$(mktemp)
trap 'rm -f "$CFG"' EXIT
"$PY" - "$CFG" <<'EOF'
import json, os, sys
env = dict(l.strip().split("=", 1) for l in open(os.path.expanduser("~/.config/solarvest/gateway.env")) if "=" in l)
wifi = json.load(open(os.path.expanduser("~/.config/solarvest/wifi.json")))
cfg = {"url": env["SV_URL"], "token": env["SV_DEVICE_TOKEN"], "gateway_id": "esp32-gw", "wifi": wifi}
pp = os.path.expanduser("~/.config/solarvest/portal.json")
if os.path.exists(pp):
    cfg["portal"] = json.load(open(pp))
json.dump(cfg, open(sys.argv[1], "w"))
print("config: %d Wi-Fi network(s), portal login %s" % (len(wifi), "on" if "portal" in cfg else "off"))
EOF
args=()
for f in "$HERE"/lib/aioble/*.py; do args+=("$f:/lib/aioble/$(basename "$f")"); done
"$PY" "$HERE/mpy_put.py" "$PORT" "${args[@]}" "$HERE/srun.py:/srun.py" "$HERE/main.py:/main.py" "$CFG:/config.json"
"$PY" "$HERE/mpy_put.py" "$PORT" --reset
echo PUSH_DONE
