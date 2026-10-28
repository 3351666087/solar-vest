"""End-to-end tests for server.py (stdlib unittest). Run: python3 test_server.py

Each test class starts the real server on a random port with a temporary database and talks
to it over HTTP, the same way the console and the gateways do.
"""

import http.client
import json
import os
import socket
import sqlite3
import sys
import tempfile
import threading
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import server  # noqa: E402

PASSWORD = "correct horse"
TOKEN = "dev-token-123"
VECTORS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "protocol", "vectors.json")


def sample(ts, seq, **over):
    """A valid decoded sample (based on the first protocol vector)."""
    with open(VECTORS) as f:
        s = json.load(f)[0]["expected"]
    s = json.loads(json.dumps(s))
    s.update(ts=ts, seq=seq, **over)
    return s


def gw(gid="mac-gw", kind="python", ble="connected"):
    return {"id": gid, "kind": kind, "ble": ble, "rssi": -60, "device": "SolarVest-PMB"}


class ServerCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.app = server.App(password=PASSWORD, device_token=TOKEN, secret="s3cret",
                             db_path=os.path.join(cls.tmp.name, "sv.db"), cookie_secure=False,
                             cmd_timeout=30)
        cls.srv = server.make_server("127.0.0.1", 0, cls.app)
        cls.port = cls.srv.server_address[1]
        cls.thread = threading.Thread(target=cls.srv.serve_forever, daemon=True)
        cls.thread.start()
        cls.cookie = cls.login()

    @classmethod
    def tearDownClass(cls):
        cls.app.shutdown()
        cls.srv.shutdown()
        cls.srv.server_close()
        cls.app.store.close()
        cls.tmp.cleanup()

    # -- HTTP helpers
    @classmethod
    def req(cls, method, path, body=None, headers=None, raw=False):
        c = http.client.HTTPConnection("127.0.0.1", cls.port, timeout=10)
        h = dict(headers or {})
        data = None
        if body is not None:
            data = body if isinstance(body, bytes) else json.dumps(body).encode()
            h.setdefault("Content-Type", "application/json")
        c.request(method, path, body=data, headers=h)
        r = c.getresponse()
        payload = r.read()
        c.close()
        if raw:
            return r, payload
        try:
            return r, json.loads(payload) if payload else None
        except ValueError:
            return r, payload

    @classmethod
    def login(cls, password=PASSWORD, ip_headers=None):
        r, body = cls.req("POST", "/api/login", {"password": password}, headers=ip_headers)
        if r.status != 200:
            return None
        sc = r.getheader("Set-Cookie")
        return sc.split(";", 1)[0]

    def sess(self, method, path, body=None):
        return self.req(method, path, body, headers={"Cookie": self.cookie})

    def ingest(self, body, auth="token"):
        h = {"Authorization": f"Bearer {TOKEN}"} if auth == "token" else {"Cookie": self.cookie}
        return self.req("POST", "/api/ingest", body, headers=h)

    def db(self):
        return sqlite3.connect(self.app.store.db.execute("PRAGMA database_list").fetchone()[2])


