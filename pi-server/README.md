# Classroom CTF — Raspberry Pi Server

The target app for the whole-class Capture-the-Flag round described in
[CLASSROOM-CTF-EVENT-en.md](../CLASSROOM-CTF-EVENT-en.md). Run this on the
Raspberry Pi that's projected on the classroom screen.

> ⚠️ Run this only on a network your classroom fully controls — never on a
> production machine or one reachable from the internet. It's deliberately
> full of security holes on purpose.

Running a class session? [CLASSROOM-CTF-TEACHER-GUIDE-en.md](../CLASSROOM-CTF-TEACHER-GUIDE-en.md)
has the full step-by-step, answer key, and troubleshooting. Give students
[CLASSROOM-CTF-STUDENT-GUIDE-en.md](../CLASSROOM-CTF-STUDENT-GUIDE-en.md) (no answers).

## Setting up a brand-new Raspberry Pi from scratch

If the Pi has never been set up before, start here. If it's already running
Raspberry Pi OS, skip to [Setup](#setup).

1. **Flash the OS.** Install [Raspberry Pi Imager](https://www.raspberrypi.com/software/)
   on your computer, insert a microSD card (16 GB+), open Imager, and choose
   **Raspberry Pi OS (64-bit)**. Click the gear icon before writing to set a
   hostname (anything short, e.g. `ctf-pi`), a username/password (write the
   password down — you'll need it for every `sudo` command later), and
   enable SSH if you're setting the Pi up headless (no monitor). If Imager
   says the card is "in use by another program": cancel any "format this
   disk?" popup from Windows (don't format), close File Explorer windows
   showing the card, and/or run Imager as Administrator.
2. **First boot.** Insert the card into the Pi and power it on. With a
   monitor/keyboard attached, a desktop appears — open a terminal. Headless,
   wait a minute then `ssh <username>@<hostname>.local` from your computer.
3. **Update the system:**
   ```bash
   sudo apt update && sudo apt full-upgrade -y
   ```
4. **Turn the Pi into its own Wi-Fi hotspot** — this is the network every
   ESP32 and every student device will join for the exercise:
   ```bash
   sudo nmcli device wifi hotspot ifname wlan0 ssid "ClassroomCTF" password "cyberclass123"
   ```
   (Pick your own SSID/password if you like — just use the same ones
   everywhere below.) Find the Pi's IP address on that hotspot:
   ```bash
   ip a show wlan0
   ```
   Look for a line like `inet 10.42.0.1/24` — `10.42.0.1` is what you'll give
   students as the "Target IP." This hotspot does **not** survive a reboot;
   re-run the `nmcli` command before each class session.

   > **Running 15+ boards? Consider a dedicated router instead.** The Pi's
   > own Wi-Fi firmware caps out around ~10 reliable clients in AP mode — a
   > full class of 15 ESP32s plus a few student phones can start dropping
   > connections. A cheap Wi-Fi router handles this fine and needs **no
   > internet access** — it's just acting as a local AP/switch:
   > - Leave the router's WAN/Internet port empty; only use its LAN/Wi-Fi.
   > - Connect the Pi to it **over Ethernet** if you can (this removes the
   >   Pi's own Wi-Fi client-count limit entirely). Wi-Fi also works:
   >   `sudo nmcli device wifi connect "<RouterSSID>" password "<RouterPassword>"`.
   > - Every ESP32 and student device joins the **router's** SSID/password
   >   instead of `ClassroomCTF` — skip the `nmcli hotspot` command above.
   > - Find the Pi's new IP with `ip a` (check `eth0` if wired, `wlan0` if
   >   wireless) — likely something like `192.168.1.50`, not `10.42.0.1`.
   >   That's the new "Target IP."
   > - Make sure the router's "client/AP isolation" setting (common on
   >   guest networks) is **off**, or devices won't be able to reach the Pi.
   >
   > Prefer to keep using the Pi's own hotspot? Some Pi Wi-Fi chips support
   > an AP-optimized firmware variant that raises the limit to ~19 clients:
   > ```bash
   > sudo update-alternatives --list cyfmac43455-sdio.bin
   > ```
   > If that lists more than one option, `--config` (instead of `--list`)
   > lets you pick the AP-optimized one, then reboot. If the command errors
   > out, your Pi's chip uses a different firmware file and this trick
   > doesn't apply — use the router option above instead.
5. **Install git and Python tooling:**
   ```bash
   sudo apt install -y python3-pip python3-venv git
   ```
6. **Clone this repo:**
   ```bash
   git clone https://github.com/burak-akdogan/Cyber-Security-ESP32-EDU.git
   cd Cyber-Security-ESP32-EDU/pi-server
   ```
   Now continue with [Setup](#setup) below.

## Setup

```bash
cd pi-server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Leave that terminal running — the app has started once you see a line like
`Running on http://0.0.0.0:8080`. The dashboard is then at
`http://<pi-ip-address>:8080/` (e.g. `http://192.168.0.138:8080/` if you're
on a router, or `http://10.42.0.1:8080/` if you're on the Pi's own hotspot)
— put that address on the projector.

> **On the Pi's own screen** you can also use `http://localhost:8080/` or
> `http://127.0.0.1:8080/` — those mean "this machine." From any *other*
> device (your laptop, a student's phone, an ESP32) `localhost` refers to
> *that* device, not the Pi — you must use the Pi's real IP address (from
> `ip a show eth0` on a router, or `ip a show wlan0` on the Pi's own
> hotspot) instead. That other device also has to be joined to the same
> network first — the router's Wi-Fi, or `ClassroomCTF` if you're using the
> Pi's own hotspot.

### If port 8080 seems stuck / "address already in use"

Something (often a previous `python3 app.py` you forgot to stop) is already
holding the port:
```bash
sudo lsof -i :8080
```
If that lists a PID, stop it and try again:
```bash
sudo kill -9 <PID>
python3 app.py
```
If `lsof -i :8080` prints nothing at all, the port is free — the real
problem is that `app.py` isn't running yet (check that terminal for an
error, e.g. `ModuleNotFoundError` usually means the `venv` isn't activated).

## Before class

- **If you're on a router:** just power it and the Pi on — a router keeps
  its Wi-Fi/DHCP settings across reboots, nothing to re-run. Confirm the
  Pi's IP hasn't changed with `ip a show eth0` (most routers hand the same
  device the same IP each time, but it's worth a quick check).
- **If you're on the Pi's own hotspot:** re-run the
  `nmcli device wifi hotspot ...` command from step 4 above — it doesn't
  survive a reboot, so the Pi needs to be turned back into `ClassroomCTF`
  each session before students connect.
- Write the Pi's IP address somewhere visible (the projector screen itself
  works well) — students need it for the "Send to Board" form on the
  [flashing site](https://burak-akdogan.github.io/Cyber-Security-ESP32-EDU/).
- Give students [docs/ctf-rules.html](../docs/ctf-rules.html) (the
  "Download the Rules" button on the site) — it explains scoring without
  spoiling any flag.

## Testing with one ESP32 before class

1. Plug an ESP32 into your computer via USB, and make sure that computer has
   also joined the event network (the router's Wi-Fi, or `ClassroomCTF` if
   you're using the Pi's own hotspot).
2. Open the [flashing site](https://burak-akdogan.github.io/Cyber-Security-ESP32-EDU/),
   accept the code of conduct if prompted, scroll to **"Whole-Class Capture
   the Flag,"** and open **CTF · Recon Scanner**.
3. Click **Install** and flash the board.
4. In the same panel's Wi-Fi form, enter:
   - **SSID / Password:** the router's, or `ClassroomCTF` / `cyberclass123`
     for the Pi's own hotspot
   - **Target IP:** whatever `ip a show eth0` (router) or `ip a show wlan0`
     (Pi's own hotspot) showed you — e.g. `192.168.0.138` or `10.42.0.1`
5. Click **Send to Board** and pick the ESP32's serial port when asked. The
   console under the form should show the board joining the Wi-Fi, then a
   list of ports/paths it found on the Pi. If that shows up, the whole chain
   (network → Flask app → ESP32 → site) is working end to end.

## Between class periods

State (scores, found flags, which vulnerabilities are patched) lives only in
memory — restarting `app.py` wipes it. To reset without restarting the
process, send the instructor-only reset (change the PIN in `app.py` first):

```bash
curl -X POST http://localhost:8080/admin/reset-all -d "pin=1234"
```

## What's deliberately vulnerable

See the table in [CLASSROOM-CTF-EVENT-en.md §4](../CLASSROOM-CTF-EVENT-en.md#4-the-vulnerabilities-flags)
for the full list and the real-world lesson behind each one. Every
vulnerability can be independently "patched" from the dashboard — patching
is permanent until the next reset.

## Bonus: the DDoS demo

The dashboard also tracks live requests/second and can flip on a per-IP
rate limit (**🛡️ Enable DDoS Protection** button) — this pairs with the
**CTF · DDoS Flood** ESP32 tool for a separate, optional volume-attack demo.
See [CLASSROOM-CTF-TEACHER-GUIDE-en.md §8](../CLASSROOM-CTF-TEACHER-GUIDE-en.md#8-bonus-the-ddos-demo-separate-from-flag-hunting)
for how to run it. Run it as its own activity, not during the flag round —
a heavy flood makes the whole dashboard sluggish for everyone by design.
