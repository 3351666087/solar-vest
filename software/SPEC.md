# SolarVest remote console: interface spec (v1, 2026-10-28)

The PMB-H board's XIAO nRF52840 only has BLE. Data reaches the internet through a **gateway**:
either `gateway-mac/` (Python + bleak on the Mac, unattended), `gateway-esp32/` (MicroPython on an ESP32), or the console page itself
(Web Bluetooth "relay mode" in Chrome/Edge on Android or Mac). All three speak the same HTTP API.

```
XIAO (firmware/) --BLE--> gateway (Mac python | ESP32 | browser relay) --HTTPS--> server/ (console.example.org) --> console (browser)
                 <--BLE-- commands <------------------------------ pending commands <--------- control buttons
```

Repository layout (paths relative to the repository root):
- `firmware/solarvest_pmb/solarvest_pmb.ino`: Arduino sketch, core `Seeeduino:nrf52` 1.1.13 (Adafruit Bluefruit based), FQBN `Seeeduino:nrf52:xiaonRF52840Sense`.
- `software/server/`: `server.py` (Python 3.12 **stdlib only**), `console.html` (single file, vanilla JS, no CDN), `Dockerfile`, `test_server.py`.
- `software/gateway-mac/`: `gateway.py` (Python 3, `bleak` + `aiohttp` or stdlib urllib in a thread), `requirements.txt`, `run.sh`.
- `software/gateway-esp32/`: MicroPython gateway for an ESP32 (`main.py`, `srun.py`, `test_host.py`, helper scripts).
- `software/protocol/vectors.json`: shared decode test vectors (hex payload, then the expected decoded JSON). Firmware packing, `gateway.py` and the console JS decoder must all agree with it.

## 1. Hardware facts (from the schematic, verified)

XIAO pins (Arduino pin number = Dn):
- D0/A0: NTC_ADC. D1: NTC_EN; drive HIGH to bias the divider R11 = 10k from NTC_EN to NTC_ADC (NTC to GND, C9 = 100 nF), and wait ≥ 10 ms before analogRead.
- D2: SYNC_OUT.
- D3: LOAD_EN, HIGH = load ON (Core B and the LIB); there is a 100k pull-down, so it is OFF by default.
- D4/D5: SDA/SCL.
- D6: CHG_INH, HIGH = charging inhibited (default LOW = charging).
- D7: RANGE_LO, HIGH = panel current low range (default LOW = high range).
- D8: CHRG_N, LOW = charging. D9: DONE_N, LOW = charge complete. Both are open-drain with pull-ups.
- D10: PV_EN, LOW = panel disconnected (night); 100k pull-up to 3V3 makes ON the default.

ADC on this core: 10-bit, 3.6 V full scale by default. Temperature: V = raw·3.6/1023, R = 10000·V/(3.3 − V), B = 3950, T0 = 25 °C.

INA226 (register 0x01 shunt, LSB 2.5 µV, signed; 0x02 bus, LSB 1.25 mV; 0xFE = 0x5449; config register 0x00 = 0x4527 → AVG 16, 1.1 ms/1.1 ms, continuous):

| addr | name | shunt Ω | meaning |
|---|---|---|---|
| 0x40 | PV high range | 0.050 | panel current, always in the path |
| 0x43 | PV low range | 0.220 | meaningful only when RANGE_LO = HIGH (≤ 372 mA) |
| 0x41 | BAT | 0.050 | + = charging into the battery |
| 0x42 | LOAD | 0.100 | current to the chest unit, bus = VLOAD |
| 0x44 | REF1 | 0.470 | reference cell short-circuit current. **The cell is wired reversed: multiply by −1** |
| 0x45 | REF2 | 0.470 | same, also reversed: multiply by −1 |

Panel current reported = 0x43 reading when RANGE_LO is HIGH, else the 0x40 reading. VPV = bus voltage of 0x40.

## 2. BLE GATT (firmware ⇄ gateways)

- Advertised name `SolarVest-PMB`; the advertisement includes the service UUID. One peripheral connection. Restart advertising on disconnect. Bandwidth `BANDWIDTH_MAX`, but every payload is ≤ 20 bytes so the default MTU of 23 works (Android Chrome may not raise the MTU).
- Service `5f1e0001-6a2b-4c3d-9e8f-50a1b2c3d4e5`.
- `5f1e0002-6a2b-4c3d-9e8f-50a1b2c3d4e5` **TELEM_A**: Read + Notify, sent every 1 s, 20 bytes, little-endian:

