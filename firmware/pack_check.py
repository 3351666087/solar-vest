#!/usr/bin/env python3
"""Check that the firmware's TELEM_A / TELEM_B packing reproduces software/protocol/vectors.json.

This mirrors packTelemA()/packTelemB() in solarvest_pmb/solarvest_pmb.ino: it takes each
vector's decoded `expected` values as the firmware inputs, packs them the same way, and
asserts the bytes equal a_hex / b_hex.

Field order (little-endian, 20 bytes each, software/SPEC.md section 2):

TELEM_A  off type  field   firmware scaling
         0   u8    seq
         1   u16   vpv     mV          round(V * 1000), clamp 0..65535
         3   i16   ipv     0.1 mA      round(mA * 10),  clamp int16 (0x43 if RANGE_LO else 0x40)
         5   u16   vbat    mV
         7   i16   ibat    0.1 mA      + = charging
         9   u16   vload   mV
         11  i16   iload   0.1 mA
         13  i16   iref1   10 uA       round(mA * 100), already sign-corrected (x -1)
         15  i16   iref2   10 uA
         17  u8    ina_ok  bit i = chip [0x40,0x43,0x41,0x42,0x44,0x45][i] answered
         18  u8    pad     0
         19  u8    proto   1

TELEM_B  0   u8    seq
         1   i16   ntc     0.1 C, -32768 = invalid
         3   u8    outputs b0 load b1 pv b2 chg_inh b3 range_lo b4 sync
         4   u8    inputs  b0 charging b1 done
         5   u8    mode    b0 pv_auto b1 chg_auto b2 range_auto b3 autoload b4 load_manual_on
         6   u8    safety  b0 batt_lockout b1 temp_inhibit b2 night_pv_off b3 ntc_fault
         7   u32   uptime  s
         11  u8    reset_reason
         12  u8    fw      1
         13..19    pad     0
"""
import json
import struct
import sys
from pathlib import Path

VECTORS = Path(__file__).resolve().parent.parent / "software" / "protocol" / "vectors.json"
NTC_INVALID = -32768


def lround(x: float) -> int:
    # C lroundf(): half away from zero (Python's round() is banker's rounding)
    return int(x + 0.5) if x >= 0 else -int(-x + 0.5)


def clamp_i16(x: float) -> int:
    return max(-32768, min(32767, lround(x)))


def clamp_u16(x: float) -> int:
    return max(0, min(65535, lround(x)))


def bits(flags: dict, order: list) -> int:
    return sum(1 << i for i, name in enumerate(order) if flags[name])


def pack_a(s: dict) -> bytes:
    return struct.pack(
        "<BHhHhHhhhBBB",
        s["seq"] & 0xFF,
        clamp_u16(s["vpv_v"] * 1000),
        clamp_i16(s["ipv_ma"] * 10),
        clamp_u16(s["vbat_v"] * 1000),
        clamp_i16(s["ibat_ma"] * 10),
        clamp_u16(s["vload_v"] * 1000),
        clamp_i16(s["iload_ma"] * 10),
        clamp_i16(s["iref1_ma"] * 100),
        clamp_i16(s["iref2_ma"] * 100),
        s["ina_ok"],
        0,
        1,
    )


def pack_b(s: dict) -> bytes:
    ntc = NTC_INVALID if s["ntc_c"] is None else clamp_i16(s["ntc_c"] * 10)
    head = struct.pack(
        "<BhBBBBIBB",
        s["seq"] & 0xFF,
        ntc,
        bits(s["outputs"], ["load", "pv", "chg_inh", "range_lo", "sync"]),
        bits(s["inputs"], ["charging", "done"]),
        bits(s["mode"], ["pv_auto", "chg_auto", "range_auto", "autoload", "load_manual_on"]),
        bits(s["safety"], ["batt_lockout", "temp_inhibit", "night_pv_off", "ntc_fault"]),
        s["uptime_s"],
        s["reset_reason"],
        s["fw"],
    )
    return head + bytes(20 - len(head))


def main() -> int:
    vectors = json.loads(VECTORS.read_text())
    failures = 0
    for v in vectors:
        a, b = pack_a(v["expected"]), pack_b(v["expected"])
        assert len(a) == 20 and len(b) == 20
        ok_a, ok_b = a.hex() == v["a_hex"], b.hex() == v["b_hex"]
        print(f"{'OK ' if ok_a and ok_b else 'FAIL'} {v['name']}")
        if not ok_a:
            print(f"   A got {a.hex()}\n   A exp {v['a_hex']}")
        if not ok_b:
            print(f"   B got {b.hex()}\n   B exp {v['b_hex']}")
        failures += not (ok_a and ok_b)
    print(f"{len(vectors) - failures}/{len(vectors)} vectors match")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
