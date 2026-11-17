"""Render datasheet pages (or a clip of a page) to PNG so vendor curves can be read and digitised.
usage: render.py <name> <page> [x0,y0,x1,y1] [dpi]   (reads ../../../cache/datasheets/<name>.pdf)"""
import sys, pathlib, pymupdf
HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE.parents[2] / "cache" / "datasheets"
name, page = sys.argv[1], int(sys.argv[2])
clip = tuple(float(x) for x in sys.argv[3].split(",")) if len(sys.argv) > 3 and sys.argv[3] else None
dpi = int(sys.argv[4]) if len(sys.argv) > 4 else 110
doc = pymupdf.open(SRC / f"{name}.pdf")
pg = doc[page - 1]
print("page size", pg.rect)
pix = pg.get_pixmap(dpi=dpi, clip=pymupdf.Rect(*clip) if clip else None)
out = HERE / "img" / f"{name}_p{page}{'_clip' if clip else ''}.png"
pix.save(out); print(out, pix.width, pix.height)
