#!/usr/bin/env python3
"""SolarVest remote console server (SPEC.md section 4).

Python 3.12 standard library only. One process serves:
  * the console page (console.html) at /
  * the JSON API used by the console and by the gateways (/api/...)
  * a Server-Sent Events stream with live samples, gateway status and command changes

Storage is a single SQLite file in WAL mode, shared by all request threads through one
connection guarded by a lock (writes are tiny; this keeps things simple and correct).

Environment:
  SV_CONSOLE_PASSWORD  console login password (required)
  SV_DEVICE_TOKEN      bearer token for gateways (required)
  SV_SESSION_SECRET    HMAC key for session cookies (random per start if unset: sessions then
                       do not survive a restart)
  SV_DB                database path, default /data/solarvest.db
  PORT                 listen port, default 8790
  SV_COOKIE_SECURE     "1" (default) adds the Secure flag to the cookie; "0" for plain-http tests
  SV_TRUST_PROXY       "1" to take the client IP from CF-Connecting-IP / X-Forwarded-For
                       (only when the server is reachable exclusively through that proxy)
  SV_CMD_TIMEOUT       seconds a command may stay "sent" without an ack, default 30
"""

from __future__ import annotations

import collections
import csv
import hashlib
import hmac
import io
import json
import os
import queue
import secrets
import signal
import sqlite3
import sys
import threading
import time
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

HERE = os.path.dirname(os.path.abspath(__file__))

MAX_BODY = 1024 * 1024            # requests larger than 1 MB are rejected
SESSION_TTL = 30 * 86400          # 30 days
LOGIN_WINDOW = 600                # 10 minutes
LOGIN_MAX_FAILS = 10
SOCKET_TIMEOUT = 30.0             # seconds per socket read/write (see Handler.timeout)
MAX_DELIVERIES = 3                # a command is "failed" after this many unacked deliveries
SSE_PING = 15.0
MAX_SAMPLES_PER_INGEST = 5000
MAX_HISTORY_SECONDS = 30 * 86400
SSE_SAMPLE_FANOUT = 120           # at most this many (newest) samples per ingest go to SSE

# Command whitelist from SPEC section 2.
COMMANDS = frozenset({
    "LOAD ON", "LOAD OFF",
    "AUTOLOAD ON", "AUTOLOAD OFF",
    "PV ON", "PV OFF", "PV AUTO",
    "CHG ON", "CHG OFF", "CHG AUTO",
    "RANGE HIGH", "RANGE LOW", "RANGE AUTO",
    "SYNC ON", "SYNC OFF",
    "REBOOT",
})

NUMERIC_FIELDS = ("vpv_v", "ipv_ma", "vbat_v", "ibat_ma", "vload_v", "iload_ma",
                  "iref1_ma", "iref2_ma", "ntc_c")
FLAG_GROUPS = {
    "outputs": ("load", "pv", "chg_inh", "range_lo", "sync"),
    "inputs": ("charging", "done"),
    "mode": ("pv_auto", "chg_auto", "range_auto", "autoload", "load_manual_on"),
    "safety": ("batt_lockout", "temp_inhibit", "night_pv_off", "ntc_fault"),
}
INT_FIELDS = ("ina_ok", "uptime_s", "reset_reason", "fw")

CSV_COLUMNS = (["ts", "seq", *NUMERIC_FIELDS[:-1], "ina_ok", "ntc_c"]
               + [f"{g}_{k}" for g, keys in FLAG_GROUPS.items() for k in keys]
               + ["uptime_s", "reset_reason", "fw"])


