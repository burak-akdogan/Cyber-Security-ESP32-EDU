# "It Looked So Real" — A Convincing Captive Portal, Then the Reveal
### (ESP32 DevKit V1 only — no additional hardware)

> 🚨 **FOR EDUCATIONAL PURPOSES ONLY.** This lab is provided solely to teach cybersecurity awareness in a supervised classroom setting, with informed consent from everyone involved. Do not use these techniques against real people, devices, or networks without explicit authorization — doing so may violate computer-misuse, wiretapping, or other laws in your jurisdiction.

Real Wi-Fi login pages at airports, hotels, and cafés look polished and professional — which is exactly why fake ones fool people. This lab builds a **realistic, good-looking captive portal** for a **fictional brand** ("SkyLink Free WiFi") so students feel how natural it is to type in. Then, the instant they submit, the page **flips into a REVEAL screen**: *"That was fake. Here's exactly how you could have known."*

The power of this lab is the moment between "this looks legit" and "...oh no."

> **Design boundary:** This portal uses an **invented brand**, not a clone of any real company (no Google/Instagram/school logos or exact copies). It is polished enough to feel real, generic enough that it can't be dropped into the wild as a working phishing page against a real service. Students enter **test data only**; nothing real is ever collected.

---

## ⚠️ Read This First: Ethical and Legal Framework

- **Consent + test data:** Announce the demo. Students type only fake data (`test / test123`). Never real passwords or emails.
- **Fictional brand only:** The portal impersonates no real company. Do not modify it to clone a real brand's login — that turns an awareness demo into a live phishing tool and is illegal outside a lab.
- **Classroom only:** Run it in the room, on consenting devices, under supervision.
- **The goal is awareness:** The realistic look is the point — students learn that "professional-looking" is not "safe."

---

## 1. Required Materials

- ESP32 DevKit V1
- Micro-USB data cable
- Arduino IDE with the ESP32 board package

Libraries (all bundled): `WiFi.h`, `DNSServer.h`, `WebServer.h`, `SPIFFS.h`

---

## 2. How It Works (Conceptual Overview)

1. The ESP32 opens an open AP (`SkyLink_Free_WiFi`) and a captive DNS that redirects everything to itself
2. The phone auto-opens the portal — a clean, modern "Connect to Free Wi-Fi" page
3. It looks trustworthy: brand name, terms checkbox, "Powered by SkyLink Networks", a realistic layout
4. On submit, the ESP32 logs the (test) entry to SPIFFS and **replaces the page with a REVEAL**
5. The reveal walks through the exact clues that gave the fake away — right on the page they just trusted

---

## 3. Full Code

