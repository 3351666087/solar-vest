"""Helpers for pin-accurate netlist diagrams in Graphviz HTML-like labels."""
INK="#0B1220"; DEEP="#14233D"; SLATE="#46556E"; MUTED="#8B97AB"
LINE="#CBD4E3"; PANEL="#F6F8FC"; WHITE="#FFFFFF"
SOLAR="#B8720F"; SOLAR_L="#FDF3E2"
VOLT="#2F6BE4";  VOLT_L="#EDF2FE"
OK="#15845F";    OK_L="#E4F4EE"
RISK="#CB4034";  RISK_L="#FCEAE8"
PURP="#6B4FCF"
CJK='PingFang SC'; UI='Inter'; MONO='Menlo'

_KEEP = ("<BR/>", "<B>", "</B>", "<SUB>", "</SUB>", "<I>", "</I>")
def esc(t):
    """Escape for Graphviz HTML-like labels, keeping a small tag whitelist."""
    if t is None: return t
    t = str(t)
    for i, k in enumerate(_KEEP): t = t.replace(k, f"\x00{i}\x00")
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    for i, k in enumerate(_KEEP): t = t.replace(f"\x00{i}\x00", k)
    return t

HEAD = """digraph G {{
  bgcolor="transparent";
  rankdir={rankdir}; splines={splines}; nodesep={nodesep}; ranksep={ranksep};
  node [shape=plaintext, fontname="{cjk}", fontsize=8];
  edge [fontname="{mono}", fontsize=6.5, color="{slate}", penwidth=1.0, arrowsize=0.55];
"""

def chip(nid, title, pins, sub=None, hdr=DEEP, body=WHITE, tcol=WHITE, width=None):
    """pins: list of (port, pin, desc) — port None = plain row."""
    rows = []
    title = esc(title); sub = esc(sub)
    hdr_extra = f'<BR/><FONT POINT-SIZE="6.4" COLOR="#C8D3E6">{sub}</FONT>' if sub else ""
    rows.append(f'<TR><TD COLSPAN="2" BGCOLOR="{hdr}" ALIGN="LEFT">'
                f'<FONT FACE="{MONO}" POINT-SIZE="8.6" COLOR="{tcol}"><B>{title}</B></FONT>{hdr_extra}</TD></TR>')
    for p in pins:
        port, pin, desc = p
        pin, desc = esc(pin), esc(desc)
        pa  = f' PORT="{port}"' if port else ""      # west side (incoming)
        pa2 = f' PORT="{port}_o"' if port else ""    # east side (outgoing)
        rows.append(
            f'<TR><TD{pa} ALIGN="LEFT" BGCOLOR="{PANEL}"><FONT FACE="{MONO}" POINT-SIZE="7.2" COLOR="{INK}">{pin}</FONT></TD>'
            + (f'<TD{pa2} ALIGN="LEFT"><FONT FACE="{CJK}" POINT-SIZE="7" COLOR="{SLATE}">{desc}</FONT></TD></TR>'
               if desc else f'<TD{pa2}> </TD></TR>'))
    w = f' WIDTH="{width}"' if width else ""
    return (f'  {nid} [label=<<TABLE BORDER="1" COLOR="{LINE}" CELLBORDER="0" CELLSPACING="0" '
            f'CELLPADDING="3" BGCOLOR="{body}"{w}>' + "".join(rows) + '</TABLE>>];\n')

def plain(nid, title, sub=None, fill=WHITE, border=LINE, tcol=INK, fam=None, size=8.4):
    fam = fam or CJK
    title = esc(title); sub = esc(sub)
    s = f'<FONT FACE="{fam}" POINT-SIZE="{size}" COLOR="{tcol}"><B>{title}</B></FONT>'
    if sub: s += f'<BR/><FONT FACE="{CJK}" POINT-SIZE="6.6" COLOR="{MUTED}">{sub}</FONT>'
    return (f'  {nid} [label=<<TABLE BORDER="1" COLOR="{border}" CELLBORDER="0" CELLSPACING="0" '
            f'CELLPADDING="5" BGCOLOR="{fill}"><TR><TD>{s}</TD></TR></TABLE>>];\n')

def cluster(cid, label, body, color=LINE, bg="#FBFCFE", fc=SLATE):
    label = esc(label)
    return (f'  subgraph cluster_{cid} {{\n'
            f'    style="rounded,filled"; color="{color}"; fillcolor="{bg}"; penwidth=1.0;\n'
            f'    label=<<FONT FACE="{CJK}" POINT-SIZE="8" COLOR="{fc}"><B>{label}</B></FONT>>;\n'
            f'    labeljust="l"; margin=10;\n' + body + '  }\n')

def edge(a, b, label=None, color=SLATE, pw=1.0, style=None, ltail=None, constraint=None):
    at = [];
    if label: at.append(f'label=<<FONT FACE="{MONO}" POINT-SIZE="6.4" COLOR="{color}">{esc(label)}</FONT>>')
    at.append(f'color="{color}"'); at.append(f'penwidth={pw}')
    if style: at.append(f'style={style}')
    if constraint is not None: at.append(f'constraint={str(constraint).lower()}')
    return f'  {a} -> {b} [{", ".join(at)}];\n'

def render(body, rankdir="LR", splines="spline", nodesep=0.28, ranksep=0.55):
    return HEAD.format(rankdir=rankdir, splines=splines, nodesep=nodesep,
                       ranksep=ranksep, cjk=CJK, mono=MONO, slate=SLATE) + body + "}\n"
