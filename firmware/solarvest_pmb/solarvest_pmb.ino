// SolarVest PMB-H production firmware (XIAO nRF52840 Sense)
// Spec: software/SPEC.md sections 1–3; protocol test vectors: software/protocol/vectors.json
// Core: Seeeduino:nrf52 1.1.13 (Adafruit Bluefruit), FQBN Seeeduino:nrf52:xiaonRF52840Sense
//
// Once per second: re-probe missing INA226s → read all chips and the NTC → safety/control logic → BLE notify TELEM_A/B → print one serial line.
// Commands arrive via the BLE COMMAND characteristic or the serial port (115200, newline-terminated); both paths share one parser.
// No watchdog (it would get in the way of bootloader flashing), no persistence; at power-up the board is in the spec default state.

#include <Wire.h>
#include <bluefruit.h>
#include <Adafruit_LittleFS.h>
#include <InternalFileSystem.h>
using namespace Adafruit_LittleFS_Namespace;

// ───────────────────────── Version and protocol ─────────────────────────
static const uint8_t FW_VERSION = 2;

// v2: autoload on by default and stored in flash; BLE gateway keepalive (PING) and stale-connection cleanup
static const char *SETTINGS_FILE = "/svcfg";            // 1 byte: 'A' = autoload on, 'a' = off
static const uint32_t CENTRAL_NO_SUB_MS = 30000;        // connected 30 s without subscribing to telemetry → disconnect
static const uint32_t CENTRAL_SILENT_MS = 180000;       // 180 s without any write (the gateway sends PING every 60 s) → disconnect
static const uint8_t PROTO_VERSION = 1;
static const uint8_t PAYLOAD_LEN = 20;

// ───────────────────────── Pins (XIAO Dn) ─────────────────────────
static const uint8_t PIN_NTC_ADC = A0;  // D0
static const uint8_t PIN_NTC_EN = 1;    // HIGH = power the NTC divider
static const uint8_t PIN_SYNC = 2;      // sync pulse output
static const uint8_t PIN_LOAD_EN = 3;   // HIGH = load on (100k pull-down, off by default)
static const uint8_t PIN_CHG_INH = 6;   // HIGH = charging inhibited
static const uint8_t PIN_RANGE_LO = 7;  // HIGH = panel current low range
static const uint8_t PIN_CHRG_N = 8;    // LOW = charging (open-drain)
static const uint8_t PIN_DONE_N = 9;    // LOW = fully charged (open-drain)
static const uint8_t PIN_PV_EN = 10;    // LOW = panel disconnected (100k pull-up, connected by default)

// ───────────────────────── Safety/control thresholds (SPEC §3) ─────────────────────────
static const uint16_t LOCKOUT_SET_MV = 3300;        // load on and below this value...
static const uint16_t LOCKOUT_SET_SECONDS = 10;     // ...for this many consecutive seconds → lockout
static const uint16_t LOCKOUT_CLEAR_MV = 3550;      // lockout clears once the battery is back above this value
static const uint16_t AUTOLOAD_ON_MV = 3700;        // autoload turn-on voltage
static const uint16_t BAT_MISSING_OFF_SECONDS = 10; // load on and BAT chip (0x41) missing for this many consecutive seconds → load off
static const float TEMP_CHG_MIN_C = 0.0f;           // inhibit charging below 0 °C
static const float TEMP_CHG_MAX_C = 45.0f;          // inhibit charging above 45 °C
static const float NIGHT_REF_MA = 1.0f;             // both reference cells below 1 mA counts as night
static const uint16_t NIGHT_SECONDS = 300;          // panel disconnected only after 300 s of continuous night
static const float RANGE_TO_LOW_MA = 150.0f;        // high-range reading below this value...
static const uint16_t RANGE_TO_LOW_SECONDS = 5;     // ...for 5 consecutive seconds → switch to low range
static const float RANGE_TO_HIGH_MA = 300.0f;       // low-range reading above this value → switch back to high range immediately

// NTC: R11 = 10k pull-up to NTC_EN, NTC to GND; ADC 10-bit, 3.6 V full scale
static const float NTC_VREF = 3.6f, NTC_VSUPPLY = 3.3f, NTC_RPULL = 10000.0f;
static const float NTC_R0 = 10000.0f, NTC_BETA = 3950.0f, NTC_T0_K = 298.15f;
static const int NTC_RAW_MIN = 10, NTC_RAW_MAX = 1013;  // outside this range = invalid (short/open circuit)
static const float NTC_PLAUSIBLE_MIN_C = -40.0f, NTC_PLAUSIBLE_MAX_C = 125.0f;
static const int16_t NTC_INVALID = -32768;

// ───────────────────────── INA226 ─────────────────────────
static const uint8_t INA_REG_CONFIG = 0x00, INA_REG_SHUNT = 0x01, INA_REG_BUS = 0x02, INA_REG_ID = 0xFE;
static const uint16_t INA_ID = 0x5449;
static const uint16_t INA_CONFIG = 0x4527;  // AVG16, 1.1 ms/1.1 ms, continuous
static const float INA_SHUNT_LSB_V = 2.5e-6f;
static const float INA_BUS_LSB_MV = 1.25f;
static const uint8_t INA_RECHECK_CONFIG_EVERY_S = 10;  // a chip loses its config after a power-on reset, so re-check periodically

