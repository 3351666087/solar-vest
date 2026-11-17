#!/usr/bin/env python3
"""SIM-11: BLE link budget from the SIM-10 on-body antenna gain.

Criterion (ARCHITECTURE §9): >= 10 dB margin at 2 m with 15 dB body shadow and a
phone antenna of -5 dBi; otherwise trigger R4.

Band antenna gain toward the phone: two definitions are reported
  * mean realized gain  G_mean = 10 log10(eta_tot)  (sphere average; the honest
    number for an unknown phone direction, used for the pass/fail)
  * peak realized gain  G_peak = D_max + 10 log10(eta_tot) (from the SIM-10 far
    field, informative only: the phone is rarely in the beam peak)
eta_tot is the SIM-10 total efficiency at the 50-ohm RF node; the Nordic match
loss from SIM-09 is subtracted separately.

  python sim11_link.py ../sim10_ifa/results/sim10_<final>.json [sim09.json] [--ff-from sim10_<coarse>.json]

--ff-from: take the (informational) directivity from another SIM-10 result that stored
near-field faces (the fine-mesh runs do not); eta_tot, which decides pass/fail, always
comes from the first argument.
"""
import os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results")

C0 = 299792458.0


def fspl(d_m, f_hz):
    return 20 * math.log10(4 * math.pi * d_m * f_hz / C0)


def main(sim10_json, sim09_json, ff_json=None):
    S = json.load(open(sim10_json))
    FF = json.load(open(ff_json)) if ff_json else S
    S9 = json.load(open(sim09_json))
    ch = S["chosen"]
    il_nordic = S9["nordic_murata_pads"]["IL_dB_band_max"]                       # [SIM-09]
    inputs = {
        "P_tx_band_dBm": (4.0, "nRF52832 max TX power, PS v1.x [BLE lane, datasheet]"),
        "sens_band_dBm": (-96.0, "nRF52832 BLE 1 Msps sensitivity, PS v1.x [BLE lane, datasheet]"),
        "P_tx_phone_dBm": (4.0, "assumed equal to the band (typical phones 0..+10 dBm) [E]"),
        "sens_phone_dBm": (-96.0, "assumed equal to the band (typical phones -90..-97 dBm) [E]"),
        "G_phone_dBi": (-5.0, "ARCHITECTURE §9 SIM-11 criterion"),
        "body_shadow_dB": (15.0, "ARCHITECTURE §9 SIM-11 criterion"),
        "distance_m": (2.0, "ARCHITECTURE §9 SIM-11 criterion"),
        "IL_nordic_match_dB": (il_nordic, "SIM-09, Murata S2P + lands, worst in 2.402-2.480 GHz"),
    }
    rows = []
    for fk in sorted(ch["eta_tot_body"]):
        f = float(fk) * 1e9
        eta = ch["eta_tot_body"][fk]
        g_mean = 10 * math.log10(eta)
        ff = (FF.get("farfield_body") or {}).get(f"{float(fk):.2f}")
        d_max = ff["Dmax_dBi"] if ff else None
        g_peak = d_max + g_mean if d_max is not None else None
        L = fspl(inputs["distance_m"][0], f)
        for direction, ptx, sens in (("band->phone", inputs["P_tx_band_dBm"][0], inputs["sens_phone_dBm"][0]),
                                     ("phone->band", inputs["P_tx_phone_dBm"][0], inputs["sens_band_dBm"][0])):
            prx = ptx - inputs["IL_nordic_match_dB"][0] + g_mean + inputs["G_phone_dBi"][0] - L - inputs["body_shadow_dB"][0]
            rows.append(dict(f_GHz=float(fk), direction=direction, eta_tot_body=eta, G_mean_dBi=g_mean,
                             D_max_dBi=d_max, G_peak_dBi=g_peak, FSPL_dB=L, P_rx_dBm=prx, margin_dB=prx - sens))
    worst = min(r["margin_dB"] for r in rows)
    # sensitivity: extra real-world losses not in the ARCHITECTURE criterion [E]
    extra = dict(polarization_mismatch_dB=3.0, fade_margin_dB=0.0)
    d_max_range = None
    budget = worst + 0.0
    # distance at which the criterion margin reaches 10 dB (free-space slope 20 dB/decade)
    d10 = inputs["distance_m"][0] * 10 ** ((worst - 10.0) / 20.0)
    d0 = inputs["distance_m"][0] * 10 ** ((worst - 0.0) / 20.0)
    R = dict(sim10_source=sim10_json, directivity_source=ff_json or sim10_json, inputs={k: dict(value=v[0], source=v[1]) for k, v in inputs.items()}, rows=rows,
             worst_margin_dB=worst, pass_ge_10dB=bool(worst >= 10.0),
             with_3dB_polarization_loss_margin_dB=worst - extra["polarization_mismatch_dB"],
             range_for_10dB_margin_m=d10, range_for_0dB_margin_m_free_space_slope=d0,
             note="free-space path loss; indoor multipath can add or remove ~10 dB; the 15 dB body shadow is the "
                  "ARCHITECTURE allowance, not a simulated value (the phantom in SIM-10 covers only the wrist).")
    os.makedirs(OUT, exist_ok=True)
    json.dump(R, open(os.path.join(OUT, "sim11_results.json"), "w"), indent=1)
    print(json.dumps(R, indent=1))


if __name__ == "__main__":
    args = sys.argv[1:]
    ffj = None
    if "--ff-from" in args:
        i = args.index("--ff-from"); ffj = args[i + 1]; del args[i:i + 2]
    main(args[0], args[1] if len(args) > 1 else os.path.join(HERE, "..", "sim09_match", "results", "sim09_results.json"), ffj)
