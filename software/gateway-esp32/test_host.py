# Host (CPython) tests for the ESP32 gateway logic: python3 software/gateway-esp32/test_host.py
# Stubs machine/network/bluetooth/aioble/ntptime and a fake ticks clock; no network, no hardware.
import asyncio
import json
import os
import sys
import tempfile
import time
import types

HERE = os.path.dirname(os.path.abspath(__file__))
VECTORS = os.path.join(HERE, "..", "protocol", "vectors.json")
sys.path.insert(0, HERE)

# ---------------------------------------------------------------- fake clocks
CLK = {"ms": 1000, "wall": 1793210400, "ns": 1793210400 * 10**9}
time.ticks_ms = lambda: CLK["ms"]
time.ticks_diff = lambda a, b: a - b
_real_time = time.time


def advance(s):
    CLK["ms"] += int(s * 1000)
    CLK["wall"] += int(s)


# ---------------------------------------------------------------- module stubs
def _mod(name, **kw):
    m = types.ModuleType(name)
    m.__dict__.update(kw)
    sys.modules[name] = m
    return m


class _Pin:
    OUT = 1

    def __init__(self, *a):
        self.v = 0

    def value(self, v=None):
        if v is None:
            return self.v
        self.v = int(bool(v))


class _WLAN:
    def __init__(self, *a):
        pass

    def config(self, k):
        return b"\x48\xe7\x29\x98\x0c\xf0"

    def isconnected(self):
        return False

    def active(self, *a):
        return True


_mod("machine", Pin=_Pin, WDT=lambda timeout=0: types.SimpleNamespace(feed=lambda: None),
     RTC=lambda: types.SimpleNamespace(datetime=lambda t: None), reset=lambda: None)
_mod("network", WLAN=_WLAN, STA_IF=0)
_mod("bluetooth", UUID=lambda s: s)
_mod("aioble", scan=None)
_mod("ntptime", settime=lambda: None, host="")

TMP = tempfile.mkdtemp()
with open(os.path.join(TMP, "config.json"), "w") as f:
    json.dump({"url": "https://sv.example.org/x", "token": "t", "gateway_id": "esp32-test", "wifi": []}, f)
os.chdir(TMP)

import srun   # noqa: E402
import main   # noqa: E402

PASSED = []


def ok(name):
    PASSED.append(name)
    print("ok  ", name)


# ---------------------------------------------------------------- 1. login_params + qs
def test_login_params_qs():
    import hashlib
    time.time = lambda: 1793210400
    try:
        p1 = srun.login_params("user0001", "p@ss w0rd!", "10.7.8.9", "a" * 64)
        p2 = srun.login_params("user0001", "p@ss w0rd!", "10.7.8.9", "a" * 64)
    finally:
        time.time = _real_time
    assert p1 == p2
    q = srun.qs(p1)
    # golden value computed with the reference srun.py (crypto verified against Portal.js; same algorithm, neutral test username)
    assert hashlib.sha256(q.encode()).hexdigest() == \
        "1dcace23c593c4cefeab72bd43ad004c73bb330d7bb6851e11c36b3fed4d4750", q
    assert "chksum=679f1786aab497e572e0a057e4ec7412adce40d1" in q
    # ASCII whitelist: non-ASCII letters are always percent-encoded
    assert srun.qs([("u", "é²ª Ã"), ("k", "aZ09-_.~+/=&")]) == "u=%C3%A9%C2%B2%C2%AA%20%C3%83&k=aZ09-_.~%2B%2F%3D%26"
    ok("login_params + qs determinism / golden / ASCII whitelist")


# ---------------------------------------------------------------- 2. portal backoff state machine
class FakePortal:
    def __init__(self):
        self.online = False
        self.login_res = [{"error": "password_error", "error_msg": "E2553: Password is error."}]
        self.calls = []
        self.user_mac = ""
        self.switch_code = 0
        self.bind_err = "ok"

    async def get(self, path, method="GET", body=None, ctype=None):
        self.calls.append((method, path, body))
        if path.startswith("/cgi-bin/rad_user_info"):
            d = {"error": "ok" if self.online else "not_online_error", "client_ip": "10.7.8.9"}
            if self.online and self.user_mac:
                d["user_mac"] = self.user_mac
            return "jQuery(%s)" % json.dumps(d)
        if path.startswith("/cgi-bin/get_challenge"):
            return 'jQuery({"challenge":"%s","client_ip":"10.7.8.9","error":"ok"})' % ("c" * 64)
        if path.startswith("/cgi-bin/srun_portal"):
            r = self.login_res.pop(0) if len(self.login_res) > 1 else self.login_res[0]
            if r.get("error") == "ok":
                self.online = True
            return "jQuery(%s)" % json.dumps(r)
        if path == "/v1/mfa/switch_mac":
            return json.dumps({"code": self.switch_code, "message": "x"})
        if path.startswith("/cgi-bin/bind_mac_auth"):
            return 'jQuery({"error":"%s"})' % self.bind_err
        raise AssertionError(path)

    def n_logins(self):
        return sum(1 for c in self.calls if c[1].startswith("/cgi-bin/srun_portal"))


