# Classroom CTF — Teacher Guide
### Full steps, answer key, and troubleshooting

> 🚨 **FOR EDUCATIONAL PURPOSES ONLY.** Run this only on a network your classroom fully controls. See [CLASSROOM-CTF-EVENT-en.md](CLASSROOM-CTF-EVENT-en.md) for the full design rationale — this file is the run-it-today reference. Give students [CLASSROOM-CTF-STUDENT-GUIDE-en.md](CLASSROOM-CTF-STUDENT-GUIDE-en.md) (it has no flag answers).

---

## 1. Timing (fits one class period)

| Phase | Length |
|---|---|
| Setup (before students arrive) | 10–15 min |
| Briefing + code of conduct | 5 min |
| Live round | 25–30 min |
| Debrief | 10 min |

---

## 2. Materials

- 1 Raspberry Pi 5 + power + monitor/projector
- The class's ESP32 DevKit V1 fleet
- A device per student (or per pair) with Wi-Fi, to reach the scoreboard

---

## 3. Setup checklist (before students arrive)

Full first-time setup (Imager, OS, hotspot, Flask) is in
[pi-server/README.md](pi-server/README.md). Once that's done once, each
session is just:

1. Power on the Pi.
2. Re-create the hotspot (does not survive a reboot):
   ```bash
   sudo nmcli device wifi hotspot ifname wlan0 ssid "ClassroomCTF" password "cyberclass123"
   ip a show wlan0   # confirm the IP, e.g. 10.42.0.1
   ```
3. Start the server:
   ```bash
   cd ~/Cyber-Security-ESP32-EDU/pi-server
   source venv/bin/activate
   python3 app.py
   ```
4. On the Pi itself, open `http://localhost:8080/` to confirm the dashboard loads, then project it.
5. Write on the board (or a slide): **SSID, password, and the Pi's IP address** — students need all three.
6. Reset state so the round starts clean:
   ```bash
   curl -X POST http://localhost:8080/admin/reset-all -d "pin=1234"
   ```

---

## 4. Splitting the class

**Flexible teams (simplest):** 3–5 teams of 3–5 students, each team does both finding and patching, racing each other. No extra briefing needed beyond the student guide.

