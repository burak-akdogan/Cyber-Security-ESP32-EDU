# "The Wi-Fi Ghost" — Sensing Movement Through Walls With Radio
### (ESP32 DevKit V1 only — no additional hardware)

> 🚨 **FOR EDUCATIONAL PURPOSES ONLY.** This lab is provided solely to teach cybersecurity awareness in a supervised classroom setting, with informed consent from everyone involved. Do not use these techniques against real people, devices, or networks without explicit authorization — doing so may violate computer-misuse, wiretapping, or other laws in your jurisdiction.

**The unsettling idea:** you don't need a camera to know someone is in a room. When a person moves, their body disturbs the Wi-Fi radio waves already bouncing around the space. This project measures the **jitter in signal strength (RSSI)** from a nearby router and detects *human motion* — even through a wall — turning Wi-Fi itself into a motion sensor.

Students discover that the same radio signals they trust for the internet can silently reveal whether a room is occupied and when people move.

> Passive measurement of signal strength from a network you own/are permitted to observe. No connecting to others' networks, no traffic capture.

---

## ⚠️ Read This First: Ethical and Legal Framework

- **Use your own network:** Point it at the classroom/your own router only. Do not surveil others' spaces.
- **Surveillance ethics:** This *is* a form of sensing people without their knowledge — that's exactly why it's worth studying. Discuss the ethics openly.
- **No footage, no identity:** It only senses "movement vs. still," not who or what.
- **The goal is awareness:** "The radio waves around you can be read as a motion sensor — by anyone, invisibly."

---

## 1. Required Materials

- ESP32 DevKit V1
- Micro-USB data cable
- A Wi-Fi router/AP you control (to measure against)
- Arduino IDE with ESP32 board package

Uses:
- `WiFi.h`
- `WebServer.h` (built into the ESP32 core — hosts a live dashboard page, no extra hardware needed)

---

## 2. How It Works (Conceptual Overview)

1. The ESP32 repeatedly reads the RSSI (signal strength) of a chosen access point
2. In a still room, RSSI is relatively stable
3. When a person moves, their body reflects/absorbs the signal → RSSI **fluctuates**
4. The code tracks the *variance* (jitter) of recent readings
5. High variance = **motion detected**; low variance = room is still — even with the ESP32 and router on opposite sides of a wall
6. The ESP32 also hosts a small **web dashboard** on its own Wi-Fi connection — open its IP address from any phone/laptop on the same network to see a live status banner and a jitter chart, instead of reading raw text in the Serial Monitor

---

## 3. Full Code