class TestAuth(ServerCase):
    def test_healthz_and_index_public(self):
        r, body = self.req("GET", "/healthz")
        self.assertEqual((r.status, body), (200, {"ok": True}))
        r, page = self.req("GET", "/", raw=True)
        self.assertEqual(r.status, 200)
        self.assertIn(b'<script id="decoder">', page)
        self.assertIn("text/html", r.getheader("Content-Type"))

    def test_cookie_attributes(self):
        r, _ = self.req("POST", "/api/login", {"password": PASSWORD})
        sc = r.getheader("Set-Cookie")
        for attr in ("sv_session=", "HttpOnly", "SameSite=Lax", "Path=/", "Max-Age=2592000"):
            self.assertIn(attr, sc)

    def test_secure_flag_default(self):
        app = server.App(password="x", device_token="y", secret="z", db_path=":memory:")
        try:
            h = type("H", (server.Handler,), {"app": app})
            self.assertIn("Secure", server.Handler.cookie_header(h.__new__(h), "v", 1))
        finally:
            app.shutdown()

    def test_401s(self):
        for method, path in [("GET", "/api/state"), ("GET", "/api/history"), ("GET", "/api/stream"),
                             ("GET", "/api/export.csv"), ("POST", "/api/command"), ("POST", "/api/ingest")]:
            r, body = self.req(method, path, {"cmd": "LOAD ON"} if method == "POST" else None)
            self.assertEqual(r.status, 401, path)
            self.assertEqual(body["ok"], False)
        # wrong bearer, forged / tampered cookies
        r, _ = self.req("POST", "/api/ingest", {"gateway": gw(), "samples": []},
                        headers={"Authorization": "Bearer nope"})
        self.assertEqual(r.status, 401)
        exp, nonce, sig = self.cookie.split("=", 1)[1].split(".")
        for bad in (f"{int(exp) + 999}.{nonce}.{sig}", "garbage", f"{exp}.{nonce}.{'0' * 64}"):
            r, _ = self.req("GET", "/api/state", headers={"Cookie": f"sv_session={bad}"})
            self.assertEqual(r.status, 401, bad)
        # the device token is not a console session
        r, _ = self.req("GET", "/api/state", headers={"Authorization": f"Bearer {TOKEN}"})
        self.assertEqual(r.status, 401)

    def test_expired_session(self):
        tok = self.app.auth.make_session(time.time() - server.SESSION_TTL - 5)
        r, _ = self.req("GET", "/api/state", headers={"Cookie": f"sv_session={tok}"})
        self.assertEqual(r.status, 401)

    def test_logout_clears_cookie(self):
        r, _ = self.req("POST", "/api/logout", {})
        self.assertIn("Max-Age=0", r.getheader("Set-Cookie"))

    def test_login_rate_limit(self):
        # Rate limit is per IP; trust_proxy lets this test use its own address without
        # locking out the other tests (which come from 127.0.0.1).
        self.app.trust_proxy = True
        try:
            ip = {"CF-Connecting-IP": "203.0.113.9"}
            for i in range(10):
                r, _ = self.req("POST", "/api/login", {"password": "wrong"}, headers=ip)
                self.assertEqual(r.status, 401, i)
            r, _ = self.req("POST", "/api/login", {"password": "wrong"}, headers=ip)
            self.assertEqual(r.status, 429)
            # even the right password is refused while blocked
            r, _ = self.req("POST", "/api/login", {"password": PASSWORD}, headers=ip)
            self.assertEqual(r.status, 429)
            # other addresses are unaffected
            self.assertIsNotNone(self.login(ip_headers={"CF-Connecting-IP": "203.0.113.10"}))
            # the window expires
            dq = self.app.auth._fails["203.0.113.9"]
            for k in range(len(dq)):
                dq[k] = (dq[k][0] - server.LOGIN_WINDOW - 1, dq[k][1])
            self.assertIsNotNone(self.login(ip_headers=ip))
        finally:
            self.app.trust_proxy = False

    def test_login_rate_limit_concurrent(self):
        # Parallel wrong passwords from one address must not get more than LOGIN_MAX_FAILS tries.
        self.app.trust_proxy = True
        try:
            ip = {"CF-Connecting-IP": "203.0.113.50"}
            statuses, barrier = [], threading.Barrier(30)

            def attempt():
                barrier.wait()
                r, _ = self.req("POST", "/api/login", {"password": "wrong"}, headers=ip)
                statuses.append(r.status)
            ts = [threading.Thread(target=attempt) for _ in range(30)]
            for t in ts:
                t.start()
            for t in ts:
                t.join()
            self.assertEqual(statuses.count(401), server.LOGIN_MAX_FAILS)
            self.assertEqual(statuses.count(429), 30 - server.LOGIN_MAX_FAILS)
            # a successful login does not use up a slot; a malformed body does not either
            ip2 = {"CF-Connecting-IP": "203.0.113.51"}
            for _ in range(server.LOGIN_MAX_FAILS + 2):
                self.assertIsNotNone(self.login(ip_headers=ip2))
                r, _ = self.req("POST", "/api/login", b"{bad", headers=ip2)
                self.assertEqual(r.status, 400)
        finally:
            self.app.trust_proxy = False

    def test_cookie_header_with_foreign_cookies(self):
        # Cookies set by sibling services on the same domain must not hide sv_session.
        for junk in ("a=b c", 'j={"a":1}', "k@=1", "flag", 'q="x y"'):
            for hdr in (f"{junk}; {self.cookie}", f"{self.cookie}; {junk}"):
                r, _ = self.req("GET", "/api/state", headers={"Cookie": hdr})
                self.assertEqual(r.status, 200, hdr)
        r, _ = self.req("GET", "/api/state", headers={"Cookie": "a=b c; other=1"})
        self.assertEqual(r.status, 401)

    def test_post_csrf_guard(self):
        ck = {"Cookie": self.cookie}
        cases = [
            ({"Content-Type": "text/plain"}, 403),                          # HTML form / simple request
            ({"Content-Type": "application/x-www-form-urlencoded"}, 403),
            ({"Origin": "https://evil.example.org"}, 403),              # sibling subdomain
            ({"Sec-Fetch-Site": "same-site"}, 403),
            ({"Origin": f"http://127.0.0.1:{self.port}", "Sec-Fetch-Site": "same-origin"}, 200),
            ({}, 200),                                                       # non-browser client
        ]
        for extra, want in cases:
            r, _ = self.req("POST", "/api/command", {"cmd": "SYNC ON"}, headers={**ck, **extra})
            self.assertEqual(r.status, want, extra)
        # bearer gateways send application/json and no Origin
        r, _ = self.ingest({"gateway": gw(), "samples": []})
        self.assertEqual(r.status, 200)
        r, _ = self.req("POST", "/api/ingest", b"{}", headers={"Authorization": f"Bearer {TOKEN}",
                                                                "Content-Type": "text/plain"})
        self.assertEqual(r.status, 403)
        # the console's logout has no body
        r, _ = self.req("POST", "/api/logout", headers={"Origin": f"http://127.0.0.1:{self.port}"})
        self.assertEqual(r.status, 200)
        r, _ = self.req("POST", "/api/logout", headers={"Origin": "https://evil.example"})
        self.assertEqual(r.status, 403)

    def test_socket_timeout(self):
        h = self.srv.RequestHandlerClass
        old = h.timeout
        h.timeout = 0.5
        try:
            # idle connection that never sends a request line is closed
            s1 = socket.create_connection(("127.0.0.1", self.port), timeout=5)
            self.assertEqual(s1.recv(100), b"")
            s1.close()
            # a body that never completes gets 408 and a closed connection
            s2 = socket.create_connection(("127.0.0.1", self.port), timeout=5)
            s2.sendall(f"POST /api/command HTTP/1.1\r\nHost: x\r\nCookie: {self.cookie}\r\n"
                       f"Content-Type: application/json\r\nContent-Length: 100\r\n\r\n{{".encode())
            self.assertIn(b" 408 ", s2.makefile("rb").readline())
            s2.close()
        finally:
            h.timeout = old

    def test_bad_requests(self):
        r, body = self.req("POST", "/api/command", b"{not json", headers={"Cookie": self.cookie})
        self.assertEqual(r.status, 400)
        self.assertNotIn("Traceback", json.dumps(body))
        # Oversized body: the server answers 413 from the Content-Length without reading it.
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        sock.sendall(f"POST /api/command HTTP/1.1\r\nHost: x\r\nCookie: {self.cookie}\r\n"
                     f"Content-Type: application/json\r\nContent-Length: {server.MAX_BODY + 1}\r\n\r\n{{".encode())
        self.assertIn(b" 413 ", sock.makefile("rb").readline())
        sock.close()
        r, _ = self.req("GET", "/nope")
        self.assertEqual(r.status, 404)
        r, _ = self.req("GET", "/api/login")
        self.assertEqual(r.status, 405)
        r, _ = self.ingest({"gateway": gw(kind="bogus"), "samples": []})
        self.assertEqual(r.status, 400)
        r, _ = self.ingest({"gateway": gw(), "samples": [{"ts": "x", "seq": 1}]})
        self.assertEqual(r.status, 400)


