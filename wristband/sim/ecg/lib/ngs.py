"""ctypes wrapper around KiCad 10's bundled libngspice (shared mode).
Derived from SolarVest_repo/tools/cad/simulation/ngs.py; adds complex vectors (AC analysis), XSPICE
code-model loading (analog.cm gives s_xfer) and an error check on every run."""
import ctypes, os, numpy as np
APP = os.path.expanduser("~/Applications/KiCad/KiCad/KiCad/KiCad.app/Contents")
LIB = APP + "/Frameworks/libngspice.0.dylib"
CM = APP + "/PlugIns/sim/ngspice/analog.cm"
_out = []

class _VI(ctypes.Structure):
    _fields_ = [("v_name", ctypes.c_char_p), ("v_type", ctypes.c_int), ("v_flags", ctypes.c_short),
                ("v_realdata", ctypes.POINTER(ctypes.c_double)), ("v_compdata", ctypes.POINTER(ctypes.c_double)),
                ("v_length", ctypes.c_int)]

class NGS:
    _lib = None
    def __init__(self):
        if NGS._lib is None:
            lib = ctypes.CDLL(LIB)
            CB_PRINT = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
            CB_STAT = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
            CB_EXIT = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
            def pr(s, i, p):
                t = s.decode(errors="replace")
                if "Reference value" not in t: _out.append(t)
                return 0
            NGS._cbs = (CB_PRINT(pr), CB_STAT(lambda s, i, p: 0), CB_EXIT(lambda a, b, c, d, p: 0))
            lib.ngSpice_Init(NGS._cbs[0], NGS._cbs[1], NGS._cbs[2], None, None, None, None)
            lib.ngSpice_Command.argtypes = [ctypes.c_char_p]
            lib.ngGet_Vec_Info.restype = ctypes.c_void_p
            lib.ngSpice_CurPlot.restype = ctypes.c_char_p
            lib.ngSpice_AllVecs.restype = ctypes.POINTER(ctypes.c_char_p)
            lib.ngSpice_AllVecs.argtypes = [ctypes.c_char_p]
            lib.ngSpice_Command(f"codemodel {CM}".encode())
            NGS._lib = lib
        self.lib = NGS._lib

    def cmd(self, c):
        self.lib.ngSpice_Command(c.encode())

    def run(self, netlist):
        _out.clear(); self.cmd("destroy all"); self.cmd("remcirc")
        lines = [l for l in netlist.strip().splitlines()]
        arr = (ctypes.c_char_p * (len(lines) + 1))(*[l.encode() for l in lines], None)
        self.lib.ngSpice_Circ(arr); self.cmd("run")
        log = "".join(x + "\n" for x in _out)
        bad = [l for l in log.splitlines() if ("Error" in l or "error" in l.lower() and "MIF" in l
               or "singular" in l.lower() or "Timestep too small" in l or "not parsed" in l)]
        if bad:
            raise RuntimeError("ngspice failed:\n" + "\n".join(bad[:20]) + "\n--- log tail ---\n" + log[-2500:])
        return log

    def vecs(self):
        plot = self.lib.ngSpice_CurPlot()
        p = self.lib.ngSpice_AllVecs(plot); names = []; i = 0
        while p[i]: names.append(p[i].decode()); i += 1
        return names

    def vec(self, name):
        ptr = self.lib.ngGet_Vec_Info(name.encode())
        if not ptr: raise KeyError(name)
        vi = ctypes.cast(ptr, ctypes.POINTER(_VI)).contents
        n = vi.v_length
        if vi.v_realdata:
            return np.ctypeslib.as_array(vi.v_realdata, shape=(n,)).copy()
        a = np.ctypeslib.as_array(vi.v_compdata, shape=(2 * n,)).copy()
        return a[0::2] + 1j * a[1::2]
