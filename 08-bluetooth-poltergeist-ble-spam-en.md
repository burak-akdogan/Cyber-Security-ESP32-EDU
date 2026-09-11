# "The Bluetooth Poltergeist" — Phantom Devices From Thin Air
### (ESP32 DevKit V1 only — uses the onboard Bluetooth Low Energy radio)

> 🚨 **FOR EDUCATIONAL PURPOSES ONLY.** This lab is provided solely to teach cybersecurity awareness in a supervised classroom setting, with informed consent from everyone involved. Do not use these techniques against real people, devices, or networks without explicit authorization — doing so may violate computer-misuse, wiretapping, or other laws in your jurisdiction.

Bluetooth Low Energy advertising is a **one-way, unsigned shout**: any device can broadcast "I'm here, and this is my name" and nearby phones just believe it — there's no proof, no signature, nothing to verify. This project makes an ESP32 impersonate a rotating cast of familiar-sounding devices (`AirPods Pro`, `Smart Lock 4B`, `Fitbit Charge 5`...) that appear and vanish in students' own phones' Bluetooth scanners, live, out of thin air.

None of it is real. Nothing pairs. Nothing connects. That's the point — the *name* was never proof of anything to begin with.

> Passive broadcast only — no pairing, no connection, no data exchange. The ESP32 never receives or accesses anything from nearby phones; this is a one-way loudspeaker announcing fake device names into the air, and no one's device can be paired with or read from through it.

---

## ⚠️ Read This First: Ethical and Legal Framework

- **This is the one lab that reaches every phone in range, not just a consenting one.** BLE advertising is a public radio broadcast — anyone with Bluetooth on nearby will see the fake names, whether they're part of the demo or not. Run it only in the classroom, for a short window, and announce it to **everyone present**, not just the students directly involved.
- **We deliberately stop short of the more invasive version.** Public tools exist that spoof brand-specific protocols (e.g. Apple's Continuity/"Nearby Action" format) to pop an actual pairing sheet on a stranger's iPhone. That technique has been used to harass people in public and is intentionally **out of scope here** — this lab only makes fake names *appear in a scan list*; it never triggers a system popup on someone else's phone.
- **No pairing, no data, ever:** the ESP32 exposes no GATT services. Attempting to actually connect to one of the phantom names will simply fail — that failure is itself part of the lesson.
- **The goal is awareness:** "Bluetooth will hand you a friendly name for anything nearby. The name was never proof of what the thing actually is."

---

## 1. Required Materials

- ESP32 DevKit V1
- Micro-USB data cable
- Arduino IDE with ESP32 board package
- A phone with Bluetooth on and a scanner open (built-in "available devices" list under Bluetooth settings, or a free app like nRF Connect / LightBlue for more detail)

Uses (all bundled with the ESP32 Arduino core): `BLEDevice.h`, `BLEUtils.h`, `BLEAdvertising.h`

---

## 2. How It Works (Conceptual Overview)

1. A BLE advertising packet is a small broadcast frame any device sends to announce "I'm here, and this is my name"
2. Nothing about that packet has to be true — there's no signature and no verification step
3. The ESP32 cycles through a list of recognizable, brand-adjacent fake device names
4. Each time it swaps names, it rebuilds and rebroadcasts fresh advertising data
5. Anyone scanning nearby watches phantom devices appear and disappear over and over — none of them lead anywhere real

---

## 3. Full Code

```cpp
// bluetooth_poltergeist.ino
// Broadcasts a rotating stream of fake BLE device names. No pairing, no
// connection, no data exchange, no GATT services exposed. Classroom
// awareness demo — announce it to everyone in the room before running.

#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEAdvertising.h>

BLEAdvertising* advertising;

const char* fakeNames[] = {
  "AirPods Pro", "Galaxy Buds2", "Fitbit Charge 5", "Smart Lock 4B",
  "Meeting Room Mic", "Printer_HP2200", "Unknown Speaker", "Car Multimedia"
};
const int NUM_NAMES = sizeof(fakeNames) / sizeof(fakeNames[0]);
int idx = 0;

unsigned long lastSwap = 0;
const unsigned long SWAP_MS = 1200; // long enough for a scanner app to catch each one

void broadcastAs(const String& name) {
  BLEAdvertisementData advData;
  advData.setName(name.c_str());
  advData.setFlags(0x06); // general discoverable, BR/EDR not supported

  advertising->stop();
  advertising->setAdvertisementData(advData);
  advertising->setScanResponseData(advData);
  advertising->start();
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== Bluetooth Poltergeist: phantom devices incoming ===");
  Serial.println("Open a Bluetooth scanner on a nearby phone to watch them appear.\n");

  BLEDevice::init("");
  advertising = BLEDevice::getAdvertising();
  advertising->setScanResponse(true);
  broadcastAs(fakeNames[0]);
  Serial.printf("[BROADCAST] now impersonating \"%s\"\n", fakeNames[0]);
  lastSwap = millis();
}

void loop() {
  if (millis() - lastSwap < SWAP_MS) return;
  lastSwap = millis();

  idx = (idx + 1) % NUM_NAMES;
  broadcastAs(fakeNames[idx]);
  Serial.printf("[BROADCAST] now impersonating \"%s\"\n", fakeNames[idx]);
}
```

---

## 4. Setup and Test Steps

1. Upload the code and open the Serial Monitor at 115200 baud — it logs each fake name as it goes out
2. On a phone, open Bluetooth settings' "available devices" list (or a scanner app for more detail)
3. Watch phantom devices with familiar, believable names appear and cycle roughly every second
4. Try tapping one to connect — it fails or times out, because nothing real is behind the name
5. Ask: "How would you have told this apart from your actual AirPods sitting right next to you?"

---

## 5. Classroom Discussion Activity

- "The name said 'AirPods Pro' — was there any proof, or was it just a broadcast trusting itself?"
- "If a smart lock or medical device advertises a friendly, guessable name, what could a stranger learn or spoof?"
- "Real-world attacks push this further into forced pairing popups on people's actual phones — why does even a 'harmless-looking' notification deserve suspicion?"
- "How is broadcasting a fake Bluetooth name similar to (and different from) the Evil Twin fake Wi-Fi network from Lab 0?"

---

## 6. Defense / Awareness Takeaways

| Risk | Mitigation |
|---|---|
| Trusting a Bluetooth name at face value | Verify the physical device itself, don't assume by name alone |
| Bluetooth left on and discoverable in public | Turn Bluetooth off, or set to "not discoverable," when not actively pairing |
| Smart devices with guessable/branded names | Rename devices to something non-identifying where the option exists |
| Unexpected pairing prompts | Never tap "pair" or "connect" on a device you didn't initiate yourself |

---

## 7. Common Issues

| Issue | Fix |
|---|---|
| No devices show up in the scan | Confirm the phone's Bluetooth is on; some scanner apps filter by signal strength — get closer |
| Only one name ever appears | Some phones cache scan results — pull to refresh, or reopen the scanner |
| Upload/compile errors on `BLEDevice.h` | Confirm the ESP32 board package (not just core Arduino) is installed and selected |
| A tap-to-connect attempt hangs briefly | Expected — there's no GATT service behind the name, so it will simply time out |

---

## 8. Student Checklist

- [ ] Announced the demo to everyone in the room before starting (not just participants)
- [ ] Watched phantom device names appear and cycle on a real phone's scanner
- [ ] Attempted to connect to one and observed the failure
- [ ] Explained why a Bluetooth name alone is not proof of a device's identity
- [ ] Wrote 2-3 habits that reduce their own exposure to this kind of spoofing
