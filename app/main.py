"""The front door.

POST /analyze: raw email in, stamped verdict out.
GET /health: is the building awake? (for the heartbeat)
GET /report: the threat desk — every verdict, gold-on-navy dashboard.
GET /report/download: the verdict log as a downloadable report.
GET /redteam: the red-team scoreboard — latest adversarial battery run.
"""
import json
import os

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse


from .schemas import AnalyzeRequest, Verdict
from .extractor import extract
from .classifier import classify
from .validator import validate
from .evidence import collect_evidence

app = FastAPI(title="PhishSquad")
@app.get("/")
def root():
    return RedirectResponse(url="/report")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERDICT_LOG = os.path.join(ROOT, "verdicts.jsonl")
REDTEAM_RESULTS = os.path.join(ROOT, "redteam", "results.json")

_DASH_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#0a0a18;background-image:radial-gradient(ellipse 80% 40% at 50% 0%,#2a1a4e 0%,transparent 60%),radial-gradient(ellipse 60% 30% at 85% 0%,#4e2a1a 0%,transparent 55%);color:#f2f2f7;font-family:'Segoe UI',system-ui,sans-serif;padding:36px 20px;min-height:100vh}
.wrap{max-width:920px;margin:auto}
.topbar{display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px}
h1{color:#f5b301;text-shadow:0 0 18px rgba(245,179,1,.55);letter-spacing:5px;font-size:32px;font-weight:800}
.sub{color:#9aa0b4;letter-spacing:3px;font-size:13px;margin:10px 0 30px}
.dl{display:inline-block;background:#f5b301;color:#0a0a18;font-weight:800;letter-spacing:2px;font-size:13px;padding:12px 22px;border-radius:8px;text-decoration:none;box-shadow:0 0 20px -4px #f5b301}
.dl:hover{box-shadow:0 0 28px -2px #f5b301}
.stats{display:flex;gap:14px;margin-bottom:26px;flex-wrap:wrap}
.stat{flex:1;min-width:140px;border:1px solid #2a2a4e;border-radius:10px;padding:18px 14px;background:rgba(18,18,42,.85);text-align:center;box-shadow:0 0 24px -8px rgba(245,179,1,.25)}
.stat .n{font-size:44px;font-weight:800}
.stat .l{font-size:12px;letter-spacing:2px;color:#9aa0b4;margin-top:8px}
.dist{margin:0 0 30px;border:1px solid #2a2a4e;border-radius:10px;padding:18px;background:rgba(14,14,30,.9)}
.drow{display:flex;align-items:center;gap:12px;margin:10px 0}
.drow .dl2{width:180px;flex-shrink:0;font-size:12px;letter-spacing:2px;color:#9aa0b4;font-weight:700}
.dbar{flex:1;height:14px;background:#1a1a30;border-radius:7px;overflow:hidden}
.dbar div{height:100%;border-radius:7px;box-shadow:0 0 12px currentColor}
.drow .dv{width:60px;text-align:right;font-weight:800;font-size:15px}
.card{--neon:#8a93a6;border:1px solid var(--neon);border-radius:10px;padding:16px 18px;margin:14px 0;background:rgba(14,14,30,.92);box-shadow:0 0 22px -8px var(--neon)}
.card-head{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.verdict{font-weight:800;letter-spacing:2px;color:var(--neon);text-shadow:0 0 12px var(--neon);font-size:16px}
.conf{color:#c6cbe0;font-size:14px;letter-spacing:1px;font-weight:700}
.tbar{height:10px;background:#1a1a30;border-radius:5px;overflow:hidden;margin:4px 0 12px}
.tfill{height:100%;border-radius:5px;background:var(--neon);box-shadow:0 0 10px var(--neon)}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.tag{background:rgba(245,179,1,.1);border:1px solid #f5b301;color:#f5b301;font-size:12px;font-weight:700;padding:4px 10px;border-radius:5px;font-family:'Courier New',monospace}
.rs{font-size:15px;margin:6px 0;color:#e8eaf2;line-height:1.55}
.empty{color:#9aa0b4;font-size:15px}
.foot{margin-top:40px;color:#5a5f7a;font-size:12px;letter-spacing:3px;text-align:center}
"""


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=Verdict)
def analyze(req: AnalyzeRequest):
    email = extract(req.raw_email)
    evidence = collect_evidence(email)
    statement = classify(email, evidence)
    return validate(statement, lambda: classify(email, evidence), evidence)


def _load_verdicts():
    rows = []
    try:
        with open(VERDICT_LOG) as f:
            for line in f:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
    except FileNotFoundError:
        pass
    return rows


@app.get("/report", response_class=HTMLResponse)
def report():
    rows = _load_verdicts()
    counts = {"phishing": 0, "legitimate": 0, "needs_review": 0}
    for v in rows:
        counts[v.get("verdict", "needs_review")] = counts.get(v.get("verdict"), 0) + 1
    total = len(rows) or 1
    neon = {"phishing": "#ff4d2e", "legitimate": "#34d399", "needs_review": "#f5b301"}
    labels = {"phishing": "PHISHING", "legitimate": "LEGITIMATE", "needs_review": "NEEDS REVIEW"}

    cards = []
    for v in reversed(rows):
        vd = v.get("verdict", "needs_review")
        c = neon.get(vd, "#8a93a6")
        conf = v.get("confidence", 0)
        chips = "".join(f"<span class='tag'>{e['check']}</span>"
                        for e in v.get("evidence", []))
        cards.append(
            f"<div class='card' style='--neon:{c}'>"
            f"<div class='card-head'><span class='verdict'>{vd.upper()}</span>"
            f"<span class='conf'>TRUST {conf}</span></div>"
            f"<div class='tbar'><div class='tfill' style='width:{int(conf * 100)}%'></div></div>"
            f"<div class='chips'>{chips or '<span class=tag>clean</span>'}</div>"
            f"</div>"
        )
    body = "\n".join(cards) or "<p class='empty'>No verdicts logged yet. Forward an email to the inbox.</p>"

    dist = "".join(
        f"<div class='drow'><span class='dl2'>{labels[k]}</span>"
        f"<div class='dbar'><div style='width:{int(counts[k] / total * 100)}%;background:{neon[k]};color:{neon[k]}'></div></div>"
        f"<span class='dv' style='color:{neon[k]}'>{counts[k]}</span></div>"
        for k in ("phishing", "legitimate", "needs_review")
    )

    stats = (
        f"<div class='stats'>"
        f"<div class='stat'><div class='n' style='color:#f2f2f7'>{len(rows)}</div><div class='l'>SCANNED</div></div>"
        f"<div class='stat'><div class='n' style='color:#ff4d2e'>{counts['phishing']}</div><div class='l'>PHISHING</div></div>"
        f"<div class='stat'><div class='n' style='color:#34d399'>{counts['legitimate']}</div><div class='l'>LEGITIMATE</div></div>"
        f"<div class='stat'><div class='n' style='color:#f5b301'>{counts['needs_review']}</div><div class='l'>NEEDS REVIEW</div></div>"
        f"</div>"
    )

    return (
        "<!DOCTYPE html><html><head><title>PHISHSQUAD // Threat Desk</title>"
        f"<style>{_DASH_CSS}</style></head><body><div class='wrap'>"
        "<div class='topbar'><div><h1>◈ PHISHSQUAD</h1>"
        "<div class='sub'>THREAT DESK // LIVE VERDICTS</div></div>"
        "<div><a class='dl' href='/redteam' style='margin-right:10px'>⚔ RED TEAM</a>"
        "<a class='dl' href='/report/download'>⬇ DOWNLOAD REPORT</a></div></div>"
        + stats + f"<div class='dist'>{dist}</div>" + body +
        "<div class='foot'>PHISHSQUAD // NEBIUS × NVIDIA HACKATHON</div>"
        "</div></body></html>"
    )


@app.get("/report/download")
def download_report():
    try:
        with open(VERDICT_LOG) as f:
            content = f.read()
    except FileNotFoundError:
        content = ""
    return PlainTextResponse(
        content,
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=phishsquad-report.json"},
    )


@app.get("/redteam", response_class=HTMLResponse)
def redteam_dash():
    try:
        with open(REDTEAM_RESULTS) as f:
            data = json.load(f)
    except FileNotFoundError:
        data = None

    if not data:
        head = ""
        body = "<p class='empty'>No red-team run yet. Run: <b>python -m app.redteam</b></p>"
    else:
        rows = []
        for a in data["attacks"]:
            c = "#34d399" if a["held"] else "#ff4d2e"
            status = "HELD" if a["held"] else "BREACHED"
            extra = ""
            if a.get("leaked"):
                extra = f" — LEAKED: {', '.join(a['leaked'])}"
            if a.get("error"):
                extra = f" — ERROR: {a['error']}"
            rows.append(
                f"<div class='card' style='--neon:{c}'>"
                f"<div class='card-head'><span class='verdict'>{status}</span>"
                f"<span class='conf'>{a['id']} · {a['category']}</span></div>"
                f"<div class='rs'>{a['name']} — expected {a['expected']}, got {a['got']}{extra}</div>"
                f"</div>"
            )
        body = "\n".join(rows)
        cats = "".join(
            f"<div class='drow'><span class='dl2'>{cat.upper()}</span>"
            f"<div class='dbar'><div style='width:{int(v['held'] / v['total'] * 100)}%;background:#f5b301;color:#f5b301'></div></div>"
            f"<span class='dv' style='color:#f5b301'>{v['held']}/{v['total']}</span></div>"
            for cat, v in data["by_category"].items()
        )
        head = (
            f"<div class='stats'>"
            f"<div class='stat'><div class='n' style='color:#34d399'>{data['held']}</div><div class='l'>HELD</div></div>"
            f"<div class='stat'><div class='n' style='color:#ff4d2e'>{data['total'] - data['held']}</div><div class='l'>BREACHED</div></div>"
            f"</div>"
            f"<div class='dist'>{cats}</div>"
            f"<p class='sub'>LAST RUN // {data['ran_at']}</p>"
        )

    return (
        "<!DOCTYPE html><html><head><title>PHISHSQUAD // Red Team</title>"
        f"<style>{_DASH_CSS}</style></head><body><div class='wrap'>"
        "<div class='topbar'><div><h1>◈ RED TEAM</h1>"
        "<div class='sub'>ADVERSARIAL SELF-TEST // LATEST BATTERY RUN</div></div>"
        "<a class='dl' href='/report'>← THREAT DESK</a></div>"
        + head + body +
        "<div class='foot'>PHISHSQUAD // NEBIUS × NVIDIA HACKATHON</div>"
        "</div></body></html>"
    )
