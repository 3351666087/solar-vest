#!/bin/bash
# SolarVest Mac BLE gateway launcher: venv + deps, then run with sleep prevented.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -x .venv/bin/python ]; then
  echo "[run.sh] creating virtual environment .venv"
  python3 -m venv .venv
fi
.venv/bin/python -m pip install --quiet --upgrade pip >/dev/null 2>&1 || true
.venv/bin/python -m pip install --quiet -r requirements.txt

# -d display, -i idle, -m disk, -s system (on AC), -u declare user active.
exec caffeinate -dimsu .venv/bin/python gateway.py "$@"
