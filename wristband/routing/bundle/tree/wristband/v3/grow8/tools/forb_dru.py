"""[grow8 P-1] Rewrite the R-2 forbidden-net lists of a .kicad_dru from a plate_forbidden_nets.json.
usage: python forb_dru.py IN.kicad_dru OUT.kicad_dru FORB.json"""
import json, re, sys


def rewrite(dru, forb):
    cond = " || ".join("A.NetName == '%s'" % n for n in forb)
    out, n = re.subn(r"\(A\.NetName == '[^)]*'\)\"", "(" + cond + ")\"", dru)
    assert n == 2, "expected the two R-2 rules, found %d" % n
    return out


if __name__ == "__main__":
    open(sys.argv[2], "w").write(rewrite(open(sys.argv[1]).read(), json.load(open(sys.argv[3]))))


def shield(dru, layers):
    """[grow8 Q-3] the R-2 inner-track rule stops applying on the shielded layers (In2 / In3 between the In1 GND and In4 VDD_1V8 planes)."""
    i = dru.index('(rule "R-2 no inner track of a forbidden net over a plate"')
    j = dru.index("A.Type == 'Track' && ", i) + len("A.Type == 'Track' && ")
    if "A.Layer != " in dru[i:j + 200]:
        return dru
    ins = "".join("A.Layer != '%s' && " % l for l in layers)
    return dru[:j] + ins + dru[j:]
