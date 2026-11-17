"""[layout] One picture per copper layer (+ outline) and the assembly sides of a routed board: kicad-cli pdf export, rasterised with
PyMuPDF (envs/pdfenv). usage: python render_layers.py BOARD.kicad_pcb OUTDIR PREFIX"""
import os, subprocess, sys
K = "@MACKICAD@/MacOS/kicad-cli"
PDFPY = "@SVROOT@/wristband/envs/pdfenv/bin/python"
ENV = dict(os.environ, KICAD_CONFIG_HOME=os.environ.get("TMPDIR", "/tmp") + "/solarband_kicfg")
pcb, out, pre = sys.argv[1:4]
os.makedirs(out, exist_ok=True)
SETS = {"L1_F.Cu": "F.Cu,Edge.Cuts", "L2_In1.Cu_GND": "In1.Cu,Edge.Cuts", "L3_In2.Cu": "In2.Cu,Edge.Cuts",
        "L4_In3.Cu_VDD_1V8": "In3.Cu,Edge.Cuts", "L5_In4.Cu": "In4.Cu,Edge.Cuts", "L6_B.Cu": "B.Cu,Edge.Cuts",
        "assembly_top": "F.Cu,F.Fab,F.Courtyard,Edge.Cuts", "assembly_bottom": "B.Cu,B.Fab,B.Courtyard,Edge.Cuts"}
code = ("import pymupdf,sys; d=pymupdf.open(sys.argv[1]); p=d[0]; k=72/25.4; c=[v*k for v in (98.5,98.5,139.5,131.5)]; "
        "pix=p.get_pixmap(dpi=900, clip=pymupdf.Rect(*c)); pix.save(sys.argv[2])")
for tag, layers in SETS.items():
    pdf = f"{out}/{pre}_{tag}.pdf"
    extra = ["--mirror"] if tag.endswith("bottom") else []
    r = subprocess.run([K, "pcb", "export", "pdf", "--layers", layers, "--mode-single", "-o", pdf] + extra + [pcb],
                       capture_output=True, text=True, env=ENV)
    if r.returncode:
        print("FAILED", tag, r.stderr[-300:]); continue
    subprocess.run([PDFPY, "-c", code, pdf, f"{out}/{pre}_{tag}.png"], check=True)
    os.remove(pdf)
    print("wrote", f"{out}/{pre}_{tag}.png")
