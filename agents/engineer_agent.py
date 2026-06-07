import html
import json
import os
import re
import sys
from pathlib import Path

from github import Github
from utils.base_agent import BaseAgent

ROOT = Path(__file__).resolve().parent.parent

INDUSTRIES = [
    "FINTECH", "HEALTHTECH", "EDTECH", "CREATIVE", "B2B_SAAS",
    "ECOMMERCE", "DEVELOPER_TOOLS", "CONSUMER_APP",
]

DARK_INDUSTRIES = {"FINTECH", "DEVELOPER_TOOLS", "B2B_SAAS", "CREATIVE", "CONSUMER_APP", "EDTECH"}
LIGHT_INDUSTRIES = {"HEALTHTECH", "ECOMMERCE"}

INDUSTRY_THEME = {
    "FINTECH": {"bg": "#0a0e1a", "card": "#0d1526", "text": "#e2e8f0", "heading": "#ffffff", "accent": "#00d4ff", "gold": "#ffd700"},
    "HEALTHTECH": {"bg": "#f0fdf4", "card": "#ffffff", "text": "#334155", "heading": "#059669", "accent": "#0ea5e9", "gold": "#059669"},
    "EDTECH": {"bg": "#1e1b4b", "card": "#312e81", "text": "#e2e8f0", "heading": "#ffffff", "accent": "#f59e0b", "gold": "#a78bfa"},
    "CREATIVE": {"bg": "#09090b", "card": "#18181b", "text": "#e2e8f0", "heading": "#ffffff", "accent": "#ec4899", "gold": "#8b5cf6"},
    "B2B_SAAS": {"bg": "#0f172a", "card": "#1e293b", "text": "#e2e8f0", "heading": "#ffffff", "accent": "#3b82f6", "gold": "#10b981"},
    "ECOMMERCE": {"bg": "#fffbeb", "card": "#ffffff", "text": "#44403c", "heading": "#dc2626", "accent": "#f97316", "gold": "#dc2626"},
    "DEVELOPER_TOOLS": {"bg": "#0d1117", "card": "#161b22", "text": "#c9d1d9", "heading": "#ffffff", "accent": "#58a6ff", "gold": "#3fb950"},
    "CONSUMER_APP": {"bg": "#18181b", "card": "#27272a", "text": "#e2e8f0", "heading": "#ffffff", "accent": "#f43f5e", "gold": "#6366f1"},
}

RENDER_FIX_HEAD = """<meta http-equiv="X-UA-Compatible" content="IE=edge">
<style>
/* Company OS render fix */
body { min-height: 100vh; }
h1,h2,h3,h4,h5,h6,p,span,a,li,td,th,label { color: inherit; }
section, div { visibility: visible !important; opacity: 1 !important; }
</style>
"""

VERIFY_MIN_LENGTH = 5000
DASHBOARD_URL = os.getenv("DASHBOARD_URL", "http://localhost:5000")


def _esc(text):
    return html.escape(str(text if text is not None else ""))


def _fmt_money(val):
    try:
        return f"${int(float(val)):,}"
    except (TypeError, ValueError):
        return _esc(val)


