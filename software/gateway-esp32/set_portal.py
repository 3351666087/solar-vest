"""Save the captive-portal account the ESP32 gateway logs in with (an SRun (Shenlan) campus captive
portal) to ~/.config/solarvest/portal.json (readable only by you). The password is not echoed.
The portal host name is stored with the account and ends up in config.json as "portal": {"host": ...}.
The ESP32 logs in once and turns on MAC auth."""
import getpass
import json
import os

path = os.path.expanduser("~/.config/solarvest/portal.json")
host = input("Portal host name (e.g. portal.example.edu, no https://): ").strip()
host = host.split("://", 1)[-1].strip("/")
user = input("Campus network username: ").strip()
pw = getpass.getpass("Password (not shown while typing): ")
if not host or not user or not pw:
    raise SystemExit("Host, username or password is empty; nothing saved.")
os.makedirs(os.path.dirname(path), exist_ok=True)
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as f:
    json.dump({"host": host, "username": user, "password": pw}, f)
print("Saved. Tell Claude \"the account is ready\".")
