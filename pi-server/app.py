#!/usr/bin/env python3
# Classroom CTF target app -- runs on the Raspberry Pi.
# See CLASSROOM-CTF-EVENT-en.md and pi-server/README.md for the full picture.
#
# Educational use only: this app is deliberately full of common, realistic
# web-server vulnerabilities so a class can find and then patch them. Run it
# only on a network your classroom fully controls, never on a production or
# internet-facing machine.

from flask import Flask, request, jsonify
import time
import collections
import random

app = Flask(__name__)

# Shared PIN for every instructor-only action (dashboard resets, and the
# Cyber Town/DDoS control buttons below) -- change this before running a
# real class if you want it to be less guessable.
INSTRUCTOR_PIN = "1234"


def pin_ok():
    return request.form.get("pin", "") == INSTRUCTOR_PIN


FLAGS = {
    1: "FLAG{default_creds_are_forever}",
    2: "FLAG{security_through_obscurity_isnt}",
    3: "FLAG{access_control_matters}",
    4: "FLAG{never_leave_backups_public}",
    5: "FLAG{verbose_errors_leak_secrets}",
    6: "FLAG{check_auth_on_every_endpoint}",
    7: "FLAG{never_trust_raw_input_near_a_shell}",
}

VULN_NAMES = {
    1: "Default Admin Credentials",
    2: "Hidden Unlinked Page",
    3: "Insecure Direct Object Reference",
    4: "Exposed Backup File",
    5: "Verbose Error Disclosure",
    6: "Unauthenticated Admin Endpoint",
    7: "Simulated Command Injection",
}

patched = {i: False for i in FLAGS}
teams = {}       # team name -> {"score": int, "found": set(), "patched": set()}
events = []      # recent activity, newest first


def get_team(name):
    if name not in teams:
        teams[name] = {"score": 0, "found": set(), "patched": set()}
    return teams[name]


def log(msg):
    events.insert(0, {"t": time.strftime("%H:%M:%S"), "msg": msg})
    del events[50:]


# ---------------------------------------------------------------------------
# Classroom DDoS demo: every request is timestamped so the dashboard can show
# a live requests/sec figure. When ddos_protection is on, any single IP
# sending too many requests too fast gets a cheap 429 instead of being
# processed -- a real, explainable mitigation (per-IP rate limiting).
# ---------------------------------------------------------------------------
TRAFFIC_WINDOW = 2.0      # seconds of history used to compute live req/s
ATTACK_THRESHOLD = 20     # req/s at or above this counts as "under attack"
RATE_LIMIT_WINDOW = 1.0   # seconds
RATE_LIMIT_MAX = 15       # max requests per IP per RATE_LIMIT_WINDOW when protection is on

traffic_times = collections.deque()
ip_times = collections.defaultdict(collections.deque)
ip_blocked = collections.defaultdict(int)
ddos_protection = False
blocked_count = 0

# Rolling log of the most recent requests to "/" (the DDoS demo's actual
# target) -- newest first, capped so it can never grow unbounded during a
# real flood. Only "/" is logged (not the CTF vulnerability paths) so this
# never leaks one team's exploitation strategy to everyone watching.
request_log = collections.deque(maxlen=30)

# Control-plane traffic (the dashboard's own polling, flag submission,
# patching, admin reset) is never counted or blocked -- only the public "/"
# page is the attack surface here. This guarantees the instructor can always
# see the dashboard and flip protection on/off, even mid-flood.
_RATE_LIMIT_EXEMPT_PREFIXES = ("/api/state", "/api/ddos-protection", "/admin/", "/submit", "/patch/", "/game/")


@app.before_request
def _traffic_guard():
    global blocked_count
    if request.path.startswith(_RATE_LIMIT_EXEMPT_PREFIXES):
        return

    now = time.time()
    traffic_times.append(now)
    cutoff = now - TRAFFIC_WINDOW
    while traffic_times and traffic_times[0] < cutoff:
        traffic_times.popleft()

    ip = request.remote_addr or "unknown"
    log_entry = None
    if request.path == "/":
        log_entry = {"t": time.strftime("%H:%M:%S"), "ip": ip, "blocked": False}
        request_log.appendleft(log_entry)

    if ddos_protection:
        dq = ip_times[ip]
        dq.append(now)
        ip_cutoff = now - RATE_LIMIT_WINDOW
        while dq and dq[0] < ip_cutoff:
            dq.popleft()
        if len(dq) > RATE_LIMIT_MAX:
            blocked_count += 1
            ip_blocked[ip] += 1
            if log_entry is not None:
                log_entry["blocked"] = True
            return jsonify(error="rate limited -- too many requests from this device"), 429


def current_traffic():
    now = time.time()
    recent = sum(1 for t in traffic_times if now - t <= TRAFFIC_WINDOW)
    attackers = []
    if ddos_protection:
        ip_cutoff = now - RATE_LIMIT_WINDOW
        for ip, dq in ip_times.items():
            while dq and dq[0] < ip_cutoff:
                dq.popleft()
            rps = len(dq)
            blocked = ip_blocked.get(ip, 0)
            if rps > 0 or blocked > 0:
                attackers.append({"ip": ip, "rps": rps, "blocked": blocked})
        attackers.sort(key=lambda a: (-a["rps"], -a["blocked"]))
        attackers = attackers[:10]
    return {
        "rps": round(recent / TRAFFIC_WINDOW, 1),
        "underAttack": (recent / TRAFFIC_WINDOW) >= ATTACK_THRESHOLD,
        "protection": ddos_protection,
        "blocked": blocked_count,
        "attackers": attackers,
        "log": list(request_log),
    }


# ---------------------------------------------------------------------------
# Vulnerability #1: default admin credentials
# ---------------------------------------------------------------------------
LOGIN_HTML = """
<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Admin Login</title>
<style>
  body{background:#0b0f14;color:#d7e2ea;font-family:system-ui,sans-serif;margin:0;padding:40px 20px;display:flex;justify-content:center}
  .card{background:#131a22;border:1px solid #24313d;border-radius:12px;padding:28px;max-width:340px;width:100%}
  h1{font-size:18px;color:#8fb3c9;margin:0 0 18px}
  label{display:block;font-size:12px;color:#9fb2c0;margin:14px 0 4px}
  input{width:100%;padding:10px;border-radius:8px;border:1px solid #24313d;background:#0f151c;color:#e2e8f0;box-sizing:border-box}
  button{width:100%;margin-top:18px;padding:11px;border:0;border-radius:8px;background:#38bdf8;color:#04121a;font-weight:700}
  .msg{margin-top:14px;font-size:13px;color:#f87171}
</style></head><body>
  <div class="card">
    <h1>Admin Portal</h1>
    <form method="post">
      <label>Username</label><input name="username" autocomplete="off">
      <label>Password</label><input name="password" type="password" autocomplete="off">
      <button type="submit">Sign in</button>
    </form>
    {message}
  </div>
</body></html>
"""


