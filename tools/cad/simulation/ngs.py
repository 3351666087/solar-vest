"""Thin ctypes wrapper around KiCad's bundled libngspice (shared mode)."""
import ctypes, os, numpy as np
LIB = os.path.expanduser("~/Applications/KiCad/KiCad/KiCad/KiCad.app/Contents/Frameworks/libngspice.0.dylib")
_out = []
class NGS:
    def __init__(self):
        self.lib = ctypes.CDLL(LIB)
        CB_PRINT = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
        CB_STAT = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_void_p)
        CB_EXIT = ctypes.CFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.c_bool, ctypes.c_bool, ctypes.c_int, ctypes.c_void_p)
        def pr(s, i, p):
            t = s.decode(errors="replace")
            if "Reference value" not in t: _out.append(t)
            return 0
        def st(s, i, p): return 0
        def ex(a, b, c, d, p): return 0
        self._cbs = (CB_PRINT(pr), CB_STAT(st), CB_EXIT(ex))
        self.lib.ngSpice_Init(self._cbs[0], self._cbs[1], self._cbs[2], None, None, None, None)
        self.lib.ngSpice_Command.argtypes = [ctypes.c_char_p]
        self.lib.ngGet_Vec_Info.restype = ctypes.c_void_p
        self.lib.ngSpice_CurPlot.restype = ctypes.c_char_p
        self.lib.ngSpice_AllVecs.restype = ctypes.POINTER(ctypes.c_char_p)
        self.lib.ngSpice_AllVecs.argtypes = [ctypes.c_char_p]
    def cmd(self, c): self.lib.ngSpice_Command(c.encode())
    def run(self, netlist):
        _out.clear(); self.cmd("destroy all"); self.cmd("reset")
        lines = [l for l in netlist.strip().splitlines()]
        arr = (ctypes.c_char_p * (len(lines) + 1))(*[l.encode() for l in lines], None)
        self.lib.ngSpice_Circ(arr); self.cmd("run")
        return "".join(x + "\n" for x in _out)
    def vecs(self):
        plot = self.lib.ngSpice_CurPlot()
        p = self.lib.ngSpice_AllVecs(plot); names = []; i = 0
        while p[i]: names.append(p[i].decode()); i += 1
        return names
    def vec(self, name):
        class VI(ctypes.Structure):
            _fields_ = [("v_name", ctypes.c_char_p), ("v_type", ctypes.c_int), ("v_flags", ctypes.c_short),
                        ("v_realdata", ctypes.POINTER(ctypes.c_double)), ("v_compdata", ctypes.c_void_p), ("v_length", ctypes.c_int)]
        ptr = self.lib.ngGet_Vec_Info(name.encode())
        if not ptr: raise KeyError(name)
        vi = ctypes.cast(ptr, ctypes.POINTER(VI)).contents
        return np.ctypeslib.as_array(vi.v_realdata, shape=(vi.v_length,)).copy()
