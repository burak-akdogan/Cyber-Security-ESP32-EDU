// cyber-town.ino
// Classroom game: a Mafia / Town-of-Salem style social deduction game
// played over the classroom's own Raspberry Pi. Every ESP32 is one
// anonymous player -- roles (Attacker / Defender / Civilian) are assigned
// secretly by the Pi and only ever sent back to the player they belong to.
// Interaction is typed Serial commands (attack/defend/vote); the onboard
// LED (GPIO2 on most DevKit V1 boards) mirrors your status at a glance.
// See CLASSROOM-CTF-EVENT-en.md and pi-server/README.md for the full game.

#include <WiFi.h>
#include <HTTPClient.h>

#define LED_PIN 2

String targetSsid, targetPass, targetIP;
bool connected = false;
bool registered = false;
bool named = false;
String myMac;

int myNum = 0;
String myName;
String myPhase = "";
String myRole = "";
bool amAlive = true;

unsigned long lastPoll = 0;
const unsigned long POLL_INTERVAL = 1500;

unsigned long ledTimer = 0;
bool ledState = false;

// Forgives common copy/paste mistakes in the Target IP field, e.g.
// "http://10.42.0.1/" or "10.42.0.1:8080" -- both would otherwise get
// mangled when base() builds "http://" + targetIP + ":8080".
String sanitizeTargetIP(String ip) {
  ip.trim();
  int schemeEnd = ip.indexOf("://");
  if (schemeEnd >= 0) ip = ip.substring(schemeEnd + 3);
  int slash = ip.indexOf('/');
  if (slash >= 0) ip = ip.substring(0, slash);
  if (ip.endsWith(":8080")) ip = ip.substring(0, ip.length() - 5);
  return ip;
}

String base() {
  return "http://" + targetIP + ":8080";
}

bool httpPostForm(const String& path, const String& body, String& outBody) {
  HTTPClient http;
  http.begin(base() + path);
  http.addHeader("Content-Type", "application/x-www-form-urlencoded");
  int code = http.POST(body);
  outBody = http.getString();
  http.end();
  return code >= 200 && code < 300;
}

bool httpGet(const String& path, String& outBody) {
  HTTPClient http;
  http.begin(base() + path);
  int code = http.GET();
  outBody = http.getString();
  http.end();
  return code >= 200 && code < 300;
}

// Tiny hand-rolled lookups -- the Pi always replies with one flat,
// compact JSON object (no nested objects, no spaces), so a real JSON
// library would be overkill here.
String jsonStr(const String& body, const String& key) {
  String needle = "\"" + key + "\":\"";
  int i = body.indexOf(needle);
  if (i < 0) return "";
  i += needle.length();
  int end = body.indexOf('"', i);
  if (end < 0) return "";
  return body.substring(i, end);
}

int jsonInt(const String& body, const String& key) {
  String needle = "\"" + key + "\":";
  int i = body.indexOf(needle);
  if (i < 0) return -1;
  i += needle.length();
  int end = i;
  while (end < (int)body.length() && (isDigit(body[end]) || body[end] == '-')) end++;
  if (end == i) return -1;
  return body.substring(i, end).toInt();
}

bool jsonBool(const String& body, const String& key) {
  String needle = "\"" + key + "\":";
  int i = body.indexOf(needle);
  if (i < 0) return false;
  return body.startsWith("true", i + needle.length());
}

void printMenu() {
  Serial.println("\n=== Cyber Town -- commands ===");
  if (myPhase == "night" && myRole == "Attacker" && amAlive) {
    Serial.println("  attack <player number>   e.g. attack 5");
  } else if (myPhase == "night" && myRole == "Defender" && amAlive) {
    Serial.println("  defend <player number>   e.g. defend 5");
  } else if (myPhase == "day_vote" && amAlive) {
    Serial.println("  vote <player number>     e.g. vote 5");
  } else {
    Serial.println("  (nothing to do right now -- watch the projector)");
  }
  Serial.println("  menu                     show this again");
  Serial.println("===============================");
}

void registerWithPi() {
  myMac = WiFi.macAddress();
  String resp;
  if (!httpPostForm("/game/register", "mac=" + myMac, resp)) {
    Serial.println("Couldn't reach the Pi -- check the Target IP, then type 'retry'.");
    return;
  }
  registered = true;
  myNum = jsonInt(resp, "num");
  myName = jsonStr(resp, "name");
  myPhase = jsonStr(resp, "phase");
  Serial.printf("\nRegistered as Player %d (%s).\n", myNum, myName.c_str());
  Serial.println("Type your name and press Enter (or just press Enter to keep that name):");
}

