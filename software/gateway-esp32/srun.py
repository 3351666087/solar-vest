# Login + MAC-auth binding for an SRun (Shenlan) campus captive portal ("srun_bx1"), MicroPython and CPython.
# Ported from the portal's own static/themes/<theme>/js/Portal.js (_loginAccount, _encodeUserInfo,
# bindMacAuth, setBindMac). The portal host is not hard-coded: it comes from config.json
# ("portal": {"host": ...}), see set_portal.py. Only stdlib-level modules so it can be unit-tested on the Mac.
# HTTP is pluggable: login() awaits get(path, method, body, ctype) -> response text, so the device
# can use non-blocking asyncio streams and tests can use a fake portal.
import binascii
import hashlib
import json
import time

try:
    import asyncio
except ImportError:  # very old MicroPython
    import uasyncio as asyncio

PORTAL = None  # portal host name; the caller sets it from config.json ("portal": {"host": ...})
AC_ID = "0"
N, TYPE, ENC = "200", "1", "srun_bx1"
_STD = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
_ALPHA = b"LVoJPiCN2R8G90yg+hmFHuacZ1OWMnrsSTXkYpUq/3dlbfKwv6xztjI7DeBE45QA"
M32 = 0xFFFFFFFF


# ---------------------------------------------------------------- crypto helpers
def _md5(data):
    try:
        return hashlib.md5(data)
    except AttributeError:  # some MicroPython builds lack md5
        import md5py
        return md5py.md5(data)


def hmac_md5_hex(key, msg):
    key, msg = key.encode(), msg.encode()
    if len(key) > 64:
        key = _md5(key).digest()
    key = key + b"\x00" * (64 - len(key))
    ipad = bytes(b ^ 0x36 for b in key)
    opad = bytes(b ^ 0x5C for b in key)
    inner = _md5(ipad + msg).digest()
    return binascii.hexlify(_md5(opad + inner).digest()).decode()


def sha1_hex(s):
    return binascii.hexlify(hashlib.sha1(s.encode()).digest()).decode()


def _words(b, with_len):
    v = []
    for i in range(0, len(b), 4):
        w = 0
        for j in range(4):
            if i + j < len(b):
                w |= b[i + j] << (8 * j)
        v.append(w)
    if with_len:
        v.append(len(b))
    return v


def xencode(msg, key):
    """XXTEA variant from Portal.js encode(); msg/key are latin-1 byte strings (bytes)."""
    if not msg:
        return b""
    v = _words(msg, True)
    k = _words(key, False)
    while len(k) < 4:
        k.append(0)
    n = len(v) - 1
    z, y = v[n], v[0]
    c = 0x9E3779B9          # 0x86014019 | 0x183639A0
    q = 6 + 52 // (n + 1)
    d = 0
    while q > 0:
        q -= 1
        d = (d + c) & M32
        e = (d >> 2) & 3
        for p in range(n):
            y = v[p + 1]
            m = (z >> 5) ^ ((y << 2) & M32)
            m += ((y >> 3) ^ ((z << 4) & M32)) ^ (d ^ y)
            m += k[(p & 3) ^ e] ^ z
            v[p] = (v[p] + m) & M32
            z = v[p]
        y = v[0]
        p = n
        m = (z >> 5) ^ ((y << 2) & M32)
        m += ((y >> 3) ^ ((z << 4) & M32)) ^ (d ^ y)
        m += k[(p & 3) ^ e] ^ z
        v[n] = (v[n] + m) & M32
        z = v[n]
    out = bytearray()
    for w in v:
        out += bytes((w & 0xFF, w >> 8 & 0xFF, w >> 16 & 0xFF, w >> 24 & 0xFF))
    return bytes(out)


def srun_b64(b):
    std = binascii.b2a_base64(b).strip()
    table = {s: a for s, a in zip(_STD, _ALPHA)}
    return bytes(table.get(ch, ch) for ch in std).decode()


