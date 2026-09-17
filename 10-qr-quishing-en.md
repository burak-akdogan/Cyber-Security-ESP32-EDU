# QR Quishing — Scan the Code, Join the Trap
### (ESP32 DevKit V1 only — no additional hardware)

> 🚨 **FOR EDUCATIONAL PURPOSES ONLY.** This lab is provided solely to teach cybersecurity awareness in a supervised classroom setting, with informed consent from everyone involved. Do not use these techniques against real people, devices, or networks without explicit authorization — doing so may violate computer-misuse, wiretapping, or other laws in your jurisdiction.

Lab 7 ("It Looked So Real") taught that a fake login page can fool you. This lab asks a sharper question: **what if you never even got the chance to notice the network's name before you joined it?** A printed QR code, scanned with a phone's camera, can auto-join a Wi-Fi network in one tap — skipping the exact moment (browsing the Wi-Fi list) where a suspicious name might have given it away. That's "quishing": QR-code phishing, and it's a real, growing attack — fake QR stickers have been found on parking meters, restaurant tables, and campus bulletin boards.

> **Design boundary:** This portal uses an **invented brand** ("CampusConnect"), not a clone of any real school system or company. It is realistic enough to feel plausible, generic enough that it can't be dropped into the wild as a working phishing page. Students enter **test data only**; nothing real is ever collected.

---

## ⚠️ Read This First: Ethical and Legal Framework

- **Consent + test data:** Announce the demo. Students type only fake data (`test@example.com` / `test123`). Never real passwords or emails — and never their real school credentials.
- **Fictional brand only:** The portal impersonates no real school, company, or product. Do not modify it to clone your actual school's Wi-Fi login — that turns an awareness demo into a live phishing tool and is illegal outside a lab.
- **Classroom only:** Run it in the room, on consenting devices, under supervision. The printed QR code should never leave the room or be posted anywhere students outside the demo could scan it.
- **The goal is awareness:** The realism of "scan for Wi-Fi" is the point — students learn that a QR code removes a safety check they didn't even know they were relying on.

---

## 1. Required Materials

- ESP32 DevKit V1
- Micro-USB data cable
- Arduino IDE with the ESP32 board package
- A way to print or display a QR code (phone/laptop screen is fine — no printer required)

Libraries (all bundled): `WiFi.h`, `DNSServer.h`, `WebServer.h`, `SPIFFS.h`

---

## 2. How It Works (Conceptual Overview)

1. The ESP32 opens an open AP (`CampusConnect_Library_WiFi`) and a captive DNS that redirects everything to itself — exactly like Lab 7.
2. **The difference is how students get there:** instead of opening Wi-Fi settings and picking a name, they scan a QR code encoding `WIFI:T:nopass;S:CampusConnect_Library_WiFi;;` — a standard format most phone cameras recognize and offer to auto-join.
3. The phone joins instantly and auto-opens the portal — a "verify your student account for Wi-Fi" page.
4. On submit, the ESP32 logs the (test) entry to SPIFFS and **replaces the page with a REVEAL** that leads with the QR-specific lesson: *you never even saw the network name.*

---

## 3. Generate the QR Code (one-time setup, before class)

The ESP32 has no display, so the QR code itself is generated separately and printed/shown in the room:

1. Flash the board first (Section 4) so you know the exact SSID it's broadcasting (it's `CampusConnect_Library_WiFi` by default — change it in the code if you like, just keep the QR code text matching).
2. Take this exact string to any free QR code generator (search "free QR code generator," paste the text, download the image):
   ```
   WIFI:T:nopass;S:CampusConnect_Library_WiFi;;
   ```
3. Print it, or display it on a laptop/tablet screen, somewhere visible in the room (a "table tent" or taped-up sheet works well — mimic how a real café or library might post one).
4. **Do not connect this QR code to your real classroom Wi-Fi** — it must only ever point at the ESP32's own fake network.

---

## 4. Full Code