| off | type | field | unit |
|---|---|---|---|
| 0 | u8 | seq | increments every second, wraps |
| 1 | u16 | vpv | mV |
| 3 | i16 | ipv | 0.1 mA |
| 5 | u16 | vbat | mV |
| 7 | i16 | ibat | 0.1 mA (+ = charging) |
| 9 | u16 | vload | mV |
| 11 | i16 | iload | 0.1 mA |
| 13 | i16 | iref1 | 10 µA (already sign-corrected) |
| 15 | i16 | iref2 | 10 µA |
| 17 | u8 | ina_ok | bit i set ⇒ chip i in the order [0x40, 0x43, 0x41, 0x42, 0x44, 0x45] answered this cycle |
| 18 | u8 | pad | 0 |
| 19 | u8 | proto | 1 |

When a chip is missing, its fields are 0 and its `ina_ok` bit is clear.

- `5f1e0003-…` **TELEM_B**: Read + Notify, sent right after TELEM_A with the same seq, 20 bytes:

| off | type | field | meaning |
|---|---|---|---|
| 0 | u8 | seq | same as TELEM_A |
| 1 | i16 | ntc | 0.1 °C; −32768 = invalid (ADC < 10 or > 1013) |
| 3 | u8 | outputs | b0 load_en, b1 pv_en, b2 chg_inh, b3 range_lo, b4 sync |
| 4 | u8 | inputs | b0 charging (CHRG_N low), b1 done (DONE_N low) |
| 5 | u8 | mode | b0 pv_auto, b1 chg_auto, b2 range_auto, b3 autoload; b4 load_manual_on (the user asked for load ON) |
| 6 | u8 | safety | b0 batt_lockout, b1 temp_inhibit, b2 night_pv_off, b3 ntc_fault |
| 7 | u32 | uptime | s |
| 11 | u8 | reset_reason | low byte of NRF_POWER->RESETREAS at boot |
| 12 | u8 | fw | firmware version, 1 |
| 13..19 | u8 | pad | 0 |

- `5f1e0004-…` **COMMAND**: Write and WriteWithoutResponse, ASCII, ≤ 20 bytes, case-insensitive, trailing whitespace ignored. Unknown commands are ignored (logged on Serial).
  - `LOAD ON` / `LOAD OFF`: manual load. ON is refused while batt_lockout is set.
  - `AUTOLOAD ON` / `AUTOLOAD OFF`: when set, turn the load on automatically once vbat ≥ 3700 mV and no lockout.
  - `PV ON` / `PV OFF` / `PV AUTO`
  - `CHG ON` (allow charging) / `CHG OFF` (inhibit) / `CHG AUTO`
  - `RANGE HIGH` / `RANGE LOW` / `RANGE AUTO`
  - `SYNC ON` / `SYNC OFF` (D2 toggles every 500 ms)
  - `REBOOT` (NVIC_SystemReset after 200 ms)
  - `PING`: keepalive, no effect; gateways send it every 60 s; the firmware drops a central silent for 180 s or not subscribed for 30 s.

## 3. Firmware behaviour

Boot defaults:
- load OFF;
- autoload ON by default (fw v2); the setting is persisted in flash (`/svcfg`), so AUTOLOAD OFF / LOAD OFF survive reboots;
- PV AUTO, with the panel ON at start;
- CHG AUTO;
- RANGE AUTO, starting on the high range;
- SYNC OFF.

Nothing is persisted. It keeps working with no gateway connected and while the battery is still recovering at sunrise. Every 1 s:
1. Re-probe and re-configure any INA226 that is not OK; never block on a missing chip.
2. Read all chips and the NTC.
3. **Battery lockout** (always enforced):
   - If the load is ON and vbat < 3300 mV for 10 consecutive seconds, set the load OFF and set lockout.
   - Clear lockout when vbat ≥ 3550 mV.
   - While lockout is set the load stays OFF, whatever the commands say.
4. **Temperature** (always enforced): if the NTC is valid and T < 0 °C or T > 45 °C, CHG_INH is HIGH (temp_inhibit), even after `CHG ON`. If the NTC is invalid, set ntc_fault but do **not** inhibit by itself (an unattended system must still be able to charge).
5. CHG mode:
   - AUTO: inhibit only through rule 4.
   - ON: allow (rule 4 still wins).
   - OFF: inhibit.
