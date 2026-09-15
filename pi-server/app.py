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

app = Flask(__name__)

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
ddos_protection = False
blocked_count = 0

# Control-plane traffic (the dashboard's own polling, flag submission,
# patching, admin reset) is never counted or blocked -- only the public "/"
# page is the attack surface here. This guarantees the instructor can always
# see the dashboard and flip protection on/off, even mid-flood.
_RATE_LIMIT_EXEMPT_PREFIXES = ("/api/state", "/api/ddos-protection", "/admin/", "/submit", "/patch/")


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

    if ddos_protection:
        ip = request.remote_addr or "unknown"
        dq = ip_times[ip]
        dq.append(now)
        ip_cutoff = now - RATE_LIMIT_WINDOW
        while dq and dq[0] < ip_cutoff:
            dq.popleft()
        if len(dq) > RATE_LIMIT_MAX:
            blocked_count += 1
            return jsonify(error="rate limited -- too many requests from this device"), 429


def current_traffic():
    now = time.time()
    recent = sum(1 for t in traffic_times if now - t <= TRAFFIC_WINDOW)
    return {
        "rps": round(recent / TRAFFIC_WINDOW, 1),
        "underAttack": (recent / TRAFFIC_WINDOW) >= ATTACK_THRESHOLD,
        "protection": ddos_protection,
        "blocked": blocked_count,
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
    ddos_protection = False
    blocked_count = 0
    log("--- round reset by instructor ---")
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

  .topbar{display:flex; align-items:center; gap:14px; flex-wrap:wrap; margin-bottom:6px}

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

  .live{display:flex; align-items:center; gap:7px; font-size:12px; color:var(--ink-dim); margin-left:auto}
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
  }
  .patch-btn:hover{background:rgba(0,255,242,.18)}

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
    width:100%; padding:11px; border:0; border-radius:9px; font-weight:800; font-size:13.5px; cursor:pointer;
    background:linear-gradient(135deg,var(--accent),var(--accent-2)); color:#02120d; letter-spacing:.03em;
  }
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
  .traffic-status{ font-size:15px; font-weight:800; white-space:nowrap }
  .traffic-metric{ font-size:13px; color:var(--ink-dim); white-space:nowrap }
  .traffic-metric b{ color:var(--ink); font-size:20px }
  .ddos-btn{
    padding:9px 16px; border-radius:9px; border:1px solid rgba(0,255,242,.4);
    background:rgba(0,255,242,.08); color:var(--accent); font-weight:700; font-size:12.5px; cursor:pointer; white-space:nowrap;
    font-family:inherit;
  }
  .ddos-btn.active{ border-color:rgba(0,255,157,.5); background:rgba(0,255,157,.12); color:var(--good) }
</style></head><body>

  <div class="scanlines"></div>

  <div class="topbar">
    <h1 class="glitch" data-text="Classroom CTF -- Live Scoreboard">Classroom CTF -- Live Scoreboard</h1>
    <div class="live"><span class="dot" id="liveDot"></span><span id="liveText">live</span></div>
  </div>
  <div class="sub">Find flags, submit them below. <b>First</b> team to find a flag = 100 pts, later finders = 50 pts. Patching a vulnerability = <b>+75</b> pts (finding it first isn't required) &mdash; and it locks that flag for everyone.</div>

  <div class="traffic-banner" id="trafficBanner">
    <div class="traffic-left">
      <span class="traffic-status" id="trafficStatusText">&#128994; Normal traffic</span>
      <span class="traffic-metric"><b id="trafficRps">0</b> req/s &middot; <span id="trafficBlocked">0</span> blocked</span>
    </div>
    <button class="ddos-btn" id="ddosToggleBtn" onclick="toggleDdosProtection()">&#128737;&#65039; Enable DDoS Protection</button>
  </div>

  <div class="layout">
    <div class="panel">
      <h2>Scoreboard</h2>
      <div id="board"><div class="empty-msg">No teams yet -- be the first to submit a flag.</div></div>

      <div class="submit-box">
        <h2 style="margin-bottom:10px">Submit a flag</h2>
        <input id="teamName" placeholder="Team name">
        <input id="flagCode" placeholder="FLAG{...}">
        <button onclick="submitFlag()">Submit</button>
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

<script>
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
        ${v.patched ? '' : `<button class="patch-btn" onclick="patchVuln(${v.id})">Patch</button>`}
      </div>
    `).join('');

    document.getElementById('events').innerHTML = d.events.length
      ? d.events.map(e => `<div>[${e.t}] ${e.msg}</div>`).join('')
      : '<div style="color:#5f7385">Nothing yet</div>';

    const t = d.traffic;
    const banner = document.getElementById('trafficBanner');
    const statusText = document.getElementById('trafficStatusText');
    document.getElementById('trafficRps').textContent = t.rps;
    document.getElementById('trafficBlocked').textContent = t.blocked;
    banner.className = 'traffic-banner' + (t.underAttack ? ' attack' : (t.protection ? ' protected' : ''));
    statusText.textContent = t.underAttack
      ? '\U0001F534 UNDER ATTACK'
      : (t.protection ? '✅ Protected' : '\U0001F7E2 Normal traffic');
    const btn = document.getElementById('ddosToggleBtn');
    btn.textContent = t.protection ? '\U0001F6D1 Disable DDoS Protection' : '\U0001F6E1️ Enable DDoS Protection';
    btn.className = 'ddos-btn' + (t.protection ? ' active' : '');
    btn.dataset.enabled = t.protection ? 'true' : 'false';
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

refreshNow();
</script>
</body></html>
"""


@app.route("/")
def dashboard():
    return DASHBOARD_HTML


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