// The index is the ina_ok bit number; the order is fixed as [0x40, 0x43, 0x41, 0x42, 0x44, 0x45]
enum { INA_PV_HI = 0, INA_PV_LO, INA_BAT, INA_LOAD, INA_REF1, INA_REF2, INA_COUNT };

struct InaChip {
  uint8_t addr;
  const char *name;
  float shuntOhm;
  float sign;  // REF1/REF2 are wired reversed on the real board, multiply by −1
  bool ok;
  int16_t shuntRaw;
  uint16_t busRaw;
};

static InaChip ina[INA_COUNT] = {
  {0x40, "PV_HI", 0.050f, +1.0f, false, 0, 0},
  {0x43, "PV_LO", 0.220f, +1.0f, false, 0, 0},
  {0x41, "BAT", 0.050f, +1.0f, false, 0, 0},
  {0x42, "LOAD", 0.100f, +1.0f, false, 0, 0},
  {0x44, "REF1", 0.470f, -1.0f, false, 0, 0},
  {0x45, "REF2", 0.470f, -1.0f, false, 0, 0},
};

// ───────────────────────── Measurements and control state ─────────────────────────
struct Measurements {
  bool ok[INA_COUNT];
  float vpv_mV, ipvHi_mA, ipvLo_mA, vbat_mV, ibat_mA, vload_mV, iload_mA, iref1_mA, iref2_mA;
  bool rangeLoAtRead;  // RANGE_LO state at read time; decides which panel-current range is reported
  int ntcRaw;
  bool ntcValid;
  float ntc_C;
  bool charging, done;
};

enum TriMode : uint8_t { MODE_AUTO, MODE_ON, MODE_OFF };  // RANGE: ON = HIGH, OFF = LOW

struct Control {
  // modes set by the user/commands
  TriMode pvMode = MODE_AUTO;
  TriMode chgMode = MODE_AUTO;
  TriMode rangeMode = MODE_AUTO;  // MODE_ON = force high range, MODE_OFF = force low range
  bool autoload = true;           // on by default; the actual value is read from flash at boot
  bool loadManualOn = false;
  bool syncEnabled = false;
  // internal latches and counters
  bool autoloadLatched = false;  // autoload has switched on (latched, so the load-induced voltage drop does not toggle it back and forth)
  bool battLockout = false;
  uint16_t lowBattSeconds = 0;
  uint16_t batMissingSeconds = 0;  // consecutive seconds the BAT chip has been missing while the load is on
  uint16_t darkSeconds = 0;
  uint16_t lowCurrentSeconds = 0;
  // safety flags
  bool tempInhibit = false;
  bool nightPvOff = false;
  bool ntcFault = false;
  // actual outputs
  bool loadOn = false;
  bool pvOn = true;
  bool chgInh = false;
  bool rangeLo = false;
};

static Measurements meas;
static Control ctl;

static volatile uint16_t connHdl = BLE_CONN_HANDLE_INVALID;
static volatile uint32_t connSinceMs = 0;     // time the connection was established
static volatile uint32_t lastWriteMs = 0;     // last command write (including PING)
static volatile uint32_t lastSubMs = 0;       // last time telemetry was seen subscribed

// ═════════════════════════ Settings (flash) ═════════════════════════
// Only "autoload" is stored: the user's choice survives a reboot or power loss; on if the file does not exist.
static bool fsOk = false;

static void loadSettings() {
  fsOk = InternalFS.begin();
  if (!fsOk) { Serial.println(F("Flash file system unavailable, autoload uses the default (on)")); return; }
  File f(InternalFS);
  if (f.open(SETTINGS_FILE, FILE_O_READ)) {
    char c = 0;
    if (f.read(&c, 1) == 1 && (c == 'A' || c == 'a')) ctl.autoload = (c == 'A');
    f.close();
  }
  Serial.printf("Settings: autoload %s\n", ctl.autoload ? "on" : "off");
}

static void saveSettings() {
  if (!fsOk) return;
  InternalFS.remove(SETTINGS_FILE);  // FILE_O_WRITE is append mode, so delete first, then write
  File f(InternalFS);
  if (f.open(SETTINGS_FILE, FILE_O_WRITE)) {
    char c = ctl.autoload ? 'A' : 'a';
    f.write(&c, 1);
    f.close();
  }
}

static void setAutoload(bool on) {
  if (ctl.autoload == on) return;  // no change, so do not write flash
  ctl.autoload = on;
  saveSettings();
}
static bool haveMeasurements = false;
static uint8_t seq = 0;
static uint8_t resetReason = 0;
static uint64_t uptimeMs = 0;
static uint32_t lastMillis = 0;
static uint32_t tTick = 0, tSync = 0;
static bool syncLevel = false;
static uint32_t rebootAt = 0;
static bool rebootPending = false;

