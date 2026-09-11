// covert_sender.ino
// Encodes a secret message into rotating SSID broadcasts.

#include <WiFi.h>

const char* SECRET = "Meet at 3pm. Code is 7412."; // message to smuggle
const char* PREFIX = "MSG";
const int CHUNK = 8;           // characters per SSID chunk
String ssids[64];
int total = 0;

void buildChunks() {
  String msg = String(SECRET);
  int n = (msg.length() + CHUNK - 1) / CHUNK;
  total = n;
  for (int i = 0; i < n; i++) {
    String part = msg.substring(i * CHUNK, min((int)msg.length(), (i+1)*CHUNK));
    char idx[3]; sprintf(idx, "%02d", i);
    // Format: MSG|<total>|<index>|<payload>
    ssids[i] = String(PREFIX) + "|" + String(total) + "|" + idx + "|" + part;
  }
}

void setup() {
  Serial.begin(115200);
  buildChunks();
  WiFi.mode(WIFI_AP);
  Serial.printf("Broadcasting %d secret chunks in a loop...\n", total);
}

void loop() {
  for (int i = 0; i < total; i++) {
    WiFi.softAP(ssids[i].c_str());      // broadcast this chunk as an SSID
    Serial.printf("Beaconing: %s\n", ssids[i].c_str());
    delay(1500);                        // hold long enough for a scan to catch it
    WiFi.softAPdisconnect(true);
    delay(150);
  }
}
