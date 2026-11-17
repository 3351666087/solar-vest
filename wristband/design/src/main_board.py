"""SolarBand V3-F MAIN board, top level: global nets + the blocks (v3/decide/BASELINE.md).
Run:  [SB_FL=fit|dnp|none] [SB_LED=fit|none] [SB_MOTOR=erm8|erm7|erm6|none] [SB_O2=std|merged|pack] python main_board.py
Outputs (design/out/<variant>): solarband_main.net (SKiDL netlist, KiCad format), parts.json, skidl_erc.log
"""
import os, sys, types, io as _io, contextlib
from common import Net, ERC, generate_netlist, export_parts, check_all_pins_assigned, DESIGN, VARIANT, VTAG, ABSENT_NETS
import skidl
import power, mcu_rf, ecg, ppg, sensors_storage, io_block, charger, o2, hmi

NETS = """GND GND_PMIC VDD_1V8 VSTOR VSTOR_SW SW_ON VBAT_IC BATT_P VIN_DC PV_NODE PV_SW PV_Q VLED AVDD_ECG ECG_PWR_EN AVDD_EN
VREF_SAMP VBAT_OK VOUT_EN VBAT_OV VRDIV OK_HYST OK_PROG VOUT_SET LBUCK LBOOST PV_INH NTC NTC_EN NTC_ADC
BQ_EN EN_HOLD PWR_HOLD CYC_G CYC_A PWR_CYC VDD_DIS INA_VS INA_EN ALERT_LED ALERT_A ALERT_K
I2C_SDA I2C_SCL SPI_SCK SPI_MOSI SPI_MISO CS_ECG CS_PPG CS_FLASH ECG_DRDY ECG_START ECG_PWDN PPG_INT
IMU_INT1 SWDIO SWDCLK NRESET FLASH_WP FLASH_RST
DEC1 DEC2 DEC3 DEC4 DCC DCDC_MID XC1 XC2 XL1 XL2 RF_ANT RF_50R ANT_FEED
ECG_INP ECG_INN E1_PAD E1_LINK E1_MID E2_PAD E2_LINK E2_MID E3_PAD E3_MID RLD_OUT RLD_INV RLD_Z PGA1P PGA1N PGA2P PGA2N ECG_VREFP ECG_VCAP1
ECG_VCAP2 ECG_CLK ECG_GPIO1 ECG_GPIO2
PPG_VREF PD_GND PD1_IN LED1_DRV LED2_DRV
VBUS_K VBUS ISET ISET_RC VSET CHG_PG_N VB_DET CHG_DIS BTN BTN_SUP BTN_N
GND_K GK_G BTN_G
O2_G O2_OK O2_NC O2_PV V_O2 O2_TC O2_TH O2_HB
VDD_DISP DISP_EN DISP_SCS DISP_CTRL EXTCOMIN D_SCLK D_SI D_SCS D_EXTCOMIN D_DISP FL_EN FL_A FL_K MOTOR_PWM MOTOR_G MOTOR_N MOTOR_S
BATT_P_A GND_A1 NTC_A GND_A2 PV_W GND_B""".split()

def build():
    n = types.SimpleNamespace(**{k: Net(k) for k in NETS})
    power.build(n); mcu_rf.build(n); ecg.build(n); ppg.build(n); sensors_storage.build(n); io_block.build(n)
    charger.build(n); o2.build(n); hmi.build(n)
    return n

if __name__ == "__main__":
    out = os.path.join(DESIGN, "out", VTAG); os.makedirs(out, exist_ok=True)
    n = build()
    circ = __import__("builtins").default_circuit
    check_all_pins_assigned(circ)
    lonely = [k for k in NETS if len(getattr(n, k).pins) < 2 and not (k in ABSENT_NETS and len(getattr(n, k).pins) == 0)]   # [G1] nets of a removed block have no pins
    if lonely: raise SystemExit(f"nets with < 2 pins: {lonely}")
    buf = _io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        ERC()
    open(os.path.join(out, "skidl_erc.log"), "w").write(buf.getvalue())
    generate_netlist(file_=os.path.join(out, "solarband_main.net"))
    rows = export_parts(circ, os.path.join(out, "parts.json"))
    print(VTAG, VARIANT, len(rows), "parts;", sum(1 for r in rows.values() if r["jlc_placed"]), "JLC-placed;", len(NETS), "named nets")
