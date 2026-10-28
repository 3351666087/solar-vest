#!/usr/bin/env python3
"""SolarVest Mac BLE gateway (software/SPEC.md section 6).

XIAO nRF52840 --BLE notify--> this gateway --HTTPS /api/ingest--> server
                <--BLE write--  commands returned by the server  <--

Only third-party dependency: bleak (imported lazily, so --selftest and
--dry-run work without it). HTTP uses stdlib urllib in a thread executor.

Usage:
  python3 gateway.py                 # normal unattended mode
  python3 gateway.py --selftest      # decoder vs protocol/vectors.json, exit 0/1
  python3 gateway.py --dry-run --url http://127.0.0.1:8790 --token dev
                                     # fake device replaying the vectors
"""
from __future__ import annotations

import argparse
import asyncio
import collections
import http.client
import json
import logging
import os
import signal
import ssl
import struct
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable, Optional

# --------------------------------------------------------------------------
# Protocol constants (SPEC section 2)
# --------------------------------------------------------------------------
DEVICE_NAME = "SolarVest-PMB"
SERVICE_UUID = "5f1e0001-6a2b-4c3d-9e8f-50a1b2c3d4e5"
TELEM_A_UUID = "5f1e0002-6a2b-4c3d-9e8f-50a1b2c3d4e5"
TELEM_B_UUID = "5f1e0003-6a2b-4c3d-9e8f-50a1b2c3d4e5"
COMMAND_UUID = "5f1e0004-6a2b-4c3d-9e8f-50a1b2c3d4e5"

NTC_INVALID = -32768
_A_FMT = struct.Struct("<BHhHhHhhhBBB")  # 20 bytes
_B_FMT = struct.Struct("<BhBBBBIBB7x")   # 20 bytes

# Timing / limits
B_WAIT_S = 1.5                 # wait this long for the matching TELEM_B
FLUSH_INTERVAL_S = 1.0
BACKOFF_MAX_S = 30.0
BUFFER_MAX = 7 * 24 * 3600     # 7 days at 1 Hz
BATCH_MAX = 300                # samples per POST (~200 kB, well under 1 MB)
HTTP_TIMEOUT_S = 15.0
RESCAN_DELAY_S = 2.0
SCAN_TIMEOUT_S = 10.0
CONNECT_TIMEOUT_S = 20.0
NOTIFY_STALL_S = 15.0          # connected but silent this long => reconnect
CMD_HOLD_S = 20.0              # hold commands this long while BLE is down
STATUS_INTERVAL_S = 60.0
PING_INTERVAL_S = 60.0         # keepalive; firmware v2 drops a central silent on COMMAND for 180 s
PING_TIMEOUT_S = 5.0
PING_PAYLOAD = b"PING"         # SPEC §2: no-op keepalive

log = logging.getLogger("gateway")


# --------------------------------------------------------------------------
# Decoder (must match protocol/vectors.json exactly)
# --------------------------------------------------------------------------
def _bits(value: int, names: list[str]) -> dict[str, bool]:
    return {name: bool(value >> i & 1) for i, name in enumerate(names)}


def decode(a: bytes, b: bytes, ts: float) -> dict[str, Any]:
    """Decode one TELEM_A + TELEM_B pair into the SPEC section 4 sample dict."""
    if len(a) < 20 or len(b) < 20:
        raise ValueError(f"short payload: a={len(a)} b={len(b)}")
    (seq, vpv, ipv, vbat, ibat, vload, iload, iref1, iref2,
     ina_ok, _pad, _proto) = _A_FMT.unpack_from(a)
    (_bseq, ntc, outputs, inputs, mode, safety,
     uptime, reset_reason, fw) = _B_FMT.unpack_from(b)
    return {
        "ts": ts,
        "seq": seq,
        "vpv_v": round(vpv / 1000, 3),
        "ipv_ma": round(ipv / 10, 1),
        "vbat_v": round(vbat / 1000, 3),
        "ibat_ma": round(ibat / 10, 1),
        "vload_v": round(vload / 1000, 3),
        "iload_ma": round(iload / 10, 1),
        "iref1_ma": round(iref1 / 100, 2),
        "iref2_ma": round(iref2 / 100, 2),
        "ina_ok": ina_ok,
        "ntc_c": None if ntc == NTC_INVALID else round(ntc / 10, 1),
        "outputs": _bits(outputs, ["load", "pv", "chg_inh", "range_lo", "sync"]),
        "inputs": _bits(inputs, ["charging", "done"]),
        "mode": _bits(mode, ["pv_auto", "chg_auto", "range_auto",
                             "autoload", "load_manual_on"]),
        "safety": _bits(safety, ["batt_lockout", "temp_inhibit",
                                 "night_pv_off", "ntc_fault"]),
        "uptime_s": uptime,
        "reset_reason": reset_reason,
        "fw": fw,
    }


