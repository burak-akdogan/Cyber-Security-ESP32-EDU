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
    return jsonify(board=board, vulns=vulns, events=events[:15])


# ---------------------------------------------------------------------------
# Instructor-only reset between class periods (not linked from the UI)
# ---------------------------------------------------------------------------
@app.route("/admin/reset-all", methods=["POST"])
def reset_all():
    if request.form.get("pin", "") != "1234":
        return jsonify(error="wrong pin"), 403
    teams.clear()
    events.clear()
    for k in patched:
        patched[k] = False
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
    --bg:#05070a; --panel:#11161d; --panel-border:#232f3b;
    --ink:#e4edf4; --ink-dim:#8fa3b3; --ink-dimmer:#5f7385;
    --accent:#38bdf8; --accent-2:#a78bfa; --good:#4ade80; --bad:#f87171; --warn:#fbbf24;
  }
  *{box-sizing:border-box}
  body{
    background:var(--bg); color:var(--ink); margin:0; padding:22px clamp(14px,3vw,32px) 40px;
    font-family:-apple-system,"Segoe UI",Roboto,system-ui,sans-serif;
  }
  .topbar{display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:10px; margin-bottom:6px}
  h1{font-size:clamp(20px,3vw,26px); margin:0; display:flex; align-items:center; gap:10px}
  h1 .flag-emoji{filter:drop-shadow(0 0 10px rgba(56,189,248,.5))}
  .live{display:flex; align-items:center; gap:7px; font-size:12px; color:var(--ink-dim); font-family:ui-monospace,Consolas,monospace}
  .dot{width:8px; height:8px; border-radius:50%; background:var(--good); box-shadow:0 0 8px var(--good); animation:pulse 1.6s ease-in-out infinite}
  .dot.lost{background:var(--bad); box-shadow:0 0 8px var(--bad); animation:none}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
  .sub{color:var(--ink-dim); font-size:13px; line-height:1.6; margin:6px 0 24px; max-width:760px}
  .sub b{color:var(--ink)}

  .layout{display:grid; grid-template-columns:1.2fr 1fr; gap:18px; align-items:start}
  @media (max-width:880px){.layout{grid-template-columns:1fr}}

  .panel{background:var(--panel); border:1px solid var(--panel-border); border-radius:14px; padding:18px}
  .panel h2{font-size:12px; color:var(--ink-dim); text-transform:uppercase; letter-spacing:.06em; margin:0 0 14px; font-weight:700}

  .board-row{
    display:flex; align-items:center; gap:12px; padding:10px 8px; border-radius:10px;
    border-bottom:1px solid var(--panel-border);
  }
  .board-row:last-child{border-bottom:none}
  .rank{
    width:26px; height:26px; border-radius:50%; display:flex; align-items:center; justify-content:center;
    font-size:12px; font-weight:800; background:#0c1319; color:var(--ink-dim); flex-shrink:0;
  }
  .rank.r1{background:rgba(251,191,36,.15); color:var(--warn)}
  .rank.r2{background:rgba(148,163,184,.18); color:#cbd5e1}
  .rank.r3{background:rgba(217,119,6,.15); color:#d97706}
  .board-name{flex:1; font-size:14px; font-weight:600; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap}
  .board-meta{font-size:11px; color:var(--ink-dimmer); font-family:ui-monospace,Consolas,monospace}
  .board-score{font-size:18px; font-weight:800; color:var(--good); font-variant-numeric:tabular-nums; min-width:56px; text-align:right}
  .empty-msg{color:var(--ink-dimmer); font-size:13px; padding:8px 0}

  .vuln-row{display:flex; align-items:center; gap:10px; padding:11px 0; border-bottom:1px solid var(--panel-border)}
  .vuln-row:last-child{border-bottom:none}
  .vuln-id{font-family:ui-monospace,Consolas,monospace; font-size:11px; color:var(--ink-dimmer); width:20px; flex-shrink:0}
  .vuln-name{font-size:13px; flex:1; min-width:0}
  .badge{font-family:ui-monospace,Consolas,monospace; font-size:10px; font-weight:700; letter-spacing:.03em; padding:3px 9px; border-radius:999px; white-space:nowrap}
  .badge.open{background:rgba(248,113,113,.12); color:var(--bad); border:1px solid rgba(248,113,113,.35)}
  .badge.patched{background:rgba(74,222,128,.12); color:var(--good); border:1px solid rgba(74,222,128,.35)}
  .patch-btn{
    padding:5px 12px; border-radius:7px; border:1px solid rgba(56,189,248,.4);
    background:rgba(56,189,248,.1); color:var(--accent); cursor:pointer; font-size:11px; font-weight:600;
  }
  .patch-btn:hover{background:rgba(56,189,248,.2)}

  .events{font-family:ui-monospace,Consolas,monospace; font-size:12px; color:var(--ink-dim); max-height:220px; overflow-y:auto}
  .events div{padding:5px 0; border-bottom:1px solid var(--panel-border)}
  .events div:last-child{border-bottom:none}

  .submit-box{margin-top:20px; padding-top:18px; border-top:1px solid var(--panel-border)}
  .submit-box input{
    width:100%; margin-bottom:9px; padding:10px 12px; border-radius:9px; border:1px solid var(--panel-border);
    background:#0b1015; color:var(--ink); box-sizing:border-box; font-size:13.5px;
  }
  .submit-box input:focus{outline:none; border-color:var(--accent)}
  .submit-box button{
    width:100%; padding:11px; border:0; border-radius:9px; font-weight:700; font-size:13.5px; cursor:pointer;
    background:linear-gradient(135deg,var(--accent),var(--accent-2)); color:#04121a;
  }
  .result{margin-top:10px; font-size:13px; min-height:18px}
  .result.ok{color:var(--good)}
  .result.bad{color:var(--bad)}
</style></head><body>

  <div class="topbar">
    <h1><span class="flag-emoji">&#128681;</span> Classroom CTF &mdash; Live Scoreboard</h1>
    <div class="live"><span class="dot" id="liveDot"></span><span id="liveText">live</span></div>
  </div>
  <div class="sub">Find flags, submit them below. <b>First</b> team to find a flag = 100 pts, later finders = 50 pts. Patching a vulnerability = <b>+75</b> pts (finding it first isn't required) &mdash; and it locks that flag for everyone.</div>

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
      <div class="events" id="events"><div style="color:#5f7385">Nothing yet</div></div>
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
  }catch(e){
    document.getElementById('liveDot').className = 'dot lost';
    document.getElementById('liveText').textContent = 'connection lost -- retrying...';
  }
}
setInterval(refreshNow, 2000);

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
