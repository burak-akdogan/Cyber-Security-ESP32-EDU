# Classroom CTF — Student Guide
### Whole-Class Capture the Flag against a Raspberry Pi

> 🚨 **FOR EDUCATIONAL PURPOSES ONLY.** Only ever target the instructor's Raspberry Pi on the event Wi-Fi. Never point any tool at another student's device, the school network, or anything you don't have explicit permission to test.

This is a live event: your class finds (and can patch) real, intentionally planted security holes on a shared Raspberry Pi, projected on the classroom screen. No coding required — everything here is flash-a-board-and-click.

---

## 1. What you're doing

- A Raspberry Pi on the classroom screen is running a small web app full of common, realistic vulnerabilities.
- Each vulnerability hides a **flag** — a short code like `FLAG{...}`.
- You use an ESP32 board (flashed from your browser, no code) to find flags over Wi-Fi, then submit them on the shared scoreboard to score points.
- You can also **patch** a vulnerability you find — that locks it for everyone else and earns your team a bigger bonus.

If your instructor assigned you a role, follow it: **Red Team** attacks (finds flags), **Blue Team** defends (patches vulnerabilities on the scoreboard — no ESP32 needed for this).

If your instructor says it's **individual** (no teams), just type **your own name** wherever the scoreboard asks for a "team name" — you'll show up as your own row, scored the same way as a team would be.

---

## 2. Step by step

### Step 1 — Join the event Wi-Fi
Ask your instructor for the network name (SSID), password, and the **target IP address** of the Raspberry Pi. Join that Wi-Fi on your phone/laptop.

### Step 2 — Get an ESP32 (Red Team / attackers only)
If you're on Blue Team, skip to Step 6 — you don't need a board.

### Step 3 — Open the flashing site
Go to **https://burak-akdogan.github.io/Cyber-Security-ESP32-EDU/**. If a Code of Conduct screen appears, read and accept it.

### Step 4 — Find the CTF section
Scroll down to **"Whole-Class Capture the Flag."** There are two tools:

| Tool | What it does |
|---|---|
| **CTF · Recon Scanner** | Lists what's open on the Pi (ports, pages) — a map, no exploiting |
| **CTF · Flag Prober** | Automatically tries every known vulnerability and prints any flag it captures |

Start with Recon Scanner if you want to explore first, or go straight to Flag Prober.

### Step 5 — Flash it and connect
1. Open the tool's guide panel, click **Install**, and flash your ESP32.
2. In the same panel, fill in the Wi-Fi form: **SSID**, **Password**, and **Target IP** (the Pi's address from Step 1).
3. Click **Send to Board**, and pick your ESP32's serial port when your browser asks.
4. Watch the console that appears under the form.

### Step 6 — Read the results
- Recon Scanner prints a list of ports/paths and status codes.
- Flag Prober prints `[FOUND] #<n> <vulnerability name>: FLAG{...}` for anything it captured.

### Step 7 — Score it
Go to the scoreboard on the classroom screen (or open `http://<pi-ip>:8080/` yourself on the same Wi-Fi). Type your **team name** and the **flag code**, then submit.

### Step 8 — Patch (optional, or Blue Team's main job)
On the same scoreboard, each vulnerability has a **Patch** button. Clicking it:
- Closes that vulnerability for everyone (no one can score from it again)
- Earns your team a bonus — you don't need to have found the flag yourself to patch it

---

## 3. Scoring

| Action | Points |
|---|---|
| First team to find a flag | 100 |
| Another team also finds the same (still-open) flag | 50 |
| Patch a vulnerability (finding it first isn't required) | +75, and it's closed to everyone else |

---

## 4. What you're looking for

Seven vulnerability categories are planted on the Pi. No spoilers here — just the categories, so you know what each one is testing:

| # | Category | Hint |
|---|---|---|
| 1 | Default credentials | Some accounts still use the password they shipped with |
| 2 | Hidden pages aren't secret | Not being linked anywhere isn't the same as being protected |
| 3 | Broken access control (IDOR) | What happens if you just... change an ID in a URL? |
| 4 | Leftover files | Developers sometimes forget to remove things from a live server |
| 5 | Oversharing errors | A crash message can say more than it should |
| 6 | Missing authentication | Not every sensitive action checks who's asking |
| 7 | Untrusted input (hardest) | What a service does with input it never expected |

---

## 5. If you get stuck

- Ask your instructor — don't guess your way into trying something outside the Pi.
- Try Recon Scanner again if you're not sure what's even reachable.
- If your ESP32's console shows a Wi-Fi connection error, double-check the SSID/password and that you're within range.

---

## 6. Rules, one more time

- Only the instructor's Raspberry Pi is a valid target — nothing else, ever.
- Red Team: attack only. Blue Team: patch only (if roles were assigned).
- Don't interfere with another team's device or board.
- This is a game about understanding *why* each vulnerability is dangerous, not just "winning" — be ready to explain what you found in the debrief.