// ───────────────────────── BLE ─────────────────────────
// 128-bit UUIDs stored little-endian: 5f1e000X-6a2b-4c3d-9e8f-50a1b2c3d4e5
#define SV_UUID(x) {0xe5, 0xd4, 0xc3, 0xb2, 0xa1, 0x50, 0x8f, 0x9e, 0x3d, 0x4c, 0x2b, 0x6a, (x), 0x00, 0x1e, 0x5f}
static const uint8_t UUID_SERVICE[16] = SV_UUID(0x01);
static const uint8_t UUID_TELEM_A[16] = SV_UUID(0x02);
static const uint8_t UUID_TELEM_B[16] = SV_UUID(0x03);
static const uint8_t UUID_COMMAND[16] = SV_UUID(0x04);

static BLEService svService(UUID_SERVICE);
static BLECharacteristic chrTelemA(UUID_TELEM_A);
static BLECharacteristic chrTelemB(UUID_TELEM_B);
static BLECharacteristic chrCommand(UUID_COMMAND);

// The BLE write callback runs in Bluefruit's callback task; it only queues the command, which is handled in loop() to avoid concurrent I2C access
static const size_t CMD_MAX = 20;
struct CmdMsg { char text[CMD_MAX + 1]; };
static QueueHandle_t cmdQueue = nullptr;

// ═════════════════════════ Helpers ═════════════════════════

static int16_t clampI16(float v) {
  long r = lroundf(v);
  if (r > 32767) return 32767;
  if (r < -32768) return -32768;
  return (int16_t)r;
}

static uint16_t clampU16(float v) {
  long r = lroundf(v);
  if (r > 65535) return 65535;
  if (r < 0) return 0;
  return (uint16_t)r;
}

static void putU16(uint8_t *p, uint16_t v) { p[0] = v & 0xFF; p[1] = v >> 8; }
static void putI16(uint8_t *p, int16_t v) { putU16(p, (uint16_t)v); }
static void putU32(uint8_t *p, uint32_t v) {
  p[0] = v & 0xFF; p[1] = (v >> 8) & 0xFF; p[2] = (v >> 16) & 0xFF; p[3] = v >> 24;
}

static uint32_t uptimeSeconds() { return (uint32_t)(uptimeMs / 1000ULL); }

// ═════════════════════════ INA226 ═════════════════════════

static bool inaRead(uint8_t addr, uint8_t reg, uint16_t &val) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission() != 0) return false;
  if (Wire.requestFrom(addr, (uint8_t)2) != 2) return false;
  uint8_t hi = Wire.read();
  uint8_t lo = Wire.read();
  val = (uint16_t)((hi << 8) | lo);
  return true;
}

static bool inaWrite(uint8_t addr, uint8_t reg, uint16_t val) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write((uint8_t)(val >> 8));
  Wire.write((uint8_t)(val & 0xFF));
  return Wire.endTransmission() == 0;
}

// Check the manufacturer ID and write the config; a missing chip NACKs and returns at once, never blocks
static bool inaProbe(InaChip &c) {
  uint16_t id;
  if (!inaRead(c.addr, INA_REG_ID, id) || id != INA_ID) return false;
  return inaWrite(c.addr, INA_REG_CONFIG, INA_CONFIG);
}

static void inaService(bool recheckConfig) {
  for (auto &c : ina) {
    if (!c.ok) {
      c.ok = inaProbe(c);
    } else if (recheckConfig) {
      uint16_t cfg;
      if (!inaRead(c.addr, INA_REG_CONFIG, cfg)) c.ok = false;
      else if (cfg != INA_CONFIG) c.ok = inaWrite(c.addr, INA_REG_CONFIG, INA_CONFIG);
    }
    uint16_t sh = 0, bus = 0;
    if (c.ok && inaRead(c.addr, INA_REG_SHUNT, sh) && inaRead(c.addr, INA_REG_BUS, bus)) {
      c.shuntRaw = (int16_t)sh;
      c.busRaw = bus;
    } else {
      c.ok = false;  // re-probe next second
      c.shuntRaw = 0;
      c.busRaw = 0;
    }
  }
}

static float inaCurrent_mA(const InaChip &c) {
  if (!c.ok) return 0.0f;
  return c.sign * (c.shuntRaw * INA_SHUNT_LSB_V) / c.shuntOhm * 1000.0f;
}

static float inaBus_mV(const InaChip &c) { return c.ok ? c.busRaw * INA_BUS_LSB_MV : 0.0f; }

// ═════════════════════════ NTC ═════════════════════════

