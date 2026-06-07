import sys
from dotenv import load_dotenv

load_dotenv()

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agents.orchestrator import Orchestrator
from agents.ceo_agent import CEOAgent
from agents.legal_agent import LegalAgent
from agents.sales_agent import SalesAgent
from agents.finance_agent import FinanceAgent
from agents.risk_agent import RiskAgent
from agents.engineer_agent import EngineerAgent


DEFAULT_IDEA = "AI-powered task management for remote teams"


def print_banner():
    print("\n" + "=" * 60)
    print("  COMPANY OS — Autonomous Startup Agent Pipeline")
    print("=" * 60 + "\n")


def print_step_complete(agent_name, result):
    status = result.get("status", "unknown") if isinstance(result, dict) else "done"
    print(f"\n[MAIN] ✓ {agent_name} complete — status: {status}\n")


def run_pipeline(founder_input):
    print_banner()
    print(f"[MAIN] Starting pipeline for: \"{founder_input}\"\n")

    results = {}
    plan = {}

    # 1. Orchestrator
    try:
        print("[MAIN] ── Step 1/7: Orchestrator ──")
        orchestrator = Orchestrator()
        plan = orchestrator.plan(founder_input)
        results["orchestrator"] = {"status": "complete", "plan": plan}
        print_step_complete("Orchestrator", results["orchestrator"])
    except Exception as e:
        print(f"[MAIN] Orchestrator failed: {e}")
        return results

    # 2. CEO
    try:
        print("[MAIN] ── Step 2/7: CEO Agent ──")
        ceo = CEOAgent()
        results["ceo_agent"] = ceo.run({})
        print_step_complete("CEO Agent", results["ceo_agent"])
    except Exception as e:
        print(f"[MAIN] CEO Agent failed: {e}")
        results["ceo_agent"] = {"status": "error", "error": str(e)}

    # 3. Legal
    try:
        print("[MAIN] ── Step 3/7: Legal Agent ──")
        legal = LegalAgent()
        results["legal_agent"] = legal.run({})
        print_step_complete("Legal Agent", results["legal_agent"])
    except Exception as e:
        print(f"[MAIN] Legal Agent failed: {e}")
        results["legal_agent"] = {"status": "error", "error": str(e)}

    # 4. Sales
    try:
        print("[MAIN] ── Step 4/7: Sales Agent (with approval gate) ──")
        sales = SalesAgent()
        results["sales_agent"] = sales.run({})
        print_step_complete("Sales Agent", results["sales_agent"])
    except Exception as e:
        print(f"[MAIN] Sales Agent failed: {e}")
        results["sales_agent"] = {"status": "error", "error": str(e)}

    # 5. Finance
    try:
        print("[MAIN] ── Step 5/7: Finance Agent ──")
        finance = FinanceAgent()
        results["finance_agent"] = finance.run({})
        print_step_complete("Finance Agent", results["finance_agent"])
    except Exception as e:
        print(f"[MAIN] Finance Agent failed: {e}")
        results["finance_agent"] = {"status": "error", "error": str(e)}

    # 6. Risk
    try:
        print("[MAIN] ── Step 6/7: Risk Agent ──")
        risk = RiskAgent()
        results["risk_agent"] = risk.run({})
        print_step_complete("Risk Agent", results["risk_agent"])
    except Exception as e:
        print(f"[MAIN] Risk Agent failed: {e}")
        results["risk_agent"] = {"status": "error", "error": str(e)}

    # 7. Engineer — deploys intelligence dashboard with ALL agent data
    try:
        print("[MAIN] ── Step 7/7: Engineer Agent (Intelligence Dashboard) ──")
        engineer = EngineerAgent()
        results["engineer_agent"] = engineer.run({})
        print_step_complete("Engineer Agent", results["engineer_agent"])
    except Exception as e:
        print(f"[MAIN] Engineer Agent failed: {e}")
        results["engineer_agent"] = {"status": "error", "error": str(e)}

    # Summary
    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60)

    ceo_data = results.get("ceo_agent", {})
    engineer_data = results.get("engineer_agent", {})
    legal_data = results.get("legal_agent", {})
    sales_data = results.get("sales_agent", {})
    finance_data = results.get("finance_agent", {})
    risk_data = results.get("risk_agent", {})

    company = ceo_data.get("company_name") or plan.get("company_name", "N/A")
    print(f"  Company:      {company}")
    print(f"  Intelligence: {engineer_data.get('github_url', 'N/A')}")
    print(f"  Legal docs:   {legal_data.get('file_path', 'N/A')}")
    print(f"  Emails sent:  {sales_data.get('sent', False)}")
    finance_proj = finance_data.get("projection", {})
    print(f"  3-mo revenue: ${finance_proj.get('total_3_month_revenue', 'N/A')}")
    risk_report = risk_data.get("risk_report", {})
    print(f"  Risk level:   {risk_report.get('overall_risk_level', 'N/A')}")
    print("=" * 60 + "\n")

    return results


if __name__ == "__main__":
    idea = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_IDEA
    run_pipeline(idea)
