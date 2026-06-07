# Company OS — Autonomous Startup Intelligence

**Microsoft Build AI Hackathon 2026 — Agent Swarms**

| | |
|---|---|
| **Demo URL** | https://kingkai31.github.io/company-os/ |
| **GitHub** | https://github.com/KingKai31/company-os |
| **Mission Control** | http://localhost:5000 (after `python run.py`) |

## Problem

3-person founding teams post-product-market-fit spend **40+ hours/week** on non-product operational work — legal, finance, sales, marketing, HR — work that requires **10 different expert roles** they cannot afford to hire.

Founders become accidental CEOs, CFOs, and general counsels instead of building product. Agencies charge $30,000+/year for work that should be automated.

## Solution

**Company OS** is an autonomous agent swarm where each agent owns one business function. Agents coordinate through a **dependency-aware shared brain**, block and unblock each other like real human teams, and run the entire company from a **single founder sentence**.

## Why This Wins

- **First system** to model inter-department task dependencies as a live blocking graph
- **Confidence negotiation**: agents that drop below 70% confidence broadcast for help rather than failing silently
- **Company memory graph** compounds daily — switching cost grows every hour the system runs
- **Three-layer defensibility**: data moat + network effect + switching cost

## Tech Stack

- **Python** — 7-agent pipeline (`main.py`)
- **Flask** — REST API + SSE streaming mission control UI
- **Azure Cosmos DB** — shared brain (`agent_state` container)
- **Claude API (Anthropic)** — all agent reasoning
- **GitHub Pages + PyGithub** — live intelligence report deployment
- **python-dotenv, requests, streamlit** — config, HTTP, optional Streamlit dashboard

## Technical Architecture

- **Frontend:** Flask + cinematic dashboard (`templates/index.html`) with SSE live streaming
- **Pipeline:** Python `main.py` orchestrates 7 agents sequentially
- **Shared Brain:** Azure Cosmos DB (`agent_state` container) — all agents read/write state
- **AI:** Claude via Anthropic API (Azure AI Foundry compatible)
- **Outputs:** GitHub Pages (PyGithub), Gmail SMTP (sales), local legal docs
- **API:** REST + Server-Sent Events (`/api/run`, `/api/stream`, `/api/results`, `/api/reset`)

See `static/architecture.html` for visual diagram.

## Azure Integration (deep, not surface)

- **Cosmos DB change feed** as nervous system — agent writes auto-trigger next agent in production
- **Azure AI Foundry** hosts all models with Prompt Flow visualization of each agent chain
- **Azure Container Apps with KEDA** for agent scaling based on pipeline queue depth
- **Azure Monitor / Application Insights** for pipeline telemetry and confidence alerts

## Demo

**Input:** `"I want to sell AI productivity templates to freelancers"`

**In ~90 seconds:**
- Live URL deployed to GitHub Pages
- 10 sales leads identified and emails drafted
- Terms of Service generated
- 3-month revenue projection calculated
- Risk analysis with confidence negotiation triggered
- All outputs verifiable after demo ends

## Business Case

Replaces **$30,000/year** in agency and contractor costs for early stage startups. **$26B** business process automation market. First solution a 3-person team can start in **under 2 minutes**.

## Why Now

2025 is the first year LLMs are reliable enough for autonomous business decisions. The window is open. **We built it.**

---

## Pre-Demo Script (10 minutes before presenting)

1. **Clear Cosmos DB**
   ```powershell
   python -c "from utils.shared_brain import clear_all; clear_all()"
   ```
   Or click **◈ RESET** in the dashboard.

2. **Test pipeline once**
   ```powershell
   python main.py "AI productivity templates for freelancers"
   ```

3. **Start full system**
   ```powershell
   python run.py
   ```

4. **Have browser open** at http://localhost:5000 (Live Demo tab)

5. **Have GitHub Pages URL ready:** https://kingkai31.github.io/company-os/

6. **Have DEMO_EMAIL inbox open** on phone for live email proof

7. **Show Architecture tab** first, then switch to Live Demo for the run

---

## How to Run

1. **Clone and install**
   ```powershell
   git clone https://github.com/KingKai31/company-os.git
   cd company-os
   pip install -r requirements.txt
   ```

2. **Configure `.env`** (copy from `.env.example` pattern — never commit secrets)
   ```
   COSMOS_CONNECTION_STRING=...
   CLAUDE_API_KEY=...
   GITHUB_TOKEN=...
   GITHUB_USERNAME=KingKai31
   GITHUB_REPO=company-os
   ```

3. **Run pipeline only (CLI)**
   ```powershell
   python main.py "I want to build a fitness app for busy professionals"
   ```

4. **Run full mission control UI**
   ```powershell
   python run.py
   ```
   Opens http://localhost:5000 — enter your idea and click **◈ INITIALIZE COMPANY OS**.

5. **Reset between demos**
   ```powershell
   python -c "from utils.shared_brain import clear_all; clear_all()"
   ```
   Or click **◈ RESET** in the dashboard header.