**Red vs. Blue (more structured, needs 15 students ≈ 8/7 split):**
- **Red Team (attack, ~8 students):** share the ESP32 fleet, run Recon Scanner + Flag Prober, submit flags for points.
- **Blue Team (defense, ~7 students):** no ESP32 needed — they watch the scoreboard and click **Patch** the moment a vulnerability looks open (or even pre-emptively, before Red finds anything — that's a legitimate "harden first" strategy). Patch scoring does **not** require having found the flag first, so Blue can score purely by defending.
- Brief both sides that this is the *only* difference — Blue could technically use the ESP32 tools too, but ask them not to, to keep the exercise meaningful.

**Individual mode (everyone attacks, no teams):** no code changes needed for
this — the "team name" field is really just a label. Have every student type
their **own name** instead of a team name when submitting a flag or
patching. Each name becomes its own row on the scoreboard, scored the same
way (first to submit a flag = 100, later students = 50, patching = +75) —
completely automatic the instant a valid flag is submitted, no grading or
waiting. Good for a smaller class or when you'd rather rank students than
teams.

---

## 5. Session script

1. **Briefing (5 min):** Explain the format, hand out/display the student guide, confirm everyone has joined the Wi-Fi, run the code-of-conduct reminder ("only the Pi is a valid target").
2. **Live round (25–30 min):** Let it run. Walk the room, help with stuck ESP32 flashes (see Troubleshooting), and watch the scoreboard for pacing — if everything's patched with 10+ minutes left, that's your cue to move to debrief early.
3. **Debrief (10 min):** Go vulnerability by vulnerability (see §7) — ask which team found/patched it and what they did, then give the one-line real-world lesson.

---

## 6. Answer key — how each vulnerability is actually solved

**Nothing runs automatically.** The Flag Prober ESP32 tool is a menu-driven
console — a student picks a challenge and types a command (via the
follow-up box under the console on the site), reads the response, and tries
again with a different guess. This is deliberate: it's the difference
between "plug in a board and a flag falls out" (too easy, not the point)
and actually working through each vulnerability.

| # | Vulnerability | ESP32 command | Direct URL equivalent | Flag |
|---|---|---|---|---|
| 1 | Default admin credentials | `1 admin:admin` | `POST http://<pi-ip>:8080/login` (`username=admin&password=admin`) | `FLAG{default_creds_are_forever}` |
| 2 | Hidden unlinked page | `2 hidden` — student must guess the path name (nothing links to it); wrong guesses just 404 | `GET http://<pi-ip>:8080/hidden` | `FLAG{security_through_obscurity_isnt}` |
| 3 | IDOR | `3 2` (id=1 and id=3 are decoys; id=2 has the flag) | `GET http://<pi-ip>:8080/api/note?id=2` | `FLAG{access_control_matters}` |
| 4 | Exposed backup file | `4 backup.zip` — student must guess the filename; wrong guesses just 404 | `GET http://<pi-ip>:8080/backup.zip` | `FLAG{never_leave_backups_public}` |
| 5 | Verbose error disclosure | `5 10 0` (or any `a b` where b=0) | `GET http://<pi-ip>:8080/api/divide?a=10&b=0` (division by zero triggers the "traceback") | `FLAG{verbose_errors_leak_secrets}` |
| 6 | Unauthenticated admin endpoint | `6` | `POST http://<pi-ip>:8080/api/admin/reset` (no login needed at all) | `FLAG{check_auth_on_every_endpoint}` |
| 7 | Simulated command injection | `7 ;whoami` | `GET http://<pi-ip>:8080/api/ping?host=;whoami` — any of `;`, `&&`, `\|`, or `` ` `` in the `host` param triggers it. **Nothing real is ever executed** — it's a scripted response, safe by design. | `FLAG{never_trust_raw_input_near_a_shell}` |

Only #2, #4, and #6 don't require a guessed argument on the ESP32 side — but
#2 and #4 still require the student to type the *right path/filename*
themselves (`2`/`4` alone just prints a usage message). If a team can't find
#2 or #4, nudge them toward Recon Scanner or common wordlists (e.g. "admin,"
"secret," "hidden" for pages; "backup.zip," "backup.tar.gz," "db_backup.sql"
for files) rather than giving away the exact answer.

If a team is stuck on #1, suggest search terms like "most common default
router passwords." Typing `menu` on the Flag Prober console re-prints the
full command list at any time.

### What each Patch button actually does

| # | Patching it... |
|---|---|
| 1 | Disables the login endpoint entirely (503) — simulates "rotate the password" |
| 2 | Makes `/hidden` return 404 |
| 3 | Blocks any note id other than the requester's own (id 1) with 403 |
| 4 | Makes `/backup.zip` return 404 |
| 5 | Replaces the verbose traceback with a generic `internal server error` |
| 6 | Requires an `Authorization: Bearer classroom-admin` header — no more anonymous calls |
| 7 | Strips anything except letters/digits/`.`/`-` from the `host` param before "using" it |

---

## 7. Debrief talking points (one per vulnerability)

- **#1 Default creds:** *"How many devices in your house still have a factory-default password?"* — change defaults, always.
- **#2 Hidden page:** *"Not linked" isn't "not accessible."* Anyone who guesses or finds the URL gets in.
- **#3 IDOR:** The server trusted the client's word for *whose* data to show. Every request needs a server-side ownership check.
- **#4 Backup file:** Real breaches have happened from exactly this — a `.zip`, `.bak`, or `.old` file left in a public web folder.
- **#5 Verbose errors:** Debug info is for developers, not the public internet — always show generic errors in production.
- **#6 Unauth admin:** A login form on the front door means nothing if a side door has no lock at all.
- **#7 Injection:** *"What could go wrong if a service just... runs whatever you send it?"* — tie this to real injection attacks (SQL injection, command injection) if your course covers them.

---

## 8. Bonus: the DDoS demo (separate from flag-hunting)

A third ESP32 tool, **CTF · DDoS Flood**, exists for a standalone
attack/defense demo: instead of finding vulnerabilities, several boards
flood the Pi's own dashboard page with requests at once, and you (the
instructor) turn on a real mitigation and show it working. Run this as its
own activity, before or after the flag round — not at the same time (it
will make the flag round's dashboard sluggish for everyone).

**How to run it:**
1. Flash **3–5+ ESP32 boards** with CTF · DDoS Flood (more boards = a more
   convincing demo). Connect each to the event Wi-Fi with the Pi's target IP,
   same as any other CTF tool.
2. On each board's console, type `start`. All boards begin hammering the
   Pi's `/` page as fast as they can, forever, until told to stop.
3. Point everyone at the **Pi's own screen** (not any single board's
   console) — a banner near the top switches to **🔴 UNDER ATTACK** once the
   combined request rate crosses ~20 req/s, and a live `req/s` counter climbs.
4. Click **🛡️ Enable DDoS Protection** on the dashboard. The banner turns
   green, a `blocked` counter starts climbing, and (if the flood was heavy
   enough to slow the Pi down) the dashboard itself feels responsive again.
5. Type `stop` on each flooding board when you're done, then explain the fix
   (below) before moving on.

**How the fix actually works (for the debrief):** protection is a **per-IP
rate limit** — once enabled, any single device sending more than 15
requests per second gets an instant, cheap rejection (HTTP 429) instead of
being processed. Each ESP32 has its own IP address on the Wi-Fi, so this
throttles every flooding board individually without needing to tell "attack"
traffic apart from "real" traffic any other way. This is a real, common
DDoS mitigation technique (rate limiting / traffic shaping) — the same idea
behind Cloudflare-style "too many requests" pages. It's not perfect (a
large-enough botnet spread across enough IPs can still overwhelm a single
per-IP limit — worth raising if a student asks "couldn't they just use more
devices?").

The scoreboard, flag submission, and patch buttons are deliberately **never
rate-limited** — they're "control-plane" traffic, exempted so you can always
see the dashboard and flip protection on/off even at the worst of a flood.

---

## 9. Troubleshooting quick reference

| Symptom | Fix |
|---|---|
| Raspberry Pi Imager: "card in use by another program" | Cancel any Windows "format this disk?" popup (don't format), close File Explorer windows showing the card, or run Imager as Administrator |
| `hostname` command errors ("extra argument") | Don't type "hostname" as part of the command — use `ip a show wlan0` instead, it's more reliable |
| Browser shows something unrelated at "localhost" | `localhost` always means *the device you're using right now* — from a student's laptop/phone you must use the **Pi's real IP**, not `localhost` |
| `python3 app.py` fails to bind port 8080 | Something (often a previous run you forgot to stop) already holds it: `sudo lsof -i :8080`, then `sudo kill -9 <PID>`, then retry. If `lsof` shows nothing, the port's free — the real issue is `app.py` isn't actually running (check for `ModuleNotFoundError`, usually a not-activated `venv`) |
| Hotspot vanished / no students can join | It doesn't survive a Pi reboot — re-run the `nmcli device wifi hotspot ...` command from §3 |
| An ESP32 won't flash / bootloops after flashing | Unrelated to this exercise's code — usually an interrupted/incomplete flash. Retry, using "Erase device" if the installer offers it, without unplugging mid-flash |

---

## 10. Resetting between class periods

```bash
curl -X POST http://localhost:8080/admin/reset-all -d "pin=1234"
```

Change the PIN in `pi-server/app.py` if you want a non-default one. This wipes scores, found flags, un-patches every vulnerability, turns DDoS protection back off, and clears the traffic counters — ready for the next class.

---

## 11. Curriculum alignment (PLTW Cybersecurity)

| This event maps to... |
|---|
| Unit 2, Project 2.2.4 "Secure the Server" / Project 2.3.4 "Find the Exploits" — this event *is* those two projects, live |
| Unit 3 "Analyze and Defend Network Attacks," "Eradicate the Vulnerabilities" |
| Unit 3, Activity 3.2.4 "Analyze and Defend Network Attacks" (the DDoS demo — real traffic, a real rate-limiting mitigation) |
| Unit 1, Activity 1.1.2 "Password Protection and Authentication" (vulnerability #1) |
| Unit 1, Activity 1.1.1 "Cybersecurity and Code of Conduct" (the consent briefing) |

See [CLASSROOM-CTF-EVENT-en.md §8](CLASSROOM-CTF-EVENT-en.md#8-ties-to-the-pltw-cybersecurity-course) for more detail.
