# "The Deauth Canary" — Build the Defender, Not the Attacker
### (ESP32 DevKit V1 only — uses the onboard LED)

Every tutorial online teaches you to *launch* a deauthentication attack (the one that kicks people off Wi-Fi). This project flips it: students build a **detector** — a "Wi-Fi smoke alarm" that sits quietly and **blinks/alarms the moment someone nearby fires a deauth attack.** You learn the attack by learning to *catch* it.

The twist: deauth frames are unauthenticated management frames that a normal device never sends in bulk. A sudden burst is an unmistakable fingerprint of an attack in progress.

> Detection only. This device never *sends* deauth frames — it just recognizes the signature of an attack happening around it.

---

## ⚠️ Read This First: Ethical and Legal Framework

- **Defensive project:** The point is to detect and understand, not to disrupt. This code cannot attack.
- **Interpreting alarms:** A few management frames are normal. Only a *burst* signals an attack — teach the difference between noise and a real event.
- **Don't accuse:** If the canary triggers in public, it means *someone* nearby ran a tool; it doesn't identify who. Discuss responsibly.
- **The goal is awareness:** "Attacks leave footprints. Defenders learn to read them."

---

## 1. Required Materials

- ESP32 DevKit V1 (onboard LED on GPIO 2)
- Micro-USB data cable
- Arduino IDE with ESP32 board package

Uses:
- `WiFi.h`, `esp_wifi.h` (promiscuous mode)

---

## 2. How It Works (Conceptual Overview)

1. The ESP32 enters promiscuous mode and reads raw 802.11 management frames
2. It counts **deauthentication (subtype 12)** and **disassociation (subtype 10)** frames
3. In normal air, these are rare and sporadic
4. If the count crosses a threshold within a short window → **ATTACK DETECTED**
5. The onboard LED flashes and the Serial Monitor logs the burst with a timestamp

---

## 3. Full Code

```cpp
// deauth_canary.ino
// Wi-Fi deauth/disassoc attack DETECTOR. Defensive — never transmits attacks.

#include <WiFi.h>
#include "esp_wifi.h"

#define LED_PIN 2
#define WINDOW_MS 1000     // measurement window
#define ALARM_THRESHOLD 5  // deauth/disassoc frames per window that = attack

volatile uint32_t deauthCount = 0;
uint32_t windowStart = 0;
int channel = 1;

void sniffer(void* buf, wifi_promiscuous_pkt_type_t type) {
  if (type != WIFI_PKT_MGMT) return;
  const wifi_promiscuous_pkt_t* pkt = (wifi_promiscuous_pkt_t*)buf;
  uint8_t subtype = (pkt->payload[0] & 0xF0) >> 4;
  // 12 = deauthentication, 10 = disassociation
  if (subtype == 12 || subtype == 10) deauthCount++;
}

void alarm(uint32_t frames) {
  Serial.printf("!!! DEAUTH ATTACK DETECTED !!!  %u frames in 1s (ch %d)\n",
                frames, channel);
  for (int i = 0; i < 10; i++) {         // fast panic blink
    digitalWrite(LED_PIN, HIGH); delay(40);
    digitalWrite(LED_PIN, LOW);  delay(40);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  Serial.println("\n=== Deauth Canary armed ===");
  Serial.println("Quietly watching for attacks...");

  WiFi.mode(WIFI_STA);
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_promiscuous_rx_cb(&sniffer);
  esp_wifi_set_channel(channel, WIFI_SECOND_CHAN_NONE);
  windowStart = millis();
}

void loop() {
  if (millis() - windowStart >= WINDOW_MS) {
    uint32_t c = deauthCount;
    deauthCount = 0;
    windowStart = millis();

    if (c >= ALARM_THRESHOLD) {
      alarm(c);
    } else {
      // slow heartbeat blink = "all clear, still watching"
      digitalWrite(LED_PIN, HIGH); delay(20); digitalWrite(LED_PIN, LOW);
      if (c > 0) Serial.printf("(quiet) %u mgmt disconnect frames on ch %d\n", c, channel);
    }

    // hop a channel each window to widen coverage
    channel = (channel % 11) + 1;
    esp_wifi_set_channel(channel, WIFI_SECOND_CHAN_NONE);
  }
}
```

---

## 4. Setup and Test Steps

1. Upload the code and open the Serial Monitor at 115200 baud — the LED gives a slow heartbeat = "watching"
2. In normal conditions it should stay quiet
3. **To test the alarm safely:** have the teacher (in a controlled setting, on their own network) briefly run a known deauth tool, or simply lower `ALARM_THRESHOLD` to `1` and reboot a nearby router to generate legitimate disassociation frames
4. Watch the LED panic-blink and the Serial log fire
5. Restore the threshold and discuss what a real detection would mean

> Keeping the canary on a single fixed channel (comment out the hop) makes it more sensitive to attacks on that channel.

---

## 5. Classroom Discussion Activity

- "Why is a *sudden burst* of these frames suspicious, when a few are normal?"
- "This attack works because deauth frames aren't authenticated. What would fix that?" (→ 802.11w / Protected Management Frames)
- "A café's Wi-Fi keeps dropping everyone at once. Attack, or bad router? How would you tell?"
- "You built a defender today instead of an attacker. Why does that skill matter more?"

---

## 6. Defense / Awareness Takeaways

| Threat | Defense |
|---|---|
| Deauth flooding kicks you offline | Use WPA3 / networks with Protected Management Frames (802.11w) |
| Attacker forces you onto an evil twin | Sudden repeated disconnects = be suspicious, don't reconnect blindly |
| Silent attacks | Monitoring tools (like this canary) surface the invisible |
| Relying only on Wi-Fi | Have a mobile-data fallback for critical moments |

---

## 7. Common Issues

| Issue | Fix |
|---|---|
| Never triggers | Lower `ALARM_THRESHOLD`; test with router reboots or a controlled tool |
| Triggers constantly | Raise threshold; a busy environment has more mgmt traffic |
| LED doesn't blink | Confirm onboard LED is GPIO 2 on your board variant |
| Misses attacks | Channel hopping can miss the attack channel — pin one channel to test |

---

## 8. Student Checklist

- [ ] Armed the canary and confirmed the "watching" heartbeat
- [ ] Triggered the alarm in a controlled/safe way
- [ ] Explained why a *burst* of deauth frames signals an attack
- [ ] Named the real fix (Protected Management Frames / WPA3)
- [ ] Wrote 2-3 reasons defenders need to understand attacks