def _guard(path, cred="h1"):
    return srun.Guard(path, cred, wall=lambda: CLK["wall"], ticks=lambda: CLK["ms"], diff=lambda a, b: a - b,
                      log=lambda *a: None)


def _login(fp, g, **kw):
    return asyncio.run(srun.login(fp.get, "user0001", "pw", guard=g, log=lambda *a: None, **kw))


def test_backoff():
    path = os.path.join(TMP, "portal_state.json")
    # terminal: password_error -> exactly one attempt, persisted across "reset", cleared by cred change
    fp = FakePortal()
    g = _guard(path)
    r = _login(fp, g)
    assert r["online"] is False and r["error"] == "password_error" and fp.n_logins() == 1
    for _ in range(5):
        advance(3 * 3600)
        r = _login(fp, g)
        assert r["skipped"] and "terminal" in r["skipped"]
    g2 = _guard(path)                       # machine.reset
    assert g2.terminal == "password_error" and not g2.may_attempt()
    assert _login(fp, g2)["skipped"] and fp.n_logins() == 1
    g3 = _guard(path, cred="h2")            # credentials changed in config
    assert g3.terminal is None and g3.may_attempt()
    for res in ({"error": "account_locked"}, {"error": "x", "error_msg": "user_must_modify_password"},
                {"error": "x", "ecode": "E2620"}, {"error": "login_error", "error_msg": "Password is error"}):
        assert srun.is_terminal(res), res
    assert not srun.is_terminal({"error": "challenge_expire_error"})

    # transient: doubling backoff 5 min -> 2 h, one attempt per window, survives reset
    os.remove(path)
    fp = FakePortal()
    fp.login_res = [{"error": "challenge_expire_error"}]
    g = _guard(path)
    _login(fp, g)
    assert fp.n_logins() == 1 and g.wait_s == 300
    advance(299)
    assert _login(fp, g)["skipped"] and fp.n_logins() == 1
    g = _guard(path)                        # reset mid-window: remaining time carried by wall clock
    assert 0 < g.remaining_s() <= 300 and _login(fp, g)["skipped"]
    advance(2)
    _login(fp, g)
    assert fp.n_logins() == 2 and g.wait_s == 600
    CLK["wall"] -= 10 * 86400               # RTC went backwards (power cycle): wait the full window
    g = _guard(path)
    assert g.remaining_s() == 600
    CLK["wall"] += 10 * 86400
    waits = []
    for _ in range(8):
        advance(g.remaining_s())
        assert g.may_attempt()
        _login(fp, g)
        waits.append(g.wait_s)
    assert waits == [1200, 2400, 4800, 7200, 7200, 7200, 7200, 7200], waits
    assert fp.n_logins() == 10

    # success resets; MAC bind uses STA MAC when user_mac empty, after a fresh login only
    fp.login_res = [{"error": "ok", "suc_msg": "login_ok"}]
    advance(g.remaining_s())
    r = _login(fp, g, bind_mac=True, sta_mac="48:E7:29:98:0C:F0")
    assert r["online"] and r["fresh"] and r["mac"] == (True, "48:e7:29:98:0c:f0"), r
    assert g.fails == 0 and g.may_attempt() and json.load(open(path))["fails"] == 0
    bind = [c for c in fp.calls if c[1].startswith("/cgi-bin/bind_mac_auth")]
    assert len(bind) == 1 and "enable_macauth=48%3Ae7%3A29%3A98%3A0c%3Af0" in bind[0][1]
    sw = [c for c in fp.calls if c[1] == "/v1/mfa/switch_mac"]
    assert sw[0][0] == "POST" and sw[0][2] == "action=set&username=user0001&value=1"
    n = len(fp.calls)
    r = _login(fp, g, bind_mac=True, sta_mac="48:e7:29:98:0c:f0")   # already online: no login, no bind
    assert r["online"] and not r["fresh"] and r["mac"] is None and len(fp.calls) == n + 1
    # failed bind responses are detected
    fp.online, fp.switch_code = False, 1
    r = _login(fp, g, bind_mac=True, sta_mac="48:e7:29:98:0c:f0")
    assert r["fresh"] and r["mac"][0] is False and "switch_mac" in r["mac"][1]
    fp.online, fp.switch_code, fp.bind_err = False, 0, "mac_auth_error"
    r = _login(fp, g, bind_mac=True, sta_mac="48:e7:29:98:0c:f0")
    assert r["mac"][0] is False and "bind_mac_auth" in r["mac"][1]
    fp.online = False
    r = _login(fp, g, bind_mac=True, sta_mac="")
    assert r["mac"] == (False, "no MAC address")
    ok("portal backoff / terminal errors / persistence / MAC-auth checks")


