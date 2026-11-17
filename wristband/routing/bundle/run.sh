#!/bin/bash
# bash run.sh            start (or resume) the 8-layer search in tmux session "t2e"; safe to log out
# bash run.sh smoke      install test: 2 candidates, 1 generation, 2 router iterations (about 5 minutes)
# bash run.sh status     the curve so far
# bash run.sh pack       one tar file with the results: ~/results_<RUN>.tgz
# Settings (environment): WORKERS (default: physical cores - 2, at most one per 2 GB of memory), POP (default: WORKERS),
#                         GENS (default 14), RUN (default rent_t2e)
HERE=$(cd "$(dirname "$0")" && pwd)
source "$HERE/env.sh"
CORES=$(lscpu -p=Core,Socket 2>/dev/null | grep -v "^#" | sort -u | wc -l); [ "$CORES" -gt 0 ] || CORES=$(nproc)
MEMW=$(( $(awk '/MemTotal/ {print int($2 / 1048576)}' /proc/meminfo) / 2 - 1 ))
W0=$(( CORES - 2 )); [ "$W0" -gt "$MEMW" ] && W0=$MEMW; [ "$W0" -lt 1 ] && W0=1
WORKERS=${WORKERS:-$W0}
POP=${POP:-$WORKERS}
GENS=${GENS:-14}
RUNNAME=${RUN:-rent_t2e}
RUN=$G/runs/$RUNNAME
SEED="--seed-dir $G/work/seed8 --base-eval $G/work/seed8"
mkdir -p "$G/runs"
case "$1" in
  smoke)  rm -rf "$G/runs/smoke"; "$GROW_PY" -B "$G/tools/evolve.py" "$G/runs/smoke" --smoke --pop 2 --gens 1 --workers 2 $SEED && \
          "$GROW_PY" -c "import json; r=[json.loads(l) for l in open('$G/runs/smoke/results.jsonl')]; assert all(x['fitness'] < 1e9 for x in r), r; print('SMOKE OK', [(x['id'], x['unconnected'], x['drc_errors']) for x in r])" ;;
  status) cat "$RUN/curve.json"; tail -5 "$RUN.out" ;;
  pack)   cd "$G/runs" && tar czf "$HOME/results_$RUNNAME.tgz" "$RUNNAME/results.jsonl" "$RUNNAME/curve.json" "$RUNNAME/config.json" "$RUNNAME/best" "$RUNNAME.out" && \
          echo "packed: $HOME/results_$RUNNAME.tgz" ;;
  *)      tmux new-session -d -s t2e "\"$GROW_PY\" -B \"$G/tools/evolve.py\" \"$RUN\" --pop $POP --gens $GENS --workers $WORKERS --slim $SEED 2>&1 | tee -a \"$RUN.out\""
          echo "started: tmux session 't2e' (tmux attach -t t2e), workers $WORKERS, pop $POP, gens $GENS; log $RUN.out" ;;
esac