class BadRequest(Exception):
    """Client error; the message is safe to return to the caller."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def normalize_command(raw) -> str:
    if not isinstance(raw, str):
        raise BadRequest("cmd must be a string")
    cmd = " ".join(raw.split()).upper()
    if cmd not in COMMANDS:
        raise BadRequest("unknown command")
    return cmd


# --------------------------------------------------------------------------- samples

def _num(v, name, required=False):
    if v is None and not required:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v or v in (float("inf"), float("-inf")):
        raise BadRequest(f"sample field {name} must be a number")
    return v


def normalize_sample(s) -> dict:
    """Validate one decoded sample and return it in canonical form (fixed key order)."""
    if not isinstance(s, dict):
        raise BadRequest("sample must be an object")
    out = {"ts": float(_num(s.get("ts"), "ts", True))}
    seq = _num(s.get("seq"), "seq", True)
    out["seq"] = int(seq)
    for f in NUMERIC_FIELDS[:-1]:
        v = _num(s.get(f), f)
        out[f] = None if v is None else float(v)
    v = _num(s.get("ina_ok"), "ina_ok")
    out["ina_ok"] = None if v is None else int(v)
    v = _num(s.get("ntc_c"), "ntc_c")
    out["ntc_c"] = None if v is None else float(v)
    for group, keys in FLAG_GROUPS.items():
        g = s.get(group, {})
        g = {} if g is None else g
        if not isinstance(g, dict):
            raise BadRequest(f"sample field {group} must be an object")
        out[group] = {k: bool(g.get(k, False)) for k in keys}
    for f in ("uptime_s", "reset_reason", "fw"):
        v = _num(s.get(f), f)
        out[f] = None if v is None else int(v)
    if not (1e9 < out["ts"] < 1e10):
        raise BadRequest("sample ts out of range")
    return out


def sample_csv_row(s: dict) -> list:
    row = [s["ts"], s["seq"], *(s.get(f) for f in NUMERIC_FIELDS[:-1]), s.get("ina_ok"), s.get("ntc_c")]
    for g, keys in FLAG_GROUPS.items():
        row += [int(bool(s.get(g, {}).get(k))) for k in keys]
    row += [s.get("uptime_s"), s.get("reset_reason"), s.get("fw")]
    return ["" if v is None else v for v in row]


# --------------------------------------------------------------------------- SSE broker

class Broker:
    """Fan-out of SSE events to subscriber queues. Slow subscribers are dropped."""

    def __init__(self):
        self._lock = threading.Lock()
        self._subs: set[queue.Queue] = set()

    def subscribe(self) -> queue.Queue:
        q = queue.Queue(maxsize=2000)
        with self._lock:
            self._subs.add(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self._lock:
            self._subs.discard(q)

    @staticmethod
    def _hang_up(q: queue.Queue):
        """Discard the backlog and leave only the sentinel, so the writer closes the stream
        and the browser's EventSource reconnects (then resyncs via /api/state)."""
        with q.mutex:
            q.queue.clear()
            q.queue.append(None)
            q.not_empty.notify()
            q.not_full.notify_all()

    def publish(self, event: str, data):
        payload = f"event: {event}\ndata: {json.dumps(data, separators=(',', ':'))}\n\n".encode()
        with self._lock:
            subs = list(self._subs)
        for q in subs:
            try:
                q.put_nowait(payload)
            except queue.Full:
                self.unsubscribe(q)
                self._hang_up(q)

    def close_all(self):
        with self._lock:
            subs = list(self._subs)
            self._subs.clear()
        for q in subs:
            self._hang_up(q)


# --------------------------------------------------------------------------- storage

SCHEMA = """
CREATE TABLE IF NOT EXISTS samples (
    ts REAL NOT NULL,
    seq INTEGER NOT NULL,
    vpv_v REAL, ipv_ma REAL, vbat_v REAL, ibat_ma REAL, vload_v REAL, iload_ma REAL,
    iref1_ma REAL, iref2_ma REAL, ntc_c REAL,
    data TEXT NOT NULL,
    PRIMARY KEY (ts, seq)
) WITHOUT ROWID;
CREATE TABLE IF NOT EXISTS commands (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    cmd TEXT NOT NULL,
    status TEXT NOT NULL,          -- pending | sent | acked | failed
    by TEXT NOT NULL,
    sent_to TEXT,
    sent_ts REAL,
    deliveries INTEGER NOT NULL DEFAULT 0,
    ack_ts REAL,
    error TEXT
);
CREATE INDEX IF NOT EXISTS commands_status ON commands(status);
CREATE TABLE IF NOT EXISTS gateways (
    id TEXT PRIMARY KEY,
    kind TEXT, ble TEXT, rssi INTEGER, device TEXT,
    last_seen REAL NOT NULL
);
"""

CMD_COLS = "id, ts, cmd, status, by, sent_to, ack_ts, error"


def _cmd_row(r) -> dict:
    return dict(zip(("id", "ts", "cmd", "status", "by", "sent_to", "ack_ts", "error"), r))