# ---------------------------------------------------------------- 3. sample JSON with integer ts
def test_samples():
    vecs = json.load(open(VECTORS))
    r = main.Ring(8)
    for v in vecs:
        ts_ms = int(round(v["ts"] * 1000))
        r.push(bytes.fromhex(v["a_hex"]), bytes.fromhex(v["b_hex"]), ts_ms)
    for i, v in enumerate(vecs):
        s = main.sample_json(r.get(i))
        assert json.loads(s) == v["expected"], (v["name"], s)
    assert main.sample_json(r.get(0)).startswith('{"ts":1793210400.500,'), main.sample_json(r.get(0))
    r.push(bytes.fromhex(vecs[0]["a_hex"]), bytes.fromhex(vecs[0]["b_hex"]), 1793210400005)
    s = main.sample_json(r.get(len(r) - 1))
    assert s.startswith('{"ts":1793210400.005,') and json.loads(s)["ts"] == 1793210400.005

    # now_ms is an integer from time_ns
    time_ns = time.time_ns
    time.time_ns = lambda: 1793210400 * 10**9 + 500_123_456
    try:
        assert main.now_ms() == 1793210400500 and isinstance(main.now_ms(), int)
    finally:
        time.time_ns = time_ns

    # body
    main.ring = r
    body = json.loads(main.build_body(2, [{"id": 3, "ok": True, "error": None}]))
    assert body["gateway"]["kind"] == "esp32" and len(body["samples"]) == 2 and body["acks"][0]["id"] == 3
    assert body["samples"][0]["ts"] == 1793210400.5
    main.ring = main.Ring(main.MAX_BUF)
    ok("sample JSON ('%d.%03d' ts) matches protocol/vectors.json; body builds")


def test_merge():
    vec = json.load(open(VECTORS))[0]
    a0, b0 = bytes.fromhex(vec["a_hex"]), bytes.fromhex(vec["b_hex"])

    def A(seq):
        return bytes([seq]) + a0[1:]

    def B(seq):
        return bytes([seq]) + b0[1:]

    main.time_ok = True
    main.ring = main.Ring(16)
    main.pend_a, main.last_b = None, None
    main.pend_b.clear()
    t = [1793210400000]
    main.now_ms = lambda: t[0]
    main.on_a(A(1))                         # A only, no B ever seen -> placeholder after 1.5 s
    advance(1.6)
    main.flush_pending()
    assert len(main.ring) == 1
    d = json.loads(main.sample_json(main.ring.get(0)))
    assert d["seq"] == 1 and d["ntc_c"] is None and d["ts"] == 1793210400.0
    main.on_a(A(2))
    main.on_b(B(2))                         # normal pair
    assert len(main.ring) == 2 and main.pend_a is None
    t[0] += 1000
    main.on_a(A(3))                         # B(3) lost; A(4) forces A(3) out with last B
    t[0] += 1000
    advance(1.0)
    main.on_a(A(4))
    assert len(main.ring) == 3 and json.loads(main.sample_json(main.ring.get(2)))["seq"] == 3
    main.on_b(B(4))
    main.on_b(B(5))                         # B before its A
    main.on_a(A(5))
    assert len(main.ring) == 5 and main.pend_a is None and json.loads(main.sample_json(main.ring.get(4)))["seq"] == 5
    main.on_a(b"\x01\x02")                  # short packet ignored
    assert main.st["bad_len"] == 1
    main.time_ok = False
    main.ring = main.Ring(main.MAX_BUF)
    ok("A/B merge: placeholder B, forced flush on next A, early B by seq")


