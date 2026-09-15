// ctf_recon_scanner.ino
// Classroom CTF tool: connects to the event Wi-Fi and reports which common
// ports and paths respond on the target Raspberry Pi -- the "where do I
// even start" recon step. Read-only observation, no exploitation.
// See CLASSROOM-CTF-EVENT-en.md for the full exercise this supports.

#include <WiFi.h>
#include <HTTPClient.h>

String targetSsid, targetPass, targetIP;
bool provisioned = false;

const int PORTS[] = {22, 80, 443, 8080};
const int NUM_PORTS = sizeof(PORTS) / sizeof(PORTS[0]);

const char* PATHS[] = {
  "/", "/login", "/hidden", "/backup.zip",
  "/api/note?id=1", "/api/divide?a=1&b=1", "/api/ping?host=test"
};
const int NUM_PATHS = sizeof(PATHS) / sizeof(PATHS[0]);

// Forgives common copy/paste mistakes in the Target IP field, e.g.
// "http://10.42.0.1/" or "10.42.0.1:8080" -- both would otherwise get
// mangled when we build "http://" + targetIP + ":8080..." below.
String sanitizeTargetIP(String ip) {
  ip.trim();
  int schemeEnd = ip.indexOf("://");
  if (schemeEnd >= 0) ip = ip.substring(schemeEnd + 3);
  int slash = ip.indexOf('/');
  if (slash >= 0) ip = ip.substring(0, slash);
  if (ip.endsWith(":8080")) ip = ip.substring(0, ip.length() - 5);
  return ip;
}

void scanPorts() {
  Serial.println("\n--- Port scan ---");
  for (int i = 0; i < NUM_PORTS; i++) {
    WiFiClient client;
    client.setTimeout(1000);
    bool open = client.connect(targetIP.c_str(), PORTS[i]);
    Serial.printf("  port %-5d %s\n", PORTS[i], open ? "OPEN" : "closed");
    client.stop();
  }
}

void scanPaths() {
  Serial.println("\n--- HTTP path scan ---");
  for (int i = 0; i < NUM_PATHS; i++) {
    HTTPClient http;
    String url = "http://" + targetIP + ":8080" + String(PATHS[i]);
    http.begin(url);
    int code = http.GET();
    Serial.printf("  %-28s -> %d\n", PATHS[i], code);
    http.end();
    delay(150);
  }
}

void connectAndScan() {
  Serial.printf("\nConnecting to \"%s\" ...\n", targetSsid.c_str());
  WiFi.mode(WIFI_STA);
  WiFi.begin(targetSsid.c_str(), targetPass.c_str());

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
    delay(300);
    Serial.print(".");
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nCouldn't connect -- check the network name/password and send it again.");
    return;
  }

  Serial.printf("\nConnected. Scanning target %s ...\n", targetIP.c_str());
  scanPorts();
  scanPaths();
  Serial.println("\n--- Scan complete ---");
  Serial.println("Now try the Flag Prober tool, or explore one of these paths yourself.");
  provisioned = true;
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== CTF Recon Scanner ===");
  Serial.println("Send: SSID,PASSWORD,TARGET_IP");
  Serial.println("(the flashing page's \"Send to Board\" form does this for you)");
}

void loop() {
  if (!provisioned && Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    int c1 = line.indexOf(',');
    int c2 = line.indexOf(',', c1 + 1);
    if (c1 > 0 && c2 > c1) {
      targetSsid = line.substring(0, c1);
      targetPass = line.substring(c1 + 1, c2);
      targetIP = sanitizeTargetIP(line.substring(c2 + 1));
      connectAndScan();
    } else {
      Serial.println("Expected format: SSID,PASSWORD,TARGET_IP");
    }
  }
}