class Store:
    def __init__(self, path: str, cmd_timeout: float):
        if path != ":memory:":
            os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None, timeout=10)
        self.lock = threading.Lock()
        self.cmd_timeout = cmd_timeout
        with self.lock:
            self.db.execute("PRAGMA journal_mode=WAL")
            self.db.execute("PRAGMA synchronous=NORMAL")
            self.db.executescript(SCHEMA)

    # -- samples
    def insert_samples(self, samples: list[dict]) -> list[dict]:
        """Insert samples, ignoring duplicates on (ts, seq). Returns the newly stored ones."""
        stored = []
        with self.lock:
            self.db.execute("BEGIN")
            try:
                for s in samples:
                    cur = self.db.execute(
                        "INSERT OR IGNORE INTO samples (ts, seq, vpv_v, ipv_ma, vbat_v, ibat_ma, vload_v,"
                        " iload_ma, iref1_ma, iref2_ma, ntc_c, data) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (s["ts"], s["seq"], *(s[f] for f in NUMERIC_FIELDS),
                         json.dumps(s, separators=(",", ":"))))
                    if cur.rowcount:
                        stored.append(s)
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
        return stored

    def latest_sample(self):
        with self.lock:
            r = self.db.execute("SELECT data FROM samples ORDER BY ts DESC LIMIT 1").fetchone()
        return json.loads(r[0]) if r else None

    def latest_ts(self):
        with self.lock:
            r = self.db.execute("SELECT MAX(ts) FROM samples").fetchone()
        return r[0]

    def history(self, seconds: float, points: int, now: float) -> dict:
        start = now - seconds
        bucket = max(1.0, seconds / points)
        cols = ", ".join(f"AVG({f})" for f in NUMERIC_FIELDS)
        with self.lock:
            rows = self.db.execute(
                f"SELECT CAST((ts - ?) / ? AS INTEGER) AS b, MAX(ts), {cols} FROM samples"
                f" WHERE ts >= ? GROUP BY b ORDER BY b", (start, bucket, start)).fetchall()
        out = {"t": [], **{f: [] for f in NUMERIC_FIELDS}}
        digits = {"vpv_v": 3, "vbat_v": 3, "vload_v": 3, "iref1_ma": 3, "iref2_ma": 3, "ntc_c": 2}
        for r in rows:
            out["t"].append(round(r[1], 3))
            for i, f in enumerate(NUMERIC_FIELDS):
                v = r[2 + i]
                out[f].append(None if v is None else round(v, digits.get(f, 2)))
        out["bucket_s"] = bucket
        return out

    def iter_samples(self, since: float, chunk: int = 2000):
        """Yield samples with ts >= since in time order, holding the lock only per chunk."""
        last = (since, -1)
        first = True
        while True:
            with self.lock:
                if first:
                    rows = self.db.execute(
                        "SELECT ts, seq, data FROM samples WHERE ts >= ? ORDER BY ts, seq LIMIT ?",
                        (since, chunk)).fetchall()
                else:
                    rows = self.db.execute(
                        "SELECT ts, seq, data FROM samples WHERE (ts > ?) OR (ts = ? AND seq > ?)"
                        " ORDER BY ts, seq LIMIT ?", (last[0], last[0], last[1], chunk)).fetchall()
            first = False
            for r in rows:
                yield json.loads(r[2])
            if len(rows) < chunk:
                return
            last = (rows[-1][0], rows[-1][1])

    # -- gateway
    def heartbeat(self, gw: dict, now: float) -> dict:
        with self.lock:
            self.db.execute(
                "INSERT INTO gateways (id, kind, ble, rssi, device, last_seen) VALUES (?,?,?,?,?,?)"
                " ON CONFLICT(id) DO UPDATE SET kind=excluded.kind, ble=excluded.ble,"
                " rssi=excluded.rssi, device=excluded.device, last_seen=excluded.last_seen",
                (gw["id"], gw["kind"], gw["ble"], gw["rssi"], gw["device"], now))
        return {**gw, "last_seen": now}

    def gateway(self):
        """The most recently seen gateway (there is normally only one active)."""
        with self.lock:
            r = self.db.execute(
                "SELECT id, kind, ble, rssi, device, last_seen FROM gateways"
                " ORDER BY last_seen DESC LIMIT 1").fetchone()
        if not r:
            return None
        return dict(zip(("id", "kind", "ble", "rssi", "device", "last_seen"), r))

    # -- commands
    def add_command(self, cmd: str, by: str, now: float) -> dict:
        with self.lock:
            cur = self.db.execute("INSERT INTO commands (ts, cmd, status, by) VALUES (?,?,?,?)",
                                  (now, cmd, "pending", by))
            r = self.db.execute(f"SELECT {CMD_COLS} FROM commands WHERE id=?", (cur.lastrowid,)).fetchone()
        return _cmd_row(r)

    def recent_commands(self, n: int = 30) -> list[dict]:
        with self.lock:
            rows = self.db.execute(f"SELECT {CMD_COLS} FROM commands ORDER BY id DESC LIMIT ?", (n,)).fetchall()
        return [_cmd_row(r) for r in rows]

    def requeue_stale(self, now: float) -> list[dict]:
        """Sent-but-unacked commands older than the timeout go back to pending, or fail after
        MAX_DELIVERIES deliveries. Returns the changed rows."""
        changed = []
        with self.lock:
            self.db.execute("BEGIN")
            try:
                rows = self.db.execute(
                    "SELECT id, deliveries FROM commands WHERE status='sent' AND sent_ts < ?",
                    (now - self.cmd_timeout,)).fetchall()
                for cid, deliveries in rows:
                    if deliveries >= MAX_DELIVERIES:
                        self.db.execute(
                            "UPDATE commands SET status='failed', error=? WHERE id=?",
                            (f"no acknowledgement after {deliveries} deliveries", cid))
                    else:
                        self.db.execute("UPDATE commands SET status='pending' WHERE id=?", (cid,))
                    changed.append(cid)
                out = [_cmd_row(self.db.execute(f"SELECT {CMD_COLS} FROM commands WHERE id=?", (c,)).fetchone())
                       for c in changed]
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
        return out

    def apply_acks(self, acks: list[dict], now: float) -> list[dict]:
        changed = []
        with self.lock:
            for a in acks:
                status = "acked" if a["ok"] else "failed"
                # A late ack for a command that was requeued is still honoured.
                cur = self.db.execute(
                    "UPDATE commands SET status=?, ack_ts=?, error=? WHERE id=? AND status IN ('sent','pending')",
                    (status, now, a["error"], a["id"]))
                if cur.rowcount:
                    changed.append(_cmd_row(self.db.execute(
                        f"SELECT {CMD_COLS} FROM commands WHERE id=?", (a["id"],)).fetchone()))
        return changed

    def deliver_pending(self, gateway_id: str, now: float) -> tuple[list[dict], list[dict]]:
        """Mark every pending command as sent to this gateway. Returns (wire list, changed rows)."""
        with self.lock:
            self.db.execute("BEGIN")
            try:
                rows = self.db.execute("SELECT id, cmd FROM commands WHERE status='pending' ORDER BY id").fetchall()
                changed = []
                for cid, _ in rows:
                    self.db.execute(
                        "UPDATE commands SET status='sent', sent_to=?, sent_ts=?, deliveries=deliveries+1"
                        " WHERE id=?", (gateway_id, now, cid))
                    changed.append(_cmd_row(self.db.execute(
                        f"SELECT {CMD_COLS} FROM commands WHERE id=?", (cid,)).fetchone()))
                self.db.execute("COMMIT")
            except BaseException:
                self.db.execute("ROLLBACK")
                raise
        return [{"id": cid, "cmd": cmd} for cid, cmd in rows], changed

    def close(self):
        with self.lock:
            self.db.close()


