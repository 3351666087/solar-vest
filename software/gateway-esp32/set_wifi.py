"""Ask for the Wi-Fi networks the ESP32 gateway should use and save them to
~/.config/solarvest/wifi.json (readable only by you). The password is not echoed.
Run it again to replace the list. Networks are tried in the order entered."""
import getpass
import json
import os

path = os.path.expanduser("~/.config/solarvest/wifi.json")
nets = []
print("Enter the Wi-Fi networks the ESP32 should join (tried in order). Leave the SSID empty and press Enter to finish.")
while True:
    ssid = input(f"Wi-Fi network {len(nets) + 1} name (SSID): ").strip()
    if not ssid:
        break
    pw = getpass.getpass("Password (press Enter for an open network; not shown while typing): ")
    nets.append({"ssid": ssid, "password": pw})
if not nets:
    raise SystemExit("No networks entered; nothing saved.")
os.makedirs(os.path.dirname(path), exist_ok=True)
fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as f:
    json.dump(nets, f, ensure_ascii=False)
print(f"Saved {len(nets)} network(s) to {path}. Tell Claude \"Wi-Fi is ready\".")
