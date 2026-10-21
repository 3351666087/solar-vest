#!/usr/bin/env python3
"""English build — mirrors build.py but reads src-en/, tools-en/, assets/svg-en/
and emits en-*.xhtml part files + parts-en.txt."""
import glob, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)

# 0. run the EN diagram generators
for g in sorted(glob.glob("tools-en/gen_*.py")):
    r = subprocess.run([sys.executable, g], capture_output=True, text=True)
    if r.returncode: sys.exit(f"generator failed {g}:\n{r.stdout}\n{r.stderr}")

# 1. render dot -> svg (EN sources -> EN assets)
os.makedirs("assets/svg-en", exist_ok=True)
for d in sorted(glob.glob("src-en/dot/*.dot")):
    name = os.path.splitext(os.path.basename(d))[0]
    out = f"assets/svg-en/{name}.svg"
    r = subprocess.run(["dot", "-Tsvg", d, "-o", out], capture_output=True, text=True)
    if r.returncode: sys.exit(f"dot failed on {d}:\n{r.stderr}")
    if r.stderr.strip(): print(f"  dot warn {name}: {r.stderr.strip()[:200]}")

def clean_svg(s, target_w=None):
    s = re.sub(r"<\?xml[^>]*\?>", "", s)
    s = re.sub(r"<!DOCTYPE[^>]*>", "", s, flags=re.S)
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    m = re.search(r"<svg([^>]*)>", s)
    if m:
        attrs = m.group(1)
        vb = re.search(r'viewBox="([^"]+)"', attrs)
        if vb:
            parts = vb.group(1).split()
            w, h = float(parts[2]), float(parts[3])
            attrs = re.sub(r'\s(width|height)="[^"]*"', "", attrs)
            attrs = re.sub(r'\sstyle="[^"]*"', "", attrs)
            px_w = int(round(target_w if target_w else w * 4 / 3))
            px_h = int(round(px_w * h / w))
            attrs += f' width="{px_w}" height="{px_h}"'
            s = s[:m.start()] + f"<svg{attrs}>" + s[m.end():]
    return s.strip()


# 2. concat sections -> ordered parts; "-L" in name means landscape
import page_rules_en as page_rules
head = open("src-en/doc/00-head.xhtml", encoding="utf-8").read()
foot = open("src-en/doc/99-foot.xhtml", encoding="utf-8").read()
cover_src = open("src-en/doc/01-cover.xhtml", encoding="utf-8").read()
def group(f):
    return "L" if "-L." in os.path.basename(f) else "P"
parts, cur, mode = [], [], None
for f in sorted(glob.glob("src-en/doc/*.xhtml")):
    bn = os.path.basename(f)
    if bn.startswith(("00-", "01-", "99-")): continue
    g = group(f)
    if g != mode:
        if cur: parts.append((mode, cur))
        cur, mode = [], g
    cur.append(open(f, encoding="utf-8").read())
if cur: parts.append((mode, cur))

docs = {"en-cover.xhtml": head.replace("@@PAGE_RULES@@", page_rules.COVER) + cover_src + foot}
order = ["en-cover.xhtml"]
for i, (g, chunks) in enumerate(parts):
    name = f"en-part{i}{g}.xhtml"
    rules = page_rules.LAND if g == "L" else page_rules.BODY
    docs[name] = head.replace("@@PAGE_RULES@@", rules) + "\n".join(chunks) + foot
    order.append(name)
open("parts-en.txt", "w").write(" ".join(order))

# 3. inline @@name@@
def repl(m):
    spec = m.group(1)
    name, _, tw = spec.partition("|")
    p = f"assets/svg-en/{name}.svg"
    if not os.path.exists(p): sys.exit(f"missing svg: {p}")
    return clean_svg(open(p, encoding="utf-8").read(), float(tw) if tw else None)
total = 0
for name, d in docs.items():
    d, n = re.subn(r"@@([A-Za-z0-9_\-]+(?:\|[0-9.]+)?)@@", repl, d)
    total += n
    open(name, "w", encoding="utf-8").write(d)
    print(f"  built {name:<16} {len(d):>8,} chars, {n} diagrams")
print(f"total {total} diagrams inlined")
print("  order:", open("parts-en.txt").read())
