# SolarVest ESP32 gateway (MicroPython 1.28, classic ESP32, no PSRAM).
# BLE central to the XIAO "SolarVest-PMB" -> HTTPS POST /api/ingest every few seconds;
# commands returned by the server are written to the XIAO's COMMAND characteristic.
# Protocol: software/SPEC.md sections 2 and 4. Config: /config.json (url, token, gateway_id, wifi[],
# portal{host, username, password}). Same semantics as software/gateway-mac/gateway.py. Rules for this port:
#  - wall-clock time is kept as an integer number of milliseconds (floats are 32-bit here);
#  - all network I/O is asyncio streams, so BLE notifications keep being served;
#  - the offline buffer is one preallocated bytearray (48 B per record).
# BLE must come up before anything large is allocated: MicroPython grows its GC heap into the
# IDF heap on demand, and the BT controller/NimBLE then cannot get internal RAM ("hci inits failed").
import bluetooth as _bt
try:
    _bt.BLE().active(True)
except Exception as _e:   # (host tests stub bluetooth without BLE)
    print("early BLE init failed", _e)

import asyncio
import gc
import json
import ssl
import struct
import time

import aioble
import bluetooth
import machine
import network
import srun

SVC = bluetooth.UUID("5f1e0001-6a2b-4c3d-9e8f-50a1b2c3d4e5")
CH_A = bluetooth.UUID("5f1e0002-6a2b-4c3d-9e8f-50a1b2c3d4e5")
CH_B = bluetooth.UUID("5f1e0003-6a2b-4c3d-9e8f-50a1b2c3d4e5")
CH_C = bluetooth.UUID("5f1e0004-6a2b-4c3d-9e8f-50a1b2c3d4e5")
NAME = "SolarVest-PMB"

POST_EVERY_S = 4          # upload interval
BATCH = 8                 # samples per POST (keeps the JSON body ~5 KB)
MAX_BUF = 300             # 5 min of samples kept while offline
REC = 48                  # record = A(20) + B(20) + ts_ms int64 (8)
B_WAIT_MS = 1500          # wait this long for TELEM_B before using the last known B
NO_UPLINK_RESET_S = 900   # no successful POST for 15 min -> reboot (Wi-Fi stuck)
CMD_HOLD_MS = 20000       # hold commands this long while BLE is down (server requeues after 30 s)
CMD_SEEN_MAX = 100        # remembered command ids (FIFO)
PING_MS = 60000           # keepalive PING on COMMAND; firmware v2 drops a central silent for 180 s
PORTAL_CHECK_MS = 60000   # at most one portal status check per minute
HTTP_TIMEOUT_S = 30
STATE_FILE = "/portal_state.json"
NTC_INVALID = -32768
EPOCH = 946684800 if time.gmtime(0)[0] == 2000 else 0   # MicroPython ESP32 epoch is 2000-01-01

_A_FMT = "<BHhHhHhhhB"    # 18 bytes
_B_FMT = "<BhBBBBIBB"     # 13 bytes

cfg = json.load(open("config.json"))
_u = cfg["url"].split("://", 1)[1]
HOST = _u.split("/", 1)[0]
GW_ID = cfg.get("gateway_id", "esp32-gw")

led = machine.Pin(2, machine.Pin.OUT)
wdt = machine.WDT(timeout=120000)

st = {"ble": "scanning", "rssi": None, "dev": None, "last_ok": time.ticks_ms(), "posts": 0, "fails": 0,
      "streak": 0, "bad_len": 0, "handler_err": 0, "a_only": 0, "ping_ok": 0, "ping_err": 0}
time_ok = False
guard = None              # srun.Guard, created in run() when portal credentials are configured
portal_t = None           # ticks_ms of the last portal check
mac_tried = False         # MAC-auth binding attempted this boot


def log(*a):
    print("[gw %d]" % time.time(), *a)


