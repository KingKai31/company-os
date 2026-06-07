import os
import re
import subprocess
import sys
import time
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parent

AGENTS = [
    ("Orchestrator", "orchestrator", "🔀"),
    ("CEO", "ceo", "🎯"),
    ("Engineer", "engineer", "⚙️"),
    ("Legal", "legal", "⚖️"),
    ("Sales", "sales", "📧"),
    ("Finance", "finance", "💰"),
    ("Risk", "risk", "⚠️"),
]

COMPLETE_PATTERNS = {
    "orchestrator": [r"\[MAIN\].*Orchestrator complete", r"\[ORCHESTRATOR\] Plan created"],
    "ceo": [r"\[MAIN\].*CEO Agent complete", r"\[CEO\] Strategy written"],
    "engineer": [r"\[MAIN\].*Engineer Agent complete", r"\[ENGINEER\] Landing page live at:"],
    "legal": [r"\[MAIN\].*Legal Agent complete", r"\[LEGAL\] Documents saved"],
    "sales": [r"\[MAIN\].*Sales Agent complete", r"\[SALES\] Complete"],
    "finance": [r"\[MAIN\].*Finance Agent complete", r"\[FINANCE\] Projection complete"],
    "risk": [r"\[MAIN\].*Risk Agent complete", r"\[RISK\] Report written"],
}

INIT_PATTERNS = {
    "orchestrator": r"Step 1/7: Orchestrator",
    "ceo": r"Step 2/7: CEO",
    "engineer": r"Step 7/7: Engineer",
    "legal": r"Step 4/7: Legal",
    "sales": r"Step 5/7: Sales",
    "finance": r"Step 6/7: Finance",
    "risk": r"Step 6/7: Risk",
}

RUNNING_PATTERNS = {
    "orchestrator": r"\[ORCHESTRATOR\]",
    "ceo": r"\[CEO\]",
    "engineer": r"\[ENGINEER\]",
    "legal": r"\[LEGAL\]",
    "sales": r"\[SALES\]",
    "finance": r"\[FINANCE\]",
    "risk": r"\[RISK\]",
}

ERROR_PATTERNS = {
    "orchestrator": r"\[MAIN\] Orchestrator failed",
    "ceo": r"\[MAIN\] CEO Agent failed",
    "engineer": r"\[MAIN\] Engineer Agent failed",
    "legal": r"\[MAIN\] Legal Agent failed",
    "sales": r"\[MAIN\] Sales Agent failed",
    "finance": r"\[MAIN\] Finance Agent failed",
    "risk": r"\[MAIN\] Risk Agent failed",
}

AGENT_LINE_TAGS = {
    "orchestrator": r"\[ORCHESTRATOR\]",
    "ceo": r"\[CEO\]",
    "engineer": r"\[ENGINEER\]",
    "legal": r"\[LEGAL\]",
    "sales": r"\[SALES\]",
    "finance": r"\[FINANCE\]",
    "risk": r"\[RISK\]",
}

PARTICLE_SEEDS = [
    (3, 8, 14, 0.0), (11, 22, 18, 0.4), (19, 5, 22, 0.8), (27, 31, 16, 1.2),
    (35, 14, 20, 1.6), (43, 38, 24, 2.0), (51, 9, 15, 2.4), (59, 27, 19, 2.8),
    (67, 45, 21, 3.2), (75, 17, 17, 3.6), (83, 33, 23, 4.0), (91, 6, 14, 4.4),
    (7, 52, 18, 0.2), (15, 68, 22, 0.6), (23, 41, 16, 1.0), (31, 77, 20, 1.4),
    (39, 59, 24, 1.8), (47, 83, 15, 2.2), (55, 24, 19, 2.6), (63, 71, 23, 3.0),
    (71, 48, 17, 3.4), (79, 91, 21, 3.8), (87, 35, 14, 4.2), (95, 63, 18, 4.6),
    (5, 19, 22, 0.3), (13, 47, 16, 0.7), (21, 74, 20, 1.1), (29, 11, 24, 1.5),
    (37, 56, 15, 1.9), (45, 88, 19, 2.3), (53, 29, 23, 2.7), (61, 65, 17, 3.1),
    (69, 42, 21, 3.5), (77, 79, 14, 3.9), (85, 15, 18, 4.3), (93, 53, 22, 4.7),
    (9, 36, 16, 0.5), (17, 61, 20, 0.9), (25, 84, 24, 1.3), (33, 23, 15, 1.7),
    (41, 49, 19, 2.1), (49, 72, 23, 2.5), (57, 97, 17, 2.9), (65, 32, 21, 3.3),
    (73, 58, 14, 3.7), (81, 86, 18, 4.1), (89, 44, 22, 4.5), (97, 69, 16, 4.9),
    (2, 54, 20, 0.1), (46, 12, 18, 2.2), (62, 87, 22, 3.6), (88, 26, 15, 4.8),
]


