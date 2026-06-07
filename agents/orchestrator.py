import os
import anthropic
from dotenv import load_dotenv
from utils.shared_brain import write_state, read_state, clear_all

load_dotenv()

client = anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))

class Orchestrator:
    def __init__(self):
        self.agent_id = "orchestrator"
        self.max_steps = 10
        self.step_count = 0

    def plan(self, founder_input):
        print(f"[ORCHESTRATOR] Planning for: {founder_input}")
        
        prompt = f"""You are the orchestrator of an autonomous company OS.
        A founder has given you this idea: "{founder_input}"
        
        Break this into specific tasks for these agents:
        1. ceo_agent - strategy and goals
        2. engineer_agent - deploy company intelligence dashboard with all agent data
        3. legal_agent - generate legal documents
        4. sales_agent - find leads and draft outreach
        5. finance_agent - revenue projection and budget
        6. risk_agent - identify risks and blockers
        
        Return a JSON object with this exact format:
        {{
            "company_name": "name based on the idea",
            "tasks": {{
                "ceo_agent": "specific task description",
                "engineer_agent": "specific task description",
                "legal_agent": "specific task description",
                "sales_agent": "specific task description",
                "finance_agent": "specific task description",
                "risk_agent": "specific task description"
            }}
        }}
        Return only the JSON, nothing else."""

        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        
        import json
        response = message.content[0].text
        clean = response.replace("```json", "").replace("```", "").strip()
        plan = json.loads(clean)
        
        write_state(self.agent_id, {
            "status": "planned",
            "founder_input": founder_input,
            "plan": plan
        })
        
        print(f"[ORCHESTRATOR] Plan created for: {plan['company_name']}")
        return plan

    def check_step_limit(self):
        self.step_count += 1
        if self.step_count >= self.max_steps:
            print("[ORCHESTRATOR] Step limit reached — stopping")
            return False
        return True