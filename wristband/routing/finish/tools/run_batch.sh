#!/bin/zsh
# run a list of placement jobs, N at a time. usage: run_batch.sh JOBFILE [PAR]   (job line: TAG ZONES VARIANT OPTS SEED ITERS)
D=/path/to/SolarVest_work/wristband/v3/layout
PAR=${2:-2}
i=0
while read -r TAG ZN VAR OPT SEED IT; do
  [[ -z "$TAG" || "$TAG" == \#* ]] && continue
  REFINE=${REFINE:-2000000} $D/tools/run_place.sh $TAG $ZN $VAR $OPT $SEED $IT > /dev/null 2>&1 &
  i=$((i+1))
  if (( i % PAR == 0 )); then wait; fi
done < $1
wait
echo "batch $1 done $(date -u +%FT%TZ)"
