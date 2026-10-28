"""Reset the ESP32 through RTS and print what it says for a few seconds."""
import sys
import time

import serial

port = sys.argv[1] if len(sys.argv) > 1 else "/dev/cu.usbserial-0001"
secs = float(sys.argv[2]) if len(sys.argv) > 2 else 6
s = serial.Serial(port, 115200, timeout=0.2)
s.dtr = False
s.rts = True
time.sleep(0.1)
s.rts = False
end = time.time() + secs
buf = b""
while time.time() < end:
    buf += s.read(4096)
s.write(b"\r\x03\x03\r\n")
time.sleep(0.5)
buf += s.read(4096)
print(buf.decode("utf-8", "replace"))