# Buffered sample = raw A (20 B) + raw B (20 B) + ts as float64 (8 B), one
# 48-byte bytes object (~81 B each in CPython, ~50 MB at the 7-day cap instead
# of ~0.9 GB for decoded dicts). Decoded only when uploaded.
_TS_FMT = struct.Struct("<d")


def pack_record(a: bytes, b: bytes, ts: float) -> bytes:
    return bytes(a[:20]) + bytes(b[:20]) + _TS_FMT.pack(ts)


def decode_record(rec: bytes) -> dict[str, Any]:
    return decode(rec[:20], rec[20:40], _TS_FMT.unpack_from(rec, 40)[0])


def _placeholder_b(seq: int) -> bytes:
    """B payload used before any real TELEM_B was seen: NTC invalid, flags 0."""
    return _B_FMT.pack(seq, NTC_INVALID, 0, 0, 0, 0, 0, 0, 0)


def _vectors_path() -> Path:
    return Path(__file__).resolve().parent.parent / "protocol" / "vectors.json"


def load_vectors() -> list[dict[str, Any]]:
    with open(_vectors_path(), encoding="utf-8") as f:
        return json.load(f)


def selftest() -> int:
    try:
        vectors = load_vectors()
    except (OSError, ValueError) as e:
        print(f"Self-test FAILED: cannot read {_vectors_path()}: {e}")
        return 1
    failures = 0
    for v in vectors:
        got = decode(bytes.fromhex(v["a_hex"]), bytes.fromhex(v["b_hex"]), v["ts"])
        # Compare the JSON encodings so types matter (true vs 1, null vs 0).
        exp = v["expected"]
        enc = lambda x: json.dumps(x, sort_keys=True)  # noqa: E731
        diffs = [k for k in set(exp) | set(got) if enc(got.get(k)) != enc(exp.get(k))]
        if diffs:
            failures += 1
            print(f"FAIL  {v['name']}")
            for k in sorted(diffs):
                print(f"      {k}: got {got.get(k)!r} expected {exp.get(k)!r}")
        else:
            print(f"ok    {v['name']}")
    # Placeholder B must decode to NTC null and all-false flags.
    ph = decode(bytes(20), _placeholder_b(0), 0.0)
    if ph["ntc_c"] is not None or any(ph["outputs"].values()):
        failures += 1
        print("FAIL  placeholder B")
    else:
        print("ok    placeholder B")
    print(f"Self-test {'PASSED' if failures == 0 else 'FAILED'}: {len(vectors)} vectors, {failures} failed")
    return 0 if failures == 0 else 1


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------
CONFIG_FILE = Path.home() / ".config" / "solarvest" / "gateway.env"


def load_env_file(path: Path) -> dict[str, str]:
    """Parse simple KEY=VALUE lines (comments, `export`, quotes allowed)."""
    out: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return out
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, _, val = line.partition("=")
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        out[key.strip()] = val
    return out


def load_config(args: argparse.Namespace) -> dict[str, str]:
    """Priority: command line > environment > ~/.config/solarvest/gateway.env."""
    cfg = load_env_file(CONFIG_FILE)
    for key in ("SV_URL", "SV_DEVICE_TOKEN", "SV_GATEWAY_ID"):
        if os.environ.get(key):
            cfg[key] = os.environ[key]
    if args.url:
        cfg["SV_URL"] = args.url
    if args.token:
        cfg["SV_DEVICE_TOKEN"] = args.token
    cfg.setdefault("SV_URL", "https://console.example.org")
    cfg.setdefault("SV_GATEWAY_ID", "mac-gw")
    cfg["SV_URL"] = cfg["SV_URL"].rstrip("/")
    return cfg