static void readNtc(Measurements &m) {
  digitalWrite(PIN_NTC_EN, HIGH);
  delay(10);  // C9 = 100 nF, τ ≤ 1 ms; 10 ms is ample settling time
  int raw = analogRead(PIN_NTC_ADC);
  digitalWrite(PIN_NTC_EN, LOW);  // power off between readings: saves power and reduces NTC self-heating
  m.ntcRaw = raw;
  m.ntcValid = false;
  m.ntc_C = 0.0f;
  if (raw < NTC_RAW_MIN || raw > NTC_RAW_MAX) return;
  float v = raw * NTC_VREF / 1023.0f;
  // With an open circuit v approaches 3.3 V and the formula gives a negative resistance or a very low temperature; treat it as invalid so charging is not inhibited by mistake
  if (v >= NTC_VSUPPLY) return;
  float r = NTC_RPULL * v / (NTC_VSUPPLY - v);
  float t = 1.0f / (1.0f / NTC_T0_K + logf(r / NTC_R0) / NTC_BETA) - 273.15f;
  if (!(t >= NTC_PLAUSIBLE_MIN_C && t <= NTC_PLAUSIBLE_MAX_C)) return;
  m.ntc_C = t;
  m.ntcValid = true;
}

static void readAll(Measurements &m, bool recheckConfig) {
  m.rangeLoAtRead = ctl.rangeLo;
  inaService(recheckConfig);
  for (int i = 0; i < INA_COUNT; i++) m.ok[i] = ina[i].ok;
  m.vpv_mV = inaBus_mV(ina[INA_PV_HI]);
  m.ipvHi_mA = inaCurrent_mA(ina[INA_PV_HI]);
  m.ipvLo_mA = inaCurrent_mA(ina[INA_PV_LO]);
  m.vbat_mV = inaBus_mV(ina[INA_BAT]);
  m.ibat_mA = inaCurrent_mA(ina[INA_BAT]);
  m.vload_mV = inaBus_mV(ina[INA_LOAD]);
  m.iload_mA = inaCurrent_mA(ina[INA_LOAD]);
  m.iref1_mA = inaCurrent_mA(ina[INA_REF1]);
  m.iref2_mA = inaCurrent_mA(ina[INA_REF2]);
  readNtc(m);
  m.charging = digitalRead(PIN_CHRG_N) == LOW;
  m.done = digitalRead(PIN_DONE_N) == LOW;
}

// Reported panel current: 0x43 when the low range is on, otherwise 0x40
static float reportedIpv_mA(const Measurements &m) { return m.rangeLoAtRead ? m.ipvLo_mA : m.ipvHi_mA; }

// ═════════════════════════ Safety and control logic (SPEC §3 items 3–8) ═════════════════════════
// Pure logic, no hardware access: computes the outputs and safety flags in ctl from the measurements and modes.
// tick = true means this is the once-per-second periodic call and the timers advance;
// tick = false is used to recompute right after a command arrives (timers do not move, so the response need not wait for the next second).
static void runSafetyAndControl(const Measurements &m, bool tick) {
  const bool batOk = m.ok[INA_BAT];
  const float vbat = m.vbat_mV;

  // 3. Battery undervoltage lockout (always active). With the BAT chip missing the voltage is unknown: no counting, no clearing, and no autoload trigger.
  if (tick) {
    if (ctl.loadOn && batOk && vbat < LOCKOUT_SET_MV) {
      if (ctl.lowBattSeconds < LOCKOUT_SET_SECONDS) ctl.lowBattSeconds++;
    } else {
      ctl.lowBattSeconds = 0;
    }
    if (ctl.lowBattSeconds >= LOCKOUT_SET_SECONDS) {
      ctl.battLockout = true;
      ctl.lowBattSeconds = 0;
    }
    // Fail-safe: with the BAT chip missing the undervoltage lockout cannot be evaluated, so if the load is on and the chip is missing for 10 s, withdraw the load-on request.
    // batt_lockout is not set (that flag means low voltage only); LOAD ON works again once the chip recovers.
    if (ctl.loadOn && !batOk) {
      if (++ctl.batMissingSeconds >= BAT_MISSING_OFF_SECONDS) {
        ctl.loadManualOn = false;
        ctl.autoloadLatched = false;
        ctl.batMissingSeconds = 0;
        Serial.println(F("[safety] battery voltage chip 0x41 missing for 10 s, load switched off"));
      }
    } else {
      ctl.batMissingSeconds = 0;
    }
  }
  if (ctl.battLockout && batOk && vbat >= LOCKOUT_CLEAR_MV) ctl.battLockout = false;
  if (ctl.battLockout) {
    // On lockout withdraw every load-on request; otherwise the battery recovers to 3.55 V unloaded, the load turns straight back on, and it oscillates
    ctl.loadManualOn = false;
    ctl.autoloadLatched = false;
  }

  // 4. Temperature (always active). An invalid NTC only reports a fault and does not by itself inhibit charging (it must still charge when unattended).
  ctl.ntcFault = !m.ntcValid;
  ctl.tempInhibit = m.ntcValid && (m.ntc_C < TEMP_CHG_MIN_C || m.ntc_C > TEMP_CHG_MAX_C);

  // 5. Charge mode: AUTO/ON are inhibited only by temperature; OFF forces inhibit
  ctl.chgInh = ctl.tempInhibit || ctl.chgMode == MODE_OFF;

  // 6. Panel mode
  if (ctl.pvMode == MODE_AUTO) {
    const bool refsOk = m.ok[INA_REF1] && m.ok[INA_REF2];
    const bool dark = refsOk && fabsf(m.iref1_mA) < NIGHT_REF_MA && fabsf(m.iref2_mA) < NIGHT_REF_MA;
    if (!dark) {
      ctl.darkSeconds = 0;
      ctl.nightPvOff = false;  // light present or reference cells missing: reconnect the panel immediately
    } else if (tick && ctl.darkSeconds < NIGHT_SECONDS) {
      ctl.darkSeconds++;
    }
    if (ctl.darkSeconds >= NIGHT_SECONDS) ctl.nightPvOff = true;
    ctl.pvOn = !ctl.nightPvOff;
  } else {
    ctl.darkSeconds = 0;
    ctl.nightPvOff = false;
    ctl.pvOn = ctl.pvMode == MODE_ON;
  }

  // 7. Range mode
  if (ctl.rangeMode == MODE_AUTO) {
    if (ctl.rangeLo) {
      // a 0x43 value is meaningful only when read in the low range
      const bool loValid = m.ok[INA_PV_LO] && m.rangeLoAtRead;
      if (!m.ok[INA_PV_LO] || (loValid && fabsf(m.ipvLo_mA) > RANGE_TO_HIGH_MA)) {
        ctl.rangeLo = false;
        ctl.lowCurrentSeconds = 0;
      }
    } else {
      const bool small = m.ok[INA_PV_HI] && m.ok[INA_PV_LO] && !m.rangeLoAtRead &&
                         fabsf(m.ipvHi_mA) < RANGE_TO_LOW_MA;
      if (!small) {
        ctl.lowCurrentSeconds = 0;
      } else if (tick && ctl.lowCurrentSeconds < RANGE_TO_LOW_SECONDS) {
        ctl.lowCurrentSeconds++;
      }
      if (ctl.lowCurrentSeconds >= RANGE_TO_LOW_SECONDS) {
        ctl.rangeLo = true;
        ctl.lowCurrentSeconds = 0;
      }
    }
  } else {
    ctl.lowCurrentSeconds = 0;
    ctl.rangeLo = ctl.rangeMode == MODE_OFF;
  }

  // 8. Load. Once autoload switches on it stays latched until autoload is turned off, the load is switched off manually, or a lockout occurs.
  if (!ctl.autoload) ctl.autoloadLatched = false;
  if (ctl.autoload && !ctl.battLockout && batOk && vbat >= AUTOLOAD_ON_MV) ctl.autoloadLatched = true;
  ctl.loadOn = (ctl.loadManualOn || ctl.autoloadLatched) && !ctl.battLockout;
}

