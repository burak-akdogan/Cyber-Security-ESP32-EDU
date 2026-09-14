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
| 1 | Default admin credentials (`admin` / `admin`) on a login panel | Try the obvious default | Change default credentials — always |
| 2 | Hidden, unlinked page (no link anywhere, but guessable/discoverable) | Basic directory guessing | "Security through obscurity" isn't security |
| 3 | IDOR — `/api/note?id=1` shows another user's note if you just change the number | Increment/change an ID in a URL | Every request needs an ownership check, not just a login |
| 4 | Exposed backup file left in the web root (`/backup.zip`) | Just... request the file | Don't leave debug/backup artifacts on a live server |
| 5 | Verbose error page that leaks a flag in a stack trace | Trigger an error on purpose | Never show raw errors to the outside world |
| 6 | Unauthenticated "admin action" endpoint (works with no login at all) | Call the endpoint directly | Authentication has to be checked on *every* sensitive endpoint, not just the login form |
| 7 *(hardest, optional)* | Simulated command-injection field (safely faked — no real shell is ever run) | Notice unsanitized input reflected back | Why raw user input near a system call is dangerous |

Each flag is a short string like `FLAG{default_creds_are_forever}` — thematic, memorable, and easy to read off an ESP32's Serial console.

---

## 5. The ESP32 "toolkit" (pre-built, no coding)

Same philosophy as every existing lab here: flash it, watch the Console, done.

| Tool firmware | What it does |
|---|---|
| **Recon Scanner** | Connects to the Pi's Wi-Fi, probes a handful of common ports/paths, prints what it finds to Serial — the "where do I even start" tool |
| **Flag Prober** | Automatically tries the known vulnerability patterns (default creds, ID increment, common backup filenames) against the Pi and prints any flag it captures |
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

## 9. Safety / ethics (same rules as every other lab in this repo)

- Runs on a network this class controls end-to-end — never the school's production Wi-Fi
- Every "victim" is the instructor's own Raspberry Pi — no third-party system is ever touched
- Consent + code-of-conduct briefing happens before power-on, same as every other lab
- Flags/vulnerabilities are reset between class periods so nothing carries over or gets genuinely broken

---

## 10. What was built

- [pi-server/app.py](pi-server/app.py) — the Flask target app: all 7 vulnerabilities, the scoreboard, flag submission, and per-vulnerability patch buttons. [pi-server/README.md](pi-server/README.md) covers running it and resetting between class periods.
- [firmware/ctf-recon-scanner/](firmware/ctf-recon-scanner/) — flash-and-go ESP32 tool that scans the target Pi's common ports/paths
- [firmware/ctf-flag-prober/](firmware/ctf-flag-prober/) — flash-and-go ESP32 tool that automatically tries every known vulnerability pattern and prints any flag it captures
- A new **"Whole-Class Capture the Flag"** section on the [flashing site](https://burak-akdogan.github.io/Cyber-Security-ESP32-EDU/), with both tools flashable the same way as every other lab (their Wi-Fi form also asks for the target Pi's IP address)
- [docs/ctf-rules.html](docs/ctf-rules.html) — the student-facing rules page (printable/downloadable from the site, no flag contents included)

Both new sketches live under `firmware/`, so the existing GitHub Actions workflow picks them up and publishes them automatically on the next push — no workflow changes were needed.