# --------------------------------------------------------------------------
# Shared gateway state
# --------------------------------------------------------------------------
class Gateway:
    def __init__(self, cfg: dict[str, str], stop: asyncio.Event):
        self.cfg = cfg
        self.stop = stop
        # Raw records (see pack_record); decoded at upload time to save memory.
        self.buffer: collections.deque[bytes] = collections.deque(maxlen=BUFFER_MAX)
        self.dropped = 0                       # samples evicted by the 7-day cap
        self.ble_state = "disconnected"        # connected | scanning | disconnected
        self.rssi: Optional[int] = None
        self.device_name: Optional[str] = None
        # A/B merge
        # seq -> (a, ts, monotonic, last B known when A arrived)
        self.pending_a: dict[int, tuple[bytes, float, float, Optional[bytes]]] = {}
        # seq -> (b, monotonic arrival); entries older than B_WAIT_S are dropped
        # so a wrapped u8 seq never pairs a new A with a stale B.
        self.pending_b: dict[int, tuple[bytes, float]] = {}
        self.last_b: Optional[bytes] = None
        self.last_notify = time.monotonic()
        # Commands: server -> BLE, results -> next ingest
        self.cmd_queue: asyncio.Queue[tuple[int, str, float]] = asyncio.Queue()
        self.cmd_seen: collections.OrderedDict[int, dict] = collections.OrderedDict()
        self.acks: list[dict] = []
        self.writer: Optional[Callable[[bytes], Any]] = None  # async fn when connected
        # Stats for the per-minute line
        self.stat = collections.Counter()
        self.last_sample: Optional[dict] = None
        self.last_post_ok: Optional[float] = None
        self.last_error: Optional[str] = None
        self.fatal = False                    # unrecoverable setup error => exit 1

    # ---- telemetry merge -------------------------------------------------
    def on_a(self, data: bytes) -> None:
        if len(data) < 20:
            self.stat["bad_len"] += 1
            return
        now = time.time()
        self.last_notify = time.monotonic()
        seq = data[0]
        self._expire_pending_b()
        pb = self.pending_b.pop(seq, None)
        if pb is not None:  # B arrived first (rare)
            self._emit(data, pb[0], now)
        else:
            self.pending_a[seq] = (bytes(data), now, time.monotonic(), self.last_b)

    def on_b(self, data: bytes) -> None:
        if len(data) < 20:
            self.stat["bad_len"] += 1
            return
        self.last_notify = time.monotonic()
        data = bytes(data)
        self.last_b = data
        seq = data[0]
        pa = self.pending_a.pop(seq, None)
        if pa is not None:
            self._emit(pa[0], data, pa[1])
        else:
            # B before its A, or a late B whose A was already emitted A-only.
            self.pending_b.pop(seq, None)  # re-insert so dict order = arrival order
            self.pending_b[seq] = (data, time.monotonic())
            self._expire_pending_b()
            if len(self.pending_b) > 8:  # keep bounded; stale Bs are useless
                self.pending_b.pop(next(iter(self.pending_b)))

    def _expire_pending_b(self) -> None:
        cutoff = time.monotonic() - B_WAIT_S
        for seq in [s for s, (_, t) in self.pending_b.items() if t < cutoff]:
            del self.pending_b[seq]

    def expire_pending(self) -> None:
        """Emit A-only samples whose B did not arrive within B_WAIT_S."""
        self._expire_pending_b()
        cutoff = time.monotonic() - B_WAIT_S
        for seq in [s for s, p in self.pending_a.items() if p[2] < cutoff]:
            # Use the B known when this A arrived, not a newer one that may
            # already belong to a later seq.
            a, ts, _, prev_b = self.pending_a.pop(seq)
            b = prev_b or _placeholder_b(seq)
            self.stat["a_only"] += 1
            self._emit(a, b, ts)

    def reset_merge(self) -> None:
        self.expire_pending()
        for seq in list(self.pending_a):  # flush everything on disconnect
            a, ts, _, prev_b = self.pending_a.pop(seq)
            self._emit(a, prev_b or _placeholder_b(seq), ts)
        self.pending_b.clear()

    def _emit(self, a: bytes, b: bytes, ts: float) -> None:
        rec = pack_record(a, b, round(ts, 3))
        try:
            sample = decode_record(rec)  # validate now; also feeds the status line
        except (ValueError, struct.error) as e:
            self.stat["decode_err"] += 1
            log.error("Decode failed: %s", e)
            return
        if len(self.buffer) == self.buffer.maxlen:
            self.dropped += 1
        self.buffer.append(rec)
        self.last_sample = sample
        self.stat["samples"] += 1

    # ---- commands --------------------------------------------------------
    def accept_commands(self, cmds: list[dict]) -> None:
        for c in cmds:
            try:
                cid, text = int(c["id"]), str(c["cmd"])
            except (KeyError, TypeError, ValueError):
                log.error("Server returned an invalid command: %r", c)
                continue
            if cid in self.cmd_seen:
                done = self.cmd_seen[cid]
                if done is not None:  # redelivered after we already executed it
                    self.acks.append(done)
                continue
            self.cmd_seen[cid] = None  # in progress
            while len(self.cmd_seen) > 500:
                self.cmd_seen.popitem(last=False)
            self.cmd_queue.put_nowait((cid, text, time.monotonic()))

    def finish_command(self, cid: int, ok: bool, error: Optional[str]) -> None:
        ack = {"id": cid, "ok": ok, "error": error}
        self.cmd_seen[cid] = ack
        self.acks.append(ack)
        self.stat["cmd_ok" if ok else "cmd_err"] += 1
        if ok:
            log.info("Command #%d written to the device", cid)
        else:
            log.error("Command #%d failed: %s", cid, error)


