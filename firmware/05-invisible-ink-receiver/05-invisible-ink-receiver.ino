// covert_receiver.ino
// Scans for MSG| SSIDs and reassembles the hidden message.

#include <WiFi.h>

const char* PREFIX = "MSG|";
String parts[64];
bool got[64];
int expectedTotal = -1;

void reset() {
  for (int i = 0; i < 64; i++) { parts[i] = ""; got[i] = false; }
  expectedTotal = -1;
}

bool complete() {
  if (expectedTotal <= 0) return false;
  for (int i = 0; i < expectedTotal; i++) if (!got[i]) return false;
  return true;
}

void printMessage() {
  String msg = "";
  for (int i = 0; i < expectedTotal; i++) msg += parts[i];
  Serial.println("\n================ DECODED SECRET ================");
  Serial.println(msg);
  Serial.println("===============================================\n");
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  reset();
  Serial.println("Listening for hidden SSIDs...");
}

void loop() {
  int n = WiFi.scanNetworks();
  for (int i = 0; i < n; i++) {
    String s = WiFi.SSID(i);
    if (!s.startsWith(PREFIX)) continue;

    // Parse MSG|<total>|<index>|<payload>
    int p1 = s.indexOf('|');
    int p2 = s.indexOf('|', p1 + 1);
    int p3 = s.indexOf('|', p2 + 1);
    if (p1 < 0 || p2 < 0 || p3 < 0) continue;

    int tot = s.substring(p1 + 1, p2).toInt();
    int idx = s.substring(p2 + 1, p3).toInt();
    String payload = s.substring(p3 + 1);

    if (expectedTotal == -1) expectedTotal = tot;
    if (idx >= 0 && idx < 64 && !got[idx]) {
      parts[idx] = payload;
      got[idx] = true;
      Serial.printf("Captured chunk %d/%d: \"%s\"\n", idx + 1, tot, payload.c_str());
    }
  }
  WiFi.scanDelete();

  if (complete()) {
    printMessage();
    reset();          // reset to catch the next full loop
    delay(3000);
  } else {
    // console heartbeat every ~5s so it's clear the receiver is still scanning
    static unsigned long lastHeartbeat = 0;
    if (millis() - lastHeartbeat >= 5000) {
      lastHeartbeat = millis();
      Serial.println("... still scanning for hidden SSIDs");
    }
  }
  delay(500);
}