```cpp
// realistic_portal_reveal.ino
// Realistic (fictional-brand) captive portal that reveals itself after submit.
// Classroom awareness demo — consent required, test data only.

#include <WiFi.h>
#include <DNSServer.h>
#include <WebServer.h>
#include <SPIFFS.h>

const char* ap_ssid = "SkyLink_Free_WiFi";   // fictional brand, not a real company
DNSServer dnsServer;
WebServer webServer(80);
const byte DNS_PORT = 53;
IPAddress apIP(192, 168, 4, 1);

void logEvent(String info) {
  File f = SPIFFS.open("/log.txt", FILE_APPEND);
  if (f) { f.println(info); f.close(); }
  Serial.println(info);
}

// --- Shared page styling: clean, modern, "real enough" ---
String css() {
  return
  "<style>"
  "*{box-sizing:border-box;margin:0;padding:0}"
  "body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:linear-gradient(135deg,#1e3a8a,#2563eb);"
  "min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;color:#0f172a}"
  ".card{background:#fff;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,.3);width:100%;max-width:380px;overflow:hidden}"
  ".head{background:#2563eb;color:#fff;padding:26px 24px;text-align:center}"
  ".logo{font-size:22px;font-weight:700;letter-spacing:.5px}"
  ".logo span{opacity:.85;font-weight:400}"
  ".sub{font-size:13px;opacity:.9;margin-top:4px}"
  ".body{padding:24px}"
  "h2{font-size:17px;margin-bottom:4px}"
  ".muted{color:#64748b;font-size:13px;margin-bottom:18px}"
  "label{display:block;font-size:12px;color:#475569;margin:12px 0 4px}"
  "input[type=text],input[type=password]{width:100%;padding:12px;border:1px solid #cbd5e1;border-radius:8px;font-size:15px}"
  "input:focus{outline:none;border-color:#2563eb}"
  ".terms{display:flex;align-items:flex-start;gap:8px;margin:16px 0;font-size:12px;color:#475569}"
  ".btn{width:100%;background:#2563eb;color:#fff;border:0;padding:13px;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;margin-top:6px}"
  ".btn:hover{background:#1d4ed8}"
  ".foot{text-align:center;font-size:11px;color:#94a3b8;padding:14px}"
  ".reveal{padding:26px}"
  ".reveal h2{color:#b91c1c;font-size:20px;margin-bottom:10px}"
  ".flag{background:#fef2f2;border-left:4px solid #dc2626;padding:10px 12px;border-radius:6px;margin:10px 0;font-size:13px}"
  ".flag b{color:#b91c1c}"
  ".ok{background:#f0fdf4;border-left:4px solid #16a34a;padding:10px 12px;border-radius:6px;margin:14px 0;font-size:13px}"
  "a{color:#2563eb;text-decoration:none}"
  "</style>";
}

// --- The convincing login page ---
void handlePortal() {
  logEvent("PORTAL VIEW from " + webServer.client().remoteIP().toString());
  String h = "<!doctype html><html><head><meta charset='utf-8'>";
  h += "<meta name='viewport' content='width=device-width,initial-scale=1'>";
  h += "<title>SkyLink Free WiFi</title>" + css() + "</head><body><div class='card'>";
  h += "<div class='head'><div class='logo'>Sky<span>Link</span></div>";
  h += "<div class='sub'>Complimentary High-Speed Internet</div></div>";
  h += "<div class='body'><h2>Sign in to continue</h2>";
  h += "<p class='muted'>Connect with your account to access free Wi-Fi.</p>";
  h += "<form action='/submit' method='POST'>";
  h += "<label>Email or username</label>";
  h += "<input type='text' name='username' placeholder='you@example.com' required>";
  h += "<label>Password</label>";
  h += "<input type='password' name='password' placeholder='Password' required>";
  h += "<div class='terms'><input type='checkbox' checked required>";
  h += "<span>I agree to the SkyLink Terms of Service and Acceptable Use Policy.</span></div>";
  h += "<button class='btn' type='submit'>Connect to Wi-Fi</button></form></div>";
  h += "<div class='foot'>Powered by SkyLink Networks · Secure Connection</div>";
  h += "</div></body></html>";
  webServer.send(200, "text/html", h);
}

// --- The REVEAL, shown right after they "log in" ---
void handleSubmit() {
  String ip = webServer.client().remoteIP().toString();
  String user = webServer.arg("username");
  // NOTE: only test data should ever reach this point.
  logEvent("SUBMIT from " + ip + " | username=" + user + " | (password length only: "
           + String(webServer.arg("password").length()) + ")");

  String h = "<!doctype html><html><head><meta charset='utf-8'>";
  h += "<meta name='viewport' content='width=device-width,initial-scale=1'>";
  h += "<title>Reveal</title>" + css() + "</head><body><div class='card'><div class='reveal'>";
  h += "<h2>⚠ That was a FAKE Wi-Fi login.</h2>";
  h += "<p class='muted'>You just handed your credentials to a $5 microcontroller. "
       "In a real attack, they'd be gone. Here's how you could have known:</p>";
  h += "<div class='flag'><b>1. It's an OPEN network.</b> \"Free WiFi\" with no password means "
       "anyone can run it — including an attacker.</div>";
  h += "<div class='flag'><b>2. A login page popped up on its own.</b> Legit free Wi-Fi rarely asks "
       "for your <i>email account</i> password — only its own guest code, if anything.</div>";
  h += "<div class='flag'><b>3. No real HTTPS / no real domain.</b> The address was 192.168.4.1, "
       "not a company you can verify. No padlock you can trust.</div>";
  h += "<div class='flag'><b>4. It asked for a password it never needs.</b> Why would airport Wi-Fi "
       "need your <i>email</i> password to give you internet?</div>";
  h += "<div class='ok'><b>What to do:</b> Never enter real account passwords into a Wi-Fi login. "
       "Turn off auto-join for open networks. Use mobile data + a VPN for anything sensitive.</div>";
  h += "<p class='muted'>This was a classroom demo. Your password was <b>not</b> stored — "
       "only its length, to prove the point.</p>";
  h += "<p style='margin-top:14px'><a href='/'>← See the fake page again</a></p>";
  h += "</div></div></body></html>";
  webServer.send(200, "text/html", h);
}

void handleLogs() {
  File f = SPIFFS.open("/log.txt", FILE_READ);
  String content = "No logs yet.";
  if (f) { content = f.readString(); f.close(); }
  webServer.send(200, "text/plain", content);
}

void setup() {
  Serial.begin(115200);
  SPIFFS.begin(true);
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ap_ssid);
  dnsServer.start(DNS_PORT, "*", apIP);
  webServer.onNotFound(handlePortal);
  webServer.on("/", handlePortal);
  webServer.on("/submit", HTTP_POST, handleSubmit);
  webServer.on("/logs", handleLogs);
  webServer.begin();
  logEvent("=== New session started ===");
  Serial.println("SkyLink portal up. Connect to 'SkyLink_Free_WiFi'.");
}

void loop() {
  dnsServer.processNextRequest();
  webServer.handleClient();
}
```

