"""Serial bridge for the PMB-H bring-up sketch.

Reads the XIAO's USB serial into serial.log and sends any characters appended
to cmd.txt, so commands can be issued from another shell. Stop with Ctrl-C.
"""
import os
import select
import sys
import termios
import time

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/cu.usbmodem101"
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "serial.log")
CMD = os.path.join(HERE, "cmd.txt")


def open_port():
    fd = os.open(PORT, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    attrs = termios.tcgetattr(fd)
    attrs[0] = 0                                   # iflag: raw
    attrs[1] = 0                                   # oflag: raw
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
    attrs[3] = 0                                   # lflag: no echo, non-canonical
    attrs[4] = attrs[5] = termios.B115200
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    return fd


def main():
    open(CMD, "a").close()
    sent = os.path.getsize(CMD)                    # ignore commands written before start
    fd = None
    with open(LOG, "a", buffering=1, encoding="utf-8", errors="replace") as log:
        while True:
            if fd is None:
                try:
                    fd = open_port()
                    print("connected", PORT, flush=True)
                except OSError:
                    time.sleep(0.5)
                    continue
            try:
                r, _, _ = select.select([fd], [], [], 0.2)
                if r:
                    data = os.read(fd, 4096)
                    if data:
                        text = data.decode("utf-8", errors="replace")
                        log.write(text)
                        sys.stdout.write(text)
                        sys.stdout.flush()
                size = os.path.getsize(CMD)
                if size > sent:
                    with open(CMD, "rb") as f:
                        f.seek(sent)
                        os.write(fd, f.read())
                    sent = size
            except OSError:                        # board reset or unplugged: reopen
                os.close(fd)
                fd = None
                time.sleep(0.5)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