@app.route("/login", methods=["GET", "POST"])
def login():
    # .replace() on purpose, not .format() -- the CSS above is full of literal
    # {curly braces}, which .format() would misread as format fields.
    if request.method == "GET":
        return LOGIN_HTML.replace("{message}", "")
    if patched[1]:
        return LOGIN_HTML.replace(
            "{message}", '<div class="msg">Login temporarily disabled by an administrator.</div>'
        ), 503
    u = request.form.get("username", "")
    p = request.form.get("password", "")
    if u == "admin" and p == "admin":
        return f"<pre>Welcome, admin!\n{FLAGS[1]}</pre>"
    return LOGIN_HTML.replace("{message}", '<div class="msg">Invalid credentials.</div>'), 401


# ---------------------------------------------------------------------------
# Vulnerability #2: hidden, unlinked page
# ---------------------------------------------------------------------------
@app.route("/hidden")
def hidden():
    if patched[2]:
        return "Not found", 404
    return f"<pre>You found the hidden page.\n{FLAGS[2]}</pre>"


# ---------------------------------------------------------------------------
# Vulnerability #3: IDOR (insecure direct object reference)
# ---------------------------------------------------------------------------
NOTES = {
    1: "Grocery list: eggs, milk, bread",
    2: f"Admin's private note -- do not share: {FLAGS[3]}",
    3: "Remember to water the plants",
}


@app.route("/api/note")
def note():
    raw_id = request.args.get("id", "1")
    try:
        note_id = int(raw_id)
    except ValueError:
        return jsonify(error="id must be a number"), 400
    if patched[3] and note_id != 1:
        return jsonify(error="access denied: ownership check enabled"), 403
    return jsonify(id=note_id, note=NOTES.get(note_id, "no such note"))


# ---------------------------------------------------------------------------
# Vulnerability #4: exposed backup file
# ---------------------------------------------------------------------------
@app.route("/backup.zip")
def backup():
    if patched[4]:
        return "Not found", 404
    return (
        f"[fake backup contents -- classroom demo only]\n"
        f"admin_password=hunter2\n"
        f"{FLAGS[4]}\n"
    ), 200, {"Content-Type": "text/plain"}


# ---------------------------------------------------------------------------
# Vulnerability #5: verbose error disclosure
# ---------------------------------------------------------------------------
@app.route("/api/divide")
def divide():
    try:
        a = float(request.args.get("a", "10"))
        b = float(request.args.get("b", "0"))
    except ValueError:
        return jsonify(error="a and b must be numbers"), 400

    if b == 0:
        if patched[5]:
            return jsonify(error="internal server error"), 500
        # Deliberately fake-verbose response -- no real exception is raised.
        return (
            "Traceback (most recent call last):\n"
            "  File \"app.py\", line 142, in divide\n"
            "    return jsonify(result=a / b)\n"
            "ZeroDivisionError: float division by zero\n"
            f"DEBUG_SECRET={FLAGS[5]}\n"
        ), 500, {"Content-Type": "text/plain"}
    return jsonify(result=a / b)


# ---------------------------------------------------------------------------
# Vulnerability #6: unauthenticated admin action endpoint
# ---------------------------------------------------------------------------
@app.route("/api/admin/reset", methods=["POST"])
def admin_reset():
    if patched[6]:
        auth = request.headers.get("Authorization", "")
        if auth != "Bearer classroom-admin":
            return jsonify(error="unauthorized"), 401
    return jsonify(status="device reset", flag=FLAGS[6])


# ---------------------------------------------------------------------------
# Vulnerability #7: simulated command injection (never runs a real command)
# ---------------------------------------------------------------------------
@app.route("/api/ping")
def ping():
    host = request.args.get("host", "")
    if patched[7]:
        safe = "".join(c for c in host if c.isalnum() or c in ".-")
        return jsonify(output=f"pinging {safe or 'localhost'} ...")
    if any(c in host for c in [";", "&&", "|", "`"]):
        return jsonify(output=f"64 bytes from 127.0.0.1: icmp_seq=1\n[injected] {FLAGS[7]}")
    return jsonify(output=f"pinging {host or 'localhost'} ...")


# ---------------------------------------------------------------------------
# Scoreboard: submit a flag, patch a vulnerability, read live state
# ---------------------------------------------------------------------------
@app.route("/submit", methods=["POST"])
def submit():
    name = request.form.get("team", "").strip()
    code = request.form.get("flag", "").strip()
    if not name:
        return jsonify(error="team name required"), 400
    t = get_team(name)
    for vid, flag in FLAGS.items():
        if code == flag:
            if vid in t["found"]:
                return jsonify(status="already_found")
            first = not any(vid in other["found"] for other in teams.values())
            points = 100 if first else 50
            t["found"].add(vid)
            t["score"] += points
            log(f"{name} found flag #{vid} ({VULN_NAMES[vid]}) [+{points}]")
            return jsonify(status="correct", points=points, vulnerability=VULN_NAMES[vid])
    return jsonify(status="wrong")


@app.route("/patch/<int:vid>", methods=["POST"])
def patch(vid):
    if vid not in FLAGS:
        return jsonify(error="no such vulnerability"), 404
    if patched[vid]:
        return jsonify(error="already patched"), 400
    name = request.form.get("team", "").strip()
    patched[vid] = True
    # Patching earns the bonus on its own -- a pure-defense team never
    # "finds" a flag themselves, so the bonus can't depend on that.
    if name:
        t = get_team(name)
        t["score"] += 75
        t["patched"].add(vid)
        log(f"{name} PATCHED #{vid} ({VULN_NAMES[vid]}) [+75]")
    else:
        log(f"#{vid} ({VULN_NAMES[vid]}) patched (no team credited)")
    return jsonify(status="patched")


@app.route("/api/state")
def state():
    board = sorted(
        (
            {
                "team": name,
                "score": t["score"],
                "found": len(t["found"]),
                "patched": len(t["patched"]),
            }
            for name, t in teams.items()
        ),
        key=lambda row: -row["score"],
    )
    vulns = [
        {"id": i, "name": VULN_NAMES[i], "patched": patched[i]}
        for i in sorted(FLAGS)
    ]
    return jsonify(board=board, vulns=vulns, events=events[:15], traffic=current_traffic())


@app.route("/api/ddos-protection", methods=["POST"])
def toggle_ddos_protection():
    global ddos_protection
    ddos_protection = request.form.get("enabled", "") == "true"
    log(f"DDoS protection {'ENABLED' if ddos_protection else 'disabled'} by instructor")
    return jsonify(status="ok", protection=ddos_protection)


# ---------------------------------------------------------------------------
# Instructor-only reset between class periods (not linked from the UI)
# ---------------------------------------------------------------------------
@app.route("/admin/reset-all", methods=["POST"])
def reset_all():
    global ddos_protection, blocked_count
    if request.form.get("pin", "") != "1234":
        return jsonify(error="wrong pin"), 403
    teams.clear()
    events.clear()
    for k in patched:
        patched[k] = False
    traffic_times.clear()
    ip_times.clear()
    ip_blocked.clear()
    request_log.clear()
    ddos_protection = False
    blocked_count = 0
    log("--- round reset by instructor ---")
    return jsonify(status="reset")