# --------------------------------------------------------------------------
# HTTP (stdlib, run in executor)
# --------------------------------------------------------------------------
def _ssl_context() -> ssl.SSLContext:
    try:
        import certifi  # optional; present after python.org "Install Certificates"
        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


_SSL_CTX = _ssl_context()


class HttpError(Exception):
    pass


def post_json(url: str, token: str, body: dict) -> dict:
    data = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "solarvest-gateway/1",
    })
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_S, context=_SSL_CTX) as r:
            return json.loads(r.read(1 << 20) or b"{}")
    except urllib.error.HTTPError as e:
        detail = e.read(300).decode("utf-8", "replace").strip()
        raise HttpError(f"HTTP {e.code} {detail}") from None
    except urllib.error.URLError as e:
        reason = e.reason
        if isinstance(reason, ssl.SSLCertVerificationError):
            raise HttpError("TLS certificate verification failed: with python.org Python, run "
                            "'Install Certificates.command', or pip install certifi") from None
        raise HttpError(f"Network error: {reason}") from None
    except (OSError, ValueError, http.client.HTTPException) as e:
        # timeouts, resets, bad JSON, truncated/garbled responses (IncompleteRead,
        # BadStatusLine, LineTooLong...) from proxies or Cloudflare
        raise HttpError(f"{type(e).__name__}: {e}") from None


async def uplink_loop(gw: Gateway) -> None:
    """Flush the buffer to /api/ingest every second; back off on errors."""
    url = gw.cfg["SV_URL"] + "/api/ingest"
    token = gw.cfg.get("SV_DEVICE_TOKEN", "")
    loop = asyncio.get_running_loop()
    backoff = 0.0
    while not gw.stop.is_set():
        gw.expire_pending()
        n = min(len(gw.buffer), BATCH_MAX)
        batch = [decode_record(gw.buffer[i]) for i in range(n)]
        dropped_before = gw.dropped
        acks = list(gw.acks)
        body = {
            "gateway": {"id": gw.cfg["SV_GATEWAY_ID"], "kind": "python",
                        "ble": gw.ble_state, "rssi": gw.rssi,
                        "device": gw.device_name if gw.ble_state == "connected" else None},
            "samples": batch,
            "acks": acks,
        }
        try:
            resp = await loop.run_in_executor(None, post_json, url, token, body)
        except HttpError as e:
            gw.stat["post_err"] += 1
            backoff = min(BACKOFF_MAX_S, max(2.0, backoff * 2))
            if gw.last_error != str(e):  # don't spam the same error every retry
                log.error("Upload failed (retrying in %.0f s, %d samples buffered): %s", backoff, len(gw.buffer), e)
            gw.last_error = str(e)
            await _sleep(gw.stop, backoff)
            continue
        # Success: drop exactly what we sent. Only this coroutine pops from the
        # left and appends go to the right, so the sent items are still at the
        # head, minus any the full deque evicted during the POST (each eviction
        # bumps gw.dropped). len() can't tell us that: it stays at maxlen.
        evicted_meanwhile = min(n, gw.dropped - dropped_before)
        for _ in range(n - evicted_meanwhile):
            gw.buffer.popleft()
        del gw.acks[:len(acks)]
        if gw.last_error:
            log.info("Upload recovered, %d samples still buffered", len(gw.buffer))
        gw.last_error = None
        backoff = 0.0
        gw.last_post_ok = time.time()
        gw.stat["posted"] += n
        gw.stat["post_ok"] += 1
        if isinstance(resp, dict) and resp.get("commands"):
            gw.accept_commands(resp["commands"])
        # Catch up quickly when there is a backlog, otherwise 1 Hz.
        await _sleep(gw.stop, 0.05 if len(gw.buffer) > BATCH_MAX else FLUSH_INTERVAL_S)


