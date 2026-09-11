// deauth_storm_self_target.ino
// Sends REAL 802.11 deauthentication frames — but ONLY at clients connected
// to this ESP32's own throwaway test AP. Pairs with the Deauth Canary (lab 02).
// Classroom awareness demo — consent required, self-owned test AP only.
// Do not repoint this at a network you do not own; see the guide's ethics section.

#include <WiFi.h>
#include "esp_wifi.h"
#include <string.h>

const char* ap_ssid = "Deauth_Test_Target"; // this board's own disposable test AP

uint8_t deauthFrame[26] = {
  0xC0, 0x00, 0x00, 0x00,               // mgmt frame, subtype 12 (deauthentication)
  0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF,   // destination -> filled per client, at runtime
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,   // source -> filled with THIS AP's own MAC
  0x00, 0x00, 0x00, 0x00, 0x00, 0x00,   // BSSID  -> filled with THIS AP's own MAC
  0x00, 0x00,                           // sequence/fragment number
  0x07, 0x00                            // reason code 7: class 3 frame from nonassociated STA
};

unsigned long lastBurst = 0;
const unsigned long BURST_EVERY_MS = 6000;

void sendDeauthTo(const uint8_t* clientMac, const uint8_t* apMac) {
  memcpy(&deauthFrame[4], clientMac, 6);
  memcpy(&deauthFrame[10], apMac, 6);
  memcpy(&deauthFrame[16], apMac, 6);
  for (int i = 0; i < 6; i++) {           // a short burst, not a continuous flood
    esp_wifi_80211_tx(WIFI_IF_AP, deauthFrame, sizeof(deauthFrame), false);
    delay(10);
  }
}

void setup() {
  Serial.begin(115200);
  delay(300);
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ap_ssid); // open network, no internet — same pattern as the other open-AP labs

  uint8_t apMac[6];
  esp_wifi_get_mac(WIFI_IF_AP, apMac);
  Serial.printf("\n=== Deauth Storm armed on \"%s\" ===\n", ap_ssid);
  Serial.println("Connect a phone to this AP, then watch it get kicked every few seconds.");
  Serial.println("This ONLY targets devices connected to THIS test AP — nothing else.\n");
}

void loop() {
  if (millis() - lastBurst < BURST_EVERY_MS) return;
  lastBurst = millis();

  uint8_t apMac[6];
  esp_wifi_get_mac(WIFI_IF_AP, apMac);

  wifi_sta_list_t stationList;
  esp_wifi_ap_get_sta_list(&stationList);

  if (stationList.num == 0) {
    Serial.println("(no phone connected yet — join the test AP to see the kick)");
    return;
  }

  for (int i = 0; i < stationList.num; i++) {
    uint8_t* m = stationList.sta[i].mac;
    Serial.printf(">>> Sending deauth burst to %02X:%02X:%02X:%02X:%02X:%02X (our own test AP client)\n",
                  m[0], m[1], m[2], m[3], m[4], m[5]);
    sendDeauthTo(m, apMac);
  }
}