static void applyOutputs() {
  digitalWrite(PIN_LOAD_EN, ctl.loadOn ? HIGH : LOW);
  digitalWrite(PIN_PV_EN, ctl.pvOn ? HIGH : LOW);
  digitalWrite(PIN_CHG_INH, ctl.chgInh ? HIGH : LOW);
  digitalWrite(PIN_RANGE_LO, ctl.rangeLo ? HIGH : LOW);
}

// ═════════════════════════ Packing (SPEC §2, little-endian) ═════════════════════════

static void packTelemA(uint8_t out[PAYLOAD_LEN], const Measurements &m) {
  memset(out, 0, PAYLOAD_LEN);
  uint8_t inaOk = 0;
  for (int i = 0; i < INA_COUNT; i++) if (m.ok[i]) inaOk |= (1u << i);
  out[0] = seq;
  putU16(out + 1, clampU16(m.vpv_mV));
  putI16(out + 3, clampI16(reportedIpv_mA(m) * 10.0f));  // 0.1 mA
  putU16(out + 5, clampU16(m.vbat_mV));
  putI16(out + 7, clampI16(m.ibat_mA * 10.0f));
  putU16(out + 9, clampU16(m.vload_mV));
  putI16(out + 11, clampI16(m.iload_mA * 10.0f));
  putI16(out + 13, clampI16(m.iref1_mA * 100.0f));       // 10 µA
  putI16(out + 15, clampI16(m.iref2_mA * 100.0f));
  out[17] = inaOk;
  out[18] = 0;
  out[19] = PROTO_VERSION;
}

static void packTelemB(uint8_t out[PAYLOAD_LEN], const Measurements &m) {
  memset(out, 0, PAYLOAD_LEN);
  out[0] = seq;
  putI16(out + 1, m.ntcValid ? clampI16(m.ntc_C * 10.0f) : NTC_INVALID);
  out[3] = (ctl.loadOn ? 0x01 : 0) | (ctl.pvOn ? 0x02 : 0) | (ctl.chgInh ? 0x04 : 0) |
           (ctl.rangeLo ? 0x08 : 0) | (ctl.syncEnabled ? 0x10 : 0);
  out[4] = (m.charging ? 0x01 : 0) | (m.done ? 0x02 : 0);
  out[5] = (ctl.pvMode == MODE_AUTO ? 0x01 : 0) | (ctl.chgMode == MODE_AUTO ? 0x02 : 0) |
           (ctl.rangeMode == MODE_AUTO ? 0x04 : 0) | (ctl.autoload ? 0x08 : 0) |
           (ctl.loadManualOn ? 0x10 : 0);
  out[6] = (ctl.battLockout ? 0x01 : 0) | (ctl.tempInhibit ? 0x02 : 0) |
           (ctl.nightPvOff ? 0x04 : 0) | (ctl.ntcFault ? 0x08 : 0);
  putU32(out + 7, uptimeSeconds());
  out[11] = resetReason;
  out[12] = FW_VERSION;
}