```cpp
// wifi_motion_ghost.ino
// Detects human motion via Wi-Fi RSSI variance, then hosts a live dashboard
// (status + jitter chart). On boot it opens its own "WiFiGhost-Setup" network
// so a student can type in the real Wi-Fi name/password from a phone or
// laptop -- no code editing, no Arduino IDE, no recompiling required.

#include <WiFi.h>
#include <WebServer.h>
#include <DNSServer.h>

const char* SETUP_SSID = "WiFiGhost-Setup"; // temporary open AP used only to collect Wi-Fi credentials
DNSServer dnsServer;
WebServer server(80);
const byte DNS_PORT = 53;
IPAddress apIP(192, 168, 4, 1);

bool provisioned = false;  // true once connected to the student's real Wi-Fi
bool connectNow = false;   // set right after the setup form is submitted
String targetSsid, targetPass;

#define SAMPLES 20
int rssiBuf[SAMPLES];
int idx = 0;
bool filled = false;

// baseline "still room" jitter, learned at startup
float baselineStdev = 0;
bool calibrated = false;

// latest readings, shared with the dashboard
float lastRssi = 0;
float lastJitter = 0;
float lastThreshold = 0;
bool motionNow = false;

#define HISTORY_LEN 60
float jitterHistory[HISTORY_LEN];
int histIdx = 0;

float stdevOf(int* buf, int n) {
  float mean = 0; for (int i = 0; i < n; i++) mean += buf[i]; mean /= n;
  float var = 0;  for (int i = 0; i < n; i++) var += (buf[i]-mean)*(buf[i]-mean);
  return sqrt(var / n);
}

// --- Step 1: setup page that asks for the Wi-Fi to point at ---
const char SETUP_HTML[] PROGMEM = R"HTML(
<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wi-Fi Ghost Setup</title>
<style>
  body{background:#0b0f14;color:#d7e2ea;font-family:system-ui,sans-serif;margin:0;padding:28px 20px;max-width:420px}
  h1{font-size:19px;color:#8fb3c9;margin:0 0 8px}
  p{font-size:13px;color:#9fb2c0;line-height:1.5}
  label{display:block;font-size:12px;color:#9fb2c0;margin:16px 0 4px}
  input{width:100%;padding:11px;border-radius:8px;border:1px solid #24313d;background:#131a22;color:#e2e8f0;font-size:15px;box-sizing:border-box}
  button{width:100%;margin-top:18px;padding:12px;border:0;border-radius:8px;background:#38bdf8;color:#04121a;font-weight:700;font-size:15px}
</style></head><body>
  <h1>Wi-Fi Ghost Setup</h1>
  <p>Point this board at a Wi-Fi network you're allowed to measure against (e.g. your classroom router). The password is only used to connect this ESP32 to that network -- it is never sent anywhere else.</p>
  <form action="/connect" method="POST">
    <label>Wi-Fi network name (SSID)</label>
    <input type="text" name="ssid" required autofocus>
    <label>Password</label>
    <input type="password" name="password">
    <button type="submit">Connect</button>
  </form>
</body></html>
)HTML";

void handleSetupRoot() {
  server.send_P(200, "text/html", SETUP_HTML);
}

void handleConnect() {
  targetSsid = server.arg("ssid");
  targetPass = server.arg("password");
  server.send(200, "text/html",
    "<body style='background:#0b0f14;color:#d7e2ea;font-family:sans-serif;padding:30px'>"
    "<h2>Connecting...</h2><p>Rejoin your normal Wi-Fi, then check this board's "
    "Console/Serial output for the dashboard address.</p></body>");
  connectNow = true; // do the actual switchover in loop(), after this response is sent
}

// --- Step 2: the live dashboard, once connected ---
const char PAGE_HTML[] PROGMEM = R"HTML(
<!DOCTYPE html><html><head><meta charset="utf-8">
<title>Wi-Fi Ghost Dashboard</title>
<style>
  body{background:#0b0f14;color:#d7e2ea;font-family:system-ui,sans-serif;margin:0;padding:20px}
  h1{font-size:18px;color:#8fb3c9;margin:0 0 16px}
  #status{font-size:28px;font-weight:700;padding:16px;border-radius:10px;text-align:center;margin-bottom:16px}
  .still{background:#123a24;color:#4ade80}
  .motion{background:#3a1212;color:#f87171;animation:blink 0.6s step-start infinite}
  @keyframes blink{50%{opacity:0.35}}
  #stats{display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap}
  .stat{background:#131a22;border-radius:8px;padding:10px 14px;min-width:110px}
  .stat .label{font-size:11px;color:#7d93a3;text-transform:uppercase}
  .stat .value{font-size:20px;font-weight:600}
  canvas{background:#0f151c;border-radius:8px;width:100%;height:220px}
</style></head><body>
  <h1>The Wi-Fi Ghost &mdash; live motion sensor</h1>
  <div id="status" class="still">CALIBRATING...</div>
  <div id="stats">
    <div class="stat"><div class="label">RSSI</div><div class="value" id="v-rssi">-</div></div>
    <div class="stat"><div class="label">Jitter</div><div class="value" id="v-jitter">-</div></div>
    <div class="stat"><div class="label">Baseline</div><div class="value" id="v-base">-</div></div>
    <div class="stat"><div class="label">Threshold</div><div class="value" id="v-thr">-</div></div>
  </div>
  <canvas id="chart" width="600" height="220"></canvas>
<script>
async function poll(){
  try{
    const r = await fetch('/data'); const d = await r.json();
    const s = document.getElementById('status');
    if(!d.calibrated){ s.textContent='CALIBRATING...'; s.className='still'; }
    else if(d.motion){ s.textContent='MOTION DETECTED'; s.className='motion'; }
    else { s.textContent='STILL'; s.className='still'; }
    document.getElementById('v-rssi').textContent = d.rssi + ' dBm';
    document.getElementById('v-jitter').textContent = d.jitter.toFixed(2) + ' dB';
    document.getElementById('v-base').textContent = d.baseline.toFixed(2) + ' dB';
    document.getElementById('v-thr').textContent = d.threshold.toFixed(2) + ' dB';
    draw(d.history, d.threshold);
  }catch(e){}
  setTimeout(poll, 200);
}
function draw(hist, thr){
  const c = document.getElementById('chart'), ctx = c.getContext('2d');
  ctx.clearRect(0,0,c.width,c.height);
  const max = Math.max(thr*1.5, ...hist, 1);
  const stepX = c.width / (hist.length - 1);
  ctx.strokeStyle = '#f59e0b'; ctx.setLineDash([6,4]); ctx.beginPath();
  const ty = c.height - (thr/max)*c.height;
  ctx.moveTo(0,ty); ctx.lineTo(c.width,ty); ctx.stroke(); ctx.setLineDash([]);
  ctx.strokeStyle = '#38bdf8'; ctx.lineWidth = 2; ctx.beginPath();
  hist.forEach((v,i)=>{ const x=i*stepX, y=c.height-(v/max)*c.height; i===0?ctx.moveTo(x,y):ctx.lineTo(x,y); });
  ctx.stroke();
}
poll();
</script></body></html>
)HTML";

void handleRoot() {
  server.send_P(200, "text/html", PAGE_HTML);
}

void handleData() {
  String json = "{";
  json += "\"calibrated\":" + String(calibrated ? "true" : "false") + ",";
  json += "\"motion\":" + String(motionNow ? "true" : "false") + ",";
  json += "\"rssi\":" + String((int)lastRssi) + ",";
  json += "\"jitter\":" + String(lastJitter, 2) + ",";
  json += "\"baseline\":" + String(baselineStdev, 2) + ",";
  json += "\"threshold\":" + String(lastThreshold, 2) + ",";
  json += "\"history\":[";
  for (int i = 0; i < HISTORY_LEN; i++) {
    int j = (histIdx + i) % HISTORY_LEN;
    json += String(jitterHistory[j], 2);
    if (i < HISTORY_LEN - 1) json += ",";
  }
  json += "]}";
  server.send(200, "application/json", json);
}

void startSetupPortal() {
  WiFi.mode(WIFI_AP);
  WiFi.softAP(SETUP_SSID);
  dnsServer.start(DNS_PORT, "*", apIP);
  server.onNotFound(handleSetupRoot);
  server.on("/", handleSetupRoot);
  server.on("/connect", HTTP_POST, handleConnect);
  server.begin();
  Serial.println("\n=== Wi-Fi Ghost: setup mode ===");
  Serial.printf("Join Wi-Fi \"%s\" (open network) from a phone or laptop, then open http://192.168.4.1\n", SETUP_SSID);
}

void connectToTarget() {
  dnsServer.stop();
  WiFi.softAPdisconnect(true);
  WiFi.mode(WIFI_STA);
  Serial.printf("\nConnecting to \"%s\" ...\n", targetSsid.c_str());
  WiFi.begin(targetSsid.c_str(), targetPass.c_str());

  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
    delay(300);
    Serial.print(".");
  }

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("\nCouldn't connect -- check the network name/password and try again.");
    startSetupPortal(); // fall back to setup mode so the student can retry
    return;
  }

  Serial.printf("\nConnected. Dashboard: http://%s\n", WiFi.localIP().toString().c_str());
  Serial.println("Keep the room STILL for a few seconds while it calibrates...");

  server.onNotFound(handleRoot);
  server.on("/", handleRoot);
  server.on("/data", handleData);
  server.begin();
  provisioned = true;
}

void setup() {
  Serial.begin(115200);
  startSetupPortal();
}

void loop() {
  if (connectNow) {
    connectNow = false;
    connectToTarget();
    return;
  }

  if (!provisioned) dnsServer.processNextRequest();
  server.handleClient();

  if (!provisioned) return; // still waiting for the student to submit Wi-Fi credentials

  if (WiFi.status() != WL_CONNECTED) { WiFi.reconnect(); delay(500); return; }

  static unsigned long lastSample = 0;
  if (millis() - lastSample < 80) return; // ~12 readings/sec, non-blocking so the dashboard stays responsive
  lastSample = millis();

  rssiBuf[idx] = WiFi.RSSI();
  lastRssi = rssiBuf[idx];
  idx = (idx + 1) % SAMPLES;
  if (idx == 0) filled = true;

  if (!filled) return;
  float s = stdevOf(rssiBuf, SAMPLES);
  lastJitter = s;
  jitterHistory[histIdx] = s;
  histIdx = (histIdx + 1) % HISTORY_LEN;

  // Auto-calibrate the "still" baseline once, then start detecting
  static int calCount = 0;
  if (!calibrated) {
    baselineStdev += s; calCount++;
    if (calCount >= 40) {
      baselineStdev /= calCount;
      calibrated = true;
      Serial.printf("Calibrated. Still-room jitter = %.2f dB. Now watching for motion.\n\n",
                    baselineStdev);
    }
    return;
  }

  float threshold = baselineStdev + 2.0; // motion if jitter clearly exceeds baseline
  lastThreshold = threshold;
  motionNow = s > threshold;

  if (motionNow) {
    Serial.printf("[MOTION]  jitter=%.2f dB  (baseline %.2f)   <-- someone moved\n",
                  s, baselineStdev);
  } else {
    Serial.printf("[ still ] jitter=%.2f dB\n", s);
  }
}
```

