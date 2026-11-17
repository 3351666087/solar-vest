"""PPG block of SolarBand V2-B: MAX86141 + 2 OSRAM CT DBLP31.12 heart-rate LEDs (D3, D4) + VEMD8080 photodiode, per the
MAX86141 typical application circuit (data sheet p.88). V2-B: the LED boost is removed; the LED anodes sit on VLED =
VSTOR_SW behind R117 3.3 Ohm (power.py), i.e. on the cell voltage 3.31-4.2 V (MAX86141 VLED range 3.1-5.5 V, p.6).
The firmware caps the LED current against VBAT and logs the driver-compliance flag (REDESIGN G-11, P-6).
D3, D4 and PD1 are the only JLC-placed parts on the skin face (B.Cu), under the optical cap; everything else is on the sky side.
"""
from common import mk, two, wire, NC

def build(n):
    B = "ppg"; gnd = n.GND
    u8 = mk("MAX86141", "U8", B, "PPG AFE (2 PD channels, LED1/LED2 drivers)")
    wire(u8, {"VLED": n.VLED, "SCLK": n.SPI_SCK, "SDO": n.SPI_MISO, "SDI": n.SPI_MOSI, "CSB": n.CS_PPG,
              "LED3_DRV": NC, "INT": n.PPG_INT, "GPIO1": NC, "GPIO2": NC, "VREF": n.PPG_VREF,
              "LED2_DRV": n.LED2_DRV, "VDD_DIG": n.VDD_1V8, "GND_DIG": gnd, "GND_ANA": gnd, "PD_GND": n.PD_GND,
              "LED1_DRV": n.LED1_DRV, "VDD_ANA": n.VDD_1V8, "PGND": gnd, "PD2_IN": n.PD_GND, "PD1_IN": n.PD1_IN})
    # CT DBLP31.12: pad 1 = anode (small land), pads 2 and 3 = cathode (small + large land), pinmap/C5603826.yaml
    d3 = mk("LED_HRM", "D3", B, "Heart-rate LED 1 (anode VLED, cathode LED1_DRV), skin face", side="B"); wire(d3, {1: n.VLED, 2: n.LED1_DRV, 3: n.LED1_DRV})
    d4 = mk("LED_HRM", "D4", B, "Heart-rate LED 2 (anode VLED, cathode LED2_DRV), skin face", side="B"); wire(d4, {1: n.VLED, 2: n.LED2_DRV, 3: n.LED2_DRV})
    pd = mk("VEMD8080", "PD1", B, "Photodiode: cathode pads -> PD1_IN, anode -> PD_GND, skin face", side="B")
    wire(pd, {1: n.PD1_IN, 2: n.PD1_IN, 3: n.PD1_IN, 4: n.PD1_IN, 5: n.PD_GND, 6: n.PD1_IN, 7: n.PD1_IN, 8: n.PD1_IN})
    two(mk("C100n", "C401", B, "VDD_ANA 0.1 uF (at bump D2)"), n.VDD_1V8, gnd)
    two(mk("C10u", "C402", B, "VDD_ANA 10 uF"), n.VDD_1V8, gnd)
    two(mk("C100n", "C405", B, "VDD_DIG 0.1 uF to GND_DIG (at bump C2)"), n.VDD_1V8, gnd)
    two(mk("C1u", "C403", B, "VREF 1 uF to GND_ANA"), n.PPG_VREF, gnd)
    two(mk("C10u_0603", "C404", B, "VLED 10 uF to PGND (at bump A1); part of the LED reservoir"), n.VLED, gnd)
    two(mk("R100k", "R401", B, "INT pull-up 100 k to 1.8 V (open-drain INT)"), n.PPG_INT, n.VDD_1V8)
    two(mk("R100k", "R402", B, "CS_PPG pull-up 100 k (deselected while the MCU is in reset)"), n.CS_PPG, n.VDD_1V8)
    two(mk("NETTIE", "NT2", B, "PD_GND -> GND shorting via (data sheet note 3)"), n.PD_GND, gnd)
