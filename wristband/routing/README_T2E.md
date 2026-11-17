# track2e: track-2 search bundle with ECO3 (U19/U20 TLV7031DCKR C2863637 SC70-5)
- Bundle: `v3/track2e/t2e_bundle.tgz` (folder `bundle/`), built by `make_bundle_t2e.sh` from `v3/track2/bundle` (track2, grow8, eco3 untouched).
- Tree changes: design/parts.json (v3/design), easyeda_rev.pretty + C2863637 SC-70-5, layout/work/fpgeom_v3f.json (eco3/work_t2),
  tools = eco3/tools_t2 (lgeom/fpdump WORK default -> layout/work in the tree), seed8 = eco3/runs/e1 (16 unc / 0 DRC; placement,
  candidate, score, routes, drc_final, board_stats, final.kicad_pcb), b0_src = e1 placement, old h4 placement removed.
- Placeholders @SVROOT@ / @MACKICAD@ as make_bundle_t2.sh; install.sh unchanged (fills them, builds libpf.so, writes env.sh).
- run.sh: tmux session `t2e`, default RUN `rent_t2e`. U19/U20 (need 1.15 mm) stay in the PV half: check_placement zone check
  (a U19 move out of the PV half gives zone_violations U19 9.36 mm2 -> not LEGAL -> evolve drops the move).
- Local test: see PROGRESS.md (one evaluation of the seed candidate, 2 router iterations, extracted copy, mac paths).
## Server (install done; packages present)
```
mkdir -p ~/t2e && tar xzf t2e_bundle.tgz -C ~/t2e && cd ~/t2e/bundle
bash install.sh
bash run.sh smoke
RUN=rent_t2e WORKERS=38 POP=38 GENS=20 bash run.sh
```
Results: `bash run.sh status`, `bash run.sh pack` -> ~/results_rent_t2e.tgz.