The dashboard needs no extra hardware: `WebServer.h` is part of the ESP32 core, and the page (HTML/CSS/JS) is served directly from the chip's flash memory. Any phone or laptop on the same Wi-Fi network can open it in a browser and see the status banner and jitter chart update live, polling `/data` every 200 ms.

---

## 4. Setup and Test Steps

1. Flash the board (Arduino IDE or the one-click browser installer) and open the Serial Monitor / Console at 115200 baud
2. On a phone or laptop, join the board's own temporary Wi-Fi network **"WiFiGhost-Setup"** (open, no password)
3. A setup page should open automatically (or open `http://192.168.4.1` yourself) — type in the SSID and password of a router you're allowed to measure against and tap Connect
4. Rejoin your normal Wi-Fi, then check the Serial Monitor / Console — once connected it prints a line like `Dashboard: http://192.168.1.42` — open that address in a browser on any device on the same network
4. **Stay still** during calibration (a few seconds) — it learns the quiet baseline
5. Then wave your arm, walk across the room, or have someone walk on the *other side of a wall*
6. Watch the dashboard flip between the green **STILL** banner and the red, blinking **MOTION DETECTED** banner, and watch the jitter line cross the orange threshold line on the chart — or, if you prefer, watch the readout flip between `[ still ]` and `[MOTION]` in the Serial Monitor

