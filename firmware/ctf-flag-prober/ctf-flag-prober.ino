// ctf_flag_prober.ino
// Classroom CTF tool: an interactive Serial console for probing the target
// Raspberry Pi one challenge at a time. Nothing runs automatically -- pick a
// challenge from the menu, type a command, read the response, and try again
// with a different guess. No coding, just typed commands.
// See CLASSROOM-CTF-EVENT-en.md for the full exercise.

#include <WiFi.h>
#include <HTTPClient.h>

String targetSsid, targetPass, targetIP;
bool connected = false;

String base() {
  return "http://" + targetIP + ":8080";
}

void printResponse(int code, const String& body) {
  Serial.printf("  HTTP %d:\n", code);
  Serial.println(body);
  int start = body.indexOf("FLAG{");
  if (start >= 0) {
    int end = body.indexOf('}', start);
    String flag = (end > start) ? body.substring(start, end + 1) : body.substring(start);
    Serial.printf("  >>> FOUND: %s\n", flag.c_str());
  }
}

void printMenu() {
  Serial.println("\n=== CTF Challenges -- type a command and press Enter ===");
  Serial.println("  1 user:pass   Default/weak credentials -- search: common admin/router default passwords");
  Serial.println("  2 path        Hidden page -- guess a page name (search: common admin/secret page names)");
  Serial.println("  3 id          Broken access control (IDOR) -- try a few different numbers");
  Serial.println("  4 filename    Leftover files -- guess a filename (search: common backup file names)");
  Serial.println("  5 a b         Oversharing errors -- try some edge-case number pairs, e.g. 5 10 0");
  Serial.println("  6             Missing authentication");
  Serial.println("  7 payload     Untrusted input (hardest) -- what belongs in a \"host\" field?");
  Serial.println("  menu          Show this list again");
  Serial.println("===========================================================");
}

void challenge1(const String& arg) {
  int sep = arg.indexOf(':');
  if (sep < 0) { Serial.println("  Usage: 1 username:password"); return; }
  HTTPClient http;
  http.begin(base() + "/login");
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");
  int code = http.POST("username=" + arg.substring(0, sep) + "&password=" + arg.substring(sep + 1));
  printResponse(code, http.getString());
  http.end();
}

void challenge2(const String& arg) {
  if (arg.length() == 0) { Serial.println("  Usage: 2 <path>  (guess a hidden page name, e.g. 2 admin)"); return; }
  HTTPClient http;
  http.begin(base() + "/" + arg);
  int code = http.GET();
  printResponse(code, http.getString());
  http.end();
}

void challenge3(const String& arg) {
  if (arg.length() == 0) { Serial.println("  Usage: 3 <id>  (try a few different numbers)"); return; }
  HTTPClient http;
  http.begin(base() + "/api/note?id=" + arg);
  int code = http.GET();
  printResponse(code, http.getString());
  http.end();
}

void challenge4(const String& arg) {
  if (arg.length() == 0) { Serial.println("  Usage: 4 <filename>  (guess a leftover file name, e.g. 4 backup.zip)"); return; }
  HTTPClient http;
  http.begin(base() + "/" + arg);
  int code = http.GET();
  printResponse(code, http.getString());
  http.end();
}

void challenge5(const String& arg) {
  int sp = arg.indexOf(' ');
  if (sp < 0) { Serial.println("  Usage: 5 <a> <b>  (try some edge-case numbers, e.g. 5 10 0)"); return; }
  String a = arg.substring(0, sp);
  String b = arg.substring(sp + 1);
  b.trim();
  HTTPClient http;
  http.begin(base() + "/api/divide?a=" + a + "&b=" + b);
  int code = http.GET();
  printResponse(code, http.getString());
  http.end();
}

void challenge6() {
  HTTPClient http;
  http.begin(base() + "/api/admin/reset");
  int code = http.POST("");
  printResponse(code, http.getString());
  http.end();
}

void challenge7(const String& arg) {
  if (arg.length() == 0) { Serial.println("  Usage: 7 <payload>  (what belongs in a \"host\" field?)"); return; }
  HTTPClient http;
  http.begin(base() + "/api/ping?host=" + arg);
  int code = http.GET();
  printResponse(code, http.getString());
  http.end();
}

void handleCommand(String line) {
  line.trim();
  if (line.length() == 0) return;
  if (line.equalsIgnoreCase("menu")) { printMenu(); return; }

  int sp = line.indexOf(' ');
  String cmd = sp < 0 ? line : line.substring(0, sp);
  String arg = sp < 0 ? "" : line.substring(sp + 1);
  arg.trim();

  if (cmd == "1") challenge1(arg);
  else if (cmd == "2") challenge2(arg);
  else if (cmd == "3") challenge3(arg);
  else if (cmd == "4") challenge4(arg);
  else if (cmd == "5") challenge5(arg);
  else if (cmd == "6") challenge6();
  else if (cmd == "7") challenge7(arg);
  else Serial.println("  Unknown command. Type 'menu' to see your options.");
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

  Serial.printf("\nConnected. Target: %s\n", targetIP.c_str());
  connected = true;
  printMenu();
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("\n=== CTF Flag Prober (interactive) ===");
  Serial.println("Send: SSID,PASSWORD,TARGET_IP");
  Serial.println("(the flashing page's \"Send to Board\" form does this for you)");
}

void loop() {
  if (!Serial.available()) return;
  String line = Serial.readStringUntil('\n');
  line.trim();
  if (line.length() == 0) return;

  if (!connected) {
    int c1 = line.indexOf(',');
    int c2 = line.indexOf(',', c1 + 1);
    if (c1 > 0 && c2 > c1) {
      targetSsid = line.substring(0, c1);
      targetPass = line.substring(c1 + 1, c2);
      targetIP = line.substring(c2 + 1);
      targetIP.trim();
      connectToWifi();
    } else {
      Serial.println("Expected format: SSID,PASSWORD,TARGET_IP");
    }
    return;
  }

  handleCommand(line);
}