class EngineerAgent(BaseAgent):
    def __init__(self):
        super().__init__("engineer_agent")

    def _parse_json(self, text):
        clean = text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)

    def _color_scheme_label(self, industry):
        return INDUSTRY_THEME.get(industry, INDUSTRY_THEME["B2B_SAAS"])["accent"]

    def _detect_dark_page(self, html, industry):
        return industry in DARK_INDUSTRIES

    def _theme_fix_css(self, industry, is_dark):
        theme = INDUSTRY_THEME.get(industry, INDUSTRY_THEME["B2B_SAAS"])
        lines = ["/* Company OS theme fix */"]
        if industry in LIGHT_INDUSTRIES:
            lines.append(f"body {{ background-color: {theme['bg']} !important; color: {theme['text']} !important; }}")
            lines.append(f"h1,h2,h3,h4,h5,h6 {{ color: {theme['heading']} !important; }}")
            lines.append(f"p,span,li,td,th,label {{ color: {theme['text']} !important; }}")
        else:
            lines.append(f"body {{ background-color: {theme['bg']} !important; color: {theme['text']} !important; }}")
            lines.append("h1,h2,h3,h4,h5,h6 { color: #ffffff !important; }")
            lines.append("p,span,li,td,th,label { color: #e2e8f0 !important; }")
        return "<style>\n" + "\n".join(lines) + "\n</style>"

    def _apply_render_fixes(self, html, industry):
        is_dark = self._detect_dark_page(html, industry)
        if "X-UA-Compatible" not in html:
            html = re.sub(
                r"</head>",
                RENDER_FIX_HEAD + self._theme_fix_css(industry, is_dark) + "\n</head>",
                html, count=1, flags=re.IGNORECASE,
            )
        return html

    def _apply_github_pages_fixes(self, html):
        if not html.strip().lower().startswith("<!doctype html"):
            html = "<!DOCTYPE html>\n" + html.lstrip()
        for old, new in {
            "linear-gradient(to bottom,": "linear-gradient(180deg,",
            "linear-gradient(to top,": "linear-gradient(0deg,",
            "linear-gradient(to right,": "linear-gradient(90deg,",
            "linear-gradient(to left,": "linear-gradient(270deg,",
        }.items():
            html = html.replace(old, new)
        if not re.search(r'<html[^>]*\blang\s*=\s*["\']en["\']', html, re.I):
            html = re.sub(r"<html([^>]*)>", r'<html lang="en"\1>', html, count=1, flags=re.I)
        if not re.search(r'charset\s*=\s*["\']?UTF-8', html, re.I):
            html = re.sub(r"(<head[^>]*>)", r'\1\n  <meta charset="UTF-8">', html, count=1, flags=re.I)
        # Do not inject <base href="/"> — breaks same-page #anchor navigation on GitHub Pages subpaths
        html = re.sub(r'\s*<base\s+href=["\'][^"\']*["\']\s*/?\>\s*', "\n", html, flags=re.I)
        html = re.sub(
            r"(?<![\w-])backdrop-filter:\s*([^;{}]+);",
            r"-webkit-backdrop-filter: \1; backdrop-filter: \1;",
            html,
        )
        return html

    def _postprocess_html(self, html, industry):
        html = self._apply_github_pages_fixes(html)
        html = self._apply_render_fixes(html, industry)
        return html

    def detect_industry(self, context):
        print("[ENGINEER] Detecting industry for dashboard theme...")
        prompt = f"""Classify this business into ONE industry category.

Founder input: {context.get('founder_input', '')}
Company: {context.get('company_name', '')}
Product: {context.get('product', '')}

Categories: FINTECH, HEALTHTECH, EDTECH, CREATIVE, B2B_SAAS, ECOMMERCE, DEVELOPER_TOOLS, CONSUMER_APP

Return ONLY JSON: {{"industry": "FINTECH", "confidence": 95}}"""

        response = self.think(prompt, system="Return only valid JSON.", max_tokens=200)
        try:
            result = self._parse_json(response)
            industry = result.get("industry", "B2B_SAAS").upper()
            if industry not in INDUSTRIES:
                industry = "B2B_SAAS"
            confidence = int(result.get("confidence", 80))
        except (json.JSONDecodeError, ValueError, TypeError):
            industry, confidence = "B2B_SAAS", 70

        print(f"[ENGINEER] Industry detected: {industry} ({confidence}% confidence)")
        print(f"[ENGINEER] Design system loaded: {_esc(self._color_scheme_label(industry))} theme")
        return industry, confidence

    def _gather_all_agent_data(self):
        print("[ENGINEER] Reading all agent outputs from shared brain...")
        ceo = self.read("ceo_agent") or {}
        finance = self.read("finance_agent") or {}
        sales = self.read("sales_agent") or {}
        risk = self.read("risk_agent") or {}
        legal = self.read("legal_agent") or {}
        orchestrator = self.read("orchestrator") or {}

        if not ceo or ceo.get("status") == "error":
            raise ValueError("CEO agent data required — run CEO before Engineer")

        strategy = ceo.get("strategy", {})
        projection = finance.get("projection", {})
        risk_report = risk.get("risk_report", {})
        risks = risk_report.get("risks", [])[:3]
        monthly = projection.get("monthly_projections", [])
        assumptions = projection.get("assumptions", {})

        phases = strategy.get("strategy_90_day", {})
        okrs = strategy.get("okrs", [])

        burn = projection.get("burn_rate_monthly")
        if burn is None and monthly:
            burn = sum(m.get("expenses", 0) for m in monthly) / max(len(monthly), 1)

        runway = projection.get("runway_months")
        if runway is None and burn:
            cash = projection.get("starting_cash", 10000)
            try:
                runway = round(float(cash) / float(burn), 1)
            except (TypeError, ValueError, ZeroDivisionError):
                runway = "N/A"

        def _month_rev(m):
            if not m:
                return 0
            return m.get("mrr") or m.get("revenue") or m.get("net", 0)

        rev_m1 = _month_rev(monthly[0] if len(monthly) > 0 else {})
        rev_m2 = _month_rev(monthly[1] if len(monthly) > 1 else {})
        rev_m3 = _month_rev(monthly[2] if len(monthly) > 2 else {})
        max_rev = max(rev_m1, rev_m2, rev_m3, 1)

        return {
            "founder_input": orchestrator.get("founder_input", ""),
            "company_name": strategy.get("company_name") or ceo.get("company_name", "Company"),
            "vision": strategy.get("vision", ""),
            "target_customer": strategy.get("target_market", ""),
            "product": strategy.get("product", ""),
            "okrs": okrs,
            "phase_1": phases.get("phase_1_days_1_30", ""),
            "phase_2": phases.get("phase_2_days_31_60", ""),
            "phase_3": phases.get("phase_3_days_61_90", ""),
            "rev_m1": rev_m1, "rev_m2": rev_m2, "rev_m3": rev_m3,
            "max_rev": max_rev,
            "burn_rate": burn,
            "runway": runway,
            "break_even": projection.get("break_even_month", "N/A"),
            "finance_summary": projection.get("summary", ""),
            "conversion_rate": assumptions.get("conversion_rate_percent"),
            "price_per_month": assumptions.get("price_per_month"),
            "monthly_leads": assumptions.get("monthly_leads"),
            "leads_identified": sales.get("leads_identified") or len(sales.get("drafts", [])),
            "target_profile": sales.get("target_customer_profile") or strategy.get("target_market", ""),
            "outreach_strategy": sales.get("outreach_strategy") or orchestrator.get("plan", {}).get("tasks", {}).get("sales_agent", ""),
            "risks": risks,
            "risk_confidence": risk.get("confidence", 100),
            "overall_risk": risk_report.get("overall_risk_level", "unknown"),
            "risk_summary": risk_report.get("summary", ""),
            "negotiation": risk.get("confidence", 100) < 70,
            "tos_ok": legal.get("terms_of_service", False),
            "refund_ok": legal.get("refund_policy", False),
            "legal_path": legal.get("file_path", ""),
        }

    def _profile_initials(self, text):
        words = (text or "TC").split()[:2]
        return "".join(w[0].upper() for w in words if w)[:2] or "TC"

    def _ltv_cac_ratio(self, data):
        price = data.get("price_per_month")
        burn = data.get("burn_rate")
        leads = data.get("leads_identified") or 1
        try:
            if price and burn:
                ltv = float(price) * 12
                cac = float(burn) / max(int(leads), 1)
                if cac > 0:
                    return f"{ltv / cac:.1f}:1"
        except (TypeError, ValueError):
            pass
        return "N/A"

    def _severity_class(self, severity):
        s = (severity or "").lower()
        if s in ("critical", "high"):
            return "critical"
        if s == "medium":
            return "medium"
        return "low"

    def _build_intelligence_dashboard(self, data, industry):
        t = INDUSTRY_THEME.get(industry, INDUSTRY_THEME["B2B_SAAS"])
        is_light = industry in LIGHT_INDUSTRIES
        border = "rgba(255,255,255,0.08)" if not is_light else "rgba(0,0,0,0.08)"
        muted = "#94a3b8" if not is_light else "#64748b"
        btn_text = "#0a0e1a" if not is_light else "#fff"
        ltv_cac = self._ltv_cac_ratio(data)
        initials = self._profile_initials(data["target_profile"])
        conf = int(data["risk_confidence"] or 0)
        conf_deg = int(360 * conf / 100)

        okr_cards = ""
        for okr in data["okrs"]:
            obj = okr.get("objective", "")
            krs = okr.get("key_results", [])
            kr_html = "".join(f"<li>{_esc(kr)}</li>" for kr in krs)
            okr_cards += f"""
            <div class="card okr-card">
              <h3>{_esc(obj)}</h3>
              <ul class="kr-list">{kr_html}</ul>
              <div class="progress-wrap"><div class="progress-bar"></div></div>
              <span class="progress-label">Day 1 of 90 — 0% complete</span>
            </div>"""

        if not okr_cards:
            okr_cards = '<div class="card okr-card"><p>Strategy OKRs loaded from CEO agent.</p></div>'

        risk_cards = ""
        for i, risk in enumerate(data["risks"]):
            sev = self._severity_class(risk.get("severity"))
            risk_cards += f"""
            <div class="card risk-card sev-{sev}">
              <div class="risk-severity-bar"></div>
              <div class="risk-body">
                <div class="risk-header">
                  <span class="badge {sev}">{_esc(risk.get('severity', 'unknown')).upper()}</span>
                  <h3>{_esc(risk.get('title', ''))}</h3>
                </div>
                <p class="risk-desc">{_esc(risk.get('description', ''))}</p>
                <button class="mit-toggle" onclick="this.classList.toggle('open');this.nextElementSibling.classList.toggle('open')">View Mitigation ▾</button>
                <div class="mitigation-panel"><strong>Mitigation:</strong> {_esc(risk.get('mitigation', ''))}</div>
              </div>
            </div>"""

        if not risk_cards:
            risk_cards = f'<div class="card risk-card"><p>{_esc(data["risk_summary"] or "Risk analysis pending.")}</p></div>'

        neg_badge = ""
        if data["negotiation"]:
            neg_badge = '<span class="negotiation-badge">⚡ NEGOTIATION ACTIVATED</span>'

        overall_sev = self._severity_class(data["overall_risk"])
        conv_rate = data["conversion_rate"] or 0
        monthly_leads = data["monthly_leads"] or 0
        conversions = int(monthly_leads * conv_rate / 100) if monthly_leads and conv_rate else 0

        max_rev = data["max_rev"]
        bar_px1 = max(int(200 * data["rev_m1"] / max_rev), 4)
        bar_px2 = max(int(200 * data["rev_m2"] / max_rev), 4)
        bar_px3 = max(int(200 * data["rev_m3"] / max_rev), 4)
        pct1 = round(100 * data["rev_m1"] / max_rev, 1)
        pct2 = round(100 * data["rev_m2"] / max_rev, 1)
        pct3 = round(100 * data["rev_m3"] / max_rev, 1)

        tos_status = "GENERATED" if data["tos_ok"] else "PENDING"
        refund_status = "GENERATED" if data["refund_ok"] else "PENDING"

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(data['company_name'])} — Company Intelligence Report</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
  <style>
    /* Company OS — content always visible */
    body, main, .main-content, section, .container, .hero, .strategy, .financials {{
      display: block !important;
      visibility: visible !important;
      opacity: 1 !important;
    }}
    :root {{
      --bg: {t['bg']}; --card: {t['card']}; --text: {t['text']};
      --heading: {t['heading']}; --accent: {t['accent']}; --gold: {t['gold']};
      --border: {border}; --muted: {muted};
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ scroll-behavior: smooth; scroll-padding-top: 80px; }}
    body {{
      font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text);
      line-height: 1.6; overflow-x: hidden;
      animation: fadeInPage 0.8s ease forwards;
    }}
    @keyframes fadeInPage {{
      from {{ opacity: 0; }}
      to {{ opacity: 1; }}
    }}
    .container {{ max-width: 1100px; margin: 0 auto; padding: 0 24px; }}
    h1,h2,h3 {{ font-family: 'Space Grotesk', sans-serif; color: var(--heading); }}
    .section {{ padding: 72px 0; border-top: 1px solid var(--border); }}
    .section-title {{
      font-size: 0.72rem; letter-spacing: 2.5px; text-transform: uppercase;
      color: var(--accent); margin-bottom: 10px; font-weight: 600;
    }}
    .card {{
      background: var(--card); border: 1px solid var(--border);
      border-radius: 14px; padding: 24px; margin-bottom: 16px;
    }}
    /* Navbar */
    .navbar {{
      position: sticky; top: 0; z-index: 1000;
      background: color-mix(in srgb, var(--bg) 85%, transparent);
      -webkit-backdrop-filter: blur(12px); backdrop-filter: blur(12px);
      border-bottom: 1px solid var(--border);
    }}
    .nav-inner {{
      display: flex; align-items: center; justify-content: space-between;
      height: 64px; gap: 16px;
    }}
    .nav-logo {{ font-family: 'Space Grotesk', sans-serif; font-weight: 700; color: var(--heading) !important; text-decoration: none; font-size: 0.95rem; }}
    .nav-links {{ display: flex; gap: 8px; flex-wrap: wrap; list-style: none; }}
    .nav-links a {{
      text-decoration: none; color: var(--muted) !important; font-size: 0.82rem;
      font-weight: 500; padding: 6px 12px; border-radius: 6px; transition: all 0.2s;
    }}
    .nav-links a:hover, .nav-links a.active {{ color: var(--accent) !important; background: rgba(255,255,255,0.06); }}
    /* Hero */
    .hero {{ padding: 72px 0 56px; text-align: center; }}
    .hero h1 {{ font-size: clamp(2rem, 5vw, 3.2rem); margin-bottom: 16px; }}
    .hero .value-prop {{ font-size: 1.15rem; max-width: 720px; margin: 0 auto 20px; }}
    .hero .built-for {{
      display: inline-block; border: 1px solid var(--accent); border-radius: 999px;
      padding: 8px 20px; font-size: 0.85rem; margin-bottom: 32px;
      background: color-mix(in srgb, var(--accent) 8%, transparent);
    }}
    .hero-btns {{ display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; }}
    .btn {{
      padding: 14px 28px; border-radius: 8px; font-weight: 600;
      text-decoration: none; transition: transform 0.2s, box-shadow 0.2s; cursor: pointer;
    }}
    .btn-primary {{ background: linear-gradient(135deg, var(--accent), var(--gold)); color: {btn_text} !important; }}
    .btn-secondary {{ border: 1px solid var(--accent); color: var(--accent) !important; background: transparent; }}
    .btn:hover {{ transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.25); }}
    /* OKRs */
    .okr-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 16px; margin-top: 24px; }}
    .okr-card {{ border-left: 4px solid var(--accent); }}
    .okr-card h3 {{ color: var(--heading); font-weight: 700; margin-bottom: 12px; }}
    .kr-list {{ margin: 12px 0; padding-left: 18px; color: var(--muted); }}
    .kr-list li {{ margin-bottom: 6px; font-size: 0.9rem; }}
    .progress-wrap {{ background: rgba(255,255,255,0.08); border-radius: 999px; height: 6px; margin-top: 14px; }}
    .progress-bar {{ width: 0%; background: var(--accent); height: 100%; border-radius: 999px; }}
    .progress-label {{ font-size: 0.75rem; color: var(--muted); margin-top: 6px; display: block; }}
    /* Timeline steps */
    .timeline-steps {{
      display: flex; align-items: flex-start; gap: 0; margin-top: 32px; position: relative;
    }}
    .timeline-steps::before {{
      content: ''; position: absolute; top: 24px; left: 10%; right: 10%;
      height: 2px; background: var(--accent); z-index: 0;
    }}
    .step {{
      flex: 1; text-align: center; position: relative; z-index: 1; padding: 0 8px;
    }}
    .step-circle {{
      width: 48px; height: 48px; border-radius: 50%; background: var(--accent);
      color: {btn_text}; font-weight: 700; font-size: 1.1rem;
      display: flex; align-items: center; justify-content: center; margin: 0 auto 12px;
      box-shadow: 0 0 20px color-mix(in srgb, var(--accent) 40%, transparent);
    }}
    .step h4 {{ color: var(--accent); margin-bottom: 8px; font-size: 0.95rem; }}
    .step p {{ font-size: 0.85rem; color: var(--muted); text-align: left; }}
    @media (max-width: 768px) {{
      .timeline-steps {{ flex-direction: column; gap: 24px; }}
      .timeline-steps::before {{ display: none; }}
    }}
    /* Finance chart */
    .chart-wrap {{ margin: 32px 0; padding: 24px; background: var(--card); border-radius: 14px; border: 1px solid var(--border); }}
    .chart {{ display: flex; align-items: flex-end; justify-content: center; gap: 32px; height: 220px; }}
    .bar-col {{ display: flex; flex-direction: column; align-items: center; justify-content: flex-end; height: 200px; flex: 1; max-width: 100px; }}
    .bar-amount {{ font-size: 1rem; font-weight: 700; color: var(--accent); margin-bottom: 8px; }}
    .bar {{
      width: 56px; border-radius: 8px 8px 0 0;
      background: linear-gradient(180deg, var(--accent), var(--gold));
      height: 0; animation-fill-mode: forwards;
    }}
    .bar-m1 {{ animation: growBar1 1.2s ease-out 0.3s forwards; }}
    .bar-m2 {{ animation: growBar2 1.2s ease-out 0.5s forwards; }}
    .bar-m3 {{ animation: growBar3 1.2s ease-out 0.7s forwards; }}
    @keyframes growBar1 {{ from {{ height: 0; }} to {{ height: {bar_px1}px; }} }}
    @keyframes growBar2 {{ from {{ height: 0; }} to {{ height: {bar_px2}px; }} }}
    @keyframes growBar3 {{ from {{ height: 0; }} to {{ height: {bar_px3}px; }} }}
    .bar-label {{ margin-top: 10px; font-size: 0.8rem; font-weight: 600; color: var(--muted); }}
    .bar-pct {{ font-size: 0.7rem; color: var(--muted); }}
    .finance-stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-top: 24px; }}
    .metric-card {{ text-align: center; padding: 24px 16px; }}
    .metric-card .lbl {{ font-size: 0.75rem; color: var(--muted); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px; }}
    .metric-card .val {{ font-size: 1.9rem; font-weight: 700; color: var(--accent); }}
    /* Market */
    .profile-card {{ display: flex; gap: 20px; align-items: flex-start; }}
    .avatar {{
      width: 56px; height: 56px; border-radius: 50%; flex-shrink: 0;
      background: linear-gradient(135deg, var(--accent), var(--gold));
      color: {btn_text}; font-weight: 700; font-size: 1.1rem;
      display: flex; align-items: center; justify-content: center;
    }}
    .leads-metric {{ text-align: center; padding: 32px; }}
    .leads-metric .val {{ font-size: 3.5rem; font-weight: 700; color: var(--accent); line-height: 1; }}
    .funnel {{ display: flex; flex-direction: column; align-items: center; gap: 4px; margin-top: 16px; }}
    .funnel-step {{
      text-align: center; padding: 12px; color: #fff; font-weight: 600; font-size: 0.85rem;
    }}
    .funnel-step:nth-child(1) {{ width: 100%; background: var(--accent); clip-path: polygon(0 0, 100% 0, 92% 100%, 8% 100%); }}
    .funnel-step:nth-child(2) {{ width: 75%; background: color-mix(in srgb, var(--accent) 70%, var(--gold)); clip-path: polygon(0 0, 100% 0, 90% 100%, 10% 100%); }}
    .funnel-step:nth-child(3) {{ width: 50%; background: var(--gold); clip-path: polygon(0 0, 100% 0, 88% 100%, 12% 100%); color: {btn_text}; }}
    /* Risk */
    .risk-top {{ display: flex; align-items: center; gap: 24px; flex-wrap: wrap; margin-bottom: 24px; }}
    .overall-badge {{
      font-size: 0.85rem; font-weight: 700; padding: 10px 20px; border-radius: 8px;
      letter-spacing: 1px; text-transform: uppercase;
    }}
    .overall-badge.critical {{ background: #ef4444; color: #fff; }}
    .overall-badge.medium {{ background: #eab308; color: #000; }}
    .overall-badge.low {{ background: #22c55e; color: #fff; }}
    .confidence-ring {{
      width: 72px; height: 72px; border-radius: 50%; position: relative;
      background: conic-gradient(var(--accent) {conf_deg}deg, rgba(255,255,255,0.1) 0deg);
      display: flex; align-items: center; justify-content: center;
    }}
    .confidence-ring::before {{
      content: ''; position: absolute; inset: 6px; border-radius: 50%; background: var(--card);
    }}
    .confidence-ring span {{ position: relative; z-index: 1; font-weight: 700; font-size: 0.85rem; color: var(--accent); }}
    .risk-card {{ display: flex; overflow: hidden; padding: 0; }}
    .risk-severity-bar {{ width: 5px; flex-shrink: 0; }}
    .sev-critical .risk-severity-bar {{ background: #ef4444; }}
    .sev-medium .risk-severity-bar {{ background: #eab308; }}
    .sev-low .risk-severity-bar {{ background: #22c55e; }}
    .risk-body {{ padding: 20px 24px; flex: 1; }}
    .badge {{ font-size: 0.65rem; font-weight: 700; padding: 4px 10px; border-radius: 999px; letter-spacing: 1px; }}
    .badge.critical {{ background: #ef4444; color: #fff; }}
    .badge.medium {{ background: #eab308; color: #000; }}
    .badge.low {{ background: #22c55e; color: #fff; }}
    .risk-header {{ display: flex; align-items: center; gap: 12px; margin-bottom: 10px; flex-wrap: wrap; }}
    .risk-header h3 {{ color: var(--heading); font-weight: 700; font-size: 1rem; }}
    .risk-desc {{ color: var(--muted); font-size: 0.9rem; margin-bottom: 12px; }}
    .mit-toggle {{
      background: none; border: 1px solid var(--border); color: var(--accent);
      padding: 8px 14px; border-radius: 6px; cursor: pointer; font-size: 0.82rem;
    }}
    .mitigation-panel {{
      display: none; margin-top: 12px; padding: 14px;
      background: rgba(255,255,255,0.04); border-radius: 8px; font-size: 0.9rem;
    }}
    .mitigation-panel.open {{ display: block; }}
    .negotiation-badge {{
      display: inline-block; background: #eab308; color: #000;
      padding: 10px 18px; border-radius: 8px; font-weight: 700;
      font-size: 0.82rem; letter-spacing: 1px; margin-bottom: 16px;
      animation: negPulse 1.5s ease infinite;
    }}
    @keyframes negPulse {{ 0%,100% {{ box-shadow: 0 0 0 0 rgba(234,179,8,0.6); }} 50% {{ box-shadow: 0 0 0 12px rgba(234,179,8,0); }} }}
    /* Legal */
    .legal-row {{
      display: flex; align-items: center; gap: 16px; padding: 16px 0;
      border-bottom: 1px solid var(--border);
    }}
    .legal-row:last-child {{ border-bottom: none; }}
    .icon-circle {{
      width: 36px; height: 36px; border-radius: 50%; display: flex;
      align-items: center; justify-content: center; font-weight: 700; flex-shrink: 0;
    }}
    .icon-circle.ok {{ background: rgba(34,197,94,0.15); color: #22c55e; }}
    .icon-circle.pending {{ background: rgba(148,163,184,0.15); color: var(--muted); }}
    .status-badge {{ margin-left: auto; font-size: 0.7rem; font-weight: 700; padding: 4px 10px; border-radius: 999px; letter-spacing: 1px; }}
    .status-badge.ok {{ background: rgba(34,197,94,0.15); color: #22c55e; }}
    .status-badge.pending {{ background: rgba(148,163,184,0.15); color: var(--muted); }}
    /* Attribution */
    .attrib {{ text-align: center; padding: 64px 0; }}
    .attrib h2 {{ margin-bottom: 16px; }}
    .attrib p {{ color: var(--muted); margin-bottom: 8px; }}
  </style>
</head>
<body>
    <nav class="navbar">
      <div class="container nav-inner">
        <a class="nav-logo" href="#">{_esc(data['company_name'])}</a>
        <ul class="nav-links">
          <li><a href="#strategy" data-nav="strategy">Strategy</a></li>
          <li><a href="#financials" data-nav="financials">Financials</a></li>
          <li><a href="#market" data-nav="market">Market</a></li>
          <li><a href="#risks" data-nav="risks">Risks</a></li>
          <li><a href="#legal" data-nav="legal">Legal</a></li>
        </ul>
      </div>
    </nav>

    <section class="hero">
      <div class="container">
        <div class="section-title">Company Intelligence Report</div>
        <h1>{_esc(data['company_name'])}</h1>
        <p class="value-prop">{_esc(data['vision'])}</p>
        <div class="built-for">Built for: {_esc(data['target_customer'])}</div>
        <div class="hero-btns">
          <a href="#strategy" class="btn btn-primary">View Strategy</a>
          <a href="#financials" class="btn btn-secondary">See Financials</a>
        </div>
      </div>
    </section>

    <section id="strategy" class="section">
      <div class="container">
        <div class="section-title">90-Day Strategy</div>
        <h2>Strategic OKRs &amp; Milestones</h2>
        <div class="okr-grid">{okr_cards}</div>
        <div class="timeline-steps">
          <div class="step">
            <div class="step-circle">1</div>
            <h4>Month 1</h4>
            <p>{_esc(data['phase_1'])}</p>
          </div>
          <div class="step">
            <div class="step-circle">2</div>
            <h4>Month 2</h4>
            <p>{_esc(data['phase_2'])}</p>
          </div>
          <div class="step">
            <div class="step-circle">3</div>
            <h4>Month 3</h4>
            <p>{_esc(data['phase_3'])}</p>
          </div>
        </div>
      </div>
    </section>

    <section id="financials" class="section">
      <div class="container">
        <div class="section-title">Financial Projections</div>
        <h2>Revenue &amp; Runway Analysis</h2>
        <p style="margin:16px 0;color:var(--muted)">{_esc(data['finance_summary'])}</p>
        <div class="chart-wrap">
          <div class="chart">
            <div class="bar-col">
              <div class="bar-amount">{_fmt_money(data['rev_m1'])}</div>
              <div class="bar bar-m1"></div>
              <div class="bar-label">Month 1 MRR</div>
              <div class="bar-pct">{pct1}% of peak</div>
            </div>
            <div class="bar-col">
              <div class="bar-amount">{_fmt_money(data['rev_m2'])}</div>
              <div class="bar bar-m2"></div>
              <div class="bar-label">Month 2 MRR</div>
              <div class="bar-pct">{pct2}% of peak</div>
            </div>
            <div class="bar-col">
              <div class="bar-amount">{_fmt_money(data['rev_m3'])}</div>
              <div class="bar bar-m3"></div>
              <div class="bar-label">Month 3 MRR</div>
              <div class="bar-pct">{pct3}% of peak</div>
            </div>
          </div>
        </div>
        <div class="finance-stats">
          <div class="card metric-card">
            <div class="lbl">Burn Rate / Month</div>
            <div class="val">{_fmt_money(data['burn_rate'] or 0)}</div>
          </div>
          <div class="card metric-card">
            <div class="lbl">Runway</div>
            <div class="val">{_esc(data['runway'])} mo</div>
          </div>
          <div class="card metric-card">
            <div class="lbl">Break-Even Target</div>
            <div class="val">M{_esc(data['break_even'])}</div>
          </div>
          <div class="card metric-card">
            <div class="lbl">LTV:CAC Ratio</div>
            <div class="val">{_esc(ltv_cac)}</div>
          </div>
        </div>
      </div>
    </section>

    <section id="market" class="section">
      <div class="container">
        <div class="section-title">Market Intelligence</div>
        <h2>Sales &amp; Customer Profile</h2>
        <div class="card profile-card">
          <div class="avatar">{_esc(initials)}</div>
          <div>
            <h3>Target Customer Profile</h3>
            <p>{_esc(data['target_profile'])}</p>
          </div>
        </div>
        <div class="card leads-metric">
          <div class="lbl" style="color:var(--muted);text-transform:uppercase;letter-spacing:1px;font-size:0.75rem">Leads Identified</div>
          <div class="val">{data['leads_identified']}</div>
        </div>
        <div class="card">
          <h3>Outreach Strategy</h3>
          <p>{_esc(data['outreach_strategy'])}</p>
        </div>
        <div class="card">
          <h3>Conversion Assumptions</h3>
          <div class="funnel">
            <div class="funnel-step">{monthly_leads} Monthly Leads</div>
            <div class="funnel-step">{conv_rate}% Conversion Rate</div>
            <div class="funnel-step">~{conversions} Paying Customers / Mo</div>
          </div>
          <p style="margin-top:16px;color:var(--muted);font-size:0.9rem">{_esc(data['finance_summary'])}</p>
        </div>
      </div>
    </section>

    <section id="risks" class="section">
      <div class="container">
        <div class="section-title">Risk Dashboard</div>
        <h2>Risk Analysis &amp; Mitigation</h2>
        {neg_badge}
        <div class="risk-top">
          <span class="overall-badge {overall_sev}">Overall: {_esc(data['overall_risk']).upper()}</span>
          <div class="confidence-ring"><span>{conf}%</span></div>
          <span style="color:var(--muted);font-size:0.9rem">Agent Confidence Score</span>
        </div>
        {risk_cards}
      </div>
    </section>

    <section id="legal" class="section">
      <div class="container">
        <div class="section-title">Legal Status</div>
        <h2>Compliance &amp; Documentation</h2>
        <div class="card">
          <div class="legal-row">
            <div class="icon-circle {'ok' if data['tos_ok'] else 'pending'}">{'✓' if data['tos_ok'] else '○'}</div>
            <span>Terms of Service</span>
            <span class="status-badge {'ok' if data['tos_ok'] else 'pending'}">{tos_status}</span>
          </div>
          <div class="legal-row">
            <div class="icon-circle {'ok' if data['refund_ok'] else 'pending'}">{'✓' if data['refund_ok'] else '○'}</div>
            <span>Refund Policy</span>
            <span class="status-badge {'ok' if data['refund_ok'] else 'pending'}">{refund_status}</span>
          </div>
          <p style="margin-top:16px;color:var(--muted);font-size:0.85rem">Powered by Company OS Legal Agent</p>
        </div>
      </div>
    </section>

    <section id="about" class="section attrib">
      <div class="container">
        <div class="section-title">About Company OS</div>
        <h2>This company was built autonomously by Company OS</h2>
        <p>7 AI agents — 90 seconds — zero human input</p>
        <p>Microsoft Build AI Hackathon 2026 — Agent Swarms</p>
      </div>
    </section>

  <script>
    const navLinks = document.querySelectorAll('.nav-links a[data-nav]');
    const sections = ['strategy','financials','market','risks','legal'].map(id => document.getElementById(id));

    const navObs = new IntersectionObserver(entries => {{
      entries.forEach(e => {{
        if (e.isIntersecting) {{
          navLinks.forEach(a => a.classList.toggle('active', a.dataset.nav === e.target.id));
        }}
      }});
    }}, {{ rootMargin: '-30% 0px -60% 0px' }});

    sections.forEach(s => {{ if (s) navObs.observe(s); }});

    document.querySelectorAll('a[href^="#"]').forEach(a => {{
      a.addEventListener('click', e => {{
        const id = a.getAttribute('href');
        if (id && id.length > 1) {{
          e.preventDefault();
          const el = document.querySelector(id);
          if (el) el.scrollIntoView({{ behavior: 'smooth' }});
        }}
      }});
    }});
  </script>
</body>
</html>"""

    def _github_pages_url(self):
        username = os.getenv("GITHUB_USERNAME", "KingKai31").strip().lower()
        repo_name = os.getenv("GITHUB_REPO", "company-os").strip()
        return f"https://{username}.github.io/{repo_name}/"

    def _verify_github_commit(self, repo):
        contents = repo.get_contents("index.html")
        committed = contents.decoded_content.decode("utf-8")
        length = len(committed)
        if length < VERIFY_MIN_LENGTH:
            raise ValueError(f"GitHub verification failed: index.html only {length} chars")
        print(f"[ENGINEER] HTML verified: {length} characters committed successfully")
        return length

    def _commit_to_github(self, html_content, company_name):
        token = os.getenv("GITHUB_TOKEN")
        username = os.getenv("GITHUB_USERNAME")
        repo_name = os.getenv("GITHUB_REPO")
        if not all([token, username, repo_name]):
            raise ValueError("Missing GITHUB_TOKEN, GITHUB_USERNAME, or GITHUB_REPO in .env")

        print(f"[ENGINEER] Deploying intelligence dashboard to {username}/{repo_name}...")
        g = Github(token)
        repo = g.get_repo(f"{username}/{repo_name}")
        msg = f"Deploy {company_name} intelligence dashboard — Company OS"

        try:
            contents = repo.get_contents("index.html")
            repo.update_file(contents.path, msg, html_content, contents.sha)
        except Exception:
            repo.create_file("index.html", msg, html_content)

        self._verify_github_commit(repo)
        url = self._github_pages_url()
        print(f"[ENGINEER] Deployed successfully to {url}")
        return url

    def run(self, context):
        print("[ENGINEER] Building company intelligence dashboard from agent outputs...")

        try:
            data = self._gather_all_agent_data()
            company_name = data["company_name"]

            print(f"[ENGINEER] Loaded data for {company_name}:")
            print(f"[ENGINEER]   CEO: {len(data['okrs'])} OKRs, strategy phases loaded")
            print(f"[ENGINEER]   Finance: M1={_fmt_money(data['rev_m1'])}, M2={_fmt_money(data['rev_m2'])}, M3={_fmt_money(data['rev_m3'])}")
            print(f"[ENGINEER]   Sales: {data['leads_identified']} leads identified")
            print(f"[ENGINEER]   Risk: {len(data['risks'])} risks, confidence={data['risk_confidence']}%")
            print(f"[ENGINEER]   Legal: ToS={'yes' if data['tos_ok'] else 'no'}, Refund={'yes' if data['refund_ok'] else 'no'}")

            industry, industry_conf = self.detect_industry(data)

            print("[ENGINEER] Assembling intelligence dashboard HTML...")
            html_content = self._build_intelligence_dashboard(data, industry)
            html_content = self._postprocess_html(html_content, industry)
            print(f"[ENGINEER] Dashboard generated: {len(html_content)} characters")

            github_url = self._commit_to_github(html_content, company_name)
            confidence = self.score_confidence(html_content[:3000])

            result = {
                "status": "complete",
                "company_name": company_name,
                "github_url": github_url,
                "industry": industry,
                "industry_confidence": industry_conf,
                "dashboard_type": "intelligence_report",
                "html_length": len(html_content),
                "confidence": confidence,
            }

            self.write(result)
            print(f"[ENGINEER] Landing page live at: {github_url}")
            print(f"[ENGINEER] github_url written to shared brain: {github_url}")
            return result

        except Exception as e:
            print(f"[ENGINEER] Error: {e}")
            self.write({"status": "error", "error": str(e)})
            return {"status": "error", "error": str(e)}
