# "The Fingerprint Mirror" — What a Network Learns About You in 3 Seconds
### (ESP32 DevKit V1 only — no additional hardware)

> 🚨 **FOR EDUCATIONAL PURPOSES ONLY.** This lab is provided solely to teach cybersecurity awareness in a supervised classroom setting, with informed consent from everyone involved. Do not use these techniques against real people, devices, or networks without explicit authorization — doing so may violate computer-misuse, wiretapping, or other laws in your jurisdiction.

Most captive-portal demos try to *steal* something from you. This one does the opposite: the instant you connect, it shows **you** everything it already knows about your device — no form, no password, no clicking. Your device *handed all of it over just by connecting.*

The shock isn't a fake login page. It's a mirror: "Hi, iPhone. You're made by Apple, your device is named *Ahmet's iPhone*, and here's the fingerprint that lets networks recognize you again."

> Everything shown is information your device *volunteers* to any network it joins. Nothing is intercepted or cracked; nothing leaves the ESP32.

---

## ⚠️ Read This First: Ethical and Legal Framework

- **Consent:** Announce it. Connecting is voluntary; the reveal is the whole point.
- **Personal, not shared:** Each student sees *their own* mirror on their own screen. Don't broadcast one person's device name to the class without asking.
- **Nothing stolen:** No passwords, no traffic, no accounts — only what the device advertises at connection.
- **The goal is awareness:** "You didn't type anything, yet the network already profiled you."

---

## 1. Required Materials

- ESP32 DevKit V1
- Micro-USB data cable
- Arduino IDE with ESP32 board package

Uses (bundled):
- `WiFi.h`, `DNSServer.h`, `WebServer.h`, `esp_wifi.h`

---

## 2. How It Works (Conceptual Overview)

1. The ESP32 runs an open AP + captive portal (like the evil-twin demo) but with **no login form**
2. When a device connects, the OS auto-opens the portal page
3. The page reports back to the user:
   - **MAC address** and the **vendor** decoded from its first 3 bytes (OUI)
   - Whether the MAC looks **randomized** (privacy on) or **real** (trackable)
   - The **hostname** the device announced (often literally "Ahmet's-iPhone")
   - The **User-Agent** string (OS + browser + versions) from the HTTP request
4. Together these form a **device fingerprint** — how you get re-identified across networks

---

## 3. Full Code