> Best effect: put the ESP32 and the router in different rooms so the signal path crosses where people walk. Movement in that path shows up strongest.

---

## 5. Classroom Discussion Activity

- "We detected a person with no camera and no wearable. How is that possible?"
- "If a landlord or employer did this, would tenants/employees ever know?"
- "Could an attacker outside your apartment tell when you leave for work?"
- "Is sensing 'someone is moving' as invasive as a camera? Where's the line?"

---

## 6. Defense / Awareness Takeaways

| Concern | Consideration |
|---|---|
| Wi-Fi reveals occupancy/motion | Understand that radio isn't "invisible" — presence leaks |
| Passive, undetectable sensing | There's no easy way to know you're being sensed this way |
| Pattern-of-life inference | Regular movement patterns can reveal routines |
| Trust in "no camera = private" | Absence of a camera doesn't mean absence of sensing |

---

## 7. Common Issues

| Issue | Fix |
|---|---|
| Always says MOTION | Recalibrate in a truly still room; raise the `+2.0` margin |
| Never says MOTION | Lower the margin; move the ESP32/router so the path crosses the person |
| RSSI reads 0 / not connected | Check SSID/password; ensure the router is in range |
| Very noisy readings | Increase `SAMPLES` for smoother averaging |
| Dashboard won't load in browser | Make sure your phone/laptop is on the *same* Wi-Fi network as the router; re-check the IP printed in the Serial Monitor (it can change on reconnect) |

---

## 8. Student Checklist

- [ ] Calibrated the still-room baseline
- [ ] Detected their own motion via RSSI jitter
- [ ] Attempted through-wall detection and reported results
- [ ] Explained how a body disturbs radio waves
- [ ] Wrote 2-3 privacy implications of radio-based sensing