# ── Pipeline logic (unchanged) ────────────────────────────────────────────────

def init_session_state():
    defaults = {
        "running": False,
        "agent_status": {key: "idle" for _, key, _ in AGENTS},
        "agent_output": {key: "Standby" for _, key, _ in AGENTS},
        "activity_feed": [],
        "pipeline_start": None,
        "pipeline_end": None,
        "sweep_done": set(),
        "metrics_animated": set(),
        "results": {
            "url": None,
            "github_url": None,
            "emails_sent": None,
            "email_count": 0,
            "risk_level": None,
            "finance_summary": None,
            "revenue_value": None,
            "company": None,
            "legal_docs": None,
        },
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def reset_run_state():
    st.session_state.agent_status = {key: "idle" for _, key, _ in AGENTS}
    st.session_state.agent_output = {key: "Standby" for _, key, _ in AGENTS}
    st.session_state.activity_feed = []
    st.session_state.pipeline_start = time.time()
    st.session_state.pipeline_end = None
    st.session_state.sweep_done = set()
    st.session_state.metrics_animated = set()
    st.session_state.results = {
        "url": None,
        "github_url": None,
        "emails_sent": None,
        "email_count": 0,
        "risk_level": None,
        "finance_summary": None,
        "revenue_value": None,
        "company": None,
        "legal_docs": None,
    }


def mark_sweeps():
    for _, key, _ in AGENTS:
        if st.session_state.agent_status.get(key) == "complete":
            st.session_state.sweep_done.add(key)


def update_agent_status(line):
    for key, pattern in ERROR_PATTERNS.items():
        if re.search(pattern, line):
            st.session_state.agent_status[key] = "error"
            return
    for key, patterns in COMPLETE_PATTERNS.items():
        if any(re.search(p, line) for p in patterns):
            st.session_state.agent_status[key] = "complete"
            return
    for key, pattern in INIT_PATTERNS.items():
        if re.search(pattern, line) and st.session_state.agent_status[key] not in ("complete", "error"):
            st.session_state.agent_status[key] = "initializing"
    for key, pattern in RUNNING_PATTERNS.items():
        if re.search(pattern, line) and st.session_state.agent_status[key] not in ("complete", "error"):
            st.session_state.agent_status[key] = "running"


def update_agent_output(line):
    for key, tag in AGENT_LINE_TAGS.items():
        if re.search(tag, line):
            preview = line.strip()
            st.session_state.agent_output[key] = preview[:70] + ("..." if len(preview) > 70 else "")


def parse_results_from_line(line):
    results = st.session_state.results
    url_match = re.search(r"Landing page:\s*(https?://\S+)", line)
    if url_match:
        results["url"] = url_match.group(1).strip()
    engineer_url = re.search(r"\[ENGINEER\].*?(https?://\S+)", line)
    if engineer_url:
        url = engineer_url.group(1).strip().rstrip(".")
        results["github_url"] = url
        results["url"] = url
    emails_match = re.search(r"Emails sent:\s*(True|False)", line, re.IGNORECASE)
    if emails_match:
        results["emails_sent"] = emails_match.group(1).lower() == "true"
    sales_count = re.search(r"\[SALES\] Generated (\d+) email drafts", line)
    if sales_count:
        results["email_count"] = int(sales_count.group(1))
    risk_match = re.search(r"Risk level:\s*(\w+)", line)
    if risk_match:
        results["risk_level"] = risk_match.group(1).lower()
    risk_report = re.search(r"\[RISK\] Report written — overall level:\s*(\w+)", line)
    if risk_report:
        results["risk_level"] = risk_report.group(1).lower()
    revenue_match = re.search(r"3-mo revenue:\s*\$?([\d,]+|N/A)", line)
    if revenue_match:
        val = revenue_match.group(1)
        if val != "N/A":
            results["revenue_value"] = val
            results["finance_summary"] = f"3-month revenue: ${val}"
    finance_line = re.search(r"\[FINANCE\] Projection complete — 3-month revenue: \$([\d,]+)", line)
    if finance_line:
        val = finance_line.group(1)
        results["revenue_value"] = val
        results["finance_summary"] = f"3-month revenue: ${val}"
    company_match = re.search(r"Company:\s*(.+)", line)
    if company_match:
        results["company"] = company_match.group(1).strip()
    legal_match = re.search(r"Legal docs:\s*(.+)", line)
    if legal_match:
        results["legal_docs"] = legal_match.group(1).strip()


def get_github_url_from_brain():
    try:
        from utils.shared_brain import read_state
        engineer = read_state("engineer_agent")
        url = engineer.get("github_url")
        if url and isinstance(url, str) and url.startswith("http"):
            return url.strip()
    except Exception:
        pass
    return None


def load_results_from_brain():
    try:
        from utils.shared_brain import read_state
        engineer = read_state("engineer_agent")
        sales = read_state("sales_agent")
        finance = read_state("finance_agent")
        risk = read_state("risk_agent")
        ceo = read_state("ceo_agent")
        orchestrator = read_state("orchestrator")
        legal = read_state("legal_agent")
        results = st.session_state.results
        github_url = engineer.get("github_url")
        if github_url and isinstance(github_url, str) and github_url.startswith("http"):
            results["github_url"] = github_url.strip()
            results["url"] = results["github_url"]
        if sales:
            results["emails_sent"] = sales.get("sent", False)
            results["email_count"] = len(sales.get("drafts", []))
        if finance.get("projection"):
            proj = finance["projection"]
            rev = proj.get("total_3_month_revenue")
            summary = proj.get("summary", "")
            if rev is not None:
                results["revenue_value"] = f"{rev:,}" if isinstance(rev, (int, float)) else str(rev)
                results["finance_summary"] = f"3-month revenue: ${results['revenue_value']}"
            elif summary:
                results["finance_summary"] = summary[:200]
        if risk.get("risk_report"):
            results["risk_level"] = risk["risk_report"].get("overall_risk_level", "unknown")
        if legal.get("file_path"):
            results["legal_docs"] = legal["file_path"]
        results["company"] = ceo.get("company_name") or orchestrator.get("plan", {}).get("company_name")
    except Exception:
        pass


def format_runtime():
    start = st.session_state.pipeline_start
    end = st.session_state.pipeline_end or (time.time() if st.session_state.running else None)
    if not start or not end:
        return "—"
    elapsed = int(end - start)
    mins, secs = divmod(elapsed, 60)
    return f"{mins:02d}:{secs:02d}"


def esc(text):
    if text is None:
        return ""
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def status_label(status):
    return {
        "idle": "IDLE",
        "initializing": "INITIALIZING",
        "running": "RUNNING",
        "complete": "COMPLETE",
        "error": "ERROR",
    }.get(status, "IDLE")


def parse_number(value):
    if value is None:
        return None
    digits = re.sub(r"[^\d]", "", str(value))
    return int(digits) if digits else None


def count_up_html(metric_key, display_text, numeric_value=None, prefix=""):
    animated = metric_key in st.session_state.metrics_animated
    if numeric_value is not None and not animated:
        st.session_state.metrics_animated.add(metric_key)
        return (
            f'<span class="count-up result-value" style="--target:{numeric_value};--prefix:\'{prefix}\';">'
            f'<span class="count-display">{esc(display_text)}</span></span>'
        )
    if display_text and display_text != "—":
        cls = "result-value metric-pop" if not animated else "result-value"
        if not animated:
            st.session_state.metrics_animated.add(metric_key)
        return f'<span class="{cls}">{esc(display_text)}</span>'
    return '<span class="result-value pending">—</span>'


def colorize_line(line, idx):
    safe = esc(line)
    if re.search(r"\[ALERT\]|CRITICAL", line, re.I):
        cls = "line-danger"
    elif re.search(r"failed|Error|ERROR|warning", line, re.I):
        cls = "line-warn"
    elif re.search(r"complete|✓|written|saved|live at", line, re.I):
        cls = "line-ok"
    else:
        cls = "line-sys"
    delay = (idx % 10) * 0.02
    return f'<div class="feed-line fadeInLeft {cls}" style="animation-delay:{delay:.2f}s">{safe}</div>'


def build_particles_html():
    dots = []
    for left, top, dur, delay in PARTICLE_SEEDS:
        dots.append(
            f'<span class="particle" style="left:{left}%;top:{top}%;'
            f'animation-duration:{dur}s;animation-delay:{delay}s"></span>'
        )
    return f'<div class="cosmos-bg"><div class="grid-lines"></div><div class="particles">{"".join(dots)}</div></div>'


def build_burst_html():
    return """
<span class="burst"><span class="bp bp1"></span><span class="bp bp2"></span>
<span class="bp bp3"></span><span class="bp bp4"></span></span>"""


# ── CSS (all animations) ──────────────────────────────────────────────────────

def build_css():
    return """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

@property --num { syntax: '<integer>'; initial-value: 0; inherits: false; }

html, body, [class*="css"], .stApp {
  background-color: #060b18 !important;
  color: #ffffff !important;
  font-family: 'Inter', sans-serif !important;
}
#MainMenu, footer, header { visibility: hidden; height: 0; }
.block-container { padding: 1rem 2rem 2rem !important; max-width: 100% !important; position: relative; z-index: 2; }

/* ── Background layers ── */
.cosmos-bg {
  position: fixed; inset: 0; z-index: 0; pointer-events: none; overflow: hidden;
}
.grid-lines {
  position: absolute; inset: -50%; opacity: 0.35;
  background-image:
    linear-gradient(rgba(0,212,255,0.07) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,212,255,0.07) 1px, transparent 1px);
  background-size: 48px 48px;
  animation: gridDrift 20s linear infinite;
}
.particles { position: absolute; inset: 0; }
.particle {
  position: absolute; width: 3px; height: 3px; border-radius: 50%;
  background: #00d4ff; box-shadow: 0 0 6px #00d4ff;
  animation: floatUp linear infinite; opacity: 0;
}

/* ── Streamlit widgets ── */
div[data-testid="stTextInput"] input {
  background: #0d1526 !important; color: #00d4ff !important;
  border: 1px solid #00d4ff !important; border-radius: 8px !important;
  font-family: 'JetBrains Mono', monospace !important; font-size: 0.95rem !important;
  padding: 14px 18px !important;
  box-shadow: 0 0 16px rgba(0,212,255,0.2) !important;
}
div[data-testid="stTextInput"] label { display: none !important; }
div[data-testid="stButton"] button {
  background: linear-gradient(135deg, #00d4ff, #8b5cf6) !important;
  color: #060b18 !important; font-weight: 800 !important;
  font-family: 'Inter', sans-serif !important; letter-spacing: 1px !important;
  border: none !important; border-radius: 8px !important;
  padding: 14px 24px !important; width: 100% !important;
  animation: pulse-cyan-slow 2.5s ease-in-out infinite !important;
}
div[data-testid="stButton"] button:disabled { opacity: 0.4 !important; animation: none !important; }
div[data-testid="stDownloadButton"] button {
  background: #0d1526 !important; color: #8b5cf6 !important;
  border: 1px solid #8b5cf6 !important; font-family: 'JetBrains Mono', monospace !important;
}

/* ── Header ── */
.header-bar {
  display: flex; justify-content: space-between; align-items: center;
  background: #0d1526; border: 1px solid #1a2d4f; border-bottom: 2px solid #00d4ff;
  border-radius: 10px; padding: 14px 24px; margin-bottom: 20px;
  box-shadow: 0 4px 24px rgba(0,212,255,0.08); position: relative; z-index: 2;
}
.header-logo {
  font-family: 'JetBrains Mono', monospace; font-size: 1.25rem; font-weight: 700;
  color: #00d4ff; letter-spacing: 3px; text-shadow: 0 0 16px rgba(0,212,255,0.5);
}
.header-right {
  display: flex; align-items: center; gap: 20px;
  font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; color: #00d4ff;
}
.dot {
  display: inline-block; width: 9px; height: 9px; border-radius: 50%;
  margin-right: 8px; animation: blink 2s infinite;
}
.dot-online { background: #00ff88; box-shadow: 0 0 8px #00ff88; }
.dot-active { background: #00d4ff; box-shadow: 0 0 8px #00d4ff; }
.clock {
  color: #ffffff; font-weight: 600;
  animation: clockFade 1s ease infinite;
}

/* ── Hero ── */
.hero-wrap { text-align: center; margin: 28px 0 24px; position: relative; z-index: 2; }
.hero-h1 {
  font-size: 2rem; font-weight: 800; color: #ffffff; letter-spacing: 2px;
  margin: 0 0 10px; text-transform: uppercase;
  animation: glitch 0.9s ease 3 forwards;
}
.hero-sub { font-size: 1rem; color: #00d4ff; margin: 0 0 24px; font-family: 'JetBrains Mono', monospace; }

/* ── Agent cards ── */
.agent-grid {
  display: grid; grid-template-columns: repeat(7, 1fr); gap: 10px; margin: 20px 0;
  position: relative; z-index: 2;
}
.agent-card {
  background: #0d1526; border: 1px solid #1a2d4f; border-radius: 8px;
  padding: 0 0 10px; min-height: 130px; position: relative; overflow: hidden;
}
.agent-card.card-running {
  border-color: #00d4ff;
  animation: borderPulse 1s ease-in-out infinite;
}
.agent-card.card-complete {
  border-color: #00ff88; box-shadow: 0 0 14px rgba(0,255,136,0.25);
}
.agent-card.card-complete-sweep {
  animation: completeSweep 0.8s ease forwards;
}
.agent-card.card-error { border-color: #ff4444; box-shadow: 0 0 14px rgba(255,68,68,0.25); }
.agent-card.card-idle { border-color: #1a2d4f; opacity: 0.7; }
.status-bar { height: 4px; width: 100%; margin-bottom: 10px; }
.bar-idle { background: #1a2d4f; }
.bar-running { background: #1a2d4f; }
.bar-complete { background: #00ff88; }
.bar-error { background: #ff4444; }
.bar-init { background: #8b5cf6; }
.card-progress {
  position: absolute; bottom: 0; left: 0; height: 3px; width: 0;
  background: linear-gradient(90deg, #00d4ff, #8b5cf6);
  box-shadow: 0 0 8px rgba(0,212,255,0.6);
  animation: progressFill 1.8s ease-in-out infinite;
}
.card-body { padding: 0 10px 8px; }
.card-icon { font-size: 1.5rem; line-height: 1; margin-bottom: 6px; }
.card-name {
  font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; font-weight: 700;
  color: #ffffff; letter-spacing: 1px; text-transform: uppercase;
}
.card-status { font-family: 'JetBrains Mono', monospace; font-size: 0.58rem; margin-top: 4px; }
.st-idle { color: #64748b; } .st-running { color: #00d4ff; } .st-complete { color: #00ff88; }
.st-error { color: #ff4444; } .st-init { color: #8b5cf6; }
.card-check { position: absolute; top: 10px; right: 8px; color: #00ff88; font-size: 0.85rem; }
.card-preview {
  font-family: 'JetBrains Mono', monospace; font-size: 0.55rem; color: #64748b;
  margin-top: 6px; line-height: 1.3; word-break: break-word;
}

/* Particle burst on complete */
.burst { position: absolute; top: 50%; left: 50%; width: 0; height: 0; pointer-events: none; }
.bp {
  position: absolute; width: 4px; height: 4px; border-radius: 50%;
  background: #00ff88; box-shadow: 0 0 6px #00ff88;
  animation: burstOut 0.7s ease-out forwards;
}
.bp1 { animation-name: burstOut1; }
.bp2 { animation-name: burstOut2; }
.bp3 { animation-name: burstOut3; }
.bp4 { animation-name: burstOut4; }

/* ── Panels ── */
.panel {
  background: #0d1526; border: 1px solid #1a2d4f; border-radius: 10px;
  padding: 16px; margin-bottom: 8px; position: relative; z-index: 2;
}
.panel-head {
  font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 700;
  letter-spacing: 2px; color: #00d4ff; margin-bottom: 12px; text-transform: uppercase;
}
.terminal {
  background: #060b18; border: 1px solid #1a2d4f; border-radius: 6px;
  padding: 12px; height: 400px; overflow-y: auto;
  font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; line-height: 1.5;
}
.feed-line { margin-bottom: 1px; }
.feed-line.fadeInLeft { opacity: 0; animation: fadeInLeft 0.3s ease forwards; animation-fill-mode: forwards; }
.line-sys { color: #00d4ff; } .line-warn { color: #fbbf24; }
.line-danger { color: #ff4444; font-weight: 600; } .line-ok { color: #00ff88; }
.line-idle { color: #475569; font-style: italic; opacity: 1; animation: none; }

.result-card {
  background: #060b18; border: 1px solid #1a2d4f; border-radius: 8px;
  padding: 14px; margin-bottom: 10px;
  animation: metricReveal 0.5s ease forwards;
}
.result-label {
  font-family: 'JetBrains Mono', monospace; font-size: 0.6rem;
  letter-spacing: 1.5px; color: #00d4ff; text-transform: uppercase; margin-bottom: 6px;
}
.result-value {
  font-family: 'JetBrains Mono', monospace; font-size: 1.1rem;
  font-weight: 600; color: #ffffff;
}
.result-company {
  font-size: 1.5rem; font-weight: 800; color: #ffffff;
  text-shadow: 0 0 20px rgba(0,212,255,0.4); margin-bottom: 4px;
  animation: metricReveal 0.6s ease forwards;
}
.metric-pop { animation: countPop 0.8s ease forwards; display: inline-block; }
.count-up {
  --num: 0; display: inline-block;
  animation: countUp 1.2s ease-out forwards;
  font-family: 'JetBrains Mono', monospace; font-size: 1.1rem; font-weight: 600; color: #ffffff;
}
.count-display { animation: countPop 0.3s ease forwards; }
.url-link {
  display: inline-block; background: rgba(0,212,255,0.1); border: 1px solid #00d4ff;
  color: #00d4ff !important; text-decoration: none !important;
  padding: 10px 18px; border-radius: 6px; font-family: 'JetBrains Mono', monospace;
  font-size: 0.75rem; font-weight: 600; box-shadow: 0 0 16px rgba(0,212,255,0.2);
  animation: pulse-cyan-slow 2.5s ease-in-out infinite;
}
.pill {
  display: inline-block; padding: 5px 12px; border-radius: 20px;
  font-family: 'JetBrains Mono', monospace; font-size: 0.7rem; font-weight: 700;
  animation: metricReveal 0.5s ease forwards;
}
.pill-critical { background: rgba(255,68,68,0.15); color: #ff4444; border: 1px solid #ff4444; }
.pill-high { background: rgba(255,68,68,0.15); color: #ff4444; border: 1px solid #ff4444; }
.pill-medium { background: rgba(251,191,36,0.12); color: #fbbf24; border: 1px solid #fbbf24; }
.pill-low { background: rgba(0,255,136,0.12); color: #00ff88; border: 1px solid #00ff88; }
.pill-unknown { background: rgba(100,116,139,0.12); color: #94a3b8; border: 1px solid #475569; }
.pending { color: #475569; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; font-style: italic; }

.banner {
  text-align: center; padding: 10px; border-radius: 8px; margin: 12px 0;
  font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; font-weight: 600;
  animation: fadeInLeft 0.4s ease forwards;
}
.banner-ok { background: rgba(0,255,136,0.08); color: #00ff88; border: 1px solid #00ff88; }
.banner-err { background: rgba(255,68,68,0.08); color: #ff4444; border: 1px solid #ff4444; }

.bottom-bar {
  display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;
  background: #0d1526; border: 1px solid #1a2d4f; border-radius: 10px;
  padding: 12px 20px; margin-top: 16px;
  font-family: 'JetBrains Mono', monospace; font-size: 0.65rem; color: #64748b;
  position: relative; z-index: 2;
}
.bottom-badges { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.badge {
  background: #060b18; border: 1px solid #1a2d4f; color: #00d4ff;
  padding: 4px 10px; border-radius: 4px; font-size: 0.6rem; letter-spacing: 0.5px;
}
.runtime-val { color: #00d4ff; font-weight: 700; font-size: 0.75rem; animation: countPop 0.5s ease; }

/* ── Keyframes ── */
@keyframes floatUp {
  0% { transform: translateY(20px); opacity: 0; }
  10% { opacity: 0.8; }
  90% { opacity: 0.6; }
  100% { transform: translateY(-110vh); opacity: 0; }
}
@keyframes gridDrift {
  0% { transform: translate(0, 0); }
  100% { transform: translate(48px, 48px); }
}
@keyframes borderPulse {
  0%, 100% { box-shadow: 0 0 6px rgba(0,212,255,0.2); border-color: #00d4ff; }
  50% { box-shadow: 0 0 22px rgba(0,212,255,0.65); border-color: #8b5cf6; }
}
@keyframes completeSweep {
  0% { background: rgba(0,255,136,0.45); box-shadow: 0 0 30px rgba(0,255,136,0.6); }
  100% { background: #0d1526; box-shadow: 0 0 14px rgba(0,255,136,0.25); }
}
@keyframes progressFill {
  0% { width: 0; left: 0; }
  50% { width: 75%; left: 10%; }
  100% { width: 0; left: 100%; }
}
@keyframes burstOut1 { 0% { transform: translate(0,0); opacity:1; } 100% { transform: translate(-18px,-18px); opacity:0; } }
@keyframes burstOut2 { 0% { transform: translate(0,0); opacity:1; } 100% { transform: translate(18px,-18px); opacity:0; } }
@keyframes burstOut3 { 0% { transform: translate(0,0); opacity:1; } 100% { transform: translate(-18px,18px); opacity:0; } }
@keyframes burstOut4 { 0% { transform: translate(0,0); opacity:1; } 100% { transform: translate(18px,18px); opacity:0; } }
@keyframes pulse-cyan-slow {
  0%, 100% { box-shadow: 0 0 12px rgba(0,212,255,0.35); }
  50% { box-shadow: 0 0 28px rgba(0,212,255,0.7); }
}
@keyframes pulse-cyan-fast {
  0%, 100% { box-shadow: 0 0 16px rgba(0,212,255,0.5); transform: scale(1); }
  50% { box-shadow: 0 0 40px rgba(0,212,255,0.95); transform: scale(1.02); }
}
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.35; } }
@keyframes fadeInLeft {
  from { opacity: 0; transform: translateX(-16px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes clockFade {
  0% { opacity: 0.4; } 15% { opacity: 1; } 100% { opacity: 1; }
}
@keyframes glitch {
  0% { opacity: 1; transform: translate(0); text-shadow: none; }
  15% { opacity: 0.3; transform: translate(-2px, 1px); text-shadow: 2px 0 #ff4444, -2px 0 #00d4ff; }
  30% { opacity: 1; transform: translate(2px, -1px); text-shadow: -2px 0 #8b5cf6, 2px 0 #00ff88; }
  45% { opacity: 0.5; transform: translate(-1px, 0); text-shadow: 1px 0 #00d4ff; }
  60% { opacity: 0.8; transform: translate(1px, 1px); text-shadow: -1px 0 #ff4444; }
  75% { opacity: 0.4; transform: translate(0); text-shadow: 2px 0 #00d4ff; }
  100% { opacity: 1; transform: translate(0); text-shadow: 0 0 20px rgba(0,212,255,0.3); }
}
@keyframes countUp {
  0% { --num: 0; opacity: 0.3; transform: scale(0.85); }
  100% { --num: var(--target); opacity: 1; transform: scale(1); }
}
@keyframes countPop {
  0% { opacity: 0; transform: translateY(10px) scale(0.7); }
  70% { transform: translateY(-2px) scale(1.04); }
  100% { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes metricReveal {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 1100px) { .agent-grid { grid-template-columns: repeat(4, 1fr); } }
@media (max-width: 700px) { .agent-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
"""


# ── HTML builders ─────────────────────────────────────────────────────────────

def build_header_html():
    running = st.session_state.running
    dot_cls = "dot-active" if running else "dot-online"
    status_txt = "PIPELINE ACTIVE" if running else "SYSTEM ONLINE"
    clock = time.strftime("%H:%M:%S")
    sec = int(time.time()) % 2
    clock_cls = "clock clock-tick" if sec else "clock"
    return f"""
<div class="header-bar">
  <div class="header-logo">◈ COMPANY OS</div>
  <div class="header-right">
    <span><span class="dot {dot_cls}"></span>{status_txt}</span>
    <span class="{clock_cls}">{clock}</span>
  </div>
</div>"""


def build_hero_html():
    return """
<div class="hero-wrap">
  <h1 class="hero-h1">Initialize Your Company</h1>
  <p class="hero-sub">One idea. Seven agents. A company in minutes.</p>
</div>"""


def build_agent_cards_html():
    cards = []
    sweep_done = st.session_state.sweep_done
    burst_html = build_burst_html()

    for name, key, icon in AGENTS:
        status = st.session_state.agent_status.get(key, "idle")
        label = status_label(status)
        preview = esc(st.session_state.agent_output.get(key, "Standby"))

        extra_cls = ""
        if status == "complete":
            card_cls, bar_cls, st_cls = "card-complete", "bar-complete", "st-complete"
            if key not in sweep_done:
                extra_cls = " card-complete-sweep"
        elif status == "error":
            card_cls, bar_cls, st_cls = "card-error", "bar-error", "st-error"
        elif status == "running":
            card_cls, bar_cls, st_cls = "card-running", "bar-running", "st-running"
        elif status == "initializing":
            card_cls, bar_cls, st_cls = "card-running", "bar-init", "st-init"
        else:
            card_cls, bar_cls, st_cls = "card-idle", "bar-idle", "st-idle"

        check = '<span class="card-check">✓</span>' if status == "complete" else ""
        progress = '<div class="card-progress"></div>' if status in ("running", "initializing") else ""
        burst = burst_html if status == "complete" and key not in sweep_done else ""

        cards.append(f"""
<div class="agent-card {card_cls}{extra_cls}">
  <div class="status-bar {bar_cls}"></div>
  {check}{burst}
  <div class="card-body">
    <div class="card-icon">{icon}</div>
    <div class="card-name">{esc(name)}</div>
    <div class="card-status {st_cls}">{label}</div>
    <div class="card-preview">{preview}</div>
  </div>
  {progress}
</div>""")

    mark_sweeps()
    return f'<div class="agent-grid">{"".join(cards)}</div>'


def build_feed_html():
    feed = st.session_state.activity_feed
    if feed:
        recent = feed[-150:]
        body = "".join(colorize_line(line, i) for i, line in enumerate(recent))
    else:
        body = '<div class="feed-line line-idle">// Awaiting launch command...</div>'
    return f"""
<div class="panel">
  <div class="panel-head">⬡ Live Activity Feed</div>
  <div class="terminal">{body}</div>
</div>"""


def build_risk_pill(level):
    if not level:
        return '<span class="pill pill-unknown">UNKNOWN</span>'
    level = level.lower()
    if level in ("critical", "high"):
        return f'<span class="pill pill-{level}">{esc(level.upper())}</span>'
    if level == "medium":
        return '<span class="pill pill-medium">MEDIUM</span>'
    if level == "low":
        return '<span class="pill pill-low">LOW</span>'
    return f'<span class="pill pill-unknown">{esc(level.upper())}</span>'


def build_results_html():
    r = st.session_state.results
    github_url = get_github_url_from_brain() or r.get("github_url") or r.get("url")
    company = r.get("company")
    email_count = r.get("email_count", 0)
    emails_sent = r.get("emails_sent")
    revenue = r.get("revenue_value")
    risk = r.get("risk_level")

    if company:
        company_block = (
            f'<div class="result-card"><div class="result-label">Company Name</div>'
            f'<div class="result-company">{esc(company)}</div></div>'
        )
    else:
        company_block = (
            '<div class="result-card"><div class="result-label">Company Name</div>'
            '<div class="pending">Awaiting CEO agent...</div></div>'
        )

    if github_url:
        url_block = (
            f'<div class="result-card"><div class="result-label">Live URL</div>'
            f'<a class="url-link" href="{esc(github_url)}" target="_blank">'
            f'↗ OPEN LIVE SITE — {esc(github_url)}</a></div>'
        )
    else:
        url_block = (
            '<div class="result-card"><div class="result-label">Live URL</div>'
            '<div class="pending">Awaiting engineer agent...</div></div>'
        )

    if emails_sent is not None:
        email_display = f"{email_count} ({'sent' if emails_sent else 'drafted'})"
        email_val = count_up_html("emails", email_display, email_count)
    else:
        email_val = count_up_html("emails", "—")

    if revenue:
        rev_num = parse_number(revenue)
        revenue_val = count_up_html("revenue", f"${esc(revenue)}", rev_num, prefix="$")
    else:
        revenue_val = count_up_html("revenue", "—")

    return f"""
<div class="panel">
  <div class="panel-head">⬡ Mission Results</div>
  {company_block}
  {url_block}
  <div class="result-card">
    <div class="result-label">Emails</div>
    {email_val}
  </div>
  <div class="result-card">
    <div class="result-label">3-Month Revenue</div>
    {revenue_val}
  </div>
  <div class="result-card">
    <div class="result-label">Risk Level</div>
    <div style="margin-top:4px;">{build_risk_pill(risk)}</div>
  </div>
</div>"""


def build_bottom_html():
    runtime = format_runtime()
    return f"""
<div class="bottom-bar">
  <div class="bottom-badges">
    <span style="color:#64748b;margin-right:4px;">POWERED BY</span>
    <span class="badge">CLAUDE AI</span>
    <span class="badge">AZURE COSMOS DB</span>
    <span class="badge">GITHUB PAGES</span>
    <span class="badge">PYTHON</span>
  </div>
  <div class="runtime-val">RUNTIME: {runtime}</div>
</div>"""


def build_banner_html(success, code=0):
    if success:
        return '<div class="banner banner-ok">✓ MISSION COMPLETE — ALL AGENTS REPORTING</div>'
    return f'<div class="banner banner-err">✗ PIPELINE EXIT CODE {code}</div>'


def build_runtime_css():
    if st.session_state.running:
        return (
            "<style>div[data-testid=\"stButton\"] button { "
            "animation: pulse-cyan-fast 0.55s ease-in-out infinite !important; }</style>"
        )
    return (
        "<style>div[data-testid=\"stButton\"] button { "
        "animation: pulse-cyan-slow 2.5s ease-in-out infinite !important; }</style>"
    )

# ── Render helpers ────────────────────────────────────────────────────────────

def paint(cards_ph, feed_ph, results_ph, bottom_ph, banner_ph=None, banner_html=""):
    cards_ph.markdown(build_agent_cards_html(), unsafe_allow_html=True)
    feed_ph.markdown(build_feed_html(), unsafe_allow_html=True)
    results_ph.markdown(build_results_html(), unsafe_allow_html=True)
    if banner_ph is not None and banner_html:
        banner_ph.markdown(banner_html, unsafe_allow_html=True)
    bottom_ph.markdown(build_bottom_html(), unsafe_allow_html=True)


def run_pipeline_subprocess(idea, cards_ph, feed_ph, results_ph, banner_ph, bottom_ph):
    st.session_state.running = True
    reset_run_state()

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    process = subprocess.Popen(
        [sys.executable, str(ROOT / "main.py"), idea],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
        env=env,
        bufsize=1,
    )

    assert process.stdout is not None
    for raw_line in process.stdout:
        line = raw_line.rstrip("\n")
        if not line:
            continue
        st.session_state.activity_feed.append(line)
        update_agent_status(line)
        update_agent_output(line)
        parse_results_from_line(line)
        if st.session_state.agent_status.get("engineer") == "complete":
            load_results_from_brain()
        paint(cards_ph, feed_ph, results_ph, bottom_ph)

    process.wait()
    st.session_state.pipeline_end = time.time()
    load_results_from_brain()
    st.session_state.running = False

    banner = build_banner_html(process.returncode == 0, process.returncode)
    paint(cards_ph, feed_ph, results_ph, bottom_ph, banner_ph, banner)

    legal = st.session_state.results.get("legal_docs")
    if legal and Path(legal).exists():
        with open(legal, "rb") as f:
            st.download_button("⬇ Download Legal Docs", f.read(), Path(legal).name, "text/plain")


def main():
    st.set_page_config(page_title="Company OS — Mission Control", page_icon="🛰️", layout="wide")

    init_session_state()

    st.markdown(build_css(), unsafe_allow_html=True)
    st.markdown(build_runtime_css(), unsafe_allow_html=True)
    st.markdown(build_particles_html(), unsafe_allow_html=True)
    st.markdown(build_header_html(), unsafe_allow_html=True)
    st.markdown(build_hero_html(), unsafe_allow_html=True)

    c1, c2 = st.columns([3, 1])
    with c1:
        idea = st.text_input(
            "idea_input",
            placeholder="AI-powered task management for remote teams...",
            disabled=st.session_state.running,
            label_visibility="collapsed",
        )
    with c2:
        launch = st.button(
            "◈ LAUNCH COMPANY OS",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.running or not (idea or "").strip(),
        )

    cards_ph = st.empty()
    banner_ph = st.empty()
    col_l, col_r = st.columns(2)
    with col_l:
        feed_ph = st.empty()
    with col_r:
        results_ph = st.empty()
    bottom_ph = st.empty()

    paint(cards_ph, feed_ph, results_ph, bottom_ph)

    if launch and (idea or "").strip():
        run_pipeline_subprocess(idea.strip(), cards_ph, feed_ph, results_ph, banner_ph, bottom_ph)


if __name__ == "__main__":
    main()