class TestIngestAndCommands(ServerCase):
    def setUp(self):
        with self.app.store.lock:
            self.app.store.db.executescript("DELETE FROM samples; DELETE FROM commands; DELETE FROM gateways;")

    def test_ingest_dedupe_and_state(self):
        t = time.time()
        body = {"gateway": gw(), "samples": [sample(t - 2, 1), sample(t - 1, 2)], "acks": []}
        r, res = self.ingest(body)
        self.assertEqual(r.status, 200)
        self.assertEqual(res, {"ok": True, "stored": 2, "commands": []})
        r, res = self.ingest(body)  # exact resend: duplicates on (ts, seq) are ignored
        self.assertEqual(res["stored"], 0)
        # same seq at a different time is a different sample (seq wraps every 256 s)
        r, res = self.ingest({"gateway": gw(), "samples": [sample(t, 2)]})
        self.assertEqual(res["stored"], 1)
        r, st = self.sess("GET", "/api/state")
        self.assertEqual(r.status, 200)
        self.assertEqual(st["latest"], sample(t, 2))
        self.assertEqual(st["gateway"]["id"], "mac-gw")
        self.assertEqual(st["gateway"]["ble"], "connected")
        self.assertAlmostEqual(st["gateway"]["last_seen"], time.time(), delta=5)
        self.assertAlmostEqual(st["server_time"], time.time(), delta=5)
        with self.db() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM samples").fetchone()[0], 3)

    def test_ingest_with_session_web_relay(self):
        r, res = self.ingest({"gateway": gw("web-relay-ab12cd", "web"), "samples": [sample(time.time(), 5)]},
                             auth="session")
        self.assertEqual(r.status, 200)
        self.assertEqual(res["stored"], 1)
        _, st = self.sess("GET", "/api/state")
        self.assertEqual(st["gateway"]["kind"], "web")

    def test_vector_roundtrip(self):
        with open(VECTORS) as f:
            vecs = json.load(f)
        r, res = self.ingest({"gateway": gw(), "samples": [v["expected"] for v in vecs]})
        self.assertEqual(res["stored"], len(vecs))
        _, st = self.sess("GET", "/api/state")
        newest = max(vecs, key=lambda v: v["ts"])["expected"]
        self.assertEqual(st["latest"], newest)
        self.assertEqual(list(st["latest"].keys()), list(newest.keys()))

    def test_command_validation(self):
        r, row = self.sess("POST", "/api/command", {"cmd": "  load   on "})
        self.assertEqual(r.status, 200)
        self.assertEqual(row["cmd"], "LOAD ON")
        self.assertEqual(row["status"], "pending")
        self.assertEqual(row["by"], "console")
        for bad in ("LOAD MAYBE", "", "rm -rf", None, 5, "REBOOT NOW"):
            r, _ = self.sess("POST", "/api/command", {"cmd": bad})
            self.assertEqual(r.status, 400, bad)
        for good in server.COMMANDS:
            r, _ = self.sess("POST", "/api/command", {"cmd": good.lower()})
            self.assertEqual(r.status, 200, good)

    def test_command_lifecycle_ack(self):
        _, row = self.sess("POST", "/api/command", {"cmd": "LOAD ON"})
        cid = row["id"]
        _, res = self.ingest({"gateway": gw(), "samples": []})
        self.assertEqual(res["commands"], [{"id": cid, "cmd": "LOAD ON"}])
        _, res = self.ingest({"gateway": gw(), "samples": []})
        self.assertEqual(res["commands"], [])  # sent, not re-delivered while waiting for the ack
        _, st = self.sess("GET", "/api/state")
        c = st["commands"][0]
        self.assertEqual((c["status"], c["sent_to"]), ("sent", "mac-gw"))
        _, res = self.ingest({"gateway": gw(), "samples": [], "acks": [{"id": cid, "ok": True, "error": None}]})
        _, st = self.sess("GET", "/api/state")
        c = st["commands"][0]
        self.assertEqual(c["status"], "acked")
        self.assertIsNotNone(c["ack_ts"])
        self.assertEqual(set(c), {"id", "ts", "cmd", "status", "by", "sent_to", "ack_ts", "error"})

    def test_command_ack_error(self):
        _, row = self.sess("POST", "/api/command", {"cmd": "PV OFF"})
        self.ingest({"gateway": gw(), "samples": []})
        self.ingest({"gateway": gw(), "samples": [], "acks": [{"id": row["id"], "ok": False, "error": "GATT write failed"}]})
        _, st = self.sess("GET", "/api/state")
        self.assertEqual((st["commands"][0]["status"], st["commands"][0]["error"]), ("failed", "GATT write failed"))

    def _age_sent(self, cid, seconds=31):
        with self.app.store.lock:
            self.app.store.db.execute("UPDATE commands SET sent_ts = sent_ts - ? WHERE id=?", (seconds, cid))

    def test_command_requeue_then_failed(self):
        _, row = self.sess("POST", "/api/command", {"cmd": "REBOOT"})
        cid = row["id"]
        for delivery in (1, 2, 3):
            _, res = self.ingest({"gateway": gw(), "samples": []})
            self.assertEqual(res["commands"], [{"id": cid, "cmd": "REBOOT"}], delivery)
            self._age_sent(cid)
            # next ingest first requeues the stale command, then (for deliveries < 3) re-delivers it
        _, res = self.ingest({"gateway": gw(), "samples": []})
        self.assertEqual(res["commands"], [])
        _, st = self.sess("GET", "/api/state")
        self.assertEqual(st["commands"][0]["status"], "failed")
        self.assertTrue(st["commands"][0]["error"])

    def test_requeue_without_gateway(self):
        # The background sweeper requeues even when no gateway calls in.
        _, row = self.sess("POST", "/api/command", {"cmd": "SYNC ON"})
        self.ingest({"gateway": gw(), "samples": []})
        self._age_sent(row["id"])
        deadline = time.time() + 5
        while time.time() < deadline:
            _, st = self.sess("GET", "/api/state")
            if st["commands"][0]["status"] == "pending":
                break
            time.sleep(0.2)
        self.assertEqual(st["commands"][0]["status"], "pending")

    def test_late_ack_after_requeue(self):
        _, row = self.sess("POST", "/api/command", {"cmd": "CHG AUTO"})
        self.ingest({"gateway": gw(), "samples": []})
        self._age_sent(row["id"])
        self.app.requeue(time.time())
        self.ingest({"gateway": gw("other"), "samples": [], "acks": [{"id": row["id"], "ok": True}]})
        _, st = self.sess("GET", "/api/state")
        self.assertEqual(st["commands"][0]["status"], "acked")

    def test_commands_limited_to_30_newest_first(self):
        for _ in range(35):
            self.sess("POST", "/api/command", {"cmd": "SYNC OFF"})
        _, st = self.sess("GET", "/api/state")
        ids = [c["id"] for c in st["commands"]]
        self.assertEqual(len(ids), 30)
        self.assertEqual(ids, sorted(ids, reverse=True))

    def test_history_bucketing(self):
        now = time.time()
        samples = [sample(now - 600 + i, i % 256, vbat_v=3.0 + i / 1000, ntc_c=None if i % 2 else 20.0)
                   for i in range(600)]
        samples.append(sample(now - 7200, 1))  # outside the window
        self.ingest({"gateway": gw(), "samples": samples})
        _, h = self.sess("GET", "/api/history?seconds=600&points=60")
        keys = ["t", "vpv_v", "ipv_ma", "vbat_v", "ibat_ma", "vload_v", "iload_ma", "iref1_ma", "iref2_ma", "ntc_c"]
        for k in keys:
            self.assertIn(k, h)
            self.assertEqual(len(h[k]), len(h["t"]), k)
        self.assertLessEqual(len(h["t"]), 61)
        self.assertGreaterEqual(len(h["t"]), 55)
        self.assertEqual(h["t"], sorted(h["t"]))
        self.assertTrue(all(t >= now - 601 for t in h["t"]))
        # each bucket of 10 consecutive samples averages vbat; ntc ignores the nulls
        self.assertTrue(all(abs(v - 20.0) < 1e-6 for v in h["ntc_c"] if v is not None))
        mid = h["vbat_v"][len(h["vbat_v"]) // 2]
        self.assertTrue(3.2 < mid < 3.4, mid)
        # clamps and bad params
        r, h = self.sess("GET", "/api/history?seconds=99999999&points=5")
        self.assertEqual(r.status, 200)
        r, _ = self.sess("GET", "/api/history?seconds=abc")
        self.assertEqual(r.status, 400)

    def test_export_csv(self):
        now = time.time()
        with open(VECTORS) as f:
            v = json.load(f)
        s_night = dict(v[1]["expected"], ts=now - 10)
        s_day = dict(v[0]["expected"], ts=now - 5)
        old = dict(v[0]["expected"], ts=now - 3 * 86400)
        self.ingest({"gateway": gw(), "samples": [s_day, s_night, old]})
        r, body = self.req("GET", "/api/export.csv?hours=24", headers={"Cookie": self.cookie}, raw=True)
        self.assertEqual(r.status, 200)
        self.assertIn("text/csv", r.getheader("Content-Type"))
        self.assertIn("attachment", r.getheader("Content-Disposition"))
        lines = body.decode().strip().split("\n")
        header = lines[0].split(",")
        self.assertEqual(header, server.CSV_COLUMNS)
        for col in ("ts", "seq", "vbat_v", "ntc_c", "outputs_load", "safety_ntc_fault", "mode_load_manual_on", "fw"):
            self.assertIn(col, header)
        self.assertEqual(len(lines), 3)  # header + 2 recent rows, old one excluded
        rows = [dict(zip(header, line.split(","))) for line in lines[1:]]
        self.assertEqual(rows[0]["seq"], "255")       # time order
        self.assertEqual(rows[0]["ntc_c"], "")         # null -> empty
        self.assertEqual(rows[0]["safety_night_pv_off"], "1")
        self.assertEqual(rows[1]["outputs_load"], "1")
        self.assertEqual(rows[1]["vbat_v"], "3.912")

    def test_export_many_rows(self):
        now = time.time()
        rows = [sample(now - 4000 + i, i % 256) for i in range(3500)]
        for k in range(0, len(rows), 1000):  # stay under the 1 MB request limit
            _, res = self.ingest({"gateway": gw(), "samples": rows[k:k + 1000]})
            self.assertEqual(res["stored"], len(rows[k:k + 1000]))
        r, body = self.req("GET", "/api/export.csv?hours=2", headers={"Cookie": self.cookie}, raw=True)
        self.assertEqual(len(body.decode().strip().split("\n")), 3501)

    def test_sse(self):
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        sock.sendall(f"GET /api/stream HTTP/1.1\r\nHost: x\r\nCookie: {self.cookie}\r\n\r\n".encode())
        f = sock.makefile("rb")
        status = f.readline()
        self.assertIn(b"200", status)
        headers = {}
        while (line := f.readline()) not in (b"\r\n", b""):
            k, v = line.decode().split(":", 1)
            headers[k.strip().lower()] = v.strip()
        self.assertEqual(headers["content-type"].split(";")[0], "text/event-stream")
        self.assertEqual(headers["x-accel-buffering"], "no")

        def next_event():
            ev, data = None, None
            while True:
                line = f.readline()
                if not line:
                    raise AssertionError("stream closed")
                line = line.decode().rstrip("\n")
                if line.startswith("event: "):
                    ev = line[7:]
                elif line.startswith("data: "):
                    data = json.loads(line[6:])
                elif line == "" and ev:
                    return ev, data

        s = sample(time.time(), 77)
        _, row = self.sess("POST", "/api/command", {"cmd": "AUTOLOAD ON"})
        ev, data = next_event()
        self.assertEqual((ev, data["id"], data["status"]), ("command", row["id"], "pending"))
        self.ingest({"gateway": gw(), "samples": [s]})
        ev, data = next_event()
        self.assertEqual((ev, data), ("sample", s))
        ev, data = next_event()
        self.assertEqual(ev, "gateway")
        self.assertEqual(data["id"], "mac-gw")
        ev, data = next_event()
        self.assertEqual((ev, data["status"], data["sent_to"]), ("command", "sent", "mac-gw"))
        sock.close()

    def test_sse_initial_gateway_event(self):
        self.ingest({"gateway": gw("gw-x"), "samples": []})
        sock = socket.create_connection(("127.0.0.1", self.port), timeout=5)
        sock.sendall(f"GET /api/stream HTTP/1.1\r\nHost: x\r\nCookie: {self.cookie}\r\n\r\n".encode())
        buf = b""
        while b"event: gateway" not in buf or not buf.endswith(b"\n\n"):
            chunk = sock.recv(4096)
            if not chunk:
                break
            buf += chunk
        sock.close()
        self.assertIn(b"event: gateway", buf)
        self.assertIn(b'"gw-x"', buf)


class TestUnits(unittest.TestCase):
    def test_normalize_command(self):
        self.assertEqual(server.normalize_command("range\tlow \n"), "RANGE LOW")
        with self.assertRaises(server.BadRequest):
            server.normalize_command("RANGELOW")

    def test_normalize_sample_rejects_bad(self):
        for bad in ({"seq": 1}, {"ts": time.time()}, {"ts": True, "seq": 1}, {"ts": 5, "seq": 1},
                    {"ts": time.time(), "seq": 1, "vbat_v": "3.9"}, {"ts": time.time(), "seq": 1, "outputs": []}):
            with self.assertRaises(server.BadRequest, msg=bad):
                server.normalize_sample(bad)

    def test_broker_drops_slow_subscriber_with_hangup(self):
        b = server.Broker()
        q = b.subscribe()
        for i in range(q.maxsize + 1):
            b.publish("sample", {"i": i})
        self.assertNotIn(q, b._subs)
        self.assertIsNone(q.get_nowait())  # the writer sees the sentinel at once and hangs up
        q2 = b.subscribe()
        b.close_all()
        self.assertIsNone(q2.get_nowait())

    def test_session_token(self):
        a = server.Auth("pw", "tok", "sec")
        t = a.make_session(time.time())
        self.assertTrue(a.check_session(t, time.time()))
        self.assertFalse(server.Auth("pw2", "tok", "sec").check_session(t, time.time()))  # password change
        self.assertFalse(server.Auth("pw", "tok", "other").check_session(t, time.time()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