def now_ms():
    """Unix time in integer milliseconds. Never a float: 32-bit floats only resolve 128 s near 1.8e9."""
    return time.time_ns() // 1000000 + EPOCH * 1000


# ---------------------------------------------------------------- offline buffer
class Ring:
    """FIFO of fixed 48-byte records in one preallocated bytearray. `first` is the absolute index of
    the oldest record, so an upload can release exactly what it sent even if overflow dropped some."""

    def __init__(self, n):
        self.n = n
        self.mem = bytearray(n * REC)
        self.mv = memoryview(self.mem)
        self.head = 0
        self.count = 0
        self.first = 0
        self.dropped = 0

    def __len__(self):
        return self.count

    def push(self, a, b, ts_ms):
        if self.count == self.n:
            self.head = (self.head + 1) % self.n
            self.count -= 1
            self.first += 1
            self.dropped += 1
        o = ((self.head + self.count) % self.n) * REC
        self.mem[o:o + 20] = a[:20]
        self.mem[o + 20:o + 40] = b[:20]
        struct.pack_into("<q", self.mem, o + 40, ts_ms)
        self.count += 1

    def get(self, i):
        o = ((self.head + i) % self.n) * REC
        return self.mv[o:o + REC]

    def release(self, upto):
        """Drop records with absolute index < upto."""
        k = upto - self.first
        if k > self.count:
            k = self.count
        if k > 0:
            self.head = (self.head + k) % self.n
            self.count -= k
            self.first += k


ring = Ring(MAX_BUF)


# ---------------------------------------------------------------- decode (matches protocol/vectors.json)
def _bits(v, names):
    return {n: bool(v >> i & 1) for i, n in enumerate(names)}


def decode(rec):
    """Decoded sample without ts (see sample_json)."""
    seq, vpv, ipv, vbat, ibat, vload, iload, r1, r2, ok = struct.unpack_from(_A_FMT, rec, 0)
    _, ntc, o, i, m, sf, up, rr, fw = struct.unpack_from(_B_FMT, rec, 20)
    return {
        "seq": seq,
        "vpv_v": round(vpv / 1000, 3), "ipv_ma": round(ipv / 10, 1),
        "vbat_v": round(vbat / 1000, 3), "ibat_ma": round(ibat / 10, 1),
        "vload_v": round(vload / 1000, 3), "iload_ma": round(iload / 10, 1),
        "iref1_ma": round(r1 / 100, 2), "iref2_ma": round(r2 / 100, 2), "ina_ok": ok,
        "ntc_c": None if ntc == NTC_INVALID else round(ntc / 10, 1),
        "outputs": _bits(o, ("load", "pv", "chg_inh", "range_lo", "sync")),
        "inputs": _bits(i, ("charging", "done")),
        "mode": _bits(m, ("pv_auto", "chg_auto", "range_auto", "autoload", "load_manual_on")),
        "safety": _bits(sf, ("batt_lockout", "temp_inhibit", "night_pv_off", "ntc_fault")),
        "uptime_s": up, "reset_reason": rr, "fw": fw,
    }