// ═════════════════════════ Commands ═════════════════════════

// Normalise: trim leading/trailing whitespace, collapse internal whitespace runs to one space, convert to upper case
static void normalizeCommand(const char *in, size_t len, char *out, size_t outSize) {
  size_t n = 0;
  bool pendingSpace = false;
  for (size_t i = 0; i < len && in[i] != '\0'; i++) {
    char c = in[i];
    if (c == ' ' || c == '\t' || c == '\r' || c == '\n') {
      pendingSpace = n > 0;
      continue;
    }
    if ((unsigned char)c < 0x20 || (unsigned char)c > 0x7E) continue;  // drop other control / non-ASCII characters
    if (pendingSpace && n + 1 < outSize) out[n++] = ' ';
    pendingSpace = false;
    if (n + 1 < outSize) out[n++] = (char)toupper((unsigned char)c);
  }
  out[n] = '\0';
}

static void printHelp() {
  Serial.println(F("Commands: LOAD ON|OFF  AUTOLOAD ON|OFF  PV ON|OFF|AUTO  CHG ON|OFF|AUTO"));
  Serial.println(F("          RANGE HIGH|LOW|AUTO  SYNC ON|OFF  REBOOT  HELP (case-insensitive)"));
}

// Handle one command; source is used for logging only ("BLE" / "Serial")
static void handleCommand(const char *raw, size_t len, const char *source) {
  char cmd[CMD_MAX + 8];
  normalizeCommand(raw, len, cmd, sizeof(cmd));
  if (cmd[0] == '\0') return;

  bool known = true;
  if (!strcmp(cmd, "LOAD ON")) {
    if (ctl.battLockout) {
      Serial.printf("[%s] LOAD ON rejected: battery undervoltage lockout active\n", source);
      return;
    }
    if (haveMeasurements && !meas.ok[INA_BAT]) {
      // without the battery voltage there is no undervoltage protection, so the load may not be switched on
      Serial.printf("[%s] LOAD ON rejected: battery voltage chip 0x41 not responding\n", source);
      return;
    }
    ctl.loadManualOn = true;
  } else if (!strcmp(cmd, "LOAD OFF")) {
    // load off means really off: also turn autoload off, otherwise with the battery ≥3.70 V it would turn back on a second later
    ctl.loadManualOn = false;
    setAutoload(false);
  } else if (!strcmp(cmd, "AUTOLOAD ON")) setAutoload(true);
  else if (!strcmp(cmd, "AUTOLOAD OFF")) setAutoload(false);
  else if (!strcmp(cmd, "PING")) { /* gateway keepalive, no action */ }
  else if (!strcmp(cmd, "PV ON")) ctl.pvMode = MODE_ON;
  else if (!strcmp(cmd, "PV OFF")) ctl.pvMode = MODE_OFF;
  else if (!strcmp(cmd, "PV AUTO")) { ctl.pvMode = MODE_AUTO; ctl.darkSeconds = 0; ctl.nightPvOff = false; }
  else if (!strcmp(cmd, "CHG ON")) ctl.chgMode = MODE_ON;
  else if (!strcmp(cmd, "CHG OFF")) ctl.chgMode = MODE_OFF;
  else if (!strcmp(cmd, "CHG AUTO")) ctl.chgMode = MODE_AUTO;
  else if (!strcmp(cmd, "RANGE HIGH")) ctl.rangeMode = MODE_ON;
  else if (!strcmp(cmd, "RANGE LOW")) ctl.rangeMode = MODE_OFF;
  else if (!strcmp(cmd, "RANGE AUTO")) { ctl.rangeMode = MODE_AUTO; ctl.lowCurrentSeconds = 0; }
  else if (!strcmp(cmd, "SYNC ON")) ctl.syncEnabled = true;
  else if (!strcmp(cmd, "SYNC OFF")) ctl.syncEnabled = false;
  else if (!strcmp(cmd, "REBOOT")) {
    rebootPending = true;
    rebootAt = millis() + 200;
  } else if (!strcmp(cmd, "HELP")) {
    printHelp();
    return;
  } else known = false;

  if (!known) {
    Serial.printf("[%s] unknown command, ignored: \"%s\"\n", source, cmd);
    return;
  }
  Serial.printf("[%s] executed: %s\n", source, cmd);
  // commands take effect immediately (and so do the safety rules), without waiting for the next second
  if (haveMeasurements) runSafetyAndControl(meas, false);
  applyOutputs();
}

static void onCommandWrite(uint16_t conn_hdl, BLECharacteristic *chr, uint8_t *data, uint16_t len) {
  (void)conn_hdl; (void)chr;
  lastWriteMs = millis();  // any write (including PING) counts as the gateway being alive
  CmdMsg msg;
  size_t n = len > CMD_MAX ? CMD_MAX : len;
  memcpy(msg.text, data, n);
  msg.text[n] = '\0';
  if (cmdQueue) xQueueSend(cmdQueue, &msg, 0);  // drop if the queue is full; never block the BLE task
}

