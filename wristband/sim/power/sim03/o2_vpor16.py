"""Sensitivity: cold-start light through the O-2 with the TLV7031 POR at 1.60 V (the minimum specified supply) instead of 1.50 V (E)."""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import o2_tb as T
def ok(lux, wing, vpor):
    d = T.run(dict(pv=T.pv_table(lux=lux, wing=wing), tstop=2.0, load='cs', q14_vth=0.95, vpor=vpor, tmax='1m'))
    return T.tavg(d['time'], d['iq14'], 0.5, 2.0)
out = {}
for wing in (1.0, 0.0):
    lo, hi = 100.0, 6000.0
    for _ in range(9):
        m = math.sqrt(lo * hi)
        if ok(m, wing, 1.60) >= 21.4e-6: hi = m
        else: lo = m
    out[f'VPOR 1.60 V | wing {wing:g} | strips 2.30 mm'] = dict(lux_for_21p4uA_through_O2=round(hi, -1)); print(out)
json.dump(out, open(os.path.join(HERE, 'o2_vpor16.json'), 'w'), indent=1)