# ---------------------------------------------------------------------------
# Cyber Town -- a Mafia / Town-of-Salem style social deduction game, also
# hosted on this Pi. Fully separate state and routes from the CTF above (own
# player dict, own phase machine) so nothing here can break the flag-hunting
# round, or vice versa.
#
# Each ESP32 is one anonymous player, identified only by its Wi-Fi MAC
# address. Roles (attacker / defender / civilian) are assigned secretly by
# the instructor and never sent to any device other than the player it
# belongs to -- the projected dashboard only ever reveals a player's role
# once that player is eliminated, or the game is over.
# ---------------------------------------------------------------------------
GAME_ATTACKER = "attacker"
GAME_DEFENDER = "defender"
GAME_CIVILIAN = "civilian"
GAME_ROLE_LABEL = {GAME_ATTACKER: "Attacker", GAME_DEFENDER: "Defender", GAME_CIVILIAN: "Civilian"}

game_players = {}        # mac -> {"num", "name", "role", "alive"}
game_next_num = 1
game_phase = "lobby"     # lobby | night | day_vote | game_over
game_round = 0
game_winner = None       # None | "town" | "attackers" | "instructor"
game_night_actions = {}  # mac -> {"type": "attack"|"defend", "target": num}
game_votes = {}          # mac -> target num
game_events = []


def game_log(msg):
    game_events.insert(0, {"t": time.strftime("%H:%M:%S"), "msg": msg})
    del game_events[50:]


def game_player_by_num(num):
    for p in game_players.values():
        if p["num"] == num:
            return p
    return None


def game_check_winner():
    alive_attackers = sum(1 for p in game_players.values() if p["alive"] and p["role"] == GAME_ATTACKER)
    alive_town = sum(1 for p in game_players.values() if p["alive"] and p["role"] != GAME_ATTACKER)
    if alive_attackers == 0:
        return "town"
    if alive_attackers >= alive_town:
        return "attackers"
    return None


@app.route("/game/register", methods=["POST"])
def game_register():
    global game_next_num
    mac = request.form.get("mac", "").strip()
    if not mac:
        return jsonify(error="missing mac"), 400
    if mac not in game_players and game_phase != "lobby":
        return jsonify(error="a round is already in progress -- wait for the next round"), 409
    if mac not in game_players:
        num = game_next_num
        game_next_num += 1
        game_players[mac] = {"num": num, "name": f"Player {num}", "role": None, "alive": True}
        game_log(f"Player {num} joined the lobby")
    p = game_players[mac]
    return jsonify(num=p["num"], name=p["name"], phase=game_phase)


@app.route("/game/name", methods=["POST"])
def game_set_name():
    mac = request.form.get("mac", "").strip()
    name = request.form.get("name", "").strip()[:24]
    if mac not in game_players or not name:
        return jsonify(error="not registered or empty name"), 400
    game_players[mac]["name"] = name
    game_log(f"Player {game_players[mac]['num']} is now known as {name}")
    return jsonify(status="ok")


@app.route("/game/state")
def game_state():
    mac = request.args.get("mac", "").strip()
    p = game_players.get(mac)
    if not p:
        return jsonify(error="not registered"), 404
    result = {
        "phase": game_phase,
        "round": game_round,
        "num": p["num"],
        "name": p["name"],
        "alive": p["alive"],
        "role": GAME_ROLE_LABEL.get(p["role"]) if p["role"] else None,
    }
    if game_phase == "game_over":
        result["winner"] = game_winner
    return jsonify(result)


@app.route("/game/state-all")
def game_state_all():
    roster = []
    for p in sorted(game_players.values(), key=lambda x: x["num"]):
        reveal = (not p["alive"]) or game_phase == "game_over"
        roster.append({
            "num": p["num"],
            "name": p["name"],
            "alive": p["alive"],
            "role": GAME_ROLE_LABEL.get(p["role"]) if (reveal and p["role"]) else None,
        })
    alive_attackers = sum(1 for p in game_players.values() if p["alive"] and p["role"] == GAME_ATTACKER)
    alive_town = sum(1 for p in game_players.values() if p["alive"] and p["role"] != GAME_ATTACKER)
    return jsonify(
        phase=game_phase, round=game_round, winner=game_winner,
        roster=roster, events=game_events,
        aliveAttackers=alive_attackers, aliveTown=alive_town,
    )


@app.route("/game/start", methods=["POST"])
def game_start():
    global game_phase, game_round
    if game_phase != "lobby":
        return jsonify(error="game already in progress"), 400
    players = list(game_players.values())
    if len(players) < 3:
        return jsonify(error="need at least 3 players"), 400

    try:
        num_attackers = int(request.form.get("attackers", 0))
        num_defenders = int(request.form.get("defenders", 0))
    except ValueError:
        return jsonify(error="attackers/defenders must be numbers"), 400
    if num_attackers < 1 or num_defenders < 0 or num_attackers + num_defenders >= len(players):
        return jsonify(error="role counts don't leave room for civilians"), 400

    random.shuffle(players)
    for p in players[:num_attackers]:
        p["role"] = GAME_ATTACKER
    for p in players[num_attackers:num_attackers + num_defenders]:
        p["role"] = GAME_DEFENDER
    for p in players[num_attackers + num_defenders:]:
        p["role"] = GAME_CIVILIAN

    game_phase = "night"
    game_round = 1
    game_night_actions.clear()
    game_votes.clear()
    game_log(f"--- Game started: {num_attackers} attacker(s), {num_defenders} defender(s), "
             f"{len(players) - num_attackers - num_defenders} civilian(s) ---")
    game_log("Night 1 has begun")
    return jsonify(status="started")


@app.route("/game/attack", methods=["POST"])
def game_attack():
    mac = request.form.get("mac", "").strip()
    p = game_players.get(mac)
    if not p or not p["alive"] or p["role"] != GAME_ATTACKER or game_phase != "night":
        return jsonify(error="not allowed right now"), 400
    try:
        target = int(request.form.get("target", ""))
    except ValueError:
        return jsonify(error="bad target"), 400
    game_night_actions[mac] = {"type": "attack", "target": target}
    return jsonify(status="ok")


@app.route("/game/defend", methods=["POST"])
def game_defend():
    mac = request.form.get("mac", "").strip()
    p = game_players.get(mac)
    if not p or not p["alive"] or p["role"] != GAME_DEFENDER or game_phase != "night":
        return jsonify(error="not allowed right now"), 400
    try:
        target = int(request.form.get("target", ""))
    except ValueError:
        return jsonify(error="bad target"), 400
    game_night_actions[mac] = {"type": "defend", "target": target}
    return jsonify(status="ok")


@app.route("/game/resolve-night", methods=["POST"])
def game_resolve_night():
    global game_phase, game_winner
    if game_phase != "night":
        return jsonify(error="not night"), 400

    attacked = set()
    defended = set()
    for mac, action in game_night_actions.items():
        p = game_players.get(mac)
        if not p or not p["alive"]:
            continue
        if action["type"] == "attack" and p["role"] == GAME_ATTACKER:
            attacked.add(action["target"])
        elif action["type"] == "defend" and p["role"] == GAME_DEFENDER:
            defended.add(action["target"])

    for target_num in attacked:
        target = game_player_by_num(target_num)
        if not target or not target["alive"]:
            continue
        if target_num in defended:
            game_log(f"An attack on Player {target_num} ({target['name']}) was blocked!")
        else:
            target["alive"] = False
            game_log(f"Player {target_num} ({target['name']}) was eliminated overnight! "
                     f"Role: {GAME_ROLE_LABEL.get(target['role'], 'Unknown')}")

    game_night_actions.clear()
    winner = game_check_winner()
    if winner:
        game_phase = "game_over"
        game_winner = winner
        game_log(f"--- GAME OVER: {'Town' if winner == 'town' else 'Attackers'} win! ---")
    else:
        game_phase = "day_vote"
        game_log("Day has broken -- discuss, then vote.")
    return jsonify(status="ok", phase=game_phase)