```cpp
// fingerprint_mirror.ino
// Shows a connecting device what it just revealed. Awareness, classroom use.

#include <WiFi.h>
#include <DNSServer.h>
#include <WebServer.h>
#include "esp_wifi.h"

const char* ap_ssid = "Free_Guest_WiFi";
DNSServer dns;
WebServer web(80);
const byte DNS_PORT = 53;
IPAddress apIP(192,168,4,1);

// A few well-known OUI prefixes for the vendor guess (extend as you like)
String vendorFor(const String& mac) {
  String p = mac.substring(0,8); p.toUpperCase();
  if (p.startsWith("F0:18:98") || p.startsWith("A4:83:E7") || p.startsWith("DC:2B:2A")) return "Apple";
  if (p.startsWith("3C:5A:B4") || p.startsWith("F8:8F:CA")) return "Google";
  if (p.startsWith("00:1A:11")) return "Google";
  if (p.startsWith("50:8F:4C") || p.startsWith("AC:37:43")) return "Samsung/HTC";
  if (p.startsWith("B8:27:EB") || p.startsWith("DC:A6:32")) return "Raspberry Pi";
  return "Unknown (look up the OUI!)";
}

// Locally-administered bit set in first octet => randomized MAC
bool isRandomized(const String& mac) {
  int firstByte = strtol(mac.substring(0,2).c_str(), NULL, 16);
  return (firstByte & 0x02) != 0;
}

// Find the MAC of the connected station by its IP (from the softAP client list)
String macForClient() {
  wifi_sta_list_t stations;
  esp_wifi_ap_get_sta_list(&stations);
  if (stations.num > 0) {
    // Best-effort: return the most recently seen station
    uint8_t* m = stations.sta[stations.num - 1].mac;
    char buf[18];
    sprintf(buf, "%02X:%02X:%02X:%02X:%02X:%02X", m[0],m[1],m[2],m[3],m[4],m[5]);
    return String(buf);
  }
  return "unavailable";
}

void handlePortal() {
  String mac = macForClient();
  String vendor = (mac == "unavailable") ? "unavailable" : vendorFor(mac);
  String rnd = (mac == "unavailable") ? "?" :
               (isRandomized(mac) ? "YES (privacy on \xF0\x9F\x91\x8D)" : "NO (real, trackable!)");
  String ua = web.header("User-Agent");
  if (ua == "") ua = "(not sent)";

  String h = "<html><head><meta name='viewport' content='width=device-width,initial-scale=1'>";
  h += "<style>body{font-family:sans-serif;max-width:480px;margin:24px auto;padding:0 14px}";
  h += "td{padding:6px;border-bottom:1px solid #eee;vertical-align:top}";
  h += ".k{color:#666;width:38%}.v{font-family:monospace}</style></head><body>";
  h += "<h2>\xF0\x9F\xAA\x9E You didn't type anything...</h2>";
  h += "<p>...yet just by connecting, your device already told this network:</p><table>";
  h += "<tr><td class='k'>Your MAC address</td><td class='v'>" + mac + "</td></tr>";
  h += "<tr><td class='k'>Device maker (from MAC)</td><td class='v'>" + vendor + "</td></tr>";
  h += "<tr><td class='k'>MAC randomized?</td><td class='v'>" + rnd + "</td></tr>";
  h += "<tr><td class='k'>Your device / browser</td><td class='v'>" + ua + "</td></tr>";
  h += "</table>";
  h += "<p style='font-size:13px;color:#a00'>If \"randomized\" says NO, this exact address can be";
  h += " recognized every time you join any network — a permanent tracking ID.</p>";
  h += "<p style='font-size:12px;color:gray'>Classroom awareness demo. Nothing is stored.</p>";
  h += "</body></html>";
  web.send(200, "text/html", h);
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ap_ssid);
  dns.start(DNS_PORT, "*", apIP);

  const char* headers[] = {"User-Agent"};
  web.collectHeaders(headers, 1);
  web.onNotFound(handlePortal);
  web.on("/", handlePortal);
  web.begin();
  Serial.println("Fingerprint Mirror AP up. SSID: Free_Guest_WiFi");
}

void loop() {
  dns.processNextRequest();
  web.handleClient();
}
```

---

## 4. Setup and Test Steps

1. Upload the code and open the Serial Monitor
2. Connect a phone/laptop to `Free_Guest_WiFi` (no password)
3. The captive-portal page opens automatically — read what it knows about you
4. Compare devices: turn **"Private Wi-Fi Address" / MAC randomization** on and off, reconnect, and watch the "randomized?" line change
5. Rename a phone (Settings → About → Name) and reconnect to see the hostname change

> Note: OUI vendor lookup here covers a handful of prefixes. For a real class, have students copy their MAC's first 3 bytes into an online OUI lookup and confirm the maker.

---

## 5. Classroom Discussion Activity

- "You entered no username, no password. How did the network learn your device maker?"
- "Whose phone shows a **real** (non-randomized) MAC? What does that let a café chain do over months?"
- "Why is your MAC like a license plate for your device?"
- "The User-Agent lists your exact OS version. Why might an attacker love that?"

---

## 6. Defense / Awareness Takeaways

| Leak | Mitigation |
|---|---|
| Real MAC = permanent tracking ID | Enable **MAC randomization / Private Wi-Fi Address** per network |
| Device name reveals your identity | Rename devices to something generic |
| User-Agent exposes exact OS/browser | Keep software updated; known versions = known exploits |
| Auto-joining open networks | Disable auto-join for open Wi-Fi |

---

## 7. Common Issues

| Issue | Fix |
|---|---|
| MAC shows "unavailable" | Reload the page after fully connecting; the station list needs a moment |
| Vendor says "Unknown" | Expected — only a few OUIs are hardcoded; use an online OUI lookup |
| Page doesn't auto-open | Browse to `http://192.168.4.1` manually |
| Randomized shows the same each time | Some OSes keep a *stable-but-random* MAC per SSID — explain that nuance |

---

## 8. Student Checklist

- [ ] Connected and read their device's fingerprint with zero typing
- [ ] Toggled MAC randomization and saw the result change
- [ ] Looked up their MAC's real vendor via OUI
- [ ] Explained why a non-randomized MAC enables long-term tracking
- [ ] Wrote 2-3 settings to reduce their device's fingerprint
