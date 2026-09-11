// deauth_canary.ino
// Wi-Fi deauth/disassoc attack DETECTOR. Defensive — never transmits attacks.

#include <WiFi.h>
#include "esp_wifi.h"

#define LED_PIN 2
#define WINDOW_MS 1000     // measurement window
#define ALARM_THRESHOLD 5  // deauth/disassoc frames per window that = attack

volatile uint32_t deauthCount = 0;
uint32_t windowStart = 0;
int channel = 1;

void sniffer(void* buf, wifi_promiscuous_pkt_type_t type) {
  if (type != WIFI_PKT_MGMT) return;
  const wifi_promiscuous_pkt_t* pkt = (wifi_promiscuous_pkt_t*)buf;
  uint8_t subtype = (pkt->payload[0] & 0xF0) >> 4;
  // 12 = deauthentication, 10 = disassociation
  if (subtype == 12 || subtype == 10) deauthCount++;
}

void alarm(uint32_t frames) {
  Serial.printf("!!! DEAUTH ATTACK DETECTED !!!  %u frames in 1s (ch %d)\n",
                frames, channel);
  for (int i = 0; i < 10; i++) {         // fast panic blink
    digitalWrite(LED_PIN, HIGH); delay(40);
    digitalWrite(LED_PIN, LOW);  delay(40);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  Serial.println("\n=== Deauth Canary armed ===");
  Serial.println("Quietly watching for attacks...");

  WiFi.mode(WIFI_STA);
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_promiscuous_rx_cb(&sniffer);
  esp_wifi_set_channel(channel, WIFI_SECOND_CHAN_NONE);
  windowStart = millis();
}

void loop() {
  if (millis() - windowStart >= WINDOW_MS) {
    uint32_t c = deauthCount;
    deauthCount = 0;
    windowStart = millis();

    if (c >= ALARM_THRESHOLD) {
      alarm(c);
    } else {
      // slow heartbeat blink = "all clear, still watching"
      digitalWrite(LED_PIN, HIGH); delay(20); digitalWrite(LED_PIN, LOW);
      if (c > 0) Serial.printf("(quiet) %u mgmt disconnect frames on ch %d\n", c, channel);
    }

    // hop a channel each window to widen coverage
    channel = (channel % 11) + 1;
    esp_wifi_set_channel(channel, WIFI_SECOND_CHAN_NONE);
  }
}
