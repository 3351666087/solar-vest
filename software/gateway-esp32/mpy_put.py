"""Copy files to a MicroPython board over its raw REPL without resetting it.

mpremote toggles DTR/RTS when it opens the port, which on this CP2102 ESP32 board holds the
chip in reset, so it never reaches the raw REPL. This tool opens the port with both lines
released and talks to the raw REPL directly.

usage: mpy_put.py PORT local_path:remote_path [...]   (remote dirs are created)
       mpy_put.py PORT --exec "python code"            (runs code, prints output)
       mpy_put.py PORT --reset                         (soft reset, starts main.py)
"""
import binascii
import sys
import time

import serial


def open_port(port):
    s = serial.Serial()
    s.port = port
    s.baudrate = 115200
    s.timeout = 0.2
    s.dtr = False
    s.rts = False
    s.open()
    return s


def read_until(s, token, timeout=10):
    buf = b""
    end = time.time() + timeout
    while time.time() < end:
        buf += s.read(256)
        if buf.endswith(token) or token in buf:
            return buf
    raise TimeoutError(f"waiting for {token!r}, got {buf[-200:]!r}")


def enter_raw(s):
    time.sleep(2.0)             # opening the port may still reset the board; let it boot first
    # main.py may be busy (e.g. a blocking Wi-Fi connect); keep interrupting until the REPL answers
    buf = b""
    end = time.time() + 20
    while time.time() < end and not buf.rstrip().endswith(b">>>"):
        s.write(b"\r\x03\x03")
        time.sleep(0.5)
        buf += s.read(4096)
    time.sleep(0.3)
    s.reset_input_buffer()
    s.write(b"\r\x01")
    read_until(s, b"raw REPL; CTRL-B to exit\r\n>")


def run(s, code, timeout=30):
    s.write(code.encode() + b"\x04")
    out = read_until(s, b"\x04>", timeout)      # reply: OK<stdout>\x04<stderr>\x04>
    if not out.startswith(b"OK"):
        raise RuntimeError(f"raw REPL did not accept the code: {out[:200]!r}")
    body, _, _ = out[2:].partition(b"\x04>")
    stdout, _, stderr = body.partition(b"\x04")
    if stderr.strip():
        raise RuntimeError(stderr.decode(errors="replace"))
    return stdout.decode(errors="replace")


def put(s, local, remote):
    data = open(local, "rb").read()
    parts = remote.strip("/").split("/")[:-1]
    mk = "import os\n"
    path = ""
    for p in parts:
        path += "/" + p
        mk += f"try:\n os.mkdir('{path}')\nexcept OSError:\n pass\n"
    run(s, mk)
    run(s, f"f=open('{remote}','wb')")
    for i in range(0, len(data), 512):
        chunk = binascii.b2a_base64(data[i:i + 512], newline=False).decode()
        run(s, f"import binascii;f.write(binascii.a2b_base64('{chunk}'))")
    run(s, "f.close()")
    print(f"{local} -> {remote} ({len(data)} B)")


def main():
    port, args = sys.argv[1], sys.argv[2:]
    s = open_port(port)
    enter_raw(s)
    if args and args[0] == "--exec":
        print(run(s, args[1], 600))
    elif args and args[0] == "--reset":
        s.write(b"\x02")        # leave raw REPL
        time.sleep(0.2)
        s.write(b"\x04")        # soft reset -> boot.py, main.py
        print("soft reset sent")
        return
    else:
        for a in args:
            local, remote = a.split(":", 1)
            put(s, local, remote)
    s.write(b"\x02")


if __name__ == "__main__":
    main()
