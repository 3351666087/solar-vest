#!/bin/bash
# usage: fetch_ds.sh name url   -> cache/datasheets/<name>.pdf (+ .url/.sha256); resolves LCSC viewer pages; curl with retries
D=/path/to/SolarVest_work/wristband/cache/datasheets; n=$1; u=$2; out=$D/$n.pdf
[ -f "$out" ] && head -c5 "$out" | grep -q '%PDF-' && { echo "$n cached"; exit 0; }
UA="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
tmp=$(mktemp); curl -sL --retry 6 --retry-all-errors --retry-delay 3 -A "$UA" "$u" -o "$tmp"
if ! head -c5 "$tmp" | grep -q '%PDF-'; then
  real=$(grep -o 'https://datasheet\.lcsc\.com/datasheet/pdf/[0-9a-f]*\.pdf?productCode=C[0-9]*' "$tmp" | head -1)
  [ -z "$real" ] && { echo "$n NOT PDF"; rm -f "$tmp"; exit 1; }
  sleep 1; u2=$real; rm -f "$tmp"; tmp=$(mktemp)
  for i in 1 2 3 4 5 6; do curl -sL -C - --retry 6 --retry-all-errors --retry-delay 3 -A "$UA" "$u2" -o "$tmp" && break; sleep 3; done
fi
head -c5 "$tmp" | grep -q '%PDF-' || { echo "$n FAIL"; rm -f "$tmp"; exit 1; }
cp "$tmp" "$out"; rm -f "$tmp"; echo "$u" > $D/$n.url; shasum -a 256 "$out" | cut -d' ' -f1 > $D/$n.sha256; echo "$n ok $(wc -c < $out)"
