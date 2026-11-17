"""SENSORS_STORAGE block of SolarBand V2-B (ARCHITECTURE.md sections 2.1, 3.3, R-THERM-1; plus the skin-hot warning LED): LIS2DW12 accelerometer (I2C 0x19: CS = 1,
SA0 = 1), TMP117 skin temperature (0x48: ADD0 = GND; thermal pad floating, coupled to the E1 copper island),
MX25R1635F 16 Mbit NOR on the shared SPI, and the I2C pull-ups (4.7 k to VDD_1V8, section 2.1).
"""
from common import mk, two, wire, NC, LED_NONE

def build(n):
    B = "sensors_storage"; gnd = n.GND; v = n.VDD_1V8
    u9 = mk("LIS2DW12", "U9", B, "Accelerometer, I2C 0x19")
    wire(u9, {"SCL/SPC": n.I2C_SCL, "CS": v, "SDO/SA0": v, "SDA/SDI/SDO": n.I2C_SDA, "NC": NC, 6: gnd, "RES": gnd,
              8: gnd, "VDD": v, "VDD_IO": v, "INT2": NC, "INT1": n.IMU_INT1})   # [V3F] INT2 unused: P0.26 is the button (BASELINE 6); FIFO threshold routed to INT1 (CTRL4 INT1_FTH)
    two(mk("C100n", "C501", B, "LIS2DW12 100 nF at pin 9 (VDD) - section 4 application hints"), v, gnd)
    two(mk("C10u", "C502", B, "LIS2DW12 10 uF at pin 9 (VDD; ceramic instead of aluminium)"), v, gnd)
    u10 = mk("TMP117", "U10", B, "Skin temperature, I2C 0x48, on the dry side over the thermal-via island under an electrode plate (REDESIGN 5.7)")
    wire(u10, {"SCL": n.I2C_SCL, "GND": gnd, "ALERT": NC, "ADD0": gnd, "V+": v, "SDA": n.I2C_SDA, "ThermalPad": NC})
    two(mk("C100n", "C504", B, "TMP117 V+ 0.1 uF"), v, gnd)
    u11 = mk("MX25R1635F", "U11", B, "16 Mbit NOR: log + MCUboot secondary slot")
    wire(u11, {"CS#": n.CS_FLASH, "SO/SIO1": n.SPI_MISO, "WP#/SIO2": n.FLASH_WP, "GND": gnd, "SI/SIO0": n.SPI_MOSI,
               "SCLK": n.SPI_SCK, "RESET#/SIO3": n.FLASH_RST, "VCC": v, "EP": gnd})
    two(mk("C100n", "C505", B, "MX25R VCC 0.1 uF"), v, gnd)
    two(mk("R100k", "R501", B, "CS_FLASH pull-up 100 k (deselected while the MCU is in reset)"), n.CS_FLASH, v)
    two(mk("R100k", "R503", B, "WP# pull-up 100 k (write-protect inactive; SIO2 never driven, QE = 0)"), n.FLASH_WP, v)
    two(mk("R100k", "R504", B, "RESET# pull-up 100 k (SIO3 never driven, QE = 0)"), n.FLASH_RST, v)
    two(mk("R4k7", "R505", B, "I2C SDA pull-up 4.7 k"), n.I2C_SDA, v)
    two(mk("R4k7", "R506", B, "I2C SCL pull-up 4.7 k"), n.I2C_SCL, v)
    # ---- skin-hot warning (REDESIGN decision 5 option b, working decision 4): right-angle hyper-red LED at the board edge behind a light
    #      window in a light-tight pocket of the ring; the BLE flag is the second channel.
    #      [FIX R-06] KA-2810ASURSK (150 mcd min / 300 typ at 20 mA) instead of LTST-S270KRKT (18 / 54 mcd), 100 Ohm 0603 instead of 220 Ohm:
    #      8-25 mA while Q6 is on (CALC.md section 8); firmware blinks it at <= 25 % duty ----
    if LED_NONE: return        # [G1 level 4] SB_LED=none: the skin-hot LED chain D10 / R507 / Q6 / R508 is not on the board (only with the supervisor's release, BASELINE 5.3 reserve 1)
    d10 = mk("LED_SIDE_RED", "D10", B, "skin-hot warning LED, right-angle hyper red, at the board edge (light window in a light-tight pocket of the ring) [FIX R-06]")
    wire(d10, {"A": n.ALERT_A, "K": n.ALERT_K})
    two(mk("R100R_0402_0W1", "R507", B, "warning LED series 100 Ohm 0402 100 mW (ERJ2RK) from VSTOR_SW: 8-25 mA, <= 65 mW in the resistor at 100 % duty, <= 16 mW at the 25 % blink (CALC.md 8) [FIX R-06; G1 L0: was 0603]"), n.VSTOR_SW, n.ALERT_A)
    q6 = mk("PMZ290UNE2", "Q6", B, "warning LED switch (the LED supply is above VDD, so no GPIO sees it)")
    wire(q6, {"G": n.ALERT_LED, "S": gnd, "D": n.ALERT_K})
    two(mk("R1M", "R508", B, "ALERT_LED pull-down 1 M: LED off while the MCU is in reset"), n.ALERT_LED, gnd)
