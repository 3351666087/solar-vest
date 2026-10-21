#!/bin/bash
set -e
cd "$(dirname "$0")"
[ -f cp.txt ] || mvn -q compile dependency:build-classpath -Dmdep.outputFile=cp.txt   # local jar classpath (not committed)
python3 build_en.py
java -Djava.awt.headless=true -cp "target/classes:$(cat cp.txt)" Render "${1:-out-en.pdf}" $(cat parts-en.txt) 2>&1 \
  | grep -vE "Picked up|INFO::|css-parse WARNING.*(flex|gap)" || true
