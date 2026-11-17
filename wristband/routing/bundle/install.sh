#!/bin/bash
# SolarBand grow8 bundle: one-time install on a rented x86-64 Ubuntu 22.04 or 24.04 machine (CPU only). The user runs it:  bash install.sh
# It fetches (and nothing else):
#   apt, Ubuntu archive:  build-essential python3-venv python3-pip software-properties-common tmux
#   apt, KiCad's official PPA ppa:kicad/kicad-10.0-releases (Launchpad):  kicad 10.0.x (kicad-cli + the pcbnew Python module)
#   pip, PyPI (into tree/venv):  requirements.txt (Python >= 3.11: numpy 2.5.4, scipy 1.18.1, shapely 2.2.0, matplotlib 3.11.2)
#                                or requirements-py310.txt (Python 3.10: numpy 2.2.6, scipy 1.15.3, shapely 2.1.1, matplotlib 3.10.3)
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$HERE/tree
G=$ROOT/wristband/v3/grow8
sudo apt-get update
sudo apt-get install -y build-essential python3-venv python3-pip software-properties-common tmux
sudo add-apt-repository -y ppa:kicad/kicad-10.0-releases
sudo apt-get update
sudo apt-get install -y --no-install-recommends kicad
KV=$(kicad-cli version 2>/dev/null || true)
echo "kicad-cli version: $KV"
case "$KV" in 10.*) ;; *) echo "STOP: kicad-cli 10.x is needed (the laptop uses 10.0.7)"; exit 1;; esac
python3 -c "import pcbnew; print('pcbnew', pcbnew.Version())" || { echo "STOP: the pcbnew Python module is missing"; exit 1; }
python3 -m venv --system-site-packages "$ROOT/venv"
REQ=requirements.txt
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' || REQ=requirements-py310.txt
"$ROOT/venv/bin/pip" install -r "$HERE/$REQ"
"$ROOT/venv/bin/python" -c "import pcbnew, numpy, scipy, shapely, matplotlib; print('python OK')"
# this machine's paths into the code
find "$ROOT/wristband" \( -name "*.py" -o -name "*.json" \) -print0 | xargs -0 sed -i -e "s#@SVROOT@#$ROOT#g" -e "s#@MACKICAD@#/usr#g"
# the C core, built here with this machine's compiler (portable flags, no -march=native)
cc -O3 -shared -fPIC -o "$G/src/libpf.so" "$G/src/pf.c" -lm
cat > "$HERE/env.sh" <<EOT
export GROW_PY=$ROOT/venv/bin/python
export GROW_KPY=$ROOT/venv/bin/python
export GROW_KCLI=$(command -v kicad-cli)
export G=$G
EOT
echo "installed. Next:  bash $HERE/run.sh smoke   (about 5 minutes)"
