#!/bin/bash
# [grow8] run one candidate in the background, single core, (ps-based RSS sampling does not work in the sandbox: use score.json peak_rss_mb): runjob.sh CAND.json OUTDIR
PY=${GROW_PY:-python3}
HERE=$(cd "$(dirname "$0")" && pwd)
"$PY" -B "$HERE/evaluate.py" "$1" "$2" > "$2.out" 2>&1 &
pid=$!; peak=0
while kill -0 $pid 2>/dev/null; do
  r=$(ps -o rss= -g $(ps -o pgid= -p $pid | tr -d ' ') 2>/dev/null | sort -n | tail -1); r=${r:-0}
  [ "$r" -gt "$peak" ] && peak=$r; echo "$peak" > "$2.peak_rss_kb"; sleep 20
done
wait $pid; echo "exit $? peak_rss_kb $peak" >> "$2.out"