> **Privacy choice built into the code:** on submit it logs only the **username (test data)** and the **length** of the password — never the password itself. This keeps the demo honest even if a student forgets and types something real.

---

## 4. Setup and Test Steps

1. Upload the code and open the Serial Monitor at 115200 baud
2. Connect a phone to `SkyLink_Free_WiFi` (open network)
3. The polished portal opens automatically — note how *normal* it feels
4. Enter **test data** (`test@example.com / test123`) and tap **Connect to Wi-Fi**
5. Read the **REVEAL** screen together; then visit `http://192.168.4.1/logs` to show what was (and wasn't) captured

---

## 5. Classroom Discussion Activity

- "Before the reveal — on a scale of 1–10, how legit did it look? What sold it?"
- "Which of the four red flags would you actually have noticed in a rush at an airport?"
- "Why does a real free Wi-Fi almost never need your *email* password?"
- "The design took 10 minutes to make. What does that tell you about trusting how a page *looks*?"

---

## 6. Defense / Awareness Takeaways

| Trust trap | Reality |
|---|---|
| "It looks professional, so it's safe" | Anyone can copy a clean design in minutes |
| "The login page appeared, so I should sign in" | Unexpected login pages are a warning, not an instruction |
| "It's free Wi-Fi, of course it needs my account" | Free Wi-Fi never needs your email/bank password |
| "I'm in a hurry, it's probably fine" | Rushing is exactly what these pages count on |

---

## 7. Common Issues

| Issue | Fix |
|---|---|
| Portal doesn't auto-open | Browse to `http://192.168.4.1` manually |
| Some phones show "no internet" and drop | Expected — there is no real internet; the portal still loads |
| Page looks unstyled | Ensure the whole `css()` string uploaded; check Serial for errors |
| `/logs` empty | Someone must submit the form first |

---

## 8. Student Checklist

- [ ] Connected to the open portal and rated how real it looked
- [ ] Submitted **test data** and read the reveal
- [ ] Listed which red flags they'd realistically catch in real life
- [ ] Explained why free Wi-Fi shouldn't need an email password
- [ ] Wrote 2-3 habits to avoid falling for a fake login
