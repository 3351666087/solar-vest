# Silk marks added (add_silk_marks.py)

Input `/path/to/SolarVest_work/wristband/v3/final/board/solarband_v3f_final_rf.kicad_pcb` -> `/path/to/SolarVest_work/wristband/v3/package/final/board/solarband_v3f_final_rf_silk.kicad_pcb`

Targets 57 (ICs and polarised parts, JLC-placed, >= 2 pads); placed 57; **not placed 0**.

Rules: line width 0.15 mm, dot outer diameter 0.25 mm; clearances: pad 0.15, silk 0.15, via 0.1, board edge 0.3 mm; within 1.5 mm of the reference pad and nearer to it than to any other pad; outside other parts' courtyards (fallback when nothing fits: inside a neighbour's courtyard margin but >= 0.05 mm from its body; marked in the table).

DRC (all severities, no refill) before {'warning:track_dangling': 61, 'warning:via_dangling': 1, 'unconnected': 0}

after {'warning:track_dangling': 61, 'warning:via_dangling': 1, 'unconnected': 0}

New violations: none

## Not placed (no legal position)

| Ref | Side | Ref pad | Wanted | Candidates | Blocked by |
|---|---|---|---|---|---|
| - | | | | | |

## Placed

| Ref | Side | Pad | Mark | Board XY | Gap to pad |
|---|---|---|---|---|---|
| D10 | top | 1 | dot (cathode bar did not fit; dot instead) | [120.25, 128.28] | 0.158 |
| D11 | top | 1 | bar | [123.2, 100.25] | 0.2 |
| D12 | top | 1 | dot | [126.825, 123.195] | 0.175 |
| D13 | top | 1 | dot | [101.125, 111.8] | 0.158 |
| D14 | top | 1 | bar | [103.75, 99.375] | 0.2 |
| D15 | top | 1 | dot | [102.56, 109.05] | 0.158 |
| D16 | top | 1 | bar | [105.65, 100.12] | 0.2 |
| D17 | top | 1 | dot | [132.975, 98.22] | 0.158 |
| D18 | top | 1 | dot | [129.925, 127.875] | 0.167 |
| D19 | top | 1 | dot | [119.95, 121.47] | 0.158 |
| D3 | bottom | 1 | dot | [115.915, 115.005] | 0.175 |
| D4 | bottom | 1 | dot | [122.665, 115.105] | 0.158 |
| D5 | top | 1 | dot | [104.375, 112.125] | 0.167 |
| D6 | top | 1 | dot | [139.45, 119.125] | 0.158 |
| D7 | top | 1 | dot | [133.85, 112.575] | 0.158 |
| D8 | top | 1 | dot | [125.9, 110.425] | 0.158 |
| D9 | top | 1 | dot (cathode bar did not fit; dot instead) | [128.47, 126.925] | 0.151 |
| J13 | top | 1 | dot | [124.021, 116.2] | 0.158 |
| PD1 | bottom | 1 | dot | [120.165, 113.525] | 0.158 |
| Q1 | top | 1 | dot | [107.4, 124.67] | 0.158 |
| Q10 | top | 1 | dot | [123.95, 112.02] | 0.158 |
| Q11 | top | 1 | dot | [132.495, 128.625] | 0.175 |
| Q12 | top | 1 | dot | [130.975, 100.195] | 0.175 |
| Q13 | top | 1 | dot | [133.975, 127.33] | 0.158 |
| Q14 | top | 1 | dot | [128.325, 98.555] | 0.158 |
| Q16 | top | 1 | dot | [123.645, 103.45] | 1.233 |
| Q17 | top | 1 | dot | [123.37, 100.75] | 0.445 |
| Q18 | top | 1 | dot | [121.005, 120.1] | 0.175 |
| Q19 | top | 1 | dot | [129.35, 98.82] | 0.167 |
| Q20 | top | 1 | dot | [106.425, 108.045] | 0.158 |
| Q4 | top | 1 | dot | [122.95, 121.655] | 0.546 |
| Q5 | top | 1 | dot (in a neighbour's courtyard margin, >= 0.05 mm from its body (Fab outline)) | [123.2, 99.53] | 0.175 |
| Q6 | top | 1 | dot | [122.025, 129.43] | 0.158 |
| Q7 | top | 1 | dot | [124.53, 97.175] | 0.175 |
| Q8 | top | 1 | dot | [128.125, 99.98] | 0.179 |
| Q9 | top | 1 | dot | [120.525, 119.355] | 0.167 |
| SW1 | top | 1 | dot | [139.55, 112.35] | 1.025 |
| U1 | top | 1 | dot | [115.55, 106.435] | 0.158 |
| U10 | top | 1 | dot | [105.955, 107.0] | 0.158 |
| U11 | top | 1 | dot | [111.0, 118.3] | 0.236 |
| U12 | top | 1 | dot | [118.18, 121.325] | 0.158 |
| U13 | top | 1 | dot | [103.42, 122.8] | 0.158 |
| U15 | top | 1 | dot | [112.4, 99.614] | 0.154 |
| U16 | top | 1 | dot | [121.14, 116.47] | 0.161 |
| U17 | top | 1 | dot | [121.005, 123.55] | 0.158 |
| U19 | top | 1 | dot | [126.375, 106.275] | 0.158 |
| U20 | top | 1 | dot | [129.625, 100.675] | 0.158 |
| U21 | top | 1 | dot | [125.555, 125.025] | 0.158 |
| U3 | top | 1 | dot | [118.62, 115.425] | 0.161 |
| U4 | top | A1 | dot | [117.3, 123.7] | 0.156 |
| U5 | top | A1 | dot | [109.425, 100.0] | 0.156 |
| U6 | top | A1 | dot | [114.139, 125.255] | 0.156 |
| U7 | top | 1 | dot | [109.45, 105.3] | 0.158 |
| U8 | top | A1 | dot | [123.95, 107.9] | 0.156 |
| U9 | top | 1 | dot | [113.705, 117.36] | 0.195 |
| X1 | top | 1 | dot | [119.05, 127.1] | 0.175 |
| X2 | top | 1 | dot | [117.325, 119.225] | 0.158 |
