// fingerprint_mirror.ino
// Shows a connecting device what it just revealed. Awareness, classroom use.

#include <WiFi.h>
#include <DNSServer.h>
#include <WebServer.h>
#include "esp_wifi.h"

const char* ap_ssid = "Free_Guest_WiFi";
DNSServer dns;
WebServer web(80);
const byte DNS_PORT = 53;
IPAddress apIP(192,168,4,1);

// A few well-known OUI prefixes for the vendor guess (extend as you like)
String vendorFor(const String& mac) {
  String p = mac.substring(0,8); p.toUpperCase();
  if (p.startsWith("F0:18:98") || p.startsWith("A4:83:E7") || p.startsWith("DC:2B:2A")) return "Apple";
  if (p.startsWith("3C:5A:B4") || p.startsWith("F8:8F:CA")) return "Google";
  if (p.startsWith("00:1A:11")) return "Google";
  if (p.startsWith("50:8F:4C") || p.startsWith("AC:37:43")) return "Samsung/HTC";
  if (p.startsWith("B8:27:EB") || p.startsWith("DC:A6:32")) return "Raspberry Pi";
  return "Unknown (look up the OUI!)";
}

// Locally-administered bit set in first octet => randomized MAC
bool isRandomized(const String& mac) {
  int firstByte = strtol(mac.substring(0,2).c_str(), NULL, 16);
  return (firstByte & 0x02) != 0;
}

// Find the MAC of the connected station by its IP (from the softAP client list)
String macForClient() {
  wifi_sta_list_t stations;
  esp_wifi_ap_get_sta_list(&stations);
  if (stations.num > 0) {
    // Best-effort: return the most recently seen station
    uint8_t* m = stations.sta[stations.num - 1].mac;
    char buf[18];
    sprintf(buf, "%02X:%02X:%02X:%02X:%02X:%02X", m[0],m[1],m[2],m[3],m[4],m[5]);
    return String(buf);
  }
  return "unavailable";
}

void handlePortal() {
  String mac = macForClient();
  String vendor = (mac == "unavailable") ? "unavailable" : vendorFor(mac);
  String rnd = (mac == "unavailable") ? "?" :
               (isRandomized(mac) ? "YES (privacy on \xF0\x9F\x91\x8D)" : "NO (real, trackable!)");
  String ua = web.header("User-Agent");
  if (ua == "") ua = "(not sent)";

  String h = "<html><head><meta name='viewport' content='width=device-width,initial-scale=1'>";
  h += "<style>body{font-family:sans-serif;max-width:480px;margin:24px auto;padding:0 14px}";
  h += "td{padding:6px;border-bottom:1px solid #eee;vertical-align:top}";
  h += ".k{color:#666;width:38%}.v{font-family:monospace}</style></head><body>";
  h += "<h2>\xF0\x9F\xAA\x9E You didn't type anything...</h2>";
  h += "<p>...yet just by connecting, your device already told this network:</p><table>";
  h += "<tr><td class='k'>Your MAC address</td><td class='v'>" + mac + "</td></tr>";
  h += "<tr><td class='k'>Device maker (from MAC)</td><td class='v'>" + vendor + "</td></tr>";
  h += "<tr><td class='k'>MAC randomized?</td><td class='v'>" + rnd + "</td></tr>";
  h += "<tr><td class='k'>Your device / browser</td><td class='v'>" + ua + "</td></tr>";
  h += "</table>";
  h += "<p style='font-size:13px;color:#a00'>If \"randomized\" says NO, this exact address can be";
  h += " recognized every time you join any network — a permanent tracking ID.</p>";
  h += "<p style='font-size:12px;color:gray'>Classroom awareness demo. Nothing is stored.</p>";
  h += "</body></html>";
  web.send(200, "text/html", h);
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_AP);
  WiFi.softAP(ap_ssid);
  dns.start(DNS_PORT, "*", apIP);

  const char* headers[] = {"User-Agent"};
  web.collectHeaders(headers, 1);
  web.onNotFound(handlePortal);
  web.on("/", handlePortal);
  web.begin();
  Serial.println("Fingerprint Mirror AP up. SSID: Free_Guest_WiFi");
}

void loop() {
  dns.processNextRequest();
  web.handleClient();
}