# --------------------------------------------------------------------------
# Command writer: server commands -> COMMAND characteristic
# --------------------------------------------------------------------------
async def command_loop(gw: Gateway) -> None:
    held: list[tuple[int, str, float]] = []
    while not gw.stop.is_set():
        try:
            item = await asyncio.wait_for(gw.cmd_queue.get(), timeout=0.5)
            held.append(item)
        except asyncio.TimeoutError:
            pass
        still: list[tuple[int, str, float]] = []
        for cid, text, t0 in held:
            payload = text.strip().encode("ascii", "replace")
            if len(payload) > 20:
                gw.finish_command(cid, False, "Command longer than 20 bytes")
                continue
            writer = gw.writer
            if writer is None:
                if time.monotonic() - t0 > CMD_HOLD_S:
                    gw.finish_command(cid, False, "BLE not connected, command not delivered to the device")
                else:
                    still.append((cid, text, t0))
                continue
            try:
                await asyncio.wait_for(writer(payload), timeout=5.0)
                gw.finish_command(cid, True, None)
            except Exception as e:  # BLE errors vary by backend
                gw.finish_command(cid, False, f"BLE write failed: {type(e).__name__}: {e}"[:200])
        held = still


async def send_ping(gw: Gateway, writer: Callable[[bytes], Any]) -> bool:
    """Write the PING keepalive. Never raises (except cancellation); False = BLE error.

    A failed PING is treated like any other BLE error: the caller drops the
    link and the normal reconnect path takes over.
    """
    try:
        await asyncio.wait_for(writer(PING_PAYLOAD), timeout=PING_TIMEOUT_S)
    except asyncio.CancelledError:
        raise
    except Exception as e:  # BLE errors vary by backend; asyncio.TimeoutError included
        gw.stat["ping_err"] += 1
        log.error("PING keepalive write failed: %s: %s", type(e).__name__, e)
        return False
    gw.stat["ping_ok"] += 1
    log.debug("PING keepalive written")
    return True


