# "Ghost of Networks Past" — Your Phone Is Leaking Your Location History
### (ESP32 DevKit V1 only — no additional hardware)

**The idea nobody expects:** your phone doesn't just receive Wi-Fi — it constantly *calls out the names of every network it has ever remembered*, asking "are you here?" These are **probe requests**. By listening to them, this project rebuilds a rough map of where a person has been — coffee shops, airports, hotels, a friend's home network — **without them ever connecting to anything.**

This is not a Wi-Fi scanner (that lists routers). This listens to the *phones* and shows the history they broadcast into the air.

> Passive listening to publicly transmitted probe frames. No connecting, no deauth, no interception of traffic. The device only reads network *names* phones ask for.

---

## ⚠️ Read This First: Ethical and Legal Framework

- **Consent + anonymity:** Announce the activity. Display results as an **anonymous wall** — never label "these SSIDs belong to Ali." The lesson is collective, not a callout.
- **Don't dox locations:** If a probe reveals something sensitive (a home SSID, a workplace), discuss the *category* of leak, not the specific person.
- **Passive only:** This reads names phones already shout. It never connects or captures traffic.
- **The goal is awareness:** "Your phone has been quietly narrating your travel history to any listener in range."

---

## 1. Required Materials

- ESP32 DevKit V1
- Micro-USB data cable
- Arduino IDE with ESP32 board package

Uses the low-level ESP-IDF Wi-Fi promiscuous API (bundled with the core):
- `esp_wifi.h`, `esp_wifi_types.h`, `WiFi.h`

---

## 2. How It Works (Conceptual Overview)

1. A phone with saved networks periodically transmits **probe request** frames containing the SSIDs it remembers
2. The ESP32 enters **promiscuous (monitor) mode** and reads raw 802.11 frames
3. It filters for probe requests and extracts the requested SSID
4. Each *unique* SSID heard is added to a running "confession wall" (deduplicated)
5. On screen you see, e.g., `Starbucks_Guest`, `Hilton_Lobby`, `THY_Lounge`, `EvimWiFi_5G` — a stranger's movements, reconstructed from thin air

> Note: modern iOS/Android randomize MACs and often suppress named probes when locked. That's part of the lesson — you'll catch older devices, unlocked phones, IoT gadgets, and laptops far more.

---

## 3. Full Code

```cpp
// ghost_of_networks.ino
// Passive probe-request "confession wall" — privacy awareness, classroom use only.

#include <WiFi.h>
#include "esp_wifi.h"

#define MAX_NAMES 60
String heard[MAX_NAMES];
int count = 0;
int channel = 1;

bool alreadyHeard(const String& s) {
  for (int i = 0; i < count; i++) if (heard[i] == s) return true;
  return false;
}

void addName(const String& s) {
  if (s.length() == 0 || alreadyHeard(s)) return;
  if (count < MAX_NAMES) {
    heard[count++] = s;
    Serial.printf("[%2d] A phone here remembers: \"%s\"\n", count, s.c_str());
  }
}

// Called for every sniffed frame
void sniffer(void* buf, wifi_promiscuous_pkt_type_t type) {
  if (type != WIFI_PKT_MGMT) return;
  const wifi_promiscuous_pkt_t* pkt = (wifi_promiscuous_pkt_t*)buf;
  const uint8_t* p = pkt->payload;

  // 802.11 management frame subtype 4 = Probe Request
  uint8_t frameSubtype = (p[0] & 0xF0) >> 4;
  if (frameSubtype != 4) return;

  // Tagged params start at byte 24; first tag (0) is the SSID
  const uint8_t* tag = p + 24;
  if (tag[0] != 0) return;          // tag number 0 = SSID
  uint8_t len = tag[1];
  if (len == 0 || len > 32) return; // 0 = wildcard/broadcast probe, skip

  String ssid = "";
  for (int i = 0; i < len; i++) ssid += (char)tag[2 + i];
  addName(ssid);
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n=== Ghost of Networks Past ===");
  Serial.println("Listening for the network names phones broadcast...\n");

  WiFi.mode(WIFI_STA);
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_promiscuous_rx_cb(&sniffer);
  esp_wifi_set_channel(channel, WIFI_SECOND_CHAN_NONE);
}

void loop() {
  // Hop channels so we hear phones across the 2.4 GHz band
  delay(400);
  channel = (channel % 13) + 1;
  esp_wifi_set_channel(channel, WIFI_SECOND_CHAN_NONE);
}
```

---

## 4. Setup and Test Steps

1. Upload the code and open the Serial Monitor at 115200 baud
2. Let it run for 2–5 minutes in a room full of devices
3. Watch the "confession wall" fill with remembered network names
4. Ask a volunteer to toggle Wi-Fi **off** on their phone and note the difference
5. Compare an older/unlocked phone vs. a locked modern iPhone — see who leaks more

> Optional: project the Serial Monitor and let the class guess *which kind of place* each SSID implies (airport? gym? hotel?).

---

## 5. Classroom Discussion Activity

- "None of these phones connected to anything. So how did we learn where they've been?"
- "Pick an SSID on the wall — what does it tell you about that person's life?"
- "Why do newer phones leak less? What changed?"
- "If a stalker sat outside a café doing this all day, what could they build?"

---

## 6. Defense / Awareness Takeaways

| Leak | Mitigation |
|---|---|
| Phone broadcasting saved SSIDs | **Forget** old networks you no longer use |
| Named probe requests | Keep the OS updated; modern OSes randomize & suppress |
| Wi-Fi on in public | Turn Wi-Fi off when not actively using it |
| Home/work SSID revealed | Use generic, non-identifying network names at home |

---

## 7. Common Issues

| Issue | Fix |
|---|---|
| Very few names appear | Modern phones suppress named probes when locked — expected; try older/unlocked devices |
| Garbage characters in an SSID | Some SSIDs contain non-printable bytes; harmless |
| Nothing at all | Confirm promiscuous callback compiled; try staying on one channel to test |
| List stops growing | It deduplicates — only *new* names are added |

---

## 8. Student Checklist

- [ ] Ran the listener and watched remembered network names appear
- [ ] Explained how location history leaks *without* connecting
- [ ] Compared a leaky device vs. a privacy-hardened one
- [ ] Interpreted at least one SSID as a real-world place
- [ ] Wrote 2-3 steps to stop their own phone from leaking history
