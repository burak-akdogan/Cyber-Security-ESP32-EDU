# "The Wi-Fi Ghost" — Sensing Movement Through Walls With Radio
### (ESP32 DevKit V1 only — no additional hardware)

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

---

## 2. How It Works (Conceptual Overview)

1. The ESP32 repeatedly reads the RSSI (signal strength) of a chosen access point
2. In a still room, RSSI is relatively stable
3. When a person moves, their body reflects/absorbs the signal → RSSI **fluctuates**
4. The code tracks the *variance* (jitter) of recent readings
5. High variance = **motion detected**; low variance = room is still — even with the ESP32 and router on opposite sides of a wall

---

## 3. Full Code

```cpp
// wifi_motion_ghost.ino
// Detects human motion via Wi-Fi RSSI variance. Point at a network you control.

#include <WiFi.h>

const char* target_ssid = "YOUR_ROUTER_SSID";   // <-- set to a router you control
const char* target_pass = "YOUR_ROUTER_PASS";   // <-- its password

#define SAMPLES 20
int rssiBuf[SAMPLES];
int idx = 0;
bool filled = false;

// baseline "still room" jitter, learned at startup
float baselineStdev = 0;
bool calibrated = false;

float stdevOf(int* buf, int n) {
  float mean = 0; for (int i = 0; i < n; i++) mean += buf[i]; mean /= n;
  float var = 0;  for (int i = 0; i < n; i++) var += (buf[i]-mean)*(buf[i]-mean);
  return sqrt(var / n);
}

void setup() {
  Serial.begin(115200);
  Serial.printf("Connecting to %s ...\n", target_ssid);
  WiFi.begin(target_ssid, target_pass);
  while (WiFi.status() != WL_CONNECTED) { delay(300); Serial.print("."); }
  Serial.println("\nConnected. Keep the room STILL for calibration...");
}

void loop() {
  if (WiFi.status() != WL_CONNECTED) { WiFi.reconnect(); delay(500); return; }

  rssiBuf[idx] = WiFi.RSSI();
  idx = (idx + 1) % SAMPLES;
  if (idx == 0) filled = true;
  delay(80); // ~12 readings/sec

  if (!filled) return;
  float s = stdevOf(rssiBuf, SAMPLES);

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
  if (s > threshold) {
    Serial.printf("[MOTION]  jitter=%.2f dB  (baseline %.2f)   <-- someone moved\n",
                  s, baselineStdev);
  } else {
    Serial.printf("[ still ] jitter=%.2f dB\n", s);
  }
}
```

---

## 4. Setup and Test Steps

1. Set `target_ssid` / `target_pass` to a router you control, upload the code
2. Open the Serial Monitor at 115200 baud
3. **Stay still** during calibration (a few seconds) — it learns the quiet baseline
4. Then wave your arm, walk across the room, or have someone walk on the *other side of a wall*
5. Watch the readout flip between `[ still ]` and `[MOTION]`

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

---

## 8. Student Checklist

- [ ] Calibrated the still-room baseline
- [ ] Detected their own motion via RSSI jitter
- [ ] Attempted through-wall detection and reported results
- [ ] Explained how a body disturbs radio waves
- [ ] Wrote 2-3 privacy implications of radio-based sensing
