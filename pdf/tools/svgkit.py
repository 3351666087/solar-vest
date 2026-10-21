"""Tiny SVG builder shared by the diagram generators — keeps the design tokens in one place."""
INK="#0B1220"; DEEP="#14233D"; SLATE="#46556E"; MUTED="#8B97AB"
LINE="#D9E0EC"; PANEL="#F6F8FC"; WHITE="#FFFFFF"
SOLAR="#B8720F"; SOLAR_L="#FDF3E2"; SOLAR_B="#E09B2D"
VOLT="#2F6BE4";  VOLT_L="#EDF2FE"
OK="#15845F";    OK_L="#E4F4EE"
RISK="#CB4034";  RISK_L="#FCEAE8"
PURP="#6B4FCF";  PURP_L="#EFEBFB"

CJK='Heiti SC'; UI='Inter'; MONO='Menlo'

def esc(s):
    return (s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;"))

class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.o = w, h, []
    def raw(self, s): self.o.append(s); return self
    def rect(self, x, y, w, h, fill=WHITE, stroke=None, rx=4, sw=1, dash=None, op=None):
        a = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{fill}"'
        if stroke: a += f' stroke="{stroke}" stroke-width="{sw}"'
        if dash:   a += f' stroke-dasharray="{dash}"'
        if op is not None: a += f' fill-opacity="{op}"'
        return self.raw(a + '/>')
    def text(self, x, y, s, size=10, fill=INK, fam=None, anchor="start", weight=None, ls=None):
        fam = fam or CJK
        a = f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" fill="{fill}"'
        if anchor != "start": a += f' text-anchor="{anchor}"'
        if weight: a += f' font-weight="{weight}"'
        if ls:     a += f' letter-spacing="{ls}"'
        return self.raw(a + f'>{esc(s)}</text>')
    def line(self, x1, y1, x2, y2, stroke=SLATE, sw=1, dash=None, cap="round"):
        a = f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="{cap}"'
        if dash: a += f' stroke-dasharray="{dash}"'
        return self.raw(a + '/>')
    def path(self, d, stroke=SLATE, sw=1, fill="none", dash=None):
        a = f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"'
        if dash: a += f' stroke-dasharray="{dash}"'
        return self.raw(a + '/>')
    def arrow(self, x1, y1, x2, y2, stroke=SLATE, sw=1.2, head=4.2, dash=None):
        import math
        ang = math.atan2(y2-y1, x2-x1)
        bx, by = x2 - head*math.cos(ang), y2 - head*math.sin(ang)
        self.line(x1, y1, bx, by, stroke, sw, dash)
        p1 = (x2, y2)
        p2 = (x2 - head*1.55*math.cos(ang-0.42), y2 - head*1.55*math.sin(ang-0.42))
        p3 = (x2 - head*1.55*math.cos(ang+0.42), y2 - head*1.55*math.sin(ang+0.42))
        return self.raw(f'<polygon points="{p1[0]:.1f},{p1[1]:.1f} {p2[0]:.1f},{p2[1]:.1f} {p3[0]:.1f},{p3[1]:.1f}" fill="{stroke}"/>')
    def elbow(self, x1, y1, x2, y2, stroke=SLATE, sw=1.2, dash=None, via=None):
        """orthogonal 3-segment connector, horizontal first"""
        mx = via if via is not None else (x1+x2)/2
        self.path(f"M{x1},{y1} L{mx},{y1} L{mx},{y2} L{x2-5},{y2}", stroke, sw, dash=dash)
        return self.arrow(x2-5.01, y2, x2, y2, stroke, sw)
    def out(self):
        return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.w} {self.h}" '
                f'width="{self.w}" height="{self.h}">\n' + "\n".join(self.o) + "\n</svg>\n")

def box(s, x, y, w, h, title, sub=None, fill=WHITE, stroke=LINE, tc=INK, sc=MUTED,
        ts=10, ss=7.6, rx=4, sw=1, accent=None, mono=False, title_fam=None):
    s.rect(x, y, w, h, fill, stroke, rx, sw)
    if accent:
        s.rect(x, y, 3, h, accent, rx=1.5)
    cy = y + h/2
    if sub:
        s.text(x+w/2, cy-1.5, title, ts, tc, title_fam or (MONO if mono else CJK), "middle", 700 if not mono else None)
        s.text(x+w/2, cy+9.5, sub, ss, sc, CJK, "middle")
    else:
        s.text(x+w/2, cy+ts*0.36, title, ts, tc, title_fam or (MONO if mono else CJK), "middle", 700 if not mono else None)