# --------------------------------------------------------------------------
# BLE link (real device)
# --------------------------------------------------------------------------
async def ble_loop(gw: Gateway) -> None:
    try:
        from bleak import BleakClient, BleakScanner
    except ImportError:
        log.error("bleak is not installed: start with run.sh (it creates .venv and installs the dependencies)")
        gw.fatal = True
        gw.stop.set()
        return

    def match(device, adv) -> bool:
        uuids = [u.lower() for u in (adv.service_uuids or [])]
        name = adv.local_name or device.name
        if name == DEVICE_NAME or SERVICE_UUID in uuids:
            gw.rssi = adv.rssi
            gw.device_name = name or DEVICE_NAME
            return True
        return False

    while not gw.stop.is_set():
        gw.ble_state = "scanning"
        gw.writer = None
        try:
            device = await BleakScanner.find_device_by_filter(match, timeout=SCAN_TIMEOUT_S)
        except Exception as e:
            log.error("BLE scan error (is Bluetooth on, and does the terminal have Bluetooth permission?): %s", e)
            await _sleep(gw.stop, 10.0)
            continue
        if device is None:
            gw.stat["scan_miss"] += 1
            await _sleep(gw.stop, RESCAN_DELAY_S)
            continue

        disconnected = asyncio.Event()
        try:
            async with BleakClient(device, timeout=CONNECT_TIMEOUT_S,
                                   disconnected_callback=lambda _c: disconnected.set()) as client:
                await client.start_notify(TELEM_A_UUID, lambda _s, d: gw.on_a(bytes(d)))
                await client.start_notify(TELEM_B_UUID, lambda _s, d: gw.on_b(bytes(d)))

                write_lock = asyncio.Lock()  # PING and server commands never overlap

                async def write(payload: bytes, _c=client, _l=write_lock) -> None:
                    async with _l:
                        await _c.write_gatt_char(COMMAND_UUID, payload, response=True)

                gw.writer = write
                gw.ble_state = "connected"
                gw.last_notify = time.monotonic()
                gw.stat["connects"] += 1
                log.info("Connected to %s (%s, RSSI %s)", gw.device_name, device.address, gw.rssi)
                # Connected and subscribed: keepalive PING every PING_INTERVAL_S,
                # independent of server commands.
                next_ping = time.monotonic() + PING_INTERVAL_S
                # Stay here until disconnect, Ctrl-C, the device goes silent, or PING fails.
                while not gw.stop.is_set() and not disconnected.is_set():
                    if time.monotonic() - gw.last_notify > NOTIFY_STALL_S:
                        log.error("Connected but no data for %d s, reconnecting", NOTIFY_STALL_S)
                        break
                    if time.monotonic() >= next_ping:
                        if not await send_ping(gw, write):
                            log.error("PING failed, treating as a BLE error: disconnecting and reconnecting")
                            break
                        next_ping = time.monotonic() + PING_INTERVAL_S
                    try:
                        await asyncio.wait_for(disconnected.wait(), timeout=1.0)
                    except asyncio.TimeoutError:
                        pass
        except Exception as e:
            log.error("BLE connection error: %s: %s", type(e).__name__, e)
        finally:
            gw.writer = None
            gw.ble_state = "scanning"
            gw.reset_merge()
        if not gw.stop.is_set():
            log.info("BLE disconnected, rescanning in %.0f s", RESCAN_DELAY_S)
            gw.stat["disconnects"] += 1
            await _sleep(gw.stop, RESCAN_DELAY_S)
    gw.ble_state = "disconnected"


# --------------------------------------------------------------------------
# Fake device (--dry-run): replays vectors through the same merge path
# --------------------------------------------------------------------------
async def dry_run_loop(gw: Gateway) -> None:
    vectors = load_vectors()
    gw.device_name = DEVICE_NAME
    gw.rssi = -55

    async def fake_write(payload: bytes) -> None:
        log.info("[dry-run] write COMMAND: %s", payload.decode("ascii", "replace"))
        await asyncio.sleep(0.05)

    async def fake_ping(payload: bytes) -> None:
        log.info("[dry-run] write COMMAND (keepalive): %s", payload.decode("ascii", "replace"))
        await asyncio.sleep(0.05)

    seq, i = 0, 0
    next_ping: Optional[float] = None
    while not gw.stop.is_set():
        # Every 150 s simulate a 5 s disconnect so the "scanning" heartbeat path
        # runs; each connected stretch is long enough for two 60 s PINGs.
        if i and i % 150 == 0:
            gw.writer, gw.ble_state = None, "scanning"
            log.info("[dry-run] simulating a 5 s disconnect")
            gw.reset_merge()
            next_ping = None
            await _sleep(gw.stop, 5.0)
        if gw.writer is None:
            next_ping = time.monotonic() + PING_INTERVAL_S  # (re)connected + subscribed
        gw.writer, gw.ble_state = fake_write, "connected"
        if next_ping is not None and time.monotonic() >= next_ping:
            if await send_ping(gw, fake_ping):
                next_ping = time.monotonic() + PING_INTERVAL_S
            else:  # same handling as ble_loop: drop and reconnect
                gw.writer, gw.ble_state = None, "scanning"
                gw.reset_merge()
                await _sleep(gw.stop, RESCAN_DELAY_S)
                continue
        v = vectors[i % len(vectors)]
        a = bytearray.fromhex(v["a_hex"]); a[0] = seq
        b = bytearray.fromhex(v["b_hex"]); b[0] = seq
        gw.on_a(bytes(a))
        if i % 10 != 9:  # every 10th B is "lost" to exercise the 1.5 s fallback
            await asyncio.sleep(0.02)
            gw.on_b(bytes(b))
        seq = (seq + 1) & 0xFF
        i += 1
        await _sleep(gw.stop, 1.0)