def _jstr(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def encode_info(username, password, ip, token):
    # JSON.stringify({username,password,ip,acid,enc_ver}) -- compact, key order preserved
    info = "{%s:%s,%s:%s,%s:%s,%s:%s,%s:%s}" % (
        _jstr("username"), _jstr(username), _jstr("password"), _jstr(password), _jstr("ip"), _jstr(ip),
        _jstr("acid"), _jstr(AC_ID), _jstr("enc_ver"), _jstr(ENC))
    return "{SRBX1}" + srun_b64(xencode(info.encode(), token.encode()))


def login_params(username, password, ip, token):
    hmd5 = hmac_md5_hex(token, password)
    info = encode_info(username, password, ip, token)
    chk = token + username + token + hmd5 + token + AC_ID + token + ip + token + N + token + TYPE + token + info
    return [
        ("callback", "jQuery"), ("action", "login"), ("username", username), ("password", "{MD5}" + hmd5),
        ("os", "Linux"), ("name", "Linux"), ("nas_ip", ""), ("double_stack", "0"),
        ("chksum", sha1_hex(chk)), ("info", info), ("ac_id", AC_ID), ("ip", ip), ("n", N), ("type", TYPE),
        ("captchaId", ""), ("captchaVal", ""), ("ap_id", ""), ("ap_ip", ""), ("mac", ""),
        ("_", str(int(time.time() * 1000))),
    ]


_SAFE = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.~"


def qs(params):
    """application/x-www-form-urlencoded with an explicit ASCII whitelist (same result on CPython and MicroPython)."""
    def enc(s):
        out = []
        for b in s.encode():
            out.append(chr(b) if b in _SAFE else "%%%02X" % b)
        return "".join(out)
    return "&".join(enc(k) + "=" + enc(v) for k, v in params)


def jsonp(text):
    """'jQuery({...})' -> dict"""
    a, b = text.find("("), text.rfind(")")
    return json.loads(text[a + 1:b]) if a >= 0 and b > a else json.loads(text)


def _ms():
    return str(int(time.time()) * 1000)   # cache buster only; integer maths (no float on the device)


# ---------------------------------------------------------------- login rate limit (survives machine.reset)
BACKOFF_MIN_S = 300           # one attempt, then wait 5 min, 10, 20, ... capped at 2 h
BACKOFF_MAX_S = 7200
_JUMP_S = 30 * 86400          # wall-clock change bigger than this = clock was (re)set, elapsed unknown
TERMINAL = ("password_error", "account_locked", "user_must_modify_password", "E2620", "E2553", "E2531",
            "E2901")   # E2901: third-party (LDAP/AD) auth failure, e.g. wrong password


def is_terminal(res):
    """Portal answers that will not fix themselves by retrying (retrying could lock the account)."""
    err = str(res.get("error") or "")
    msg = str(res.get("error_msg") or "")
    code = str(res.get("ecode") or "")
    for t in TERMINAL:
        if t == err or t == msg or t == code or msg.startswith(t):
            return True
    return "password" in (err + " " + msg).lower()


def cred_hash(username, password):
    return binascii.hexlify(_md5((username + "\x00" + password).encode()).digest()).decode()[:16]


def _ticks_ms():
    try:
        return time.ticks_ms()
    except AttributeError:  # CPython
        return int(time.monotonic() * 1000)


def _ticks_diff(a, b):
    try:
        return time.ticks_diff(a, b)
    except AttributeError:
        return a - b


def _wall():
    return int(time.time())


class Guard:
    """At most one credential login per backoff window; terminal errors stop retries until the
    credentials change. State is kept in a small JSON file so machine.reset cannot bypass it.
    In-boot timing uses ticks_ms; the wall clock is only used to carry the remaining wait across
    a reset, and any implausible clock change is treated as "no time has passed" (conservative)."""

    def __init__(self, path, cred, wall=None, ticks=None, diff=None, log=print):
        self.path, self.cred, self.log = path, cred, log
        self._wall = wall or _wall
        self._ticks = ticks or _ticks_ms
        self._diff = diff or _ticks_diff
        self.fails, self.terminal, self.wait_s = 0, None, 0
        self.t0, self.win_ms = self._ticks(), 0
        try:
            with open(path) as f:
                d = json.load(f)
        except Exception:
            d = None
        if d and d.get("cred") == cred:
            self.fails = int(d.get("fails") or 0)
            self.terminal = d.get("terminal")
            self.wait_s = int(d.get("wait") or 0)
            elapsed = self._wall() - int(d.get("saved") or 0)
            if elapsed < 0 or elapsed > _JUMP_S:
                elapsed = 0
            left = int(d.get("left") or 0) - elapsed
            self.win_ms = left * 1000 if left > 0 else 0
        elif d:
            self.log("portal: credentials changed, login state reset")
            self._save()

    def remaining_s(self):
        d = self._diff(self._ticks(), self.t0)
        if d < 0:                    # ticks wrapped (~6 days of uptime): the window is long over
            self.win_ms = 0
            return 0
        r = self.win_ms - d
        return (r + 999) // 1000 if r > 0 else 0

    def may_attempt(self):
        return self.terminal is None and self.remaining_s() == 0

    def why_not(self):
        if self.terminal:
            return "stopped after terminal error %s (change portal credentials to retry)" % self.terminal
        return "backoff, next attempt in %d s" % self.remaining_s()

    def _save(self):
        d = {"cred": self.cred, "fails": self.fails, "terminal": self.terminal, "wait": self.wait_s,
             "left": self.remaining_s(), "saved": self._wall()}
        try:
            with open(self.path, "w") as f:
                json.dump(d, f)
        except Exception as e:
            self.log("portal: cannot save state", repr(e))

    def begin(self):
        """Call right before credentials are sent. Opens the next window pessimistically, so a crash
        or reset in the middle of the attempt still counts as an attempt."""
        self.fails += 1
        w = BACKOFF_MIN_S
        for _ in range(self.fails - 1):
            w *= 2
            if w >= BACKOFF_MAX_S:
                break
        self.wait_s = min(w, BACKOFF_MAX_S)
        self.t0, self.win_ms = self._ticks(), self.wait_s * 1000
        self._save()

    def result(self, res):
        if res.get("error") == "ok":
            self.fails, self.terminal, self.wait_s, self.win_ms = 0, None, 0, 0
        elif is_terminal(res):
            self.terminal = str(res.get("ecode") or res.get("error") or res.get("error_msg"))
        else:
            return                      # window already opened by begin()
        self._save()


# ---------------------------------------------------------------- flow
async def status(get):
    return jsonp(await get("/cgi-bin/rad_user_info?callback=jQuery&_=" + _ms()))


async def bind_mac_auth(get, username, ip, mac, log=print):
    """Portal.js setBindMac(true) + bindMacAuth(). Returns (ok, detail)."""
    if not mac:
        return False, "no MAC address"
    r1 = await get("/v1/mfa/switch_mac", "POST", qs([("action", "set"), ("username", username), ("value", "1")]),
                   "application/x-www-form-urlencoded; charset=UTF-8")
    try:
        j1 = json.loads(r1)
    except Exception:
        j1 = {}
    if j1.get("code") != 0:
        return False, "switch_mac code=%r %s" % (j1.get("code"), (j1.get("message") or r1[:80]))
    await asyncio.sleep(0)
    r2 = await get("/cgi-bin/bind_mac_auth?" + qs([("callback", "jQuery"), ("ip", ip), ("enable_macauth", mac),
                                                  ("_", _ms())]))
    try:
        j2 = jsonp(r2)
    except Exception:
        j2 = {}
    if j2.get("error") != "ok":
        return False, "bind_mac_auth error=%r %s" % (j2.get("error"), j2.get("error_msg") or r2[:80])
    return True, mac


async def login(get, username, password, guard=None, bind_mac=True, sta_mac="", log=print):
    """Log in if the portal says we are offline (rate-limited by guard); after a *fresh* successful login,
    optionally turn on MAC auth. Returns a dict:
      online: bool, fresh: bool (credentials were sent and accepted), error: portal error or None,
      skipped: reason when no login was attempted, mac: None | (ok, detail)."""
    out = {"online": False, "fresh": False, "error": None, "skipped": None, "mac": None}
    st = await status(get)
    ip = st.get("client_ip") or st.get("online_ip") or ""
    if st.get("error") == "ok":
        out["online"] = True
        return out
    if guard is not None and not guard.may_attempt():
        out["skipped"] = guard.why_not()
        log("portal: offline, login skipped:", out["skipped"])
        return out
    await asyncio.sleep(0)
    if guard is not None:
        guard.begin()
    ch = jsonp(await get("/cgi-bin/get_challenge?" + qs([("callback", "jQuery"), ("username", username), ("ip", ip),
                                                         ("_", _ms())])))
    token = ch["challenge"]
    ip = ch.get("client_ip") or ip
    await asyncio.sleep(0)
    res = jsonp(await get("/cgi-bin/srun_portal?" + qs(login_params(username, password, ip, token))))
    if guard is not None:
        guard.result(res)
    err = res.get("error")
    log("portal login:", err, res.get("ecode") or "", res.get("error_msg") or res.get("suc_msg") or "")
    if err != "ok":
        out["error"] = str(res.get("ecode") or err or res.get("error_msg"))
        if guard is not None:
            log("portal:", guard.why_not())
        return out
    out["online"] = out["fresh"] = True
    if bind_mac:
        await asyncio.sleep(0)
        try:
            st = await status(get)
        except Exception:
            pass
        mac = (st.get("user_mac") or sta_mac or "").lower()
        try:
            out["mac"] = await bind_mac_auth(get, username, ip, mac, log)
        except Exception as e:
            out["mac"] = (False, repr(e))
        log("mac-auth OK" if out["mac"][0] else "mac-auth FAILED", out["mac"][1])
    return out
