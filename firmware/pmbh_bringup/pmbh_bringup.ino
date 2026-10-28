// PMB-H bench bring-up test program (bench use only, not the production firmware)
// Board: Seeed XIAO nRF52840 Sense; serial monitor 115200
// Commands: l load LOAD_EN   p panel PV_EN   i inhibit charging CHG_INH
//           r panel-current indoor range RANGE_LO   s sync pulse SYNC   h help
#include <Wire.h>

// XIAO pin → PMB-H net
const int NTC_EN = 1, SYNC = 2, LOAD_EN = 3, CHG_INH = 6, RANGE_LO = 7,
          CHRG_N = 8, DONE_N = 9, PV_EN = 10;

struct Ina { uint8_t addr; const char *name; float shunt; bool ok; };
Ina ina[] = {
  {0x40, "PV high ", 0.050f, false},   // panel current, high range (RS1A)
  {0x43, "PV low  ", 0.220f, false},   // panel current, indoor range (RS1B; reads only after r is turned on)
  {0x41, "BAT     ", 0.050f, false},   // + = charging, - = discharging
  {0x42, "LOAD(B) ", 0.100f, false},   // chest unit (B + LIB)
  {0x44, "REF1    ", -0.470f, false},  // reference cell short-circuit current; both are wired reversed on the real board, so negate
  {0x45, "REF2    ", -0.470f, false},
};

bool loadOn = false, pvOn = true, inhOn = false, lowRange = false, syncOn = false;
bool syncLevel = false;
uint32_t tSync = 0, tPrint = 0;

bool rd(uint8_t a, uint8_t reg, int16_t &v) {
  Wire.beginTransmission(a);
  Wire.write(reg);
  if (Wire.endTransmission() != 0) return false;
  if (Wire.requestFrom(a, (uint8_t)2) != 2) return false;
  uint8_t hi = Wire.read();
  uint8_t lo = Wire.read();
  v = (int16_t)((hi << 8) | lo);
  return true;
}

void apply() {
  digitalWrite(LOAD_EN, loadOn);
  digitalWrite(PV_EN, pvOn);
  digitalWrite(CHG_INH, inhOn);
  digitalWrite(RANGE_LO, lowRange);
}

void help() {
  Serial.println("l=load  p=panel  i=inhibit charging  r=indoor range  s=sync pulse  h=help");
}

void setup() {
  pinMode(LOAD_EN, OUTPUT); pinMode(PV_EN, OUTPUT); pinMode(CHG_INH, OUTPUT);
  pinMode(RANGE_LO, OUTPUT); pinMode(SYNC, OUTPUT); pinMode(NTC_EN, OUTPUT);
  pinMode(CHRG_N, INPUT); pinMode(DONE_N, INPUT);
  apply();                                   // load off, panel on, charging allowed, high range

  Serial.begin(115200);
  for (uint32_t t = millis(); !Serial && millis() - t < 4000; ) {}
  Wire.begin();

  Serial.println("I2C scan (expect 0x40 0x41 0x42 0x43 0x44 0x45):");
  for (uint8_t a = 1; a < 127; a++) {
    Wire.beginTransmission(a);
    if (Wire.endTransmission() == 0) { Serial.print("  0x"); Serial.println(a, HEX); }
  }
  for (auto &u : ina) {
    int16_t id;
    u.ok = rd(u.addr, 0xFE, id) && (uint16_t)id == 0x5449;   // INA226 manufacturer ID
  }
  help();
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == 'l') loadOn = !loadOn;
    else if (c == 'p') pvOn = !pvOn;
    else if (c == 'i') inhOn = !inhOn;
    else if (c == 'r') lowRange = !lowRange;
    else if (c == 's') syncOn = !syncOn;
    else if (c == 'h') help();
    else continue;
    apply();
  }

  if (millis() - tSync >= 500) {             // with s on, D2 toggles every 0.5 s
    tSync = millis();
    syncLevel = syncOn && !syncLevel;
    digitalWrite(SYNC, syncLevel);
  }

  if (millis() - tPrint < 1000) return;
  tPrint = millis();

  Serial.println("----");
  for (auto &u : ina) {
    int16_t sh, bus;
    Serial.print(u.name);
    if (!u.ok || !rd(u.addr, 0x01, sh) || !rd(u.addr, 0x02, bus)) { Serial.println(" not found"); continue; }
    Serial.print(bus * 1.25e-3f, 3); Serial.print(" V  ");
    Serial.print(sh * 2.5e-6f / u.shunt * 1000.0f, 1); Serial.println(" mA");
  }

  digitalWrite(NTC_EN, HIGH); delay(10);          // wait for C9 to charge (τ ≤ 0.8 ms)
  int raw = analogRead(A0);
  digitalWrite(NTC_EN, LOW);
  float v = raw * 3.6f / 1023.0f;            // Seeed nRF52 core default: 10-bit, 3.6 V full scale
  if (v < 0.01f) v = 0.01f;
  if (v > 3.28f) v = 3.28f;
  float r = 10000.0f * v / (3.3f - v);       // R11 = 10 kΩ pull-up to NTC_EN
  float tc = 1.0f / (1.0f / 298.15f + logf(r / 10000.0f) / 3950.0f) - 273.15f;
  Serial.print("NTC  ADC "); Serial.print(raw);
  Serial.print("  approx. "); Serial.print(tc, 1); Serial.println(" °C (rough; cross-check against a thermometer)");

  Serial.print("Charging "); Serial.print(digitalRead(CHRG_N) == LOW ? "yes" : "no");
  Serial.print("  Fully charged "); Serial.println(digitalRead(DONE_N) == LOW ? "yes" : "no");
  Serial.print("LOAD "); Serial.print(loadOn);   Serial.print("  PV ");   Serial.print(pvOn);
  Serial.print("  INH "); Serial.print(inhOn);   Serial.print("  LOW ");  Serial.print(lowRange);
  Serial.print("  SYNC "); Serial.println(syncOn);
}