void sendName(String name) {
  if (name.length() == 0) name = myName;
  String resp;
  if (!httpPostForm("/game/name", "mac=" + myMac + "&name=" + name, resp)) {
    Serial.println("Couldn't reach the Pi -- try again.");
    return;
  }
  myName = name;
  named = true;
  Serial.println("Got it -- you're \"" + name + "\". Waiting for the instructor to start the game...");
  printMenu();
}

void pollState() {
  String resp;
  if (!httpGet("/game/state?mac=" + myMac, resp)) return;

  String newRole = jsonStr(resp, "role");
  bool newAlive = jsonBool(resp, "alive");
  String newPhase = jsonStr(resp, "phase");

  if (newRole.length() > 0 && newRole != myRole) {
    myRole = newRole;
    Serial.println("\n>>> YOUR SECRET ROLE: " + myRole + " <<<");
    Serial.println("Keep it to yourself. Nobody else's board shows this.");
  }

  if (amAlive && !newAlive) {
    Serial.println("\nYou have been ELIMINATED. You can still watch, but you can't act anymore.");
  }
  amAlive = newAlive;

  if (newPhase != myPhase) {
    myPhase = newPhase;
    if (myPhase == "night") {
      Serial.println("\n=== NIGHT has fallen -- watch the projector for the round number ===");
    } else if (myPhase == "day_vote") {
      Serial.println("\n=== DAY -- discuss out loud, then vote ===");
    } else if (myPhase == "game_over") {
      String winner = jsonStr(resp, "winner");
      String label = (winner == "attackers") ? "ATTACKERS WIN"
                    : (winner == "town") ? "TOWN WINS" : "GAME OVER";
      Serial.println("\n########## " + label + " ##########");
      Serial.println("Your role was: " + myRole);
      Serial.println("Check the projector for the full reveal.");
    }
    printMenu();
  }
}

void handleCommand(String line) {
  line.trim();
  if (line.length() == 0) return;
  if (line.equalsIgnoreCase("menu")) { printMenu(); return; }

  int sp = line.indexOf(' ');
  String cmd = sp < 0 ? line : line.substring(0, sp);
  String argStr = sp < 0 ? "" : line.substring(sp + 1);
  argStr.trim();
  cmd.toLowerCase();

  if (cmd == "attack" || cmd == "defend" || cmd == "vote") {
    if (argStr.length() == 0) { Serial.println("Usage: " + cmd + " <player number>"); return; }
    int target = argStr.toInt();
    String resp;
    bool ok = httpPostForm("/game/" + cmd, "mac=" + myMac + "&target=" + String(target), resp);
    if (ok) {
      Serial.println("Locked in: " + cmd + " " + String(target));
    } else {
      Serial.println("That didn't work -- wrong phase, wrong role, or you're eliminated. Type 'menu' to check.");
    }
  } else {
    Serial.println("Unknown command. Type 'menu' for what you can do right now.");
  }
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
  Serial.printf("\nConnected. Game server: %s\n", targetIP.c_str());
  registerWithPi();
}

void updateLed() {
  if (!connected || !registered || myPhase == "" || myPhase == "lobby" || !amAlive) {
    digitalWrite(LED_PIN, LOW);
    return;
  }
  unsigned long now = millis();
  if (myPhase == "night") {
    if (now - ledTimer > 500) { ledTimer = now; ledState = !ledState; digitalWrite(LED_PIN, ledState); }
  } else {
    digitalWrite(LED_PIN, HIGH);
  }
}

void setup() {
  Serial.begin(115200);
  delay(300);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  Serial.println("\n=== Cyber Town (classroom social deduction game) ===");
  Serial.println("Send: SSID,PASSWORD,TARGET_IP");
  Serial.println("(the flashing page's \"Send to Board\" form does this for you)");
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();

    if (!connected) {
      int c1 = line.indexOf(',');
      int c2 = line.indexOf(',', c1 + 1);
      if (c1 > 0 && c2 > c1) {
        targetSsid = line.substring(0, c1);
        targetPass = line.substring(c1 + 1, c2);
        targetIP = sanitizeTargetIP(line.substring(c2 + 1));
        connectToWifi();
      } else if (line.length() > 0) {
        Serial.println("Expected format: SSID,PASSWORD,TARGET_IP");
      }
    } else if (!registered) {
      if (line.equalsIgnoreCase("retry") || line.length() == 0) {
        registerWithPi();
      } else {
        Serial.println("Type 'retry' to try registering again.");
      }
    } else if (!named) {
      sendName(line);
    } else {
      handleCommand(line);
    }
  }

  if (connected && named && millis() - lastPoll > POLL_INTERVAL) {
    lastPoll = millis();
    pollState();
  }

  updateLed();
}