# ---------------------------------------------------------------- 4. ring buffer
def test_ring():
    r = main.Ring(3)
    assert len(main.ring.mem) == main.MAX_BUF * 48
    for i in range(5):
        r.push(bytes([i]) * 20, bytes([100 + i]) * 20, 1000 + i)
    assert len(r) == 3 and r.dropped == 2 and r.first == 2
    assert [bytes(r.get(i))[0] for i in range(3)] == [2, 3, 4]
    assert [int.from_bytes(bytes(r.get(i))[40:48], "little") for i in range(3)] == [1002, 1003, 1004]
    start, n = r.first, 2                   # upload of 2 records in flight ...
    r.push(bytes([5]) * 20, bytes([105]) * 20, 1005)   # ... overflow drops record #2 meanwhile
    r.release(start + n)                    # only #3 left to release
    assert len(r) == 2 and [bytes(r.get(i))[0] for i in range(2)] == [4, 5]
    r.release(r.first + 10)
    assert len(r) == 0
    r.push(bytes(20), bytes(20), -1 + 2**40)
    assert int.from_bytes(bytes(r.get(0))[40:48], "little") == 2**40 - 1
    ok("ring buffer push / release / overflow")


# ---------------------------------------------------------------- 5. commands
def test_commands():
    main.acks.clear()
    main.cmd_q.clear()
    main.cmd_seen.clear()
    main.cmd_order.clear()
    main.accept_commands([{"id": 1, "cmd": "LOAD ON"}, {"id": "bad"}])
    assert len(main.cmd_q) == 1
    advance(10)
    main.expire_cmds()
    assert len(main.cmd_q) == 1 and not main.acks
    main.accept_commands([{"id": 1, "cmd": "LOAD ON"}])      # redelivered while in progress: ignored
    assert len(main.cmd_q) == 1 and not main.acks
    advance(11)
    main.expire_cmds()                                        # held > 20 s with BLE down -> error ack
    assert not main.cmd_q and main.acks == [{"id": 1, "ok": False, "error": "BLE not connected, command not delivered"}]
    main.acks.clear()                                         # sent to the server
    main.accept_commands([{"id": 1, "cmd": "LOAD ON"}])      # server redelivers: re-ack, do not run
    assert not main.cmd_q and main.acks[0]["id"] == 1 and main.acks[0]["ok"] is False
    main.accept_commands([{"id": 1, "cmd": "LOAD ON"}])      # not duplicated while unsent
    assert len(main.acks) == 1
    main.acks.clear()

    written = []

    class CC:
        async def write(self, p, response=False):
            written.append(p)

    main.accept_commands([{"id": 2, "cmd": "LOAD OFF "}, {"id": 3, "cmd": "X" * 21}])
    asyncio.run(main.write_cmds(CC()))
    assert written == [b"LOAD OFF"]
    assert main.acks == [{"id": 2, "ok": True, "error": None},
                         {"id": 3, "ok": False, "error": "command longer than 20 bytes"}]
    main.acks.clear()
    main.accept_commands([{"id": 2, "cmd": "LOAD OFF"}])
    assert main.acks == [{"id": 2, "ok": True, "error": None}] and not main.cmd_q
    main.acks.clear()
    for i in range(100, 260):                                 # FIFO eviction keeps the map bounded
        main.accept_commands([{"id": i, "cmd": "PING"}])
    assert len(main.cmd_seen) == main.CMD_SEEN_MAX == len(main.cmd_order)
    assert 259 in main.cmd_seen and 100 not in main.cmd_seen
    main.cmd_q.clear()
    ok("command expiry / re-ack / FIFO seen map / 20-byte limit")


def test_ping():
    written = []

    class CC:
        def __init__(self, fail):
            self.fail = fail

        async def write(self, p, response=False):
            written.append((p, response))
            if self.fail:
                raise OSError(-128)

    n_ok, n_err = main.st["ping_ok"], main.st["ping_err"]
    assert asyncio.run(main.ping(CC(False))) is True
    assert asyncio.run(main.ping(CC(True))) is False          # failure is reported, never raised
    assert written == [(b"PING", True), (b"PING", True)]
    assert main.st["ping_ok"] == n_ok + 1 and main.st["ping_err"] == n_err + 1
    assert main.PING_MS == 60000
    ok("PING keepalive write / failure does not raise")


def test_supervisor_clock():
    assert isinstance(main.st["last_ok"], int)               # ticks_ms based, not wall clock
    ok("supervisor uses ticks_ms")


if __name__ == "__main__":
    test_login_params_qs()
    test_backoff()
    test_samples()
    test_merge()
    test_ring()
    test_commands()
    test_ping()
    test_supervisor_clock()
    print("ALL %d PASSED" % len(PASSED))
