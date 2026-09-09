# Cyber Sec ESP32 — Hands-On Wi-Fi Security Awareness Labs
### For the classroom · ESP32 DevKit V1 only · no extra hardware

A set of **buildable, consent-based** cybersecurity demonstrations for students. Each lab makes an invisible attack or privacy leak *visible* on a single ESP32 DevKit V1, then turns it into a discussion about how to defend yourself. These are not generic online tutorials — each teaches a distinct, often surprising concept.

> ⚠️ **All labs are for supervised classroom use with student consent.** They demonstrate techniques passively or against consenting devices, grant no real internet access, and are meant to build awareness — not to attack anyone. Read each guide's "Ethical and Legal Framework" section before running it.

---

## 🔧 Requirements (shared by all labs)

- **ESP32 DevKit V1** (single board — everything here runs on 2.4 GHz, no S2/S3, no HID hardware)
- Micro-USB **data** cable
- **Arduino IDE** with the ESP32 board package installed
- Serial Monitor set to **115200 baud**

All libraries used ship with the ESP32 Arduino core (`WiFi.h`, `esp_wifi.h`, `WebServer.h`, `DNSServer.h`, `BLEDevice.h`).

---

## 📚 The Labs

| # | Lab | What students witness | Core concept |
|---|---|---|---|
| 0 | [Evil Twin / Fake Wi-Fi](evil-twin-awareness-guideline-en.md) | A fake "Free WiFi" + login page logs whatever they type | Rogue AP & captive portal phishing |
| 1 | [Ghost of Networks Past](01-ghost-of-networks-past-en.md) | Phones broadcasting the names of every network they remember | Probe-request location-history leak |
| 2 | [The Deauth Canary](02-deauth-canary-wifi-smoke-alarm-en.md) | An LED alarm that fires when a deauth attack happens nearby | Building the **defender**, not the attacker |
| 3 | [The Wi-Fi Ghost](03-wifi-motion-ghost-through-wall-en.md) | Human motion detected through a wall — no camera | RSSI/radio-based presence sensing |
| 4 | [The Fingerprint Mirror](04-digital-fingerprint-mirror-en.md) | Everything a network learns about your phone with zero typing | Device fingerprinting & MAC tracking |
| 5 | [Invisible Ink](05-invisible-ink-ssid-covert-channel-en.md) | A secret message crossing with no network connection | Covert channels & air-gap myths |
| 6 | [The $100 Trick (Karma)](06-karma-wifi-pineapple-explained-en.md) | A phone auto-connecting to a fake AP no one tapped | How a Wi-Fi Pineapple really works |
| 7 | [It Looked So Real](07-realistic-captive-portal-reveal-en.md) | A polished fake login, then an instant "that was fake" reveal | Why "professional-looking" ≠ safe |

---

## 🎯 Suggested order

**Easiest to run / biggest first impression:**

1. **[Fingerprint Mirror](04-digital-fingerprint-mirror-en.md)** — flash it, connect a phone, instant "it already knows all this?" moment.
2. **[Ghost of Networks Past](01-ghost-of-networks-past-en.md)** — flash it, watch the Serial Monitor fill with places phones have been.
3. **[The $100 Trick (Karma)](06-karma-wifi-pineapple-explained-en.md)** — the natural sequel: the network *answers* those leaks and the phone auto-connects.

**Then, by theme:**
- *Attacker's view:* Evil Twin (0) → Karma (6)
- *Privacy leaks:* Ghost (1) → Fingerprint Mirror (4) → Wi-Fi Ghost (3)
- *Defender's mindset:* Deauth Canary (2) → Covert Channel (5)

---

## 🧭 Difficulty & setup notes

| Lab | Build effort | Special notes |
|---|---|---|
| 0 · Evil Twin | Easy | SPIFFS logging built in |
| 1 · Ghost | Easy | Promiscuous mode; results best with older/unlocked phones |
| 2 · Deauth Canary | Easy | Uses onboard LED (GPIO 2); lower threshold to test safely |
| 3 · Wi-Fi Ghost | Medium | Needs a router **you control** to measure against |
| 4 · Fingerprint Mirror | Easy | Captive portal; no login form |
| 5 · Invisible Ink | Medium | Best with 2 boards; **phone-only** fallback works with one |
| 6 · Karma | Medium | Most reliable against **open** saved networks; WPA2 resists (that's the lesson) |
| 7 · Realistic Portal | Easy | Fictional brand only; logs password **length**, never the password |

> **Modern phones fight back:** iOS/Android randomize MACs, suppress named probes when locked, and refuse name-only impersonation of encrypted networks. When a lab "doesn't work" against a hardened phone, that resistance *is* the lesson — discuss why.

---

## 🛡️ The through-line

Every lab ends the same way: a **defense/awareness table** and a **student checklist**. The goal is never the attack — it's the sentence a student says afterward:

> *"I didn't type anything / connect to anything / see any camera... and it still knew / still leaked / still worked."*

That realization is the whole curriculum.

---

## ⚖️ Responsible use

These materials assume a **supervised educational setting** with **informed consent** from everyone whose device is involved. Do not run Wi-Fi impersonation, probe capture, or motion sensing against people or networks outside your lab. Impersonating networks or capturing others' device data in public is illegal in most jurisdictions. Teach the defense as seriously as the demo.
