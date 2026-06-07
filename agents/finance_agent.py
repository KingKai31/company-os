import json
from utils.base_agent import BaseAgent


class FinanceAgent(BaseAgent):
    def __init__(self):
        super().__init__("finance_agent")

    def run(self, context):
        print("[FINANCE] Reading product and sales info from shared brain...")

        try:
            ceo_data = self.read("ceo_agent")
            sales_data = self.read("sales_agent")
            orchestrator_data = self.read("orchestrator")

            strategy = ceo_data.get("strategy", {})
            company_name = strategy.get("company_name", "Company")
            product = strategy.get("product", "")
            target_market = strategy.get("target_market", "")
            email_count = len(sales_data.get("drafts", []))
            emails_sent = sales_data.get("sent", False)

            finance_task = (
                orchestrator_data.get("plan", {})
                .get("tasks", {})
                .get("finance_agent", "Revenue projection")
            )

            print(f"[FINANCE] Generating 3-month revenue projection for {company_name}...")

            prompt = f"""You are a startup CFO building a financial model.

Company: {company_name}
Product: {product}
Target market: {target_market}
Outreach emails prepared: {email_count}
Emails sent: {emails_sent}
Task: {finance_task}

Create a realistic 3-month revenue projection with real dollar amounts.

Return ONLY a JSON object with this exact format:
{{
    "company_name": "{company_name}",
    "assumptions": {{
        "price_per_month": 49,
        "conversion_rate_percent": 2.5,
        "monthly_leads": 100
    }},
    "monthly_projections": [
        {{"month": 1, "leads": 100, "conversions": 3, "mrr": 147, "expenses": 500, "net": -353}},
        {{"month": 2, "leads": 150, "conversions": 5, "mrr": 392, "expenses": 600, "net": -208}},
        {{"month": 3, "leads": 200, "conversions": 8, "mrr": 784, "expenses": 700, "net": 84}}
    ],
    "burn_rate_monthly": 600,
    "runway_months": 14,
    "starting_cash": 8400,
    "total_3_month_revenue": 1323,
    "total_3_month_expenses": 1800,
    "total_3_month_net": -477,
    "break_even_month": 4,
    "summary": "One paragraph financial summary"
}}

Use realistic numbers based on the product and market. Return only JSON."""

            response = self.think(
                prompt,
                system="You are a startup CFO. Use conservative, realistic financial assumptions.",
                max_tokens=4000,
            )

            clean = response.replace("```json", "").replace("```", "").strip()
            try:
                projection = json.loads(clean)
            except json.JSONDecodeError:
                print("[FINANCE] JSON parse failed — using plain text response")
                projection = {"summary": clean, "parse_failed": True}

            confidence = self.score_confidence(json.dumps(projection))

            result = {
                "status": "complete",
                "company_name": company_name,
                "projection": projection,
                "confidence": confidence,
            }

            self.write(result)
            total_rev = projection.get("total_3_month_revenue", "N/A")
            print(f"[FINANCE] Projection complete — 3-month revenue: ${total_rev}")
            return result

        except Exception as e:
            print(f"[FINANCE] Error: {e}")
            self.write({"status": "error", "error": str(e)})
            return {"status": "error", "error": str(e)}