@app.route("/game/vote", methods=["POST"])
def game_vote():
    mac = request.form.get("mac", "").strip()
    p = game_players.get(mac)
    if not p or not p["alive"] or game_phase != "day_vote":
        return jsonify(error="not allowed right now"), 400
    try:
        target = int(request.form.get("target", ""))
    except ValueError:
        return jsonify(error="bad target"), 400
    game_votes[mac] = target
    return jsonify(status="ok")


@app.route("/game/resolve-vote", methods=["POST"])
def game_resolve_vote():
    global game_phase, game_round, game_winner
    if game_phase != "day_vote":
        return jsonify(error="not voting"), 400

    tally = collections.Counter(game_votes.values())
    game_votes.clear()
    if tally:
        top_count = max(tally.values())
        top_targets = [num for num, count in tally.items() if count == top_count]
        if len(top_targets) == 1:
            target = game_player_by_num(top_targets[0])
            if target and target["alive"]:
                target["alive"] = False
                game_log(f"Player {target['num']} ({target['name']}) was voted out! "
                         f"Role: {GAME_ROLE_LABEL.get(target['role'], 'Unknown')}")
        else:
            game_log("Vote tied -- no one is eliminated.")
    else:
        game_log("No votes cast -- no one is eliminated.")

    winner = game_check_winner()
    if winner:
        game_phase = "game_over"
        game_winner = winner
        game_log(f"--- GAME OVER: {'Town' if winner == 'town' else 'Attackers'} win! ---")
    else:
        game_round += 1
        game_phase = "night"
        game_night_actions.clear()
        game_log(f"Night {game_round} has begun")
    return jsonify(status="ok", phase=game_phase)


@app.route("/game/new-round", methods=["POST"])
def game_new_round():
    global game_phase, game_round, game_winner
    if game_phase != "game_over":
        return jsonify(error="game still in progress"), 400
    for p in game_players.values():
        p["role"] = None
        p["alive"] = True
    game_night_actions.clear()
    game_votes.clear()
    game_phase = "lobby"
    game_round = 0
    game_winner = None
    game_log("--- New round -- back to the lobby, same players ---")
    return jsonify(status="ok")


@app.route("/game/force-end", methods=["POST"])
def game_force_end():
    global game_phase, game_winner
    if request.form.get("pin", "") != "1234":
        return jsonify(error="wrong pin"), 403
    game_phase = "game_over"
    game_winner = "instructor"
    game_log("--- Game ended early by instructor -- roles revealed ---")
    return jsonify(status="ok")


@app.route("/game/reset", methods=["POST"])
def game_reset():
    global game_phase, game_round, game_winner, game_next_num
    if request.form.get("pin", "") != "1234":
        return jsonify(error="wrong pin"), 403
    game_players.clear()
    game_next_num = 1
    game_night_actions.clear()
    game_votes.clear()
    game_events.clear()
    game_phase = "lobby"
    game_round = 0
    game_winner = None
    game_log("--- Cyber Town reset by instructor ---")
    return jsonify(status="reset")