```cpp
// qr_quishing.ino
// A captive portal reached by scanning a Wi-Fi QR code instead of picking a
// network by name -- the QR code auto-joins the phone, skipping the moment
// where a student would normally glance at the network name and hesitate.
// Classroom awareness demo -- consent required, test data only.

#include <WiFi.h>
#include <DNSServer.h>
#include <WebServer.h>
#include <SPIFFS.h>

// Fictional campus brand, not a real product -- matches the "WIFI:T:nopass;S:...;;"
// string printed in the lab guide for the QR code the class scans.
const char* ap_ssid = "CampusConnect_Library_WiFi";
DNSServer dnsServer;
WebServer webServer(80);
const byte DNS_PORT = 53;
IPAddress apIP(192, 168, 4, 1);

void logEvent(String info) {
  File f = SPIFFS.open("/log.txt", FILE_APPEND);
  if (f) { f.println(info); f.close(); }
  Serial.println(info);
}

String htmlEscape(String s) {
  s.replace("&", "&amp;");
  s.replace("<", "&lt;");
  s.replace(">", "&gt;");
  s.replace("\"", "&quot;");
  return s;
}

// --- Shared page styling: clean, "campus portal" feel ---
String css() {
  return
  "<style>"
  "*{box-sizing:border-box;margin:0;padding:0}"
  "body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;background:linear-gradient(135deg,#0f5132,#14a06a);"
  "min-height:100vh;display:flex;align-items:center;justify-content:center;padding:20px;color:#0f172a}"
  ".card{background:#fff;border-radius:16px;box-shadow:0 20px 60px rgba(0,0,0,.3);width:100%;max-width:380px;overflow:hidden}"
  ".head{background:#0f5132;color:#fff;padding:26px 24px;text-align:center}"
  ".logo{font-size:22px;font-weight:700;letter-spacing:.5px}"
  ".logo span{opacity:.85;font-weight:400}"
  ".sub{font-size:13px;opacity:.9;margin-top:4px}"
  ".body{padding:24px}"
  "h2{font-size:17px;margin-bottom:4px}"
  ".muted{color:#64748b;font-size:13px;margin-bottom:18px}"
  "label{display:block;font-size:12px;color:#475569;margin:12px 0 4px}"
  "input[type=text],input[type=password]{width:100%;padding:12px;border:1px solid #cbd5e1;border-radius:8px;font-size:15px}"
  "input:focus{outline:none;border-color:#0f5132}"
  ".terms{display:flex;align-items:flex-start;gap:8px;margin:16px 0;font-size:12px;color:#475569}"
  ".btn{width:100%;background:#0f5132;color:#fff;border:0;padding:13px;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;margin-top:6px}"
  ".btn:hover{background:#0b3d26}"
  ".foot{text-align:center;font-size:11px;color:#94a3b8;padding:14px}"
  ".reveal{padding:26px}"
  ".reveal h2{color:#b91c1c;font-size:20px;margin-bottom:10px}"
  ".flag{background:#fef2f2;border-left:4px solid #dc2626;padding:10px 12px;border-radius:6px;margin:10px 0;font-size:13px}"
  ".flag b{color:#b91c1c}"
  ".captured{background:#0f172a;color:#4ade80;font-family:ui-monospace,Consolas,monospace;padding:12px 14px;border-radius:8px;margin:12px 0 16px;font-size:13px;word-break:break-all}"
  ".captured b{color:#94a3b8;font-weight:400}"
  ".ok{background:#f0fdf4;border-left:4px solid #16a34a;padding:10px 12px;border-radius:6px;margin:14px 0;font-size:13px}"
  "a{color:#0f5132;text-decoration:none}"
  "</style>";
}

// --- The convincing "verify to get Wi-Fi" page ---
void handlePortal() {
  logEvent("PORTAL VIEW from " + webServer.client().remoteIP().toString());
  String h = "<!doctype html><html><head><meta charset='utf-8'>";
  h += "<meta name='viewport' content='width=device-width,initial-scale=1'>";
  h += "<title>CampusConnect WiFi</title>" + css() + "</head><body><div class='card'>";
  h += "<div class='head'><div class='logo'>Campus<span>Connect</span></div>";
  h += "<div class='sub'>Library Free Wi-Fi</div></div>";
  h += "<div class='body'><h2>Verify to continue</h2>";
  h += "<p class='muted'>Sign in with your student account to activate today's Wi-Fi access.</p>";
  h += "<form action='/submit' method='POST'>";
  h += "<label>Student email</label>";
  h += "<input type='text' name='username' placeholder='you@school.edu' required>";
  h += "<label>Student portal password</label>";
  h += "<input type='password' name='password' placeholder='Password' required>";
  h += "<div class='terms'><input type='checkbox' checked required>";
  h += "<span>I agree to the CampusConnect Acceptable Use Policy.</span></div>";
  h += "<button class='btn' type='submit'>Activate Wi-Fi</button></form></div>";
  h += "<div class='foot'>Powered by CampusConnect &middot; Scan &amp; Go</div>";
  h += "</div></body></html>";
  webServer.send(200, "text/html", h);
}

// --- The REVEAL, shown right after they "log in" ---
void handleSubmit() {
  String ip = webServer.client().remoteIP().toString();
  String user = webServer.arg("username");
  String pass = webServer.arg("password");
  // NOTE: this classroom demo only ever sees TEST data students type in --
  // never use a real account password here.
  logEvent("SUBMIT from " + ip + " | username=" + user + " | password=" + pass);

  String h = "<!doctype html><html><head><meta charset='utf-8'>";
  h += "<meta name='viewport' content='width=device-width,initial-scale=1'>";
  h += "<title>Reveal</title>" + css() + "</head><body><div class='card'><div class='reveal'>";
  h += "<h2>&#9888; That QR code was a trap.</h2>";
  h += "<p class='muted'>Scanning it joined you to a fake Wi-Fi network automatically, then handed "
       "your school login to a $5 microcontroller. Here's exactly what it captured:</p>";
  h += "<div class='captured'><b>username:</b> " + htmlEscape(user) + "<br><b>password:</b> " + htmlEscape(pass) + "</div>";
  h += "<p class='muted'>You never even picked this network by name -- the QR code did that for you. "
       "Here's what a normal Wi-Fi login almost never does:</p>";
  h += "<div class='flag'><b>1. You never saw the network name first.</b> Scanning a QR code can "
       "auto-join you before you'd ever notice something's off in a normal Wi-Fi list.</div>";
  h += "<div class='flag'><b>2. Anyone can print a QR code.</b> No hacking skill needed -- a sticker "
       "over a sticker, or a swapped flyer on a bulletin board, is enough to plant one.</div>";
  h += "<div class='flag'><b>3. It asked for your SCHOOL password.</b> Real Wi-Fi access almost never "
       "needs your full student-account password -- at most a one-time guest code.</div>";
  h += "<div class='flag'><b>4. No real HTTPS / no real domain.</b> The address was 192.168.4.1, not "
       "a domain you could look up or verify -- no padlock you can trust.</div>";
  h += "<div class='ok'><b>What to do:</b> Before scanning any Wi-Fi QR code, ask who put it there. "
       "Most phones let you preview a QR code's content before acting on it -- use that. Never enter "
       "a real account password into a Wi-Fi login screen.</div>";
  h += "<p class='muted'>This was a classroom demo -- only ever type <b>test</b> data into it. In a "
       "real attack, that captured password would now be in the attacker's hands, ready to use.</p>";
  h += "<p style='margin-top:14px'><a href='/'>&larr; See the fake page again</a></p>";
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
  Serial.println("CampusConnect portal up.");
  Serial.println("Print a QR code for: WIFI:T:nopass;S:CampusConnect_Library_WiFi;;");
  Serial.println("(any free QR generator works -- see the lab guide)");
}

void loop() {
  dnsServer.processNextRequest();
  webServer.handleClient();
}
```

