// ghost_of_networks.ino
// Passive probe-request "confession wall" — privacy awareness, classroom use only.

#include <WiFi.h>
#include "esp_wifi.h"

#define MAX_NAMES 60
String heard[MAX_NAMES];
int count = 0;
int channel = 1;

bool alreadyHeard(const String& s) {
  for (int i = 0; i < count; i++) if (heard[i] == s) return true;
  return false;
}

void addName(const String& s) {
  if (s.length() == 0 || alreadyHeard(s)) return;
  if (count < MAX_NAMES) {
    heard[count++] = s;
    Serial.printf("[%2d] A phone here remembers: \"%s\"\n", count, s.c_str());
  }
}

// Called for every sniffed frame
void sniffer(void* buf, wifi_promiscuous_pkt_type_t type) {
  if (type != WIFI_PKT_MGMT) return;
  const wifi_promiscuous_pkt_t* pkt = (wifi_promiscuous_pkt_t*)buf;
  const uint8_t* p = pkt->payload;

  // 802.11 management frame subtype 4 = Probe Request
  uint8_t frameSubtype = (p[0] & 0xF0) >> 4;
  if (frameSubtype != 4) return;

  // Tagged params start at byte 24; first tag (0) is the SSID
  const uint8_t* tag = p + 24;
  if (tag[0] != 0) return;          // tag number 0 = SSID
  uint8_t len = tag[1];
  if (len == 0 || len > 32) return; // 0 = wildcard/broadcast probe, skip

  String ssid = "";
  for (int i = 0; i < len; i++) ssid += (char)tag[2 + i];
  addName(ssid);
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n=== Ghost of Networks Past ===");
  Serial.println("Listening for the network names phones broadcast...\n");

  WiFi.mode(WIFI_STA);
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_promiscuous_rx_cb(&sniffer);
  esp_wifi_set_channel(channel, WIFI_SECOND_CHAN_NONE);
}

void loop() {
  // Hop channels so we hear phones across the 2.4 GHz band
  delay(400);
  channel = (channel % 13) + 1;
  esp_wifi_set_channel(channel, WIFI_SECOND_CHAN_NONE);
}