# --------------------------------------------------------------------------- auth

class Auth:
    def __init__(self, password: str, device_token: str, secret: str):
        self.password_digest = hashlib.sha256(password.encode()).digest()
        self.device_digest = hashlib.sha256(device_token.encode()).digest()
        # Deriving the key from the password means changing the password invalidates sessions.
        self.key = hmac.new(secret.encode(), b"sv-session|" + self.password_digest, hashlib.sha256).digest()
        self._fails: dict[str, collections.deque] = {}
        self._fails_lock = threading.Lock()

    def check_password(self, pw: str) -> bool:
        return hmac.compare_digest(hashlib.sha256(pw.encode()).digest(), self.password_digest)

    def check_device_token(self, tok: str) -> bool:
        return hmac.compare_digest(hashlib.sha256(tok.encode()).digest(), self.device_digest)

    def make_session(self, now: float) -> str:
        body = f"{int(now) + SESSION_TTL}.{secrets.token_hex(8)}"
        sig = hmac.new(self.key, body.encode(), hashlib.sha256).hexdigest()
        return f"{body}.{sig}"

    def check_session(self, token: str | None, now: float) -> bool:
        if not token or token.count(".") != 2:
            return False
        exp, nonce, sig = token.split(".")
        good = hmac.new(self.key, f"{exp}.{nonce}".encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(sig.encode(), good.encode()):
            return False
        try:
            return int(exp) > now
        except ValueError:
            return False

    # -- login rate limit: at most LOGIN_MAX_FAILS failures per IP per LOGIN_WINDOW
    def _recent(self, ip: str, now: float) -> collections.deque:
        d = self._fails.setdefault(ip, collections.deque())
        while d and d[0][0] < now - LOGIN_WINDOW:  # entries are (timestamp, nonce)
            d.popleft()
        return d

    def reserve_attempt(self, ip: str, now: float):
        """Atomically check the limit and count this attempt as a failure up front, so parallel
        requests cannot all pass the check. Returns a token for release_attempt(), or None if blocked."""
        with self._fails_lock:
            d = self._recent(ip, now)
            if len(d) >= LOGIN_MAX_FAILS:
                return None
            tok = (now, secrets.token_bytes(4))  # unique, so release removes exactly this entry
            d.append(tok)
            if len(self._fails) > 10000:  # bound memory under a spray of addresses
                for k in [k for k, v in self._fails.items() if not v or v[-1][0] < now - LOGIN_WINDOW]:
                    del self._fails[k]
            return tok

    def release_attempt(self, ip: str, tok):
        """Un-count a reserved attempt (successful login, or a request that never tried a password)."""
        with self._fails_lock:
            d = self._fails.get(ip)
            if d is not None:
                try:
                    d.remove(tok)
                except ValueError:
                    pass


# --------------------------------------------------------------------------- app

class App:
    def __init__(self, *, password, device_token, secret, db_path, cookie_secure=True,
                 trust_proxy=False, cmd_timeout=30.0):
        self.auth = Auth(password, device_token, secret)
        self.store = Store(db_path, cmd_timeout)
        self.broker = Broker()
        self.cookie_secure = cookie_secure
        self.trust_proxy = trust_proxy
        with open(os.path.join(HERE, "console.html"), "rb") as f:
            self.console_html = f.read()
        self._stop = threading.Event()
        self._sweeper = threading.Thread(target=self._sweep_loop, name="sv-sweeper", daemon=True)
        self._sweeper.start()

    def _sweep_loop(self):
        # Requeue stale commands even when no gateway is calling in.
        while not self._stop.wait(2.0):
            try:
                self.requeue(time.time())
            except Exception:
                traceback.print_exc()

    def requeue(self, now: float):
        for row in self.store.requeue_stale(now):
            self.broker.publish("command", row)

    def shutdown(self):
        self._stop.set()
        self.broker.close_all()


def _gateway_from(body) -> dict:
    g = body.get("gateway")
    if not isinstance(g, dict):
        raise BadRequest("gateway must be an object")
    gid = g.get("id")
    if not isinstance(gid, str) or not 0 < len(gid) <= 64:
        raise BadRequest("gateway.id must be a short string")
    kind = g.get("kind")
    if kind not in ("python", "web", "esp32"):
        raise BadRequest("gateway.kind must be python, web or esp32")
    ble = g.get("ble")
    if ble not in ("connected", "scanning", "disconnected"):
        raise BadRequest("gateway.ble invalid")
    rssi = g.get("rssi")
    if rssi is not None and (isinstance(rssi, bool) or not isinstance(rssi, (int, float))):
        raise BadRequest("gateway.rssi must be a number or null")
    device = g.get("device")
    if device is not None and (not isinstance(device, str) or len(device) > 64):
        raise BadRequest("gateway.device must be a short string or null")
    return {"id": gid, "kind": kind, "ble": ble, "rssi": None if rssi is None else int(rssi), "device": device}


def _acks_from(body) -> list[dict]:
    acks = body.get("acks") or []
    if not isinstance(acks, list):
        raise BadRequest("acks must be a list")
    out = []
    for a in acks:
        if not isinstance(a, dict) or isinstance(a.get("id"), bool) or not isinstance(a.get("id"), int):
            raise BadRequest("ack id must be an integer")
        err = a.get("error")
        out.append({"id": a["id"], "ok": bool(a.get("ok")),
                    "error": None if err is None else str(err)[:200]})
    return out


class Handler(BaseHTTPRequestHandler):
    server_version = "SolarVest/1"
    sys_version = ""
    # Applied to every socket operation: bounds idle keep-alive connections, slow request
    # lines/bodies, and SSE writes to a client that stopped reading.
    timeout = SOCKET_TIMEOUT
    app: App  # set on the subclass by make_server

    # ---- plumbing
    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.client_ip(), fmt % args))

    def log_request(self, code="-", size="-"):
        # Ingest runs every second per gateway; only log it when something went wrong.
        path = self.path.split("?", 1)[0]
        if path in ("/api/ingest", "/healthz") and str(code).startswith("2"):
            return
        super().log_request(code, size)

    def client_ip(self) -> str:
        if self.app.trust_proxy:
            ip = self.headers.get("CF-Connecting-IP")
            if ip:
                return ip.strip()
            xff = self.headers.get("X-Forwarded-For")
            if xff:
                return xff.split(",")[-1].strip()
        return self.client_address[0]

    def send_json(self, status: int, obj, extra_headers=()):
        data = json.dumps(obj, separators=(",", ":"), ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in extra_headers:
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        try:
            n = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            raise BadRequest("bad Content-Length")
        if n > MAX_BODY:
            raise BadRequest("request too large", 413)
        if n <= 0:
            raise BadRequest("empty body")
        try:
            raw = self.rfile.read(n)
        except TimeoutError:
            self.close_connection = True
            raise BadRequest("request body timeout", 408)
        if len(raw) < n:
            self.close_connection = True
            raise BadRequest("incomplete body")
        try:
            body = json.loads(raw)
        except (ValueError, UnicodeDecodeError):
            raise BadRequest("invalid JSON")
        if not isinstance(body, dict):
            raise BadRequest("JSON body must be an object")
        return body

    def session_cookie(self) -> str | None:
        # Parsed by hand: SimpleCookie gives up on the whole header when a sibling service on the
        # same domain sets a cookie it considers illegal (JSON values, spaces, odd names).
        for header in self.headers.get_all("Cookie") or ():
            for part in header.split(";"):
                name, sep, value = part.partition("=")
                if sep and name.strip() == "sv_session":
                    return value.strip().strip('"')
        return None

    def session_ok(self) -> bool:
        return self.app.auth.check_session(self.session_cookie(), time.time())

    def post_allowed(self) -> bool:
        """CSRF guard for cookie-authenticated POSTs. SameSite=Lax does not stop pages on sibling
        subdomains (same-site). Requiring application/json forces a CORS preflight for any
        cross-origin fetch (which we never answer) and rules out plain HTML form posts; a browser
        Origin, when sent, must also match our own host."""
        ctype = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if ctype != "application/json":
            # Logout has no body; allow it only if the browser says it is same-origin or no Origin is sent.
            if urlsplit(self.path).path != "/api/logout":
                return False
        if self.headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
            return False
        origin = self.headers.get("Origin")
        if origin is not None:
            host = (self.headers.get("X-Forwarded-Host") if self.app.trust_proxy else None) or self.headers.get("Host") or ""
            if urlsplit(origin).netloc.lower() != host.split(",")[0].strip().lower():
                return False
        return True

    def bearer_ok(self) -> bool:
        h = self.headers.get("Authorization") or ""
        if not h.startswith("Bearer "):
            return False
        return self.app.auth.check_device_token(h[7:].strip())

    def cookie_header(self, value: str, max_age: int) -> str:
        parts = [f"sv_session={value}", f"Max-Age={max_age}", "Path=/", "HttpOnly", "SameSite=Lax"]
        if self.app.cookie_secure:
            parts.append("Secure")
        return "; ".join(parts)

    def _dispatch(self, method: str):
        url = urlsplit(self.path)
        route = ROUTES.get((method, url.path))
        if route is None:
            if any(p == url.path for _, p in ROUTES):
                self.send_json(405, {"ok": False, "error": "method not allowed"})
            else:
                self.send_json(404, {"ok": False, "error": "not found"})
            return
        fn, auth = route
        try:
            if method == "POST" and not self.post_allowed():
                self.send_json(403, {"ok": False, "error": "forbidden"})
                return
            if auth == "session" and not self.session_ok():
                self.send_json(401, {"ok": False, "error": "unauthorized"})
                return
            if auth == "ingest" and not (self.bearer_ok() or self.session_ok()):
                self.send_json(401, {"ok": False, "error": "unauthorized"})
                return
            fn(self, parse_qs(url.query))
        except BadRequest as e:
            self.send_json(e.status, {"ok": False, "error": str(e)})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            traceback.print_exc()  # details go to the log, never to the client
            try:
                self.send_json(500, {"ok": False, "error": "internal error"})
            except Exception:
                pass

    def do_GET(self):
        self._dispatch("GET")

    def do_POST(self):
        self._dispatch("POST")

    # ---- routes
    def r_index(self, q):
        body = self.app.console_html
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy",
                         "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
                         " img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none';"
                         " form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def r_healthz(self, q):
        self.send_json(200, {"ok": True})

    def r_login(self, q):
        now = time.time()
        ip = self.client_ip()
        auth = self.app.auth
        slot = auth.reserve_attempt(ip, now)  # counted as a failure unless released below
        if slot is None:
            self.send_json(429, {"ok": False, "error": "too many attempts"}, [("Retry-After", str(LOGIN_WINDOW))])
            return
        try:
            body = self.read_json()
        except BadRequest:
            auth.release_attempt(ip, slot)  # malformed request: no password was tried
            raise
        pw = body.get("password")
        if not isinstance(pw, str) or not auth.check_password(pw):
            self.send_json(401, {"ok": False, "error": "wrong password"})
            return
        auth.release_attempt(ip, slot)
        tok = auth.make_session(now)
        self.send_json(200, {"ok": True}, [("Set-Cookie", self.cookie_header(tok, SESSION_TTL))])

    def r_logout(self, q):
        self.send_json(200, {"ok": True}, [("Set-Cookie", self.cookie_header("", 0))])

    def r_ingest(self, q):
        body = self.read_json()
        now = time.time()
        gw = _gateway_from(body)
        raw = body.get("samples") or []
        if not isinstance(raw, list) or len(raw) > MAX_SAMPLES_PER_INGEST:
            raise BadRequest("samples must be a list of at most %d" % MAX_SAMPLES_PER_INGEST)
        samples = [normalize_sample(s) for s in raw]
        acks = _acks_from(body)
        app = self.app

        prev_latest = app.store.latest_ts() if samples else None
        stored = app.store.insert_samples(samples) if samples else []
        gw_row = app.store.heartbeat(gw, now)
        changed = app.store.apply_acks(acks, now)
        app.requeue(now)
        wire, delivered = app.store.deliver_pending(gw["id"], now)

        # Live view: only samples newer than what was already latest, newest last.
        live = sorted((s for s in stored if prev_latest is None or s["ts"] > prev_latest), key=lambda s: s["ts"])
        for s in live[-SSE_SAMPLE_FANOUT:]:
            app.broker.publish("sample", s)
        app.broker.publish("gateway", gw_row)
        for row in changed + delivered:
            app.broker.publish("command", row)

        self.send_json(200, {"ok": True, "stored": len(stored), "commands": wire})

    def r_state(self, q):
        now = time.time()
        st = self.app.store
        self.send_json(200, {"latest": st.latest_sample(), "gateway": st.gateway(),
                             "server_time": now, "commands": st.recent_commands(30)})

    def r_history(self, q):
        try:
            seconds = float(q.get("seconds", ["3600"])[0])
            points = int(q.get("points", ["600"])[0])
        except ValueError:
            raise BadRequest("seconds and points must be numbers")
        seconds = min(max(seconds, 60.0), MAX_HISTORY_SECONDS)
        points = min(max(points, 10), 5000)
        self.send_json(200, self.app.store.history(seconds, points, time.time()))

    def r_command(self, q):
        body = self.read_json()
        cmd = normalize_command(body.get("cmd"))
        row = self.app.store.add_command(cmd, "console", time.time())
        self.app.broker.publish("command", row)
        self.send_json(200, row)

    def r_export(self, q):
        try:
            hours = float(q.get("hours", ["24"])[0])
        except ValueError:
            raise BadRequest("hours must be a number")
        hours = min(max(hours, 0.01), 24 * 30)
        since = time.time() - hours * 3600
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        stamp = time.strftime("%Y%m%d-%H%M", time.gmtime())
        self.send_header("Content-Disposition", f'attachment; filename="solarvest-{stamp}Z.csv"')
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        w.writerow(CSV_COLUMNS)
        for i, s in enumerate(self.app.store.iter_samples(since)):
            w.writerow(sample_csv_row(s))
            if i % 1000 == 999:
                self.wfile.write(buf.getvalue().encode())
                buf.seek(0)
                buf.truncate()
        self.wfile.write(buf.getvalue().encode())

    def r_stream(self, q):
        app = self.app
        sub = app.broker.subscribe()
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache, no-transform")
            self.send_header("X-Accel-Buffering", "no")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            self.wfile.write(b"retry: 3000\n: connected\n\n")
            gw = app.store.gateway()
            if gw:
                self.wfile.write(f"event: gateway\ndata: {json.dumps(gw)}\n\n".encode())
            self.wfile.flush()
            while not app._stop.is_set():
                try:
                    msg = sub.get(timeout=SSE_PING)
                except queue.Empty:
                    msg = b": ping\n\n"
                if msg is None:
                    break
                self.wfile.write(msg)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            app.broker.unsubscribe(sub)


ROUTES = {
    ("GET", "/"): (Handler.r_index, None),
    ("GET", "/index.html"): (Handler.r_index, None),
    ("GET", "/healthz"): (Handler.r_healthz, None),
    ("POST", "/api/login"): (Handler.r_login, None),
    ("POST", "/api/logout"): (Handler.r_logout, None),
    ("POST", "/api/ingest"): (Handler.r_ingest, "ingest"),
    ("GET", "/api/state"): (Handler.r_state, "session"),
    ("GET", "/api/history"): (Handler.r_history, "session"),
    ("GET", "/api/stream"): (Handler.r_stream, "session"),
    ("POST", "/api/command"): (Handler.r_command, "session"),
    ("GET", "/api/export.csv"): (Handler.r_export, "session"),
}


class Server(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True
    request_queue_size = 64


def make_server(host: str, port: int, app: App) -> Server:
    handler = type("BoundHandler", (Handler,), {"app": app})
    return Server((host, port), handler)


def app_from_env() -> App:
    password = os.environ.get("SV_CONSOLE_PASSWORD", "")
    token = os.environ.get("SV_DEVICE_TOKEN", "")
    if not password or not token:
        sys.exit("SV_CONSOLE_PASSWORD and SV_DEVICE_TOKEN must be set")
    secret = os.environ.get("SV_SESSION_SECRET", "")
    if not secret:
        print("warning: SV_SESSION_SECRET unset; sessions will not survive a restart", file=sys.stderr)
        secret = secrets.token_hex(32)
    return App(password=password, device_token=token, secret=secret,
               db_path=os.environ.get("SV_DB", "/data/solarvest.db"),
               cookie_secure=os.environ.get("SV_COOKIE_SECURE", "1") != "0",
               trust_proxy=os.environ.get("SV_TRUST_PROXY", "0") == "1",
               cmd_timeout=float(os.environ.get("SV_CMD_TIMEOUT", "30")))


def main():
    app = app_from_env()
    port = int(os.environ.get("PORT", "8790"))
    srv = make_server("0.0.0.0", port, app)
    print(f"SolarVest server listening on :{port}", file=sys.stderr, flush=True)
    # As PID 1 in a container, SIGTERM is ignored unless handled: stop cleanly instead.
    signal.signal(signal.SIGTERM, lambda *_: threading.Thread(target=srv.shutdown, daemon=True).start())
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        app.shutdown()
        srv.server_close()


if __name__ == "__main__":
    main()