# --------------------------------------------------------------------------
# Status line, helpers, main
# --------------------------------------------------------------------------
async def _sleep(stop: asyncio.Event, seconds: float) -> None:
    """Sleep that wakes immediately on shutdown."""
    try:
        await asyncio.wait_for(stop.wait(), timeout=seconds)
    except asyncio.TimeoutError:
        pass


async def status_loop(gw: Gateway) -> None:
    while not gw.stop.is_set():
        await _sleep(gw.stop, STATUS_INTERVAL_S)
        s, gw.stat = gw.stat, collections.Counter()
        last = gw.last_sample
        vbat = f"{last['vbat_v']:.3f}V" if last else "-"
        age = f"{time.time() - gw.last_post_ok:.0f}s ago" if gw.last_post_ok else "never"
        log.info("status ble=%s rssi=%s | this minute: samples %d (A-only %d) uploaded %d samples/%d posts, failed %d, cmd ok %d err %d"
                 " PING ok %d err %d | buffered %d dropped %d task restarts %d | last successful upload %s | vbat=%s",
                 gw.ble_state, gw.rssi, s["samples"], s["a_only"], s["posted"], s["post_ok"],
                 s["post_err"], s["cmd_ok"], s["cmd_err"], s["ping_ok"], s["ping_err"], len(gw.buffer), gw.dropped,
                 s["task_crash"], age, vbat)


async def _supervise(gw: Gateway, name: str, factory: Callable[[], Any]) -> None:
    """Run a loop coroutine; if it crashes unexpectedly, log and restart it.

    The gateway must run unattended for days and nothing external restarts
    it, so a bug or unforeseen exception must not silently stop uploads.
    """
    while not gw.stop.is_set():
        try:
            await factory()
            return  # normal exit (stop set, or fatal setup error)
        except asyncio.CancelledError:
            raise
        except Exception:
            gw.stat["task_crash"] += 1
            log.exception("Task %s exited with an exception, restarting in 5 s", name)
            await _sleep(gw.stop, 5.0)


async def amain(args: argparse.Namespace) -> int:
    cfg = load_config(args)
    if not cfg.get("SV_DEVICE_TOKEN"):
        log.error("Missing SV_DEVICE_TOKEN: put it in %s or set the environment variable", CONFIG_FILE)
        return 2
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            pass
    gw = Gateway(cfg, stop)
    log.info("Gateway started id=%s url=%s mode=%s", cfg["SV_GATEWAY_ID"], cfg["SV_URL"],
             "dry-run" if args.dry_run else "ble")
    loops = {
        "dry_run" if args.dry_run else "ble": dry_run_loop if args.dry_run else ble_loop,
        "uplink": uplink_loop, "command": command_loop, "status": status_loop,
    }
    tasks = [asyncio.create_task(_supervise(gw, name, lambda f=fn: f(gw)))
             for name, fn in loops.items()]
    if args.duration:
        loop.call_later(args.duration, stop.set)
    await stop.wait()
    log.info("Exiting…")
    # Give the BLE context manager a moment to disconnect cleanly, then cancel.
    done, pending = await asyncio.wait(tasks, timeout=5.0)
    for t in pending:
        t.cancel()
    await asyncio.gather(*pending, return_exceptions=True)
    if gw.buffer:
        log.info("Exiting with %d samples not uploaded (memory buffer only)", len(gw.buffer))
    return 1 if gw.fatal else 0


def main() -> int:
    p = argparse.ArgumentParser(description="SolarVest BLE → HTTPS gateway")
    p.add_argument("--selftest", action="store_true", help="check the decoder against software/protocol/vectors.json")
    p.add_argument("--dry-run", action="store_true", help="no Bluetooth: replay the test vectors to simulate the device")
    p.add_argument("--url", help="override SV_URL")
    p.add_argument("--token", help="override SV_DEVICE_TOKEN (the config file is recommended)")
    p.add_argument("--duration", type=float, help="exit after N seconds (for testing)")
    p.add_argument("-v", "--verbose", action="store_true")
    args = p.parse_args()
    if args.selftest:
        return selftest()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s",
                        datefmt="%Y-%m-%d %H:%M:%S")
    try:
        return asyncio.run(amain(args))
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