6. PV mode:
   - AUTO: if REF1 and REF2 are both OK and |iref1| < 1 mA and |iref2| < 1 mA continuously for 300 s, set the PV off (night_pv_off). If either is ≥ 1 mA, or either chip is missing, turn the PV on immediately.
   - ON / OFF: forced.
7. RANGE mode:
   - AUTO: go LOW when the high-range |ipv| < 150 mA for 5 consecutive seconds. Go back HIGH immediately when the low-range |ipv| > 300 mA, or when the 0x43 chip is missing.
   - HIGH / LOW: forced.
8. Load:
   - ON when (manual ON, or (autoload and vbat ≥ 3700)) and not lockout.
   - `LOAD OFF` clears manual ON **and turns autoload off** (so the load really goes off). Turning autoload off clears an autoload-initiated ON.
9. Notify TELEM_A then TELEM_B when a central is connected and subscribed, and print one human-readable line on Serial.
10. Never call `while(!Serial)` without a timeout. Do not use the watchdog: it would keep the bootloader from flashing.

## 4. HTTP API (server)

Base URL `https://console.example.org` (placeholder; use your own deployment's domain). JSON everywhere. Times are unix seconds (float), as **received by the gateway**: this is the clock used for later software sync with the BITalino streams.

Auth:
- **Console session**: `POST /api/login {"password": "..."}` sets the cookie `sv_session`, an HMAC-signed token with a 30-day expiry (HttpOnly; Secure; SameSite=Lax; Path=/). Compare with a constant-time compare. Allow at most 10 failed logins per IP per 10 minutes, then return 429. `POST /api/logout` clears the cookie.
- **Device token**: `Authorization: Bearer <SV_DEVICE_TOKEN>`. Only `/api/ingest` accepts it; `/api/ingest` also accepts a console session (browser relay).
- Env: `SV_CONSOLE_PASSWORD`, `SV_DEVICE_TOKEN`, `SV_SESSION_SECRET`, `SV_DB=/data/solarvest.db`, `PORT=8790`.

Endpoints:
- `GET /`: console.html. It always serves the page; the page shows the login form when `/api/state` returns 401.
- `GET /healthz`: `{"ok":true}`, no auth.
- `POST /api/ingest` (device token or session). Body:
  `{"gateway":{"id":"mac-gw"|"web-relay-<rand>","kind":"python"|"web","ble":"connected"|"scanning"|"disconnected","rssi":-60|null,"device":"SolarVest-PMB"|null},`
  ` "samples":[ {decoded sample, see below} ... ], "acks":[{"id":12,"ok":true,"error":null}] }`
  - Stores the samples (ignoring duplicates on (ts, seq)), records the gateway heartbeat, and applies the acks.
  - Responds `{"ok":true,"commands":[{"id":12,"cmd":"LOAD ON"}]}`: every pending command, which is then marked `sent` (sent_to = gateway id).
  - A command that stays `sent` for more than 30 s without an ack goes back to `pending`. After 3 deliveries it becomes `failed`.
  - The server publishes the new samples, the gateway status and command changes on SSE.
- **Decoded sample** fields (names fixed, units in the names): `ts, seq, vpv_v, ipv_ma, vbat_v, ibat_ma, vload_v, iload_ma, iref1_ma, iref2_ma, ina_ok, ntc_c (null if invalid), outputs{load,pv,chg_inh,range_lo,sync}, inputs{charging,done}, mode{pv_auto,chg_auto,range_auto,autoload,load_manual_on}, safety{batt_lockout,temp_inhibit,night_pv_off,ntc_fault}, uptime_s, reset_reason, fw`. Booleans are true/false; ina_ok is an int.
- `GET /api/state` (session): `{"latest":sample|null, "gateway":{id,kind,ble,rssi,last_seen}|null, "server_time":t, "commands":[last 30 newest-first {id,ts,cmd,status,by,sent_to,ack_ts,error}]}`.
- `GET /api/history?seconds=3600&points=600` (session): samples bucketed to ≤ points; each bucket averages the numeric fields and takes the last of the flags. Returns `{"t":[...], "vpv_v":[...], "ipv_ma":[...], "vbat_v":[...], "ibat_ma":[...], "vload_v":[...], "iload_ma":[...], "iref1_ma":[...], "iref2_ma":[...], "ntc_c":[...]}`. seconds ≤ 30 days.
- `GET /api/stream` (session): SSE. Events: `sample` (a sample), `gateway` (gateway status), `command` (a command row). Send a comment ping every 15 s and the header `X-Accel-Buffering: no`.
- `POST /api/command {"cmd":"LOAD ON"}` (session): validated against the §2 whitelist and normalised to upper case; otherwise 400. Inserts a pending command with by = "console" and returns the row.
- `GET /api/export.csv?hours=24` (session): every raw sample as CSV, one column per sample field (flags flattened with prefixes).
- Server: `ThreadingHTTPServer`, sqlite3 in WAL mode, one connection per thread or behind a lock, requests ≤ 1 MB, no stack traces in responses.

## 5. Console UI (console.html)

- Single file, vanilla JS, no external requests (no CDN; the users are in China). Charts are hand-written canvas, HiDPI-aware.
- Dark "lab instrument" look with a solar-amber accent; mobile-first and also good on desktop; Chinese UI text.
- Header: device and gateway status pills (gateway online when last_seen < 10 s; BLE state; sample age), the current time, logout.
- Tiles:
  - Panel: power W = vpv·ipv, V, mA, range.
  - Battery: V, mA (charging/discharging), a rough SOC% from a 1S Li-ion OCV table (marked ≈), charging/done.
  - Load (BITalino B): V, mA, W, on/off, lockout.
  - Light: REF1 and REF2 in mA.
  - Battery temperature °C.
  - Uptime and firmware version.
- Charts with 15 min / 1 h / 6 h / 24 h selectors:
  - power flows (PV W, load W, battery W);
  - battery V;
  - REF1/REF2 mA.
  - Charts update live from SSE.
- Controls:
  - load switch;
  - autoload switch;
  - segmented PV / CHG / RANGE (AUTO, ON or HIGH, OFF or LOW);
  - sync switch;
  - reboot.
  - Every control sends `/api/command`. Show the command status (pending → sent → acked or failed) and the state confirmed by the next telemetry.
  - Ask for confirmation in the page (no confirm()) before LOAD ON, PV OFF, CHG ON and REBOOT.
  - Disable the controls when no gateway is online, with the explanation "Gateway offline: commands will be queued and delivered when a gateway comes online".
- Relay panel ("Use this device as the gateway"): Web Bluetooth.
  - `requestDevice({filters:[{name:"SolarVest-PMB"}], optionalServices:[SERVICE]})`.
  - Subscribe to A and B, merge by seq, decode exactly as the vectors specify, and POST /api/ingest every 1 s with gateway kind "web".
  - Write the returned commands to COMMAND and ack them.
  - Show the relay status, and a note that the screen must stay on (try a wake lock). Hide the panel with an explanation when `navigator.bluetooth` is missing (Safari/iOS).
- Command log (last 30).
- CSV export button (24 h).

## 6. Gateway (software/gateway-mac/gateway.py)

- Config from `~/.config/solarvest/gateway.env` (`SV_URL`, `SV_DEVICE_TOKEN`) or env vars.
- Loop forever:
  1. Scan for `SolarVest-PMB` (match by name or service UUID), connect, subscribe to A and B, merge by seq.
     - If a B with the same seq has not arrived within 1.5 s, emit the A-only fields with the B fields from the last known B.
  2. Decode with `decode(a: bytes, b: bytes, ts) -> dict`, which must satisfy software/protocol/vectors.json.
  3. Buffer the samples in memory (max 7 days) and flush every 1 s to /api/ingest.
     - On network errors keep the buffer and back off up to 30 s.
     - On disconnect send heartbeats with ble "scanning".
  4. Write the commands the server returns to COMMAND (with response). Ack ok or error in the next ingest.
- On BLE disconnect, rescan after 2 s. Log one line per minute plus errors.
- Must run unattended for days.
- `run.sh` creates a venv, installs the requirements, and runs under `caffeinate -dimsu`.
- Include `--selftest`: run the decoder against vectors.json and exit 0 or 1.

## 7. software/protocol/vectors.json

At least 3 vectors (normal daytime charging; night with chips missing and NTC invalid; negative currents and every flag set). Each vector gives `a_hex`, `b_hex`, `ts` and `expected` (the decoded sample as in §4). Round values sensibly: V to 3 decimals, mA to 1 decimal for ipv/ibat/iload, 2 decimals for iref, °C to 1 decimal.
