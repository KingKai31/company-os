import json
from utils.base_agent import BaseAgent


class CEOAgent(BaseAgent):
    def __init__(self):
        super().__init__("ceo_agent")

    def run(self, context):
        print("[CEO] Reading orchestrator plan from shared brain...")

        try:
            orchestrator_data = self.read("orchestrator")
            if not orchestrator_data:
                raise ValueError("No orchestrator plan found in shared brain")

            plan = orchestrator_data.get("plan", {})
            company_name = plan.get("company_name", "Unknown Company")
            ceo_task = plan.get("tasks", {}).get("ceo_agent", "Define company strategy")
            founder_input = orchestrator_data.get("founder_input", "")

            print(f"[CEO] Writing 90-day strategy for {company_name}...")

            prompt = f"""You are the CEO of "{company_name}".

Founder vision: {founder_input}
Your assigned task: {ceo_task}

Create a comprehensive 90-day strategy and OKRs.

Return ONLY a JSON object with this exact format:
{{
    "company_name": "{company_name}",
    "vision": "one sentence vision statement",
    "strategy_90_day": {{
        "phase_1_days_1_30": "focus and key actions",
        "phase_2_days_31_60": "focus and key actions",
        "phase_3_days_61_90": "focus and key actions"
    }},
    "okrs": [
        {{"objective": "...", "key_results": ["KR1", "KR2", "KR3"]}},
        {{"objective": "...", "key_results": ["KR1", "KR2", "KR3"]}},
        {{"objective": "...", "key_results": ["KR1", "KR2", "KR3"]}}
    ],
    "product": "clear product description for other agents to use",
    "target_market": "primary target customer segment"
}}

Return only the JSON, nothing else."""

            response = self.think(
                prompt,
                system="You are an experienced startup CEO. Be ambitious but realistic.",
                max_tokens=4000,
            )

            clean = response.replace("```json", "").replace("```", "").strip()
            try:
                strategy = json.loads(clean)
            except json.JSONDecodeError:
                print("[CEO] JSON parse failed — storing raw text as strategy")
                strategy = {
                    "company_name": company_name,
                    "raw_text": clean,
                    "parse_failed": True,
                }

            print("[CEO] Scoring strategy confidence...")
            confidence = self.score_confidence(
                json.dumps(strategy) if isinstance(strategy, dict) else clean
            )

            result = {
                "status": "complete",
                "company_name": strategy.get("company_name", company_name),
                "strategy": strategy,
                "confidence": confidence,
            }

            self.write(result)
            print(f"[CEO] Strategy written to shared brain (confidence: {confidence}%)")
            return result

        except Exception as e:
            print(f"[CEO] Error: {e}")
            self.write({"status": "error", "error": str(e)})
            return {"status": "error", "error": str(e)}
