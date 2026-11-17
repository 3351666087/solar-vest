"""Render the 400/300-dpi crops of vendor figures that refs/digitise.py reads and that SIM-08 cites.
Run with envs/pdftools/bin/python (pymupdf).  Crops are in PDF points (72/in) of the cached datasheets."""
import pathlib, pymupdf
HERE = pathlib.Path(__file__).resolve().parent
DS = HERE.parents[2] / "cache" / "datasheets"
CLIPS = [  # name, pdf, page (1-based), rect, dpi
    ("tps7a02_f643", "tps7a02", 15, (75, 112, 295, 255), 400),     # Fig 6-43 PSRR vs f and IOUT
    ("tps7a02_f648", "tps7a02", 15, (328, 478, 548, 612), 400),    # Fig 6-48 output noise vs f and IOUT
    ("ads1291_f8", "ads1291", 13, (70, 100, 320, 285), 400),       # Fig 8 PSRR vs f
    ("tpd1e10b06_tlp12", "tpd1e10b06", 6, (70, 255, 306, 410), 300),   # Fig 5-3 TLP pin1->pin2
    ("tpd1e10b06_tlp21", "tpd1e10b06", 6, (306, 255, 545, 410), 300),  # Fig 5-4 TLP pin2->pin1
    ("tpd1e10b06_iec_p8kv", "tpd1e10b06", 6, (70, 95, 306, 240), 300), # Fig 5-1 +8 kV clamp
]
for name, pdf, page, rect, dpi in CLIPS:
    pix = pymupdf.open(DS / f"{pdf}.pdf")[page - 1].get_pixmap(dpi=dpi, clip=pymupdf.Rect(*rect))
    pix.save(HERE / "img" / f"{name}.png"); print(name, pix.width, pix.height)
