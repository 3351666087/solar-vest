"""2-D and 3-D images of both boards with kicad-cli (English config) -> layout/renders/.
3-D: kicad-cli pcb render (top, bottom, isometric). 2-D: kicad-cli pcb export pdf per layer set, rasterised with
PyMuPDF (envs/pdfenv). Also a STEP of each board (layout/out/*.step) for the enclosure check.
usage: python render.py [main|pv|all]"""
import os, subprocess, sys
W = "@SVROOT@/wristband"
K = "@MACKICAD@/MacOS/kicad-cli"
OUT = W + "/layout/renders"
ENV = dict(os.environ, KICAD_CONFIG_HOME=os.environ.get("TMPDIR", "/tmp") + "/solarband_kicfg")
PDFPY = W + "/envs/pdfenv/bin/python"


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, env=ENV)
    if r.returncode != 0:
        print("FAILED:", " ".join(cmd[:6]), r.stderr[-400:])
    return r.returncode == 0


def raster(pdf, png, dpi=900, clip=(98.5, 98.5, 138.5, 131.5)):
    """clip = board area in page mm (board origin (0,0) at page (100,130) mm, KiCad Y down)"""
    code = ("import pymupdf,sys; d=pymupdf.open(sys.argv[1]); p=d[0]; k=72/25.4; c=[float(v)*k for v in sys.argv[4].split(',')]; "
            "pix=p.get_pixmap(dpi=int(sys.argv[3]), clip=pymupdf.Rect(*c)); pix.save(sys.argv[2])")
    subprocess.run([PDFPY, "-c", code, pdf, png, str(dpi), ",".join(map(str, clip))], check=True, capture_output=True)


def board(name, pcb, layers2d):
    os.makedirs(OUT, exist_ok=True)
    for side, extra in (("top", []), ("bottom", []), ("iso", ["--rotate", "-45,0,30", "--side", "top"])):
        args = [K, "pcb", "render", "-o", f"{OUT}/{name}_3d_{side}.png", "-w", "2000", "-h", "1600", "--quality", "high",
                "--background", "opaque", "--zoom", "1.0"]
        args += extra if extra else ["--side", side]
        run(args + [pcb])
    for tag, layers in layers2d.items():
        pdf = f"{OUT}/{name}_{tag}.pdf"
        if run([K, "pcb", "export", "pdf", "--layers", layers, "--mode-single",
                "-o", pdf, pcb]):
            try:
                raster(pdf, f"{OUT}/{name}_{tag}.png")
                os.remove(pdf)
            except Exception as e:
                print("raster failed", tag, e)
    os.makedirs(W + "/layout/out", exist_ok=True)
    run([K, "pcb", "export", "step", "--subst-models", "--force", "-o", f"{W}/layout/out/{name}.step", pcb])


def main():
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("main", "all"):
        L = {"L1_top": "F.Cu,F.SilkS,F.Mask,Edge.Cuts", "L2": "In1.Cu,Edge.Cuts", "L3": "In2.Cu,Edge.Cuts",
             "L4": "In3.Cu,Edge.Cuts", "L5": "In4.Cu,Edge.Cuts", "L6_bottom": "B.Cu,B.SilkS,Edge.Cuts",
             "assembly_top": "F.Fab,F.SilkS,F.CrtYd,Edge.Cuts", "assembly_bottom": "B.Fab,B.SilkS,Edge.Cuts"}
        board("main", W + "/layout/main/solarband_main.kicad_pcb", L)
    if which in ("pv", "all"):
        L = {"top": "F.Cu,F.SilkS,F.Mask,Edge.Cuts", "bottom": "B.Cu,B.SilkS,B.Mask,Edge.Cuts"}
        board("pv", W + "/layout/pv/solarband_pv.kicad_pcb", L)
    print(sorted(os.listdir(OUT)))


if __name__ == "__main__":
    main()