static void pollSerial() {
  static char line[64];
  static size_t n = 0;
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (n > 0) handleCommand(line, n, "Serial");
      n = 0;
    } else if (n < sizeof(line) - 1) {
      line[n++] = c;
    }
  }
}

// ═════════════════════════ BLE initialisation ═════════════════════════

static void onConnect(uint16_t conn_hdl) {
  connHdl = conn_hdl;
  connSinceMs = lastWriteMs = lastSubMs = millis();
  Serial.println(F("BLE connected"));
}

static void onDisconnect(uint16_t conn_hdl, uint8_t reason) {
  (void)conn_hdl;
  connHdl = BLE_CONN_HANDLE_INVALID;
  Serial.printf("BLE disconnected (reason 0x%02X), advertising again\n", reason);
}

static void setupBle() {
  Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);
  Bluefruit.begin(1, 0);
  Bluefruit.setName("SolarVest-PMB");
  Bluefruit.setTxPower(4);
  Bluefruit.autoConnLed(false);  // saves power; check the serial port for status
  Bluefruit.Periph.setConnectCallback(onConnect);
  Bluefruit.Periph.setDisconnectCallback(onDisconnect);

  svService.begin();

  chrTelemA.setProperties(CHR_PROPS_READ | CHR_PROPS_NOTIFY);
  chrTelemA.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  chrTelemA.setFixedLen(PAYLOAD_LEN);
  chrTelemA.begin();

  chrTelemB.setProperties(CHR_PROPS_READ | CHR_PROPS_NOTIFY);
  chrTelemB.setPermission(SECMODE_OPEN, SECMODE_NO_ACCESS);
  chrTelemB.setFixedLen(PAYLOAD_LEN);
  chrTelemB.begin();

  chrCommand.setProperties(CHR_PROPS_WRITE | CHR_PROPS_WRITE_WO_RESP);
  chrCommand.setPermission(SECMODE_NO_ACCESS, SECMODE_OPEN);
  chrCommand.setMaxLen(CMD_MAX);
  chrCommand.setWriteCallback(onCommandWrite);
  chrCommand.begin();

  uint8_t zeros[PAYLOAD_LEN] = {0};
  chrTelemA.write(zeros, PAYLOAD_LEN);
  chrTelemB.write(zeros, PAYLOAD_LEN);

  // Advertising packet: flags(3) + 128-bit service UUID(18) = 21 bytes; the complete name (15 bytes) goes in the scan response because 31 bytes cannot hold both
  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addTxPower();
  Bluefruit.Advertising.addService(svService);
  Bluefruit.ScanResponse.addName();
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(160, 800);  // fast 100 ms, then 500 ms (units of 0.625 ms)
  Bluefruit.Advertising.setFastTimeout(30);
  Bluefruit.Advertising.start(0);               // advertise forever
}

// ═════════════════════════ Serial status line ═════════════════════════

static void printStatusLine(const Measurements &m) {
  char ntc[12];
  if (m.ntcValid) snprintf(ntc, sizeof(ntc), "%.1fC", m.ntc_C);
  else snprintf(ntc, sizeof(ntc), "invalid");
  uint8_t inaOk = 0;
  for (int i = 0; i < INA_COUNT; i++) if (m.ok[i]) inaOk |= (1u << i);
  // The line can exceed the 256-byte buffer of the core's Serial.printf (the core writes past its end), so format it ourselves
  char line[384];
  int len = snprintf(line, sizeof(line),
      "#%03u panel %.3fV %.1fmA%s | batt %.3fV %+.1fmA | load %.3fV %.1fmA | ref %.2f/%.2fmA | NTC %s | "
      "out L%d P%d I%d R%d S%d | chg%d done%d | mode pv%s chg%s rng%s al%d | safety%s%s%s%s | ina 0x%02X | %s | %lus\n",
      seq, m.vpv_mV / 1000.0f, reportedIpv_mA(m), m.rangeLoAtRead ? "(lo)" : "",
      m.vbat_mV / 1000.0f, m.ibat_mA, m.vload_mV / 1000.0f, m.iload_mA, m.iref1_mA, m.iref2_mA, ntc,
      ctl.loadOn, ctl.pvOn, ctl.chgInh, ctl.rangeLo, ctl.syncEnabled, m.charging, m.done,
      ctl.pvMode == MODE_AUTO ? "A" : (ctl.pvMode == MODE_ON ? "1" : "0"),
      ctl.chgMode == MODE_AUTO ? "A" : (ctl.chgMode == MODE_ON ? "1" : "0"),
      ctl.rangeMode == MODE_AUTO ? "A" : (ctl.rangeMode == MODE_ON ? "H" : "L"), ctl.autoload,
      ctl.battLockout ? " UV-lockout" : "", ctl.tempInhibit ? " temp-inhibit" : "",
      ctl.nightPvOff ? " night-PV-off" : "", ctl.ntcFault ? " NTC-fault" : "",
      inaOk, Bluefruit.connected() ? "BLE-conn" : "BLE-adv", (unsigned long)uptimeSeconds());
  if (len < 0) return;
  if ((size_t)len >= sizeof(line)) {  // truncated: make sure it still ends with a newline
    len = sizeof(line) - 1;
    line[len - 1] = '\n';
  }
  Serial.write((const uint8_t *)line, (size_t)len);
}