def sample_json(rec):
    """One sample as JSON text; ts is written from the integer ms as '%d.%03d' (full precision)."""
    ts = struct.unpack_from("<q", rec, 40)[0]
    return '{"ts":%d.%03d,' % (ts // 1000, ts % 1000) + json.dumps(decode(rec))[1:]


def build_body(n, sent_acks):
    parts = ['{"gateway":', json.dumps({"id": GW_ID, "kind": "esp32", "ble": st["ble"], "rssi": st["rssi"],
                                        "device": st["dev"]}), ',"samples":[']
    for i in range(n):
        if i:
            parts.append(",")
        parts.append(sample_json(ring.get(i)))
    parts.append('],"acks":')
    parts.append(json.dumps(sent_acks))
    parts.append("}")
    return "".join(parts).encode()


# ---------------------------------------------------------------- A/B merge by seq (as gateway.py)
pend_a = None             # (ticks_ms, ts_ms, a_bytes, b_known_when_a_arrived)
pend_b = {}               # seq -> (b_bytes, ticks_ms): B that arrived before its A
last_b = None


def placeholder_b(seq):
    """B used before any real TELEM_B was seen: NTC invalid, flags 0."""
    return struct.pack(_B_FMT, seq, NTC_INVALID, 0, 0, 0, 0, 0, 0, 0) + bytes(7)


def emit(a, b, ts_ms):
    if not time_ok:
        return                      # no wall clock yet: a wrong timestamp is worse than a gap
    ring.push(a, b, ts_ms)


def _expire_b():
    t = time.ticks_ms()
    for s in [s for s in pend_b if time.ticks_diff(t, pend_b[s][1]) > B_WAIT_MS]:
        del pend_b[s]


def on_a(a):
    global pend_a
    if len(a) < 20:
        st["bad_len"] += 1
        return
    flush_pending(force=True)       # a newer A arrived: the old A's B is not coming any more
    ts = now_ms()
    a = bytes(a)
    _expire_b()
    pb = pend_b.pop(a[0], None)
    if pb is not None:              # B arrived first (rare)
        emit(a, pb[0], ts)
    else:
        pend_a = (time.ticks_ms(), ts, a, last_b)


def on_b(b):
    global pend_a, last_b
    if len(b) < 20:
        st["bad_len"] += 1
        return
    b = bytes(b)
    last_b = b
    if pend_a is not None and pend_a[2][0] == b[0]:
        emit(pend_a[2], b, pend_a[1])
        pend_a = None
    else:                           # B before its A, or a late B whose A was already sent A-only
        pend_b.pop(b[0], None)
        pend_b[b[0]] = (b, time.ticks_ms())
        _expire_b()
        while len(pend_b) > 8:
            t = time.ticks_ms()
            old = max(pend_b, key=lambda s: time.ticks_diff(t, pend_b[s][1]))
            del pend_b[old]


def flush_pending(force=False):
    """An A whose B never came: send it with the B known when the A arrived (as gateway.py)."""
    global pend_a
    if pend_a is not None and (force or time.ticks_diff(time.ticks_ms(), pend_a[0]) > B_WAIT_MS):
        _, ts, a, pb = pend_a
        pend_a = None
        st["a_only"] += 1
        emit(a, pb or placeholder_b(a[0]), ts)


# ---------------------------------------------------------------- commands (as gateway.py)
acks = []                 # [{"id","ok","error"}] to report on the next POST
cmd_q = []                # [(id, cmd, ticks_ms received)] waiting to be written over BLE
cmd_seen = {}             # id -> final ack, or None while in progress
cmd_order = []            # FIFO of ids in cmd_seen


def accept_commands(cmds):
    for c in cmds:
        try:
            cid, text = int(c["id"]), str(c["cmd"])
        except Exception:
            log("bad command", c)
            continue
        if cid in cmd_seen:
            done = cmd_seen[cid]
            if done is not None and done not in acks:   # redelivered after we finished it: re-ack
                acks.append(done)
            continue
        cmd_seen[cid] = None
        cmd_order.append(cid)
        while len(cmd_order) > CMD_SEEN_MAX:
            cmd_seen.pop(cmd_order.pop(0), None)
        cmd_q.append((cid, text, time.ticks_ms()))


def finish_command(cid, ok, error):
    ack = {"id": cid, "ok": ok, "error": error}
    if cid in cmd_seen:
        cmd_seen[cid] = ack
    acks.append(ack)
    log("cmd #%d" % cid, "ok" if ok else "failed: %s" % error)


def expire_cmds():
    """BLE is down: fail commands held longer than CMD_HOLD_MS instead of running them hours later."""
    t = time.ticks_ms()
    keep = []
    for item in cmd_q:
        if time.ticks_diff(t, item[2]) > CMD_HOLD_MS:
            finish_command(item[0], False, "BLE not connected, command not delivered")
        else:
            keep.append(item)
    cmd_q[:] = keep


# ---------------------------------------------------------------- network (all non-blocking)
_ctx = None


def _ssl():
    global _ctx
    if _ctx is None:
        _ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        _ctx.verify_mode = ssl.CERT_NONE   # TODO: pin the Let's Encrypt root; traffic is still encrypted
    return _ctx


def parse_http(raw):
    if not raw:
        raise OSError("empty HTTP response")
    head, _, payload = raw.partition(b"\r\n\r\n")
    lines = head.decode().split("\r\n")
    code = int(lines[0].split()[1])
    date = None
    chunked = False
    for ln in lines[1:]:
        k, _, v = ln.partition(":")
        k = k.lower()
        if k == "date":
            date = v.strip()
        elif k == "transfer-encoding" and "chunked" in v.lower():
            chunked = True
    if chunked:  # minimal de-chunking
        out, rest = b"", payload
        while rest:
            size_s, _, rest = rest.partition(b"\r\n")
            n = int(size_s.split(b";")[0], 16)
            if n == 0:
                break
            out += rest[:n]
            rest = rest[n + 2:]
        payload = out
    return code, date, payload


async def _https(host, path, method, body, ctype, auth, ua, limit):
    r, w = await asyncio.open_connection(host, 443, ssl=_ssl())
    try:
        h = "%s %s HTTP/1.1\r\nHost: %s\r\nUser-Agent: %s\r\nConnection: close\r\n" % (method, path, host, ua)
        if auth:
            h += "Authorization: Bearer %s\r\n" % auth
        if body is not None:
            h += "Content-Type: %s\r\nContent-Length: %d\r\n" % (ctype, len(body))
        w.write((h + "\r\n").encode())
        if body is not None:
            w.write(body)
        await w.drain()
        raw = bytearray()
        while len(raw) < limit:
            c = await r.read(1024)
            if not c:
                break
            raw.extend(c)
    finally:
        try:
            w.close()
            await w.wait_closed()
        except Exception:
            pass
    return parse_http(bytes(raw))


async def https(host, path, method="GET", body=None, ctype=None, auth=None, ua="SolarVest-GW", limit=32768):
    return await asyncio.wait_for(_https(host, path, method, body, ctype, auth, ua, limit), HTTP_TIMEOUT_S)


async def portal_get(path, method="GET", body=None, ctype=None):
    """HTTP hook for srun.login (awaited between portal requests)."""
    code, _, payload = await https(cfg["portal"]["host"], path, method, None if body is None else body.encode(), ctype,
                                   ua="Mozilla/5.0 (X11; Linux) SolarVest-GW", limit=16384)
    return payload.decode()


def sta_mac():
    try:
        return ":".join("%02x" % b for b in network.WLAN(network.STA_IF).config("mac"))
    except Exception:
        return ""


async def wifi():
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if sta.isconnected():
        return True
    for n in cfg.get("wifi", []):
        log("Wi-Fi ->", n["ssid"])
        try:
            sta.connect(n["ssid"], n.get("password") or "")
        except OSError as e:
            log("Wi-Fi connect error", repr(e))
        for _ in range(30):
            if sta.isconnected():
                log("Wi-Fi OK", sta.ifconfig()[0])
                return True
            await asyncio.sleep_ms(500)
        sta.disconnect()
    return False


async def portal_step(why):
    """Check the portal and log in if needed. Rate-limited here (status checks) and by srun.Guard
    (credential attempts, persisted across resets). Runs inside uplink(), i.e. never during a POST."""
    global portal_t, mac_tried
    p = cfg.get("portal")
    if not p or not p.get("host"):
        return None
    t = time.ticks_ms()
    if portal_t is not None and 0 <= time.ticks_diff(t, portal_t) < PORTAL_CHECK_MS:
        return None
    portal_t = t
    r = None
    try:
        r = await srun.login(portal_get, p["username"], p["password"], guard=guard, bind_mac=not mac_tried,
                             sta_mac=sta_mac(), log=log)
        if r["mac"] is not None:
            mac_tried = True
        log("portal (%s): online=%s fresh=%s error=%s" % (why, r["online"], r["fresh"], r["error"]))
    except Exception as e:
        log("portal error", repr(e))
    gc.collect()
    return r


def sync_time():
    global time_ok
    try:
        import ntptime
        ntptime.host = cfg.get("ntp", "ntp.aliyun.com")
        ntptime.settime()
        time_ok = True
        log("NTP OK")
    except Exception as e:
        log("NTP fail", e)


_MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def time_from_date(h):
    """Fallback clock from the HTTP Date header (1 s resolution)."""
    global time_ok
    try:  # 'Tue, 28 Oct 2026 12:40:01 GMT'
        p = h.split()
        hh, mm, ss = (int(x) for x in p[4].split(":"))
        machine.RTC().datetime((int(p[3]), _MONTHS.index(p[2]) + 1, int(p[1]), 0, hh, mm, ss, 0))
        time_ok = True
        log("clock from Date header")
    except Exception as e:
        log("Date parse fail", e)


async def uplink():
    if await wifi():
        await portal_step("boot")
        sync_time()
    while True:
        await asyncio.sleep(POST_EVERY_S)
        flush_pending()
        if st["ble"] != "connected":
            expire_cmds()
        if not network.WLAN(network.STA_IF).isconnected():
            if await wifi():
                await portal_step("wifi up")
                if not time_ok:
                    sync_time()
            continue
        while True:
            n = min(BATCH, len(ring))
            start = ring.first
            sent_acks = acks[:]
            try:
                body = build_body(n, sent_acks)
                gc.collect()
                code, date, payload = await https(HOST, "/api/ingest", "POST", body, "application/json",
                                                  auth=cfg["token"])
                body = None
                if date and not time_ok:
                    time_from_date(date)
                if code != 200:
                    raise OSError("HTTP %d %s" % (code, payload[:80]))
                ring.release(start + n)
                del acks[:len(sent_acks)]
                st["last_ok"] = time.ticks_ms()
                st["posts"] += 1
                st["streak"] = 0
                accept_commands(json.loads(payload).get("commands") or [])
                led.value(not led.value())
            except Exception as e:
                body = None
                st["fails"] += 1
                st["streak"] += 1
                log("POST fail", repr(e))
                if st["streak"] % 3 == 0:      # maybe the portal session expired
                    await portal_step("uplink failing")
                await asyncio.sleep(5)
                break
            gc.collect()
            if len(ring) <= BATCH // 2:
                break
            await asyncio.sleep_ms(50)


# ---------------------------------------------------------------- BLE
async def listen(ch, fn):
    while True:
        data = await ch.notified()
        try:
            fn(data)
        except Exception as e:              # one bad packet must not stop notifications
            st["handler_err"] += 1
            log("notify handler error", repr(e))


async def write_cmds(cc):
    while cmd_q:
        cid, cmd, _ = cmd_q.pop(0)
        p = cmd.strip().encode()
        if len(p) > 20:
            finish_command(cid, False, "command longer than 20 bytes")
            continue
        try:
            await asyncio.wait_for(cc.write(p, response=True), 5)
            finish_command(cid, True, None)
        except Exception as e:
            finish_command(cid, False, ("BLE write failed: " + repr(e))[:120])


async def ping(cc):
    """Write the PING keepalive (SPEC §2). Never raises; False means treat as a BLE error."""
    try:
        await asyncio.wait_for(cc.write(b"PING", response=True), 5)
    except Exception as e:
        st["ping_err"] += 1
        log("PING failed", repr(e))
        return False
    st["ping_ok"] += 1
    return True


async def ble():
    while True:
        st["ble"], st["rssi"], st["dev"] = "scanning", None, None
        dev = None
        try:
            async with aioble.scan(6000, interval_us=100000, window_us=30000, active=True) as sc:
                async for r in sc:
                    if r.name() == NAME or SVC in list(r.services()):
                        dev, st["rssi"] = r.device, r.rssi
                        break
        except Exception as e:
            log("scan fail", repr(e))
        if not dev:
            await asyncio.sleep(2)
            continue
        try:
            conn = await dev.connect(timeout_ms=10000)
            async with conn:
                svc = await conn.service(SVC)
                ca = await svc.characteristic(CH_A)
                cb = await svc.characteristic(CH_B)
                cc = await svc.characteristic(CH_C)
                await ca.subscribe(notify=True)
                await cb.subscribe(notify=True)
                st["ble"], st["dev"] = "connected", NAME
                log("BLE connected", st["rssi"])
                ta = asyncio.create_task(listen(ca, on_a))
                tb = asyncio.create_task(listen(cb, on_b))
                try:
                    last_ping = time.ticks_ms()     # connected + subscribed: PING every PING_MS
                    while conn.is_connected():
                        await write_cmds(cc)        # same coroutine => never two writes in flight
                        if time.ticks_diff(time.ticks_ms(), last_ping) >= PING_MS:
                            if not await ping(cc):
                                break               # like any BLE error: drop link, normal reconnect
                            last_ping = time.ticks_ms()
                        await asyncio.sleep_ms(200)
                finally:
                    ta.cancel()
                    tb.cancel()
        except Exception as e:
            log("BLE error", repr(e))
        try:
            flush_pending(force=True)
        except Exception as e:
            log("flush error", repr(e))
        pend_b.clear()
        st["ble"] = "disconnected"
        log("BLE disconnected")
        await asyncio.sleep(2)


async def supervisor():
    quiet = False
    while True:
        wdt.feed()
        if time.ticks_diff(time.ticks_ms(), st["last_ok"]) > NO_UPLINK_RESET_S * 1000:
            if guard is not None and guard.terminal:
                if not quiet:   # a reboot cannot fix rejected credentials; just keep collecting
                    log("no uplink, portal login stopped (%s); not rebooting" % guard.terminal)
                    quiet = True
            else:
                log("no uplink for 15 min -> reset")
                time.sleep(1)
                machine.reset()
        if time.time() % 60 < 5:
            log("status ble=%s buf=%d posts=%d fails=%d dropped=%d a_only=%d mem=%d" % (
                st["ble"], len(ring), st["posts"], st["fails"], ring.dropped, st["a_only"], gc.mem_free()))
        await asyncio.sleep(5)


async def run():
    global guard
    p = cfg.get("portal")
    if p and not p.get("host"):
        log("portal: no host in config.json, portal login disabled")
    if p and p.get("host"):
        srun.PORTAL = p["host"]
        guard = srun.Guard(STATE_FILE, srun.cred_hash(p["username"], p["password"]), log=log)
        if not guard.may_attempt():
            log("portal:", guard.why_not())
    # Bring BLE up before Wi-Fi starts: activating both at once fails the BT controller init
    # (esp_bt_controller_init -2) on this classic ESP32.
    for i in range(3):
        try:
            bluetooth.BLE().active(True)
            break
        except OSError as e:
            log("BLE init retry", i, repr(e))
            await asyncio.sleep(1)
    else:
        log("BLE init failed 3x -> reset")
        time.sleep(2)
        machine.reset()
    await asyncio.gather(supervisor(), ble(), uplink())


if __name__ == "__main__":
    try:
        asyncio.run(run())
    except Exception as e:
        log("fatal", repr(e))
        time.sleep(5)
        machine.reset()