> **Why it shows the actual (test) password:** the reveal screen prints exactly what was submitted, username and password both — that's the point of the lesson. This is safe specifically because everyone in the room agreed beforehand to type only fake/test data (`test@school.edu` / `test123`), never a real account password.

---

## 5. Setup and Test Steps

1. Upload the code and open the Serial Monitor at 115200 baud — it prints the exact QR text to generate.
2. Generate and display/print the QR code (Section 3) if you haven't already.
3. Have a student scan the QR code with their phone's camera — most phones show a "Join this network?" prompt.
4. Once joined, the portal opens automatically — note how normal "scan for Wi-Fi" already feels to most students.
5. Enter **test data** (`test@school.edu` / `test123`) and tap **Activate Wi-Fi**.
6. Read the **REVEAL** screen together — it leads with the QR-specific red flags; then visit `http://192.168.4.1/logs` to see the same entries logged.

---

## 6. Classroom Discussion Activity

- "Did you even look at the network name before you joined? Be honest."
- "Where have you seen 'scan this QR for Wi-Fi' signs in real life — cafés, hotels, your own school?"
- "How would you tell a real Wi-Fi QR code from a swapped-in fake one, without scanning it first?"
- "Why does a library never need your full student-account password just to give you internet?"

---

## 7. Defense / Awareness Takeaways

| Trust trap | Reality |
|---|---|
| "It's just a QR code, those are everywhere" | A QR code can point anywhere — scanning removes your normal chance to check the name first |
| "Scanning is faster than typing" | Speed is exactly what these lures are counting on |
| "It's free Wi-Fi, of course it wants my school login" | Free Wi-Fi never needs your full account password — a guest code, at most |
| "Someone official must have put this sign up" | Anyone can print and post a sticker or flyer — no technical skill required |

---

## 8. Common Issues

| Issue | Fix |
|---|---|
| Phone doesn't offer to auto-join from the QR code | Some older phones need a dedicated QR scanner app rather than the default camera; or connect to `CampusConnect_Library_WiFi` manually to demonstrate the portal itself |
| Portal doesn't auto-open after joining | Browse to `http://192.168.4.1` manually |
| Some phones show "no internet" and drop | Expected — there is no real internet; the portal still loads |
| `/logs` empty | Someone must submit the form first |

---

## 9. Student Checklist

- [ ] Scanned the QR code and noticed whether they checked the network name first
- [ ] Submitted **test data** and read the reveal
- [ ] Named at least one real-world place they've seen a "scan for Wi-Fi" sign
- [ ] Explained why a Wi-Fi login should never need a full school-account password
- [ ] Wrote 2-3 habits to avoid falling for a fake QR code
