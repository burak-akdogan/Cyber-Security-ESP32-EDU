// ctf-network-scanner.ino
// Classroom CTF tool: joins the event Wi-Fi and finds the target Raspberry
// Pi itself -- no Target IP is given up front. Scans the rest of the local
// /24 subnet for port 8080 and confirms it's really the CTF dashboard
// (not just some other device that happens to have a port open) before
// reporting it. See CLASSROOM-CTF-EVENT-en.md for the full exercise.

#include <WiFi.h>
#include <HTTPClient.h>

String targetSsid, targetPass;
bool connected = false;

void printMenu() {
  Serial.println("\nType 'scan' to search the network again, or 'menu' to see this.");
}

// A TCP connect alone isn't proof -- some other device on the LAN could
// coincidentally have something listening on 8080. Confirm it's really
// the Pi by checking the dashboard's own page for a distinctive string.
bool looksLikeTarget(IPAddress ip) {
  WiFiClient probe;
  probe.setTimeout(250);
  bool open = probe.connect(ip, 8080);
  probe.stop();
  if (!open) return false;

  HTTPClient http;
  http.setTimeout(1500);
  http.begin("http://" + ip.toString() + ":8080/");
  int code = http.GET();
  bool ok = false;
  if (code == 200) {
    ok = http.getString().indexOf("Classroom CTF") >= 0;
  }
  http.end();
  return ok;
}

void scanSubnet() {
  IPAddress myIP = WiFi.localIP();
  Serial.printf("\nMy IP: %s -- scanning the rest of this network for the target...\n", myIP.toString().c_str());
  Serial.println("(this can take a minute or two -- one dot printed per 10 addresses tried)");

  bool found = false;
  for (int host = 1; host <= 254 && !found; host++) {
    IPAddress candidate(myIP[0], myIP[1], myIP[2], host);
    if (candidate == myIP) continue;

    if (looksLikeTarget(candidate)) {
      found = true;
      Serial.println("\n\n=== FOUND THE TARGET ===");
      Serial.printf(">>> Target IP: %s <<<\n", candidate.toString().c_str());
      Serial.println("*** NOTE THIS DOWN -- you'll need to type this exact IP as the");
      Serial.println("*** \"Target IP\" for every other CTF tool (Recon Scanner, Flag");
      Serial.println("*** Prober, DDoS Flood, Cyber Town). It won't be shown to you again. ***");
      break;
    }
    if (host % 10 == 0) Serial.print(".");
  }

  if (!found) {
    Serial.println("\nNo target found on this network. Make sure the Raspberry Pi is");
    Serial.println("powered on and running app.py, then type 'scan' to try again.");
  }
  printMenu();
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
  scanSubnet();
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== CTF Network Scanner -- find the target yourself ===");
  Serial.println("Send: SSID,PASSWORD");
  Serial.println("(the flashing page's \"Send to Board\" form does this for you)");
}

void loop() {
  if (!Serial.available()) return;
  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) return;

  if (!connected) {
    int c1 = line.indexOf(',');
    if (c1 > 0) {
      targetSsid = line.substring(0, c1);
      targetPass = line.substring(c1 + 1);
      connectToWifi();
    } else {
      Serial.println("Expected format: SSID,PASSWORD");
    }
  } else if (line.equalsIgnoreCase("scan")) {
    scanSubnet();
  } else if (line.equalsIgnoreCase("menu")) {
    printMenu();
  } else {
    Serial.println("Type 'scan' to search again.");
  }
}
