"""Extract datasheet text with page markers ('=== page N ===', 1-based) into v2/design/work/ds_text/<name>.txt.
usage: envs/pdfenv/bin/python v2/design/tools/ds_text.py <pdf path> [<pdf path> ...]     (pymupdf lives in envs/pdfenv)
"""
import sys, os, pymupdf
O = "/path/to/SolarVest_work/wristband/v2/design/work/ds_text"
os.makedirs(O, exist_ok=True)
for p in sys.argv[1:]:
    n = os.path.splitext(os.path.basename(p))[0]
    doc = pymupdf.open(p)
    with open(os.path.join(O, n + ".txt"), "w") as f:
        for i, pg in enumerate(doc):
            f.write(f"\n=== page {i+1} ===\n"); f.write(pg.get_text())
    print(n, len(doc), "pages")
