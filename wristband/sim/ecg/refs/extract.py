"""Extract per-page text from the cached vendor datasheets (page-tagged, so every number can be cited by page).
usage: extract.py <name> ...   (reads ../../../cache/datasheets/<name>.pdf, writes <name>.pages.txt here)"""
import sys, hashlib, pathlib, pymupdf
HERE = pathlib.Path(__file__).resolve().parent
SRC = HERE.parents[2] / "cache" / "datasheets"
for name in sys.argv[1:]:
    p = SRC / f"{name}.pdf"
    doc = pymupdf.open(p)
    with open(HERE / f"{name}.pages.txt", "w") as f:
        f.write(f"# {p.name} sha256={hashlib.sha256(p.read_bytes()).hexdigest()} pages={doc.page_count}\n")
        for i, pg in enumerate(doc):
            f.write(f"\n=== PAGE {i+1} ===\n{pg.get_text()}")
    print(name, doc.page_count, doc.metadata.get("title"), doc.metadata.get("subject"))
