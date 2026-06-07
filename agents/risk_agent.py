import json
from utils.base_agent import BaseAgent


class RiskAgent(BaseAgent):
    def __init__(self):
        super().__init__("risk_agent")

    def _broadcast_alert(self, risk):
        print("\n" + "=" * 60)
        print("[ALERT] CRITICAL RISK DETECTED")
        print(f"  Title: {risk.get('title', 'Unknown')}")
        print(f"  Severity: {risk.get('severity', 'critical')}")
        print(f"  Impact: {risk.get('impact', 'N/A')}")
        print(f"  Mitigation: {risk.get('mitigation', 'N/A')}")
        print("=" * 60 + "\n")

    def run(self, context):
        print("[RISK] Reading all agent outputs from shared brain...")

        try:
            all_states = self.read_all()

            orchestrator_data = self.read("orchestrator")
            risk_task = (
                orchestrator_data.get("plan", {})
                .get("tasks", {})
                .get("risk_agent", "Identify risks and blockers")
            )

            print("[RISK] Analysing company-wide risks with Claude...")

            prompt = f"""You are a risk analyst for an autonomous startup OS.

All agent outputs from shared brain:
{json.dumps(all_states, indent=2)}

Task: {risk_task}

Identify the top 3 risks and blockers across all agent outputs.
Look for: legal gaps, unrealistic financials, low confidence scores, unsent sales emails,
missing deliverables, and strategic misalignment.

Return ONLY a JSON object with this exact format:
{{
    "risks": [
        {{
            "rank": 1,
            "title": "Risk title",
            "severity": "critical|high|medium|low",
            "category": "legal|financial|technical|sales|strategy",
            "description": "Detailed description",
            "impact": "Business impact",
            "mitigation": "Recommended action"
        }}
    ],
    "overall_risk_level": "critical|high|medium|low",
    "blockers": ["list of immediate blockers"],
    "summary": "Executive risk summary"
}}

Return exactly 3 risks. Return only JSON."""

            response = self.think(
                prompt,
                system="You are a seasoned startup risk analyst. Be direct and actionable.",
                max_tokens=4000,
            )

            clean = response.replace("```json", "").replace("```", "").strip()
            try:
                risk_report = json.loads(clean)
            except json.JSONDecodeError:
                print("[RISK] JSON parse failed — using plain text response")
                risk_report = {
                    "summary": clean,
                    "risks": [],
                    "overall_risk_level": "medium",
                    "blockers": [],
                    "parse_failed": True,
                }

            risks = risk_report.get("risks", [])
            critical_found = any(r.get("severity") == "critical" for r in risks)
            overall_level = risk_report.get("overall_risk_level", "medium")

            confidence = self.score_confidence(json.dumps(risk_report))

            if critical_found or overall_level == "critical":
                print("[RISK] Critical risk detected — dropping confidence and broadcasting alert...")
                self.confidence = max(confidence - 30, 10)
                for risk in risks:
                    if risk.get("severity") == "critical":
                        self._broadcast_alert(risk)
            else:
                self.confidence = confidence

            result = {
                "status": "complete",
                "risk_report": risk_report,
                "critical_alert": critical_found or overall_level == "critical",
                "confidence": self.confidence,
            }

            self.write(result)
            print(f"[RISK] Report written — overall level: {overall_level}, confidence: {self.confidence}%")
            return result

        except Exception as e:
            print(f"[RISK] Error: {e}")
            self.write({"status": "error", "error": str(e)})
            return {"status": "error", "error": str(e)}
