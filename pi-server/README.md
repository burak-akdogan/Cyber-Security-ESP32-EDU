# Classroom CTF — Raspberry Pi Server

The target app for the whole-class Capture-the-Flag round described in
[CLASSROOM-CTF-EVENT-en.md](../CLASSROOM-CTF-EVENT-en.md). Run this on the
Raspberry Pi that's projected on the classroom screen.

> ⚠️ Run this only on a network your classroom fully controls — never on a
> production machine or one reachable from the internet. It's deliberately
> full of security holes on purpose.

## Setup

```bash
cd pi-server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

The dashboard is then at `http://<pi-ip-address>:8080/` — put that address
on the projector. Find the Pi's IP with `hostname -I`.

## Before class

- Make sure the Pi and every ESP32 join the **same Wi-Fi network** — either
  the Pi's own hotspot, or a router used only for this exercise.
- Write the Pi's IP address somewhere visible (the projector screen itself
  works well) — students need it for the "Send to Board" form on the
  [flashing site](https://burak-akdogan.github.io/Cyber-Security-ESP32-EDU/).
- Give students [docs/ctf-rules.html](../docs/ctf-rules.html) (the
  "Download the Rules" button on the site) — it explains scoring without
  spoiling any flag.

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