// ═════════════════════════ setup / loop ═════════════════════════

void setup() {
  // Write the levels before enabling the outputs to avoid power-up glitches: load off, panel on, charging allowed, high range, sync low
  digitalWrite(PIN_LOAD_EN, LOW);
  digitalWrite(PIN_PV_EN, HIGH);
  digitalWrite(PIN_CHG_INH, LOW);
  digitalWrite(PIN_RANGE_LO, LOW);
  digitalWrite(PIN_SYNC, LOW);
  digitalWrite(PIN_NTC_EN, LOW);
  pinMode(PIN_LOAD_EN, OUTPUT);
  pinMode(PIN_PV_EN, OUTPUT);
  pinMode(PIN_CHG_INH, OUTPUT);
  pinMode(PIN_RANGE_LO, OUTPUT);
  pinMode(PIN_SYNC, OUTPUT);
  pinMode(PIN_NTC_EN, OUTPUT);
  pinMode(PIN_CHRG_N, INPUT);  // pull-up on the board
  pinMode(PIN_DONE_N, INPUT);
  applyOutputs();

  // the core read and cleared RESETREAS at startup; take the low byte of the saved value here
  resetReason = (uint8_t)(readResetReason() & 0xFF);

  Serial.begin(115200);  // do not wait for USB: there is no host when running on solar power alone
  Wire.begin();

  loadSettings();
  cmdQueue = xQueueCreate(8, sizeof(CmdMsg));
  setupBle();

  lastMillis = millis();
  tTick = lastMillis;
  tSync = lastMillis;
  Serial.printf("SolarVest PMB firmware v%u started, reset reason 0x%02X\n", FW_VERSION, resetReason);
  printHelp();
}

void loop() {
  const uint32_t now = millis();
  uptimeMs += (uint32_t)(now - lastMillis);  // 64-bit accumulation, unaffected by millis() wrap-around
  lastMillis = now;

  // commands (BLE queue + serial)
  CmdMsg msg;
  while (cmdQueue && xQueueReceive(cmdQueue, &msg, 0) == pdTRUE) handleCommand(msg.text, strlen(msg.text), "BLE");
  pollSerial();

  if (rebootPending && (int32_t)(now - rebootAt) >= 0) {
    Serial.println(F("Rebooting..."));
    Serial.flush();
    NVIC_SystemReset();
  }

  // sync pulse: when enabled, D2 toggles every 500 ms
  if (now - tSync >= 500) {
    tSync = now;
    syncLevel = ctl.syncEnabled && !syncLevel;
    digitalWrite(PIN_SYNC, syncLevel ? HIGH : LOW);
  }

  // once-per-second cycle
  if (now - tTick >= 1000) {
    tTick += 1000;
    if (now - tTick >= 1000) tTick = now;  // if far behind (e.g. after a long block), do not catch up

    static uint8_t configCountdown = 0;
    bool recheck = configCountdown == 0;
    configCountdown = recheck ? INA_RECHECK_CONFIG_EVERY_S - 1 : configCountdown - 1;

    readAll(meas, recheck);
    haveMeasurements = true;
    runSafetyAndControl(meas, true);
    applyOutputs();

    uint8_t a[PAYLOAD_LEN], b[PAYLOAD_LEN];
    packTelemA(a, meas);
    packTelemB(b, meas);
    chrTelemA.write(a, PAYLOAD_LEN);  // update the readable value
    chrTelemB.write(b, PAYLOAD_LEN);
    if (Bluefruit.connected()) {
      bool subscribed = chrTelemA.notifyEnabled() || chrTelemB.notifyEnabled();
      if (subscribed) lastSubMs = now;
      if (chrTelemA.notifyEnabled()) chrTelemA.notify(a, PAYLOAD_LEN);
      if (chrTelemB.notifyEnabled()) chrTelemB.notify(b, PAYLOAD_LEN);
      // Stale-connection cleanup: after the gateway process exits the OS may still hold the connection, and the XIAO would stop advertising
      uint16_t h = connHdl;
      if (h != BLE_CONN_HANDLE_INVALID) {
        if (!subscribed && now - lastSubMs > CENTRAL_NO_SUB_MS) {
          Serial.println(F("BLE: telemetry not subscribed for 30 s, disconnecting"));
          Bluefruit.disconnect(h);
        } else if (now - lastWriteMs > CENTRAL_SILENT_MS) {
          Serial.println(F("BLE: no gateway PING for 180 s, disconnecting"));
          Bluefruit.disconnect(h);
        }
      }
    }
    printStatusLine(meas);
    seq++;
  }

  delay(5);  // yield the CPU; FreeRTOS enters low power when idle
}
