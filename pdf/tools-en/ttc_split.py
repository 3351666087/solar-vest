"""Split a .ttc collection into standalone .ttf files (pure stdlib)."""
import struct, sys, os

def tables_of(d, off):
    numT = struct.unpack(">H", d[off+4:off+6])[0]
    recs = []
    for t in range(numT):
        r = off + 12 + 16*t
        tag, cs, o, ln = struct.unpack(">4sIII", d[r:r+16])
        recs.append((tag, cs, o, ln))
    return recs

def psname(d, recs):
    for tag, cs, off, ln in recs:
        if tag != b'name': continue
        fmt, cnt, so = struct.unpack(">HHH", d[off:off+6])
        best = None
        for k in range(cnt):
            pid, eid, lid, nid, l, ofs = struct.unpack(">HHHHHH", d[off+6+12*k:off+6+12*k+12])
            if nid == 6:
                raw = d[off+so+ofs: off+so+ofs+l]
                try: s = raw.decode('utf-16-be') if pid == 3 else raw.decode('mac-roman')
                except Exception: continue
                if pid == 3 or best is None: best = s
        return best
    return None

def csum(b):
    b = b + b'\0' * ((4 - len(b) % 4) % 4)
    return sum(struct.unpack(">%dI" % (len(b)//4), b)) & 0xFFFFFFFF

def extract(d, off, out):
    recs = tables_of(d, off)
    recs.sort(key=lambda r: r[0])
    n = len(recs)
    sr = 1
    while sr * 2 <= n: sr *= 2
    es = sr.bit_length() - 1
    head = struct.pack(">IHHHH", 0x00010000, n, sr*16, es, n*16 - sr*16)
    body, dirents, cur = b'', [], 12 + 16*n
    for tag, cs, o, ln in recs:
        data = d[o:o+ln]
        dirents.append(struct.pack(">4sIII", tag, csum(data), cur, ln))
        pad = (4 - ln % 4) % 4
        body += data + b'\0'*pad
        cur += ln + pad
    font = head + b''.join(dirents) + body
    # fix head.checkSumAdjustment
    for i, (tag, cs, o, ln) in enumerate(recs):
        if tag == b'head':
            hoff = struct.unpack(">I", font[12+16*i+8:12+16*i+12])[0]
            font = font[:hoff+8] + b'\0'*4 + font[hoff+12:]
            adj = (0xB1B0AFBA - csum(font)) & 0xFFFFFFFF
            font = font[:hoff+8] + struct.pack(">I", adj) + font[hoff+12:]
            break
    open(out, 'wb').write(font)
    return len(font)

src, outdir, want = sys.argv[1], sys.argv[2], sys.argv[3:]
d = open(src, 'rb').read()
tag, maj, mino, nf = struct.unpack(">4sHHI", d[:12])
assert tag == b'ttcf', tag
offs = struct.unpack(">%dI" % nf, d[12:12+4*nf])
os.makedirs(outdir, exist_ok=True)
for o in offs:
    nm = psname(d, tables_of(d, o))
    if want and nm not in want: continue
    p = os.path.join(outdir, nm + ".ttf")
    print(f"  {nm:<28} -> {extract(d, o, p):>9,} bytes")
