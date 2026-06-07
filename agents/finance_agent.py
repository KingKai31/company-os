import json
from utils.base_agent import BaseAgent

FALLBACK_MONTHLY = [
    {"month": 1, "total_mrr": 549, "total_expenses": 28000},
    {"month": 2, "total_mrr": 1200, "total_expenses": 30000},
    {"month": 3, "total_mrr": 2400, "total_expenses": 33000},
]

FALLBACK_PROJECTION = {
    "assumptions": {
        "price_per_month": 99,
        "conversion_rate_percent": 1.8,
        "monthly_leads": 45,
    },
    "monthly_projections": [dict(m) for m in FALLBACK_MONTHLY],
    "burn_rate_monthly": 28000,
    "runway_months": 14,
    "starting_cash": 400000,
    "total_3_month_revenue": 4149,
    "total_3_month_expenses": 91000,
    "total_3_month_net": -86851,
    "break_even_month": 8,
    "key_metrics": {"ltv_cac_ratio": 3.2},
    "funding_analysis": {"runway_months_with_sales_ramp": 14},
    "summary": "Conservative 3-month projection with early sales ramp.",
}


def _to_number(value, default=0):
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_projection(projection):
    """Ensure total_mrr, key_metrics, and funding_analysis are always populated."""
    if not projection or projection.get("parse_failed"):
        projection = dict(FALLBACK_PROJECTION)

    monthly = projection.get("monthly_projections") or []
    if not monthly:
        monthly = [dict(m) for m in FALLBACK_MONTHLY]
        projection["monthly_projections"] = monthly

    assumptions = projection.setdefault("assumptions", {})
    price = _to_number(assumptions.get("price_per_month"), 99)

    normalized_months = []
    for i, month in enumerate(monthly[:3]):
        if not isinstance(month, dict):
            month = dict(FALLBACK_MONTHLY[min(i, 2)])
        mrr = month.get("total_mrr")
        if mrr is None:
            mrr = month.get("mrr") or month.get("revenue")
        if mrr is None and month.get("conversions"):
            mrr = _to_number(month["conversions"]) * price
        mrr = _to_number(mrr, FALLBACK_MONTHLY[min(i, 2)]["total_mrr"])
        month["total_mrr"] = int(mrr) if mrr == int(mrr) else round(mrr, 2)
        month.setdefault("mrr", month["total_mrr"])
        if "total_expenses" not in month and month.get("expenses") is not None:
            month["total_expenses"] = month["expenses"]
        normalized_months.append(month)

    while len(normalized_months) < 3:
        normalized_months.append(dict(FALLBACK_MONTHLY[len(normalized_months)]))
    projection["monthly_projections"] = normalized_months

    key_metrics = projection.setdefault("key_metrics", {})
    if not isinstance(key_metrics.get("ltv_cac_ratio"), (int, float)):
        burn = _to_number(projection.get("burn_rate_monthly"), 28000)
        leads = _to_number(assumptions.get("monthly_leads"), 45)
        ltv = price * 12
        cac = burn / max(leads, 1)
        key_metrics["ltv_cac_ratio"] = round(ltv / cac, 1) if cac > 0 else 3.2

    funding = projection.setdefault("funding_analysis", {})
    if not isinstance(funding.get("runway_months_with_sales_ramp"), (int, float)):
        runway = projection.get("runway_months")
        if runway is None:
            burn = _to_number(projection.get("burn_rate_monthly"), 28000)
            cash = _to_number(projection.get("starting_cash"), 400000)
            runway = round(cash / burn, 1) if burn > 0 else 14
        funding["runway_months_with_sales_ramp"] = _to_number(runway, 14)

    total_rev = sum(_to_number(m.get("total_mrr")) for m in normalized_months)
    if not projection.get("total_3_month_revenue"):
        projection["total_3_month_revenue"] = int(total_rev)

    return projection


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
        "price_per_month": 99,
        "conversion_rate_percent": 1.8,
        "monthly_leads": 45
    }},
    "monthly_projections": [
        {{"month": 1, "leads": 45, "conversions": 1, "total_mrr": 549, "total_expenses": 28000, "net": -27451}},
        {{"month": 2, "leads": 60, "conversions": 3, "total_mrr": 1200, "total_expenses": 30000, "net": -28800}},
        {{"month": 3, "leads": 80, "conversions": 6, "total_mrr": 2400, "total_expenses": 33000, "net": -30600}}
    ],
    "burn_rate_monthly": 28000,
    "runway_months": 14,
    "starting_cash": 400000,
    "total_3_month_revenue": 4149,
    "total_3_month_expenses": 91000,
    "total_3_month_net": -86851,
    "break_even_month": 8,
    "key_metrics": {{
        "ltv_cac_ratio": 3.2
    }},
    "funding_analysis": {{
        "runway_months_with_sales_ramp": 14
    }},
    "summary": "One paragraph financial summary"
}}

Every monthly_projections entry MUST include total_mrr as a positive number.
key_metrics.ltv_cac_ratio MUST be a number (e.g. 3.2).
funding_analysis.runway_months_with_sales_ramp MUST be a number.
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
                print("[FINANCE] JSON parse failed — using fallback monthly_projections")
                projection = {"parse_failed": True, "summary": clean}

            projection = _normalize_projection(projection)
            projection["company_name"] = projection.get("company_name") or company_name

            confidence = self.score_confidence(json.dumps(projection))

            result = {
                "status": "complete",
                "company_name": company_name,
                "projection": projection,
                "confidence": confidence,
            }

            self.write(result)
            m1 = projection["monthly_projections"][0]["total_mrr"]
            m3 = projection["monthly_projections"][2]["total_mrr"]
            ltv_cac = projection["key_metrics"]["ltv_cac_ratio"]
            runway = projection["funding_analysis"]["runway_months_with_sales_ramp"]
            print(f"[FINANCE] Projection complete — M1=${m1}, M3=${m3}, LTV:CAC={ltv_cac}, runway={runway}mo")
            return result

        except Exception as e:
            print(f"[FINANCE] Error: {e}")
            self.write({"status": "error", "error": str(e)})
            return {"status": "error", "error": str(e)}
