# Classroom Capture-the-Flag — Whole-Class Raspberry Pi Exercise
### (ESP32 DevKit V1 fleet + one Raspberry Pi 5)

> 🚨 **FOR EDUCATIONAL PURPOSES ONLY.** This exercise is provided solely to teach cybersecurity awareness in a supervised classroom setting, with informed consent from everyone involved. Do not use these techniques against real people, devices, or networks without explicit authorization — doing so may violate computer-misuse, wiretapping, or other laws in your jurisdiction.

> **Status: built.** The Pi-side app, both ESP32 tools, the site section, and the student rules page all exist now (see §10). Run [pi-server/README.md](pi-server/README.md) before your first round.
>
> **Running an actual session?** Use [CLASSROOM-CTF-TEACHER-GUIDE-en.md](CLASSROOM-CTF-TEACHER-GUIDE-en.md) (full steps + answer key + troubleshooting) and hand students [CLASSROOM-CTF-STUDENT-GUIDE-en.md](CLASSROOM-CTF-STUDENT-GUIDE-en.md) (no answers). This file is the design rationale behind both.

---

## 1. The idea in one paragraph

The whole class plays a live Capture-the-Flag round against **one shared Raspberry Pi 5**, projected on a screen everyone can see. The Pi deliberately hosts a handful of common, realistic web-server vulnerabilities, each hiding a short "flag" code. Students use **pre-built, flash-and-go ESP32 tools** (no coding required, matching every other lab in this repo) to find flags over Wi-Fi. Finding a flag scores points; a team can also choose to *patch* the vulnerability they found (one click on the Pi's own dashboard, still no coding) to lock it away from everyone else and earn a bigger, "defender" bonus. The live scoreboard on the shared screen turns the whole thing into a visible, competitive event instead of a quiet solo lab.

---

## 2. Why this format (the decisions, and the reasoning)

| Decision | Choice | Why |
|---|---|---|
| One Pi vs. one Pi per team | **One shared Pi** | Matches what's available (one Raspberry Pi 5) and what was asked ("Pi'yi ekrana vereceğim"). Per-team isolated environments would need containers/VMs per team — real infrastructure work, and it removes the "everyone watches the same board" energy. |
| Simultaneous vs. sequential rounds | **Simultaneous, shared target** | More energy for a whole-class event; the "first to find, first to patch" dynamic is exactly how real attack-defense CTFs work, and it directly rewards being fast *and* being thorough. |
| Coding required? | **None, for students** | Every ESP32 tool is pre-built firmware (flash and use, same pattern as every other lab here). Patching a vulnerability is a button on the Pi's own dashboard, not a code edit. |
| Round length | **One class period (~40–45 min)** | 5 min consent/briefing, ~30 min live round, ~10 min debrief tying each flag back to a real-world lesson. |
| Consequence for finding vs. patching | **Both scored, patching scored higher** | Finding a flag proves the attack works; patching proves you understood *why* it worked well enough to fix it — the harder, more valuable skill. |

---

## 3. Materials

- 1 Raspberry Pi 5, connected to a classroom monitor/projector (its own screen is the shared scoreboard)
- The class's existing ESP32 DevKit V1 fleet (a handful is enough; 15 lets every student hold one)
- The Pi hosts its own Wi-Fi network (or a dedicated router) that only this exercise uses — never the school's production network
- Each ESP32 gets one of a small set of **pre-built firmware "tools"** (see §5) — flashed ahead of time or via the same one-click browser flasher this repo already has

---

## 4. The vulnerabilities (flags)

A small Flask app on the Pi, seeded with **6–7 intentionally planted issues**, easy → hard. Each is a well-known, real-world vulnerability class — this list doubles as the debrief agenda.

| # | Vulnerability | What a student does | Real-world lesson |
|---|---|---|---|
| 1 | Default admin credentials (`admin` / `admin`) on a login panel | Research common admin/router default passwords, then type a guess by hand (deliberately manual, not automated) | Change default credentials — always |
| 2 | Hidden, unlinked page (no link anywhere, but guessable/discoverable) | Type a guessed page name yourself — no auto-solve, wrong guesses just 404 | "Security through obscurity" isn't security |
| 3 | IDOR — `/api/note?id=1` shows another user's note if you just change the number | Increment/change an ID in a URL | Every request needs an ownership check, not just a login |
| 4 | Exposed backup file left in the web root (`/backup.zip`) | Type a guessed filename yourself — no auto-solve, wrong guesses just 404 | Don't leave debug/backup artifacts on a live server |
| 5 | Verbose error page that leaks a flag in a stack trace | Try edge-case number pairs yourself until one triggers an error | Never show raw errors to the outside world |
| 6 | Unauthenticated "admin action" endpoint (works with no login at all) | Call the endpoint directly | Authentication has to be checked on *every* sensitive endpoint, not just the login form |
| 7 *(hardest, optional)* | Simulated command-injection field (safely faked — no real shell is ever run) | Notice unsanitized input reflected back | Why raw user input near a system call is dangerous |

Each flag is a short string like `FLAG{default_creds_are_forever}` — thematic, memorable, and easy to read off an ESP32's Serial console.

---

## 5. The ESP32 "toolkit" (pre-built, no coding)

Same philosophy as every existing lab here: flash it, watch the Console, done.

| Tool firmware | What it does |
|---|---|
| **Recon Scanner** | Connects to the Pi's Wi-Fi, probes a handful of common ports/paths, prints what it finds to Serial — the "where do I even start" tool |
| **Flag Prober** | An interactive console, not an autosolver — it prints a 7-item menu and waits. The student types a short command (via a follow-up box on the site) to try one challenge at a time, reads the response, and keeps guessing (different IDs, credentials, payloads) until something works |
| **DDoS Flood** *(separate bonus activity, see §9)* | On command (`start`/`stop`), floods the Pi's own dashboard page with requests as fast as it can. Run on several boards at once for a volume-based denial-of-service demo the instructor can then mitigate live |
| *(optional)* **Manual mode** | For students who want to explore by hand from a laptop browser on the same Wi-Fi instead of/alongside an ESP32 |

---

## 6. The Pi-side dashboard (also no coding, just buttons)

A single page, shown on the projector, with three jobs:

1. **Live scoreboard** — team name, points found, points from patches, updated instantly
2. **Flag submission** — a simple box where a team's spokesperson types in a captured flag code (or the ESP32 could report it automatically over the network — to be decided when building)
3. **Patch buttons**, one per vulnerability, e.g. *"Rotate admin password,"* *"Delete backup file,"* *"Require login on admin endpoint"* — clicking one instantly closes that flag for everyone and credits the patching team

---

## 7. Scoring sketch

| Action | Points |
|---|---|
| First team to find a flag | 100 |
| Later team also finds the same (still-open) flag | 50 |
| Team that patches a vulnerability (finding it first isn't required) | +75 (and it's now closed to everyone else) |

---

## 8. Ties to the PLTW Cybersecurity course

This exercise is designed to be the hands-on/hardware companion to specific official PLTW units, not a standalone add-on:

- **Unit 2, Project 2.2.4 "Secure the Server" / Project 2.3.4 "Find the Exploits"** — this event *is* those two projects, live and physical
- **Unit 3** ("Analyze and Defend Network Attacks," "Eradicate the Vulnerabilities") — the find/patch loop is the same skill
- **Unit 1, Activity 1.1.2 "Password Protection and Authentication"** — flag #1 directly
- **Unit 1, Activity 1.1.1 "Cybersecurity and Code of Conduct"** — reuse this repo's existing consent/ethics gate before the round starts

---

## 9. Bonus activity: the DDoS demo

A separate, optional add-on to the flag-hunting round — run it as its own
activity, not simultaneously (a heavy flood makes the flag round's dashboard
sluggish for everyone). Several ESP32s, each running the **DDoS Flood**
tool, hammer the Pi's own dashboard page (`/`) with requests on command
(`start`/`stop`). The dashboard tracks a live requests/second figure and
flips to a **🔴 UNDER ATTACK** banner once the combined rate crosses a
threshold (~20 req/s — a handful of boards is plenty). The instructor then
clicks **🛡️ Enable DDoS Protection** to demonstrate a real mitigation: a
per-IP rate limit that cheaply rejects (HTTP 429) any single device sending
more than 15 requests/second, without needing to otherwise distinguish
"attack" traffic from real traffic. The scoreboard, flag submission, and
patch endpoints are deliberately exempt from this limit, so the instructor
can always see and control the dashboard even mid-flood.

This teaches the same lesson as [Lab 2 (Deauth Canary) / Lab 9 (Deauth
Storm)](README.md#-the-labs) one layer up the stack: a *volume* attack
doesn't need to exploit any bug at all, and a real, explainable defense
(rate limiting) can still blunt it without the attacker needing to be
"caught" individually.

---

## 10. Safety / ethics (same rules as every other lab in this repo)

- Runs on a network this class controls end-to-end — never the school's production Wi-Fi
- Every "victim" is the instructor's own Raspberry Pi — no third-party system is ever touched
- Consent + code-of-conduct briefing happens before power-on, same as every other lab
- Flags/vulnerabilities are reset between class periods so nothing carries over or gets genuinely broken
- The DDoS demo only ever targets the same Pi, over the same isolated Wi-Fi — same ownership/consent rule as everything else here, just at higher volume

---

## 11. What was built

- [pi-server/app.py](pi-server/app.py) — the Flask target app: all 7 vulnerabilities, the scoreboard, flag submission, per-vulnerability patch buttons, live traffic tracking, and the DDoS protection toggle. [pi-server/README.md](pi-server/README.md) covers running it and resetting between class periods.
- [firmware/ctf-recon-scanner/](firmware/ctf-recon-scanner/) — flash-and-go ESP32 tool that scans the target Pi's common ports/paths
- [firmware/ctf-flag-prober/](firmware/ctf-flag-prober/) — interactive, menu-driven ESP32 console for trying each of the 7 vulnerabilities by hand
- [firmware/ctf-ddos-flood/](firmware/ctf-ddos-flood/) — flash-and-go ESP32 tool for the bonus DDoS demo (§9)
- A new **"Whole-Class Capture the Flag"** section on the [flashing site](https://burak-akdogan.github.io/Cyber-Security-ESP32-EDU/), with all three tools flashable the same way as every other lab (their Wi-Fi form also asks for the target Pi's IP address)
- [docs/ctf-rules.html](docs/ctf-rules.html) — the student-facing rules page (printable/downloadable from the site, no flag contents included)

Both new sketches live under `firmware/`, so the existing GitHub Actions workflow picks them up and publishes them automatically on the next push — no workflow changes were needed.
