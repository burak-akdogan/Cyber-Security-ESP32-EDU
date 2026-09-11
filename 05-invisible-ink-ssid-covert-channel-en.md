# "Invisible Ink" — Smuggling Secrets Through Wi-Fi Network Names
### (Two ESP32 DevKit V1 boards — sender + receiver)

> 🚨 **FOR EDUCATIONAL PURPOSES ONLY.** This lab is provided solely to teach cybersecurity awareness in a supervised classroom setting, with informed consent from everyone involved. Do not use these techniques against real people, devices, or networks without explicit authorization — doing so may violate computer-misuse, wiretapping, or other laws in your jurisdiction.

**The mind-bending idea:** data can escape a locked-down network *without any network connection at all.* This project turns Wi-Fi **SSIDs (network names)** into a secret messaging channel. One ESP32 encodes a message into a series of fake network names it broadcasts; a second ESP32 (or any phone's Wi-Fi list) reads them back and reassembles the message. No pairing, no internet, no traffic to intercept.

This is a **covert channel** — the concept behind how malware exfiltrates data from air-gapped systems. Students see that "not connected to the internet" does **not** mean "can't leak data."

> Educational demonstration of a covert channel using publicly visible SSID broadcasts. No attacking, no interception of others' data — the boards only talk to each other.

---

## ⚠️ Read This First: Ethical and Legal Framework

- **SSID pollution:** Broadcasting many fake SSIDs briefly clutters the Wi-Fi list nearby. Keep sessions short and run it in class only.
- **Concept, not weapon:** The lesson is *how covert channels work* so you can recognize/defend against them — not how to smuggle data out of a real network.
- **Self-contained:** The two boards only communicate with each other; nothing else is touched.
- **The goal is awareness:** "An air gap is not a force field. Data finds creative ways out."

---

## 1. Required Materials

- **Two** ESP32 DevKit V1 boards (one sender, one receiver) — *or* one sender board + a phone to read the Wi-Fi list manually
- Two Micro-USB cables
- Arduino IDE with ESP32 board package

Uses: `WiFi.h`

---

## 2. How It Works (Conceptual Overview)

1. The sender splits a message into small chunks
2. Each chunk becomes a fake SSID like `MSG|00|He`, `MSG|01|ll`, `MSG|02|o!` (index + payload)
3. The sender rotates through these SSIDs, broadcasting each for a moment
4. The receiver runs Wi-Fi scans, spots SSIDs starting with the secret prefix `MSG|`, and collects the chunks
5. It sorts by index, strips the framing, and prints the reconstructed hidden message

No device ever *connects*. The information rides entirely in network *names* — visible to anyone, meaningful only to those who know the code.

---

## 3. Full Code

### 3a. Sender

```cpp
// covert_sender.ino
// Encodes a secret message into rotating SSID broadcasts.

#include <WiFi.h>

const char* SECRET = "Meet at 3pm. Code is 7412."; // message to smuggle
const char* PREFIX = "MSG";
const int CHUNK = 8;           // characters per SSID chunk
String ssids[64];
int total = 0;

void buildChunks() {
  String msg = String(SECRET);
  int n = (msg.length() + CHUNK - 1) / CHUNK;
  total = n;
  for (int i = 0; i < n; i++) {
    String part = msg.substring(i * CHUNK, min((int)msg.length(), (i+1)*CHUNK));
    char idx[3]; sprintf(idx, "%02d", i);
    // Format: MSG|<total>|<index>|<payload>
    ssids[i] = String(PREFIX) + "|" + String(total) + "|" + idx + "|" + part;
  }
}

void setup() {
  Serial.begin(115200);
  buildChunks();
  WiFi.mode(WIFI_AP);
  Serial.printf("Broadcasting %d secret chunks in a loop...\n", total);
}

void loop() {
  for (int i = 0; i < total; i++) {
    WiFi.softAP(ssids[i].c_str());      // broadcast this chunk as an SSID
    Serial.printf("Beaconing: %s\n", ssids[i].c_str());
    delay(1500);                        // hold long enough for a scan to catch it
    WiFi.softAPdisconnect(true);
    delay(150);
  }
}
```

### 3b. Receiver

```cpp
// covert_receiver.ino
// Scans for MSG| SSIDs and reassembles the hidden message.

#include <WiFi.h>

const char* PREFIX = "MSG|";
String parts[64];
bool got[64];
int expectedTotal = -1;

void reset() {
  for (int i = 0; i < 64; i++) { parts[i] = ""; got[i] = false; }
  expectedTotal = -1;
}

bool complete() {
  if (expectedTotal <= 0) return false;
  for (int i = 0; i < expectedTotal; i++) if (!got[i]) return false;
  return true;
}

void printMessage() {
  String msg = "";
  for (int i = 0; i < expectedTotal; i++) msg += parts[i];
  Serial.println("\n================ DECODED SECRET ================");
  Serial.println(msg);
  Serial.println("===============================================\n");
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  reset();
  Serial.println("Listening for hidden SSIDs...");
}

void loop() {
  int n = WiFi.scanNetworks();
  for (int i = 0; i < n; i++) {
    String s = WiFi.SSID(i);
    if (!s.startsWith(PREFIX)) continue;

    // Parse MSG|<total>|<index>|<payload>
    int p1 = s.indexOf('|');
    int p2 = s.indexOf('|', p1 + 1);
    int p3 = s.indexOf('|', p2 + 1);
    if (p1 < 0 || p2 < 0 || p3 < 0) continue;

    int tot = s.substring(p1 + 1, p2).toInt();
    int idx = s.substring(p2 + 1, p3).toInt();
    String payload = s.substring(p3 + 1);

    if (expectedTotal == -1) expectedTotal = tot;
    if (idx >= 0 && idx < 64 && !got[idx]) {
      parts[idx] = payload;
      got[idx] = true;
      Serial.printf("Captured chunk %d/%d: \"%s\"\n", idx + 1, tot, payload.c_str());
    }
  }
  WiFi.scanDelete();

  if (complete()) {
    printMessage();
    reset();          // reset to catch the next full loop
    delay(3000);
  }
  delay(500);
}
```

---

## 4. Setup and Test Steps

1. Flash **covert_sender.ino** to board A, **covert_receiver.ino** to board B
2. Open a Serial Monitor for each (115200 baud)
3. Board A logs each chunk as it beacons it; the chunks appear in nearby Wi-Fi lists too
4. Board B captures chunks over a few scan cycles and prints the reassembled secret
5. **Phone-only variant:** skip board B — just open your phone's Wi-Fi list and read the `MSG|...|Hello` names appearing and disappearing

---

## 5. Classroom Discussion Activity

- "The two boards never connected to each other or the internet. So how did the message get across?"
- "This is how malware can leak data from a computer with **no internet at all**. What else could carry a covert channel?" (blinking LEDs, fan speed, sound, heat...)
- "As a defender, would a normal firewall ever catch this? Why not?"
- "If you saw weird SSIDs like `MSG|03|...` in a sensitive building, what would you suspect?"

---

## 6. Defense / Awareness Takeaways

| Concept | Real-World Implication |
|---|---|
| Covert channels bypass network controls | Air-gapping alone isn't total protection |
| SSIDs carry attacker-chosen data | Monitoring the RF environment matters, not just network traffic |
| No connection = no traffic logs | Some exfiltration leaves no trace in normal logs |
| Creative side channels exist everywhere | Defense must think beyond the obvious cables |

---

## 7. Common Issues

| Issue | Fix |
|---|---|
| Receiver misses chunks | Increase sender `delay(1500)` so each SSID lives longer than a scan |
| Message never completes | Shorten the message or raise chunk hold time; scans can miss beacons |
| Garbled payload | Avoid `|` inside your secret message (it's the delimiter) |
| Only one board available | Use the phone Wi-Fi list variant to read chunks manually |

---

## 8. Student Checklist

- [ ] Ran sender + receiver (or read chunks on a phone)
- [ ] Reconstructed the hidden message with no network connection
- [ ] Explained what a covert channel is in their own words
- [ ] Named one other possible covert channel (light, sound, heat, etc.)
- [ ] Wrote 2-3 reasons air-gapping isn't a complete defense