# ---------------------------------------------------------------------------
# The projected dashboard
# ---------------------------------------------------------------------------
DASHBOARD_HTML = """
<!DOCTYPE html><html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Classroom CTF -- Live Scoreboard</title>
<style>
  :root{
    color-scheme:dark;
    --bg:#020504; --panel:rgba(5,14,10,.94); --panel-border:rgba(0,255,157,.22);
    --ink:#d8fff0; --ink-dim:#7fcbaa; --ink-dimmer:#4d7a63;
    --accent:#00fff2; --accent-2:#ff2079; --good:#00ff9d; --bad:#ff3b6b; --warn:#f0ff5c;
  }
  *{box-sizing:border-box}
  html,body{height:100%}
  body{
    background:var(--bg); color:var(--ink); margin:0; padding:22px clamp(14px,3vw,32px) 40px;
    font-family:Consolas,"Courier New",ui-monospace,monospace;
    position:relative; overflow-x:hidden;
  }
  .scanlines{
    position:fixed; inset:0; pointer-events:none; z-index:5;
    background:repeating-linear-gradient(0deg, rgba(0,255,157,.05) 0px, rgba(0,255,157,.05) 1px, transparent 1px, transparent 3px);
    mix-blend-mode:overlay;
  }
  .scanlines::after{
    content:''; position:fixed; top:-40%; left:0; right:0; height:40%;
    background:linear-gradient(rgba(0,255,242,.05), transparent 80%);
    animation:scanMove 6s linear infinite;
    will-change:transform;
  }
  @keyframes scanMove{ 0%{transform:translateY(0)} 100%{transform:translateY(350%)} }

  .topbar{display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:14px; margin-bottom:6px}
  .topbar-spacer{visibility:hidden}
  @media (max-width:700px){
    .topbar{display:flex; flex-direction:column; text-align:center}
    .live{justify-self:auto}
  }

  h1{font-size:clamp(18px,2.6vw,25px); margin:0; display:flex; align-items:center; gap:10px; position:relative}
  .glitch{ position:relative; color:var(--ink) }
  .glitch::before, .glitch::after{
    content:attr(data-text); position:absolute; left:24px; top:0; width:100%; height:100%;
    overflow:hidden; background:transparent;
  }
  .glitch::before{ color:var(--accent-2); clip-path:inset(0 0 65% 0); animation:glitchTop 3.6s infinite linear alternate-reverse }
  .glitch::after{ color:var(--accent); clip-path:inset(65% 0 0 0); animation:glitchBot 2.7s infinite linear alternate-reverse }
  @keyframes glitchTop{ 0%,92%,100%{transform:translate(0,0)} 93%{transform:translate(-2px,-1px)} 95%{transform:translate(2px,1px)} 97%{transform:translate(-1px,1px)} }
  @keyframes glitchBot{ 0%,90%,100%{transform:translate(0,0)} 91%{transform:translate(2px,1px)} 94%{transform:translate(-2px,-1px)} 96%{transform:translate(1px,-1px)} }

  .live{display:flex; align-items:center; gap:7px; font-size:12px; color:var(--ink-dim); justify-self:end}
  .dot{width:8px; height:8px; border-radius:50%; background:var(--good); box-shadow:0 0 8px var(--good); animation:pulse 1.6s ease-in-out infinite}
  .dot.lost{background:var(--bad); box-shadow:0 0 8px var(--bad); animation:none}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
  .sub{color:var(--ink-dim); font-size:13px; line-height:1.6; margin:10px 0 22px; max-width:760px}
  .sub b{color:var(--ink)}

  .layout{display:grid; grid-template-columns:1.2fr 1fr; gap:18px; align-items:start}
  @media (max-width:880px){.layout{grid-template-columns:1fr}}

  .panel{
    background:var(--panel); border:1px solid var(--panel-border); border-radius:14px; padding:18px;
    box-shadow:0 0 24px rgba(0,255,157,.05);
  }
  .panel h2{font-size:12px; color:var(--ink-dim); text-transform:uppercase; letter-spacing:.08em; margin:0 0 14px; font-weight:700}

  .board-row{
    display:flex; align-items:center; gap:12px; padding:10px 8px; border-radius:10px;
    border-bottom:1px solid var(--panel-border);
  }
  .board-row:last-child{border-bottom:none}
  .rank{
    width:26px; height:26px; border-radius:50%; display:flex; align-items:center; justify-content:center;
    font-size:12px; font-weight:800; background:rgba(0,255,157,.08); color:var(--ink-dim); flex-shrink:0;
  }
  .rank.r1{background:rgba(240,255,92,.18); color:var(--warn)}
  .rank.r2{background:rgba(0,255,242,.15); color:var(--accent)}
  .rank.r3{background:rgba(255,32,121,.15); color:var(--accent-2)}
  .board-name{flex:1; font-size:14px; font-weight:700; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
  .board-meta{font-size:11px; color:var(--ink-dimmer)}
  .board-score{font-size:18px; font-weight:800; color:var(--good); text-shadow:0 0 10px rgba(0,255,157,.5); font-variant-numeric:tabular-nums; min-width:56px; text-align:right}
  .empty-msg{color:var(--ink-dimmer); font-size:13px; padding:8px 0}

  .vuln-row{display:flex; align-items:center; gap:10px; padding:11px 0; border-bottom:1px solid var(--panel-border)}
  .vuln-row:last-child{border-bottom:none}
  .vuln-id{font-size:11px; color:var(--ink-dimmer); width:20px; flex-shrink:0}
  .vuln-name{font-size:13px; flex:1; min-width:0}
  .badge{font-size:10px; font-weight:700; letter-spacing:.03em; padding:3px 9px; border-radius:999px; white-space:nowrap}
  .badge.open{background:rgba(255,59,107,.14); color:var(--bad); border:1px solid rgba(255,59,107,.4)}
  .badge.patched{background:rgba(0,255,157,.12); color:var(--good); border:1px solid rgba(0,255,157,.4)}
  .patch-btn{
    padding:5px 12px; border-radius:7px; border:1px solid rgba(0,255,242,.4);
    background:rgba(0,255,242,.08); color:var(--accent); cursor:pointer; font-size:11px; font-weight:700;
    font-family:inherit; letter-spacing:.04em; text-transform:uppercase;
  }
  .patch-btn:hover{background:rgba(0,255,242,.18)}

  .status-dot{ width:8px; height:8px; border-radius:50%; flex-shrink:0; display:inline-block }
  .status-dot.good{ background:var(--good); box-shadow:0 0 8px var(--good) }
  .status-dot.bad{ background:var(--bad); box-shadow:0 0 8px var(--bad); animation:pulse 1.2s ease-in-out infinite }

  .events{font-size:12px; color:var(--ink-dim); max-height:220px; overflow-y:auto}
  .events div{padding:5px 0; border-bottom:1px solid var(--panel-border)}
  .events div:last-child{border-bottom:none}

  .submit-box{margin-top:20px; padding-top:18px; border-top:1px solid var(--panel-border)}
  .submit-box input{
    width:100%; margin-bottom:9px; padding:10px 12px; border-radius:9px; border:1px solid var(--panel-border);
    background:rgba(0,10,6,.6); color:var(--ink); box-sizing:border-box; font-size:13.5px; font-family:inherit;
  }
  .submit-box input:focus{outline:none; border-color:var(--accent)}
  .submit-box button{
    width:100%; padding:11px; border-radius:9px; font-weight:800; font-size:13px; cursor:pointer;
    background:rgba(0,255,242,.08); border:1px solid rgba(0,255,242,.4); color:var(--accent);
    letter-spacing:.06em; text-transform:uppercase; font-family:inherit;
  }
  .submit-box button:hover{background:rgba(0,255,242,.18)}
  .result{margin-top:10px; font-size:13px; min-height:18px}
  .result.ok{color:var(--good)}
  .result.bad{color:var(--bad)}

  .traffic-banner{
    margin:0 0 16px; padding:16px 20px; border-radius:14px;
    border:1px solid var(--panel-border); background:var(--panel);
    display:flex; align-items:center; justify-content:space-between; gap:16px; flex-wrap:wrap;
    transition:background .3s, border-color .3s;
  }
  .traffic-banner.attack{
    background:rgba(255,59,107,.1); border-color:rgba(255,59,107,.6);
    animation:attackPulse 1s ease-in-out infinite;
  }
  @keyframes attackPulse{ 0%,100%{box-shadow:0 0 0 rgba(255,59,107,0)} 50%{box-shadow:0 0 26px rgba(255,59,107,.45)} }
  .traffic-banner.protected{ background:rgba(0,255,157,.06); border-color:rgba(0,255,157,.5) }
  .traffic-left{ display:flex; align-items:center; gap:14px; flex-wrap:wrap }
  .traffic-status{ display:flex; align-items:center; gap:9px; font-size:15px; font-weight:800; letter-spacing:.03em; white-space:nowrap }
  .traffic-metric{ font-size:13px; color:var(--ink-dim); white-space:nowrap }
  .traffic-metric b{ color:var(--ink); font-size:20px }
  .ddos-btn{
    padding:9px 16px; border-radius:9px; border:1px solid rgba(0,255,242,.4);
    background:rgba(0,255,242,.08); color:var(--accent); font-weight:700; font-size:12px; cursor:pointer; white-space:nowrap;
    font-family:inherit; letter-spacing:.04em;
  }
  .ddos-btn.active{ border-color:rgba(0,255,157,.5); background:rgba(0,255,157,.12); color:var(--good) }

  .traffic-log-panel{
    margin:0 0 20px; border-radius:14px; overflow:hidden;
    border:1px solid var(--panel-border); background:rgba(2,8,5,.92);
  }
  .traffic-log-header{
    display:flex; align-items:center; justify-content:space-between; gap:10px;
    padding:10px 18px; font-size:11.5px; font-weight:800; letter-spacing:.06em;
    color:var(--ink-dim); text-transform:uppercase; border-bottom:1px solid var(--panel-border);
  }
  .traffic-log-count{ color:var(--accent); font-weight:700; text-transform:none; letter-spacing:0 }
  .traffic-log-body{
    max-height:180px; overflow-y:auto; padding:10px 18px; font-size:12px;
    display:flex; flex-direction:column; gap:3px;
  }
  .traffic-log-row{ display:flex; gap:12px; white-space:nowrap }
  .traffic-log-row.blocked{ opacity:.6 }
  .traffic-log-time{ color:var(--ink-dimmer); flex-shrink:0 }
  .traffic-log-ip{ color:var(--accent); font-weight:700; flex-shrink:0 }
  .traffic-log-verb{ color:var(--ink-dim); flex-shrink:0 }
  .traffic-log-path{ color:var(--good); flex-shrink:0 }
  .traffic-log-tag{ color:var(--bad); font-weight:700; margin-left:auto }
  .traffic-log-empty{ color:var(--ink-dimmer); font-size:12.5px }

  .attackers-panel{
    margin:0 0 20px; border-radius:14px; overflow:hidden;
    border:1px solid rgba(255,59,107,.3); background:rgba(10,2,7,.85);
  }
  .attackers-toggle{
    width:100%; display:flex; align-items:center; justify-content:space-between; gap:10px;
    padding:12px 18px; background:transparent; border:none; color:var(--bad);
    font-family:inherit; font-weight:800; font-size:12.5px; letter-spacing:.04em;
    text-transform:uppercase; cursor:pointer;
  }
  .attackers-count-badge{ color:var(--ink-dim); font-weight:700; text-transform:none; letter-spacing:0; margin-left:6px }
  .attackers-list{ padding:0 18px 14px; display:flex; flex-direction:column; gap:6px }
  .attackers-list.collapsed{ display:none }
  .attacker-row{
    display:flex; align-items:center; justify-content:space-between; gap:12px;
    padding:8px 12px; border-radius:8px; background:rgba(255,59,107,.08);
    border:1px solid rgba(255,59,107,.18); font-size:12.5px;
  }
  .attacker-ip{ font-weight:700; color:var(--ink) }
  .attacker-stats{ color:var(--ink-dim); font-variant-numeric:tabular-nums; white-space:nowrap }
  .attackers-empty{ color:var(--ink-dimmer); font-size:12.5px; padding:0 18px 14px }

  .tabs{ display:flex; gap:8px; margin:14px 0 18px }
  .tab-btn{
    padding:9px 18px; border-radius:9px 9px 0 0; border:1px solid var(--panel-border); border-bottom:none;
    background:rgba(255,255,255,.03); color:var(--ink-dim); font-family:inherit; font-weight:700; font-size:12.5px;
    cursor:pointer; letter-spacing:.03em;
  }
  .tab-btn.active{ background:var(--panel); color:var(--accent); border-color:var(--accent) }

  .game-phase-banner{
    margin:0 0 18px; padding:18px 22px; border-radius:14px; text-align:center;
    border:1px solid var(--panel-border); background:var(--panel);
  }
  .game-phase-banner.night{ background:rgba(0,255,242,.06); border-color:rgba(0,255,242,.4) }
  .game-phase-banner.day_vote{ background:rgba(240,255,92,.08); border-color:rgba(240,255,92,.45) }
  .game-phase-banner.game_over.town{ background:rgba(0,255,157,.1); border-color:rgba(0,255,157,.6) }
  .game-phase-banner.game_over.attackers{ background:rgba(255,59,107,.1); border-color:rgba(255,59,107,.6) }
  .game-phase-title{ font-size:22px; font-weight:900; letter-spacing:.03em; margin-bottom:4px }
  .game-phase-sub{ font-size:12.5px; color:var(--ink-dim) }

  .game-lobby-players{ display:flex; flex-wrap:wrap; gap:8px; margin:14px 0 }
  .game-lobby-chip{
    padding:7px 14px; border-radius:20px; background:rgba(0,255,242,.08); border:1px solid rgba(0,255,242,.35);
    font-size:12.5px; font-weight:700;
  }
  .game-start-form{ display:flex; gap:10px; align-items:end; flex-wrap:wrap; margin-top:16px }
  .game-start-form label{ display:flex; flex-direction:column; gap:5px; font-size:11.5px; color:var(--ink-dim); text-transform:uppercase; letter-spacing:.04em }
  .game-start-form input{
    width:80px; padding:9px 10px; border-radius:8px; border:1px solid var(--panel-border);
    background:rgba(255,255,255,.04); color:var(--ink); font-family:inherit; font-size:14px;
  }
  .game-btn{
    padding:11px 20px; border-radius:9px; border:1px solid rgba(0,255,157,.5);
    background:rgba(0,255,157,.08); color:var(--good); font-weight:800; font-size:12px;
    cursor:pointer; font-family:inherit; letter-spacing:.04em;
  }
  .game-btn:hover{ background:rgba(0,255,157,.18) }
  .game-btn.danger{ border-color:rgba(255,59,107,.5); color:var(--bad); background:rgba(255,59,107,.08) }
  .game-btn.danger:hover{ background:rgba(255,59,107,.16) }

  .game-roster{ display:grid; grid-template-columns:repeat(auto-fill, minmax(140px,1fr)); gap:10px; margin:16px 0 }
  .game-player-card{
    padding:12px; border-radius:10px; border:1px solid var(--panel-border); background:rgba(255,255,255,.03);
    text-align:center;
  }
  .game-player-card.dead{ opacity:.55; border-color:rgba(255,59,107,.4) }
  .game-player-num{ font-size:11px; color:var(--ink-dimmer) }
  .game-player-name{ font-weight:800; font-size:13.5px; margin:3px 0 }
  .game-player-status{ width:8px; height:8px; border-radius:50%; margin:6px auto 0 }
  .game-player-status.alive{ background:var(--good); box-shadow:0 0 8px var(--good) }
  .game-player-status.dead{ background:var(--ink-dimmer); box-shadow:none }
  .game-player-role{ font-size:11px; margin-top:3px; font-weight:700 }
  .game-player-role.attacker{ color:var(--bad) }
  .game-player-role.defender{ color:var(--accent) }
  .game-player-role.civilian{ color:var(--ink-dim) }

  .game-admin-row{ display:flex; gap:10px; margin-top:18px; flex-wrap:wrap }
</style></head><body>

  <div class="scanlines"></div>

  <div class="topbar">
    <div class="topbar-spacer"><span class="dot"></span><span>live</span></div>
    <h1 class="glitch" data-text="Classroom CTF -- Live Scoreboard">Classroom CTF -- Live Scoreboard</h1>
    <div class="live"><span class="dot" id="liveDot"></span><span id="liveText">live</span></div>
  </div>
  <div class="sub">Find flags, submit them below. <b>First</b> team to find a flag = 100 pts, later finders = 50 pts. Patching a vulnerability = <b>+75</b> pts (finding it first isn't required) &mdash; and it locks that flag for everyone.</div>

  <div class="tabs">
    <button class="tab-btn active" id="tabCtfBtn" onclick="showTab('ctf')">CTF Scoreboard</button>
    <button class="tab-btn" id="tabGameBtn" onclick="showTab('game')">Cyber Town</button>
  </div>

  <div id="ctfTab">
  <div class="traffic-banner" id="trafficBanner">
    <div class="traffic-left">
      <span class="traffic-status">
        <span class="status-dot good" id="trafficStatusDot"></span>
        <span id="trafficStatusLabel">NORMAL TRAFFIC</span>
      </span>
      <span class="traffic-metric"><b id="trafficRps">0</b> req/s &middot; <span id="trafficBlocked">0</span> blocked</span>
    </div>
    <button class="ddos-btn" id="ddosToggleBtn" onclick="toggleDdosProtection()">[ ENABLE PROTECTION ]</button>
  </div>

  <div class="traffic-log-panel" id="trafficLogPanel">
    <div class="traffic-log-header">
      <span>LIVE TRAFFIC LOG // GET /</span>
      <span class="traffic-log-count" id="trafficLogCount">[0]</span>
    </div>
    <div class="traffic-log-body" id="trafficLogBody">
      <div class="traffic-log-empty">No requests yet -- this fills up during the flag round and lights up during the DDoS demo.</div>
    </div>
  </div>

  <div class="attackers-panel" id="attackersPanel" hidden>
    <button class="attackers-toggle" id="attackersToggle" onclick="toggleAttackers()">
      <span>ATTACK SOURCES <span class="attackers-count-badge" id="attackersCount">[0]</span></span>
      <span id="attackersChevron">&#9660;</span>
    </button>
    <div class="attackers-list" id="attackersList"></div>
  </div>

  <div class="layout">
    <div class="panel">
      <h2>Scoreboard</h2>
      <div id="board"><div class="empty-msg">No teams yet -- be the first to submit a flag.</div></div>

      <div class="submit-box">
        <h2 style="margin-bottom:10px">Submit a flag</h2>
        <input id="teamName" placeholder="Team name">
        <input id="flagCode" placeholder="FLAG{...}">
        <button onclick="submitFlag()">[ SUBMIT ]</button>
        <div id="submitResult" class="result"></div>
      </div>
    </div>

    <div class="panel">
      <h2>Vulnerability status</h2>
      <div id="vulns"></div>
      <h2 style="margin-top:20px">Live feed</h2>
      <div class="events" id="events"><div style="color:#4d7a63">Nothing yet</div></div>
    </div>
  </div>
  </div>

  <div id="gameTab" hidden>
    <div class="game-phase-banner" id="gamePhaseBanner">
      <div class="game-phase-title" id="gamePhaseTitle">Waiting for players...</div>
      <div class="game-phase-sub" id="gamePhaseSub">Flash a board with the Cyber Town firmware and connect it to the event Wi-Fi.</div>
    </div>

    <div id="gameLobbyBox">
      <div class="game-lobby-players" id="gameLobbyPlayers"></div>
      <div class="game-start-form">
        <label>Attackers <input type="number" id="gameAttackersInput" value="2" min="1"></label>
        <label>Defenders <input type="number" id="gameDefendersInput" value="2" min="0"></label>
        <button class="game-btn" onclick="startGame()">[ START GAME ]</button>
      </div>
    </div>

    <div class="game-roster" id="gameRoster"></div>

    <div class="game-admin-row" id="gameInProgressControls" hidden>
      <button class="game-btn" id="gameResolveNightBtn" onclick="resolveNight()" hidden>[ RESOLVE NIGHT ]</button>
      <button class="game-btn" id="gameResolveVoteBtn" onclick="resolveVote()" hidden>[ RESOLVE VOTE ]</button>
    </div>

    <div class="game-admin-row" id="gameOverControls" hidden>
      <button class="game-btn" onclick="newGameRound()">[ NEW ROUND -- SAME PLAYERS ]</button>
    </div>

    <div class="game-admin-row">
      <button class="game-btn danger" onclick="forceEndGame()">[ FORCE END &amp; REVEAL ]</button>
      <button class="game-btn danger" onclick="resetGame()">[ RESET CYBER TOWN ]</button>
    </div>

    <h2 style="margin-top:22px">Live feed</h2>
    <div class="events" id="gameEvents"><div style="color:#4d7a63">Nothing yet</div></div>
  </div>

<script>
function showTab(name){
  document.getElementById('ctfTab').hidden = name !== 'ctf';
  document.getElementById('gameTab').hidden = name !== 'game';
  document.getElementById('tabCtfBtn').classList.toggle('active', name === 'ctf');
  document.getElementById('tabGameBtn').classList.toggle('active', name === 'game');
}

var attackersExpanded = true;

function toggleAttackers(){
  attackersExpanded = !attackersExpanded;
  document.getElementById('attackersList').classList.toggle('collapsed', !attackersExpanded);
  document.getElementById('attackersChevron').textContent = attackersExpanded ? '▼' : '▶';
}

function medal(rank){
  if(rank === 0) return 'r1';
  if(rank === 1) return 'r2';
  if(rank === 2) return 'r3';
  return '';
}

async function refreshNow(){
  try{
    const r = await fetch('/api/state');
    if(!r.ok) throw new Error('bad response');
    const d = await r.json();
    document.getElementById('liveDot').className = 'dot';
    document.getElementById('liveText').textContent = 'live';

    const board = document.getElementById('board');
    board.innerHTML = d.board.length ? d.board.map((row, i) => `
      <div class="board-row">
        <span class="rank ${medal(i)}">${i+1}</span>
        <span class="board-name">${row.team}</span>
        <span class="board-meta">${row.found} found &middot; ${row.patched} patched</span>
        <span class="board-score">${row.score}</span>
      </div>
    `).join('') : '<div class="empty-msg">No teams yet -- be the first to submit a flag.</div>';

    document.getElementById('vulns').innerHTML = d.vulns.map(v => `
      <div class="vuln-row">
        <span class="vuln-id">#${v.id}</span>
        <span class="vuln-name">${v.name}</span>
        <span class="badge ${v.patched ? 'patched' : 'open'}">${v.patched ? 'PATCHED' : 'OPEN'}</span>
        ${v.patched ? '' : `<button class="patch-btn" onclick="patchVuln(${v.id})">[ PATCH ]</button>`}
      </div>
    `).join('');

    document.getElementById('events').innerHTML = d.events.length
      ? d.events.map(e => `<div>[${e.t}] ${e.msg}</div>`).join('')
      : '<div style="color:#5f7385">Nothing yet</div>';

    const t = d.traffic;
    const banner = document.getElementById('trafficBanner');
    const statusDot = document.getElementById('trafficStatusDot');
    const statusLabel = document.getElementById('trafficStatusLabel');
    document.getElementById('trafficRps').textContent = t.rps;
    document.getElementById('trafficBlocked').textContent = t.blocked;
    banner.className = 'traffic-banner' + (t.underAttack ? ' attack' : (t.protection ? ' protected' : ''));
    statusDot.className = 'status-dot ' + (t.underAttack ? 'bad' : 'good');
    statusLabel.textContent = t.underAttack
      ? 'UNDER ATTACK'
      : (t.protection ? 'PROTECTED' : 'NORMAL TRAFFIC');
    const btn = document.getElementById('ddosToggleBtn');
    btn.textContent = t.protection ? '[ DISABLE PROTECTION ]' : '[ ENABLE PROTECTION ]';
    btn.className = 'ddos-btn' + (t.protection ? ' active' : '');
    btn.dataset.enabled = t.protection ? 'true' : 'false';

    const trafficLog = t.log || [];
    document.getElementById('trafficLogCount').textContent = '[' + trafficLog.length + ']';
    document.getElementById('trafficLogBody').innerHTML = trafficLog.length
      ? trafficLog.map(e => `
        <div class="traffic-log-row${e.blocked ? ' blocked' : ''}">
          <span class="traffic-log-time">${e.t}</span>
          <span class="traffic-log-ip">${e.ip}</span>
          <span class="traffic-log-verb">GET</span>
          <span class="traffic-log-path">/</span>
          ${e.blocked ? '<span class="traffic-log-tag">BLOCKED</span>' : ''}
        </div>
      `).join('')
      : '<div class="traffic-log-empty">No requests yet -- this fills up during the flag round and lights up during the DDoS demo.</div>';

    const attackersPanel = document.getElementById('attackersPanel');
    const attackers = t.attackers || [];
    attackersPanel.hidden = !t.protection;
    document.getElementById('attackersCount').textContent = '[' + attackers.length + ']';
    const list = document.getElementById('attackersList');
    list.innerHTML = attackers.length
      ? attackers.map(a => `
        <div class="attacker-row">
          <span class="attacker-ip">${a.ip}</span>
          <span class="attacker-stats">${a.rps} req/s &middot; ${a.blocked} blocked</span>
        </div>
      `).join('')
      : '<div class="attackers-empty">No active attackers right now.</div>';
    list.classList.toggle('collapsed', !attackersExpanded);
  }catch(e){
    document.getElementById('liveDot').className = 'dot lost';
    document.getElementById('liveText').textContent = 'connection lost -- retrying...';
  }
}
setInterval(refreshNow, 2000);

async function toggleDdosProtection(){
  const btn = document.getElementById('ddosToggleBtn');
  const enabling = btn.dataset.enabled !== 'true';
  const body = new URLSearchParams({enabled: enabling ? 'true' : 'false'});
  await fetch('/api/ddos-protection', {method:'POST', body});
  refreshNow();
}

async function submitFlag(){
  const team = document.getElementById('teamName').value.trim();
  const flag = document.getElementById('flagCode').value.trim();
  const box = document.getElementById('submitResult');
  if(!team){ box.textContent = 'Type your team name first.'; box.className = 'result bad'; return; }
  if(!flag){ box.textContent = 'Paste a flag code first.'; box.className = 'result bad'; return; }
  const body = new URLSearchParams({team, flag});
  const r = await fetch('/submit', {method:'POST', body});
  const d = await r.json();
  if(d.status === 'correct'){
    box.textContent = `Correct! +${d.points} pts (${d.vulnerability})`;
    box.className = 'result ok';
    document.getElementById('flagCode').value = '';
  } else if(d.status === 'already_found'){
    box.textContent = 'Your team already found this one.';
    box.className = 'result bad';
  } else {
    box.textContent = 'Not a valid flag -- check for typos.';
    box.className = 'result bad';
  }
  refreshNow();
}

async function patchVuln(id){
  const team = document.getElementById('teamName').value.trim();
  if(!team){ alert('Type your team name in the box first, then Patch.'); return; }
  const body = new URLSearchParams({team});
  await fetch(`/patch/${id}`, {method:'POST', body});
  refreshNow();
}

async function refreshGame(){
  try{
    const r = await fetch('/game/state-all');
    if(!r.ok) throw new Error('bad response');
    const d = await r.json();

    const banner = document.getElementById('gamePhaseBanner');
    const title = document.getElementById('gamePhaseTitle');
    const sub = document.getElementById('gamePhaseSub');
    banner.className = 'game-phase-banner ' + d.phase + (d.phase === 'game_over' ? ' ' + d.winner : '');

    document.getElementById('gameLobbyBox').hidden = d.phase !== 'lobby';
    document.getElementById('gameInProgressControls').hidden = (d.phase === 'lobby' || d.phase === 'game_over');
    document.getElementById('gameOverControls').hidden = d.phase !== 'game_over';
    document.getElementById('gameResolveNightBtn').hidden = d.phase !== 'night';
    document.getElementById('gameResolveVoteBtn').hidden = d.phase !== 'day_vote';

    if(d.phase === 'lobby'){
      title.textContent = `Waiting for players... (${d.roster.length} connected)`;
      sub.textContent = 'Flash a board with the Cyber Town firmware and connect it to the event Wi-Fi -- it appears below automatically.';
      document.getElementById('gameLobbyPlayers').innerHTML = d.roster.length
        ? d.roster.map(p => `<span class="game-lobby-chip">#${p.num} ${p.name}</span>`).join('')
        : '<span style="color:var(--ink-dimmer)">No boards connected yet.</span>';
    } else if(d.phase === 'night'){
      title.textContent = `NIGHT // ROUND ${d.round}`;
      sub.textContent = `${d.aliveAttackers} attacker(s) and ${d.aliveTown} defender/civilian(s) still alive. Attackers and defenders are choosing targets on their own boards.`;
    } else if(d.phase === 'day_vote'){
      title.textContent = `DAY // VOTE -- ROUND ${d.round}`;
      sub.textContent = 'Discuss out loud, then everyone votes on their own board for who to eliminate.';
    } else if(d.phase === 'game_over'){
      title.textContent = d.winner === 'attackers' ? 'ATTACKERS WIN'
        : d.winner === 'town' ? 'TOWN WINS'
        : 'GAME OVER -- ENDED BY INSTRUCTOR';
      sub.textContent = 'All roles are now revealed below.';
    }

    document.getElementById('gameRoster').innerHTML = d.roster.map(p => `
      <div class="game-player-card ${p.alive ? '' : 'dead'}">
        <div class="game-player-num">#${p.num}</div>
        <div class="game-player-name">${p.name}</div>
        <div class="game-player-status ${p.alive ? 'alive' : 'dead'}"></div>
        ${p.role ? `<div class="game-player-role ${p.role.toLowerCase()}">${p.role}</div>` : ''}
      </div>
    `).join('');

    document.getElementById('gameEvents').innerHTML = d.events.length
      ? d.events.map(e => `<div>[${e.t}] ${e.msg}</div>`).join('')
      : '<div style="color:#5f7385">Nothing yet</div>';
  }catch(e){
    // the CTF tab's refreshNow() already reports a lost connection -- avoid duplicate UI noise here
  }
}
setInterval(refreshGame, 2000);

async function startGame(){
  const attackers = document.getElementById('gameAttackersInput').value;
  const defenders = document.getElementById('gameDefendersInput').value;
  const body = new URLSearchParams({attackers, defenders});
  const r = await fetch('/game/start', {method:'POST', body});
  const d = await r.json();
  if(!r.ok){ alert(d.error || 'Could not start the game.'); return; }
  refreshGame();
}

async function resolveNight(){
  await fetch('/game/resolve-night', {method:'POST'});
  refreshGame();
}

async function resolveVote(){
  await fetch('/game/resolve-vote', {method:'POST'});
  refreshGame();
}

async function newGameRound(){
  await fetch('/game/new-round', {method:'POST'});
  refreshGame();
}

async function forceEndGame(){
  const pin = prompt('Instructor PIN to end the game and reveal all roles:');
  if(pin === null) return;
  const body = new URLSearchParams({pin});
  const r = await fetch('/game/force-end', {method:'POST', body});
  if(!r.ok){ alert('Wrong PIN, or no game in progress.'); return; }
  refreshGame();
}

async function resetGame(){
  const pin = prompt('Instructor PIN to fully reset Cyber Town (removes all connected players):');
  if(pin === null) return;
  const body = new URLSearchParams({pin});
  const r = await fetch('/game/reset', {method:'POST', body});
  if(!r.ok){ alert('Wrong PIN.'); return; }
  refreshGame();
}

refreshNow();
refreshGame();
</script>
</body></html>
"""


@app.route("/")
def dashboard():
    return DASHBOARD_HTML


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
