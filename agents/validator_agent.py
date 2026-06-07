import json
from utils.base_agent import BaseAgent


class ValidatorAgent(BaseAgent):
    def __init__(self):
        super().__init__("validator_agent")

    def validate(self, output, source_agent_id):
        """Fact-check agent output against shared brain context."""
        print(f"[VALIDATOR] Fact-checking output from {source_agent_id}...")

        try:
            all_states = self.read_all()
            context_summary = json.dumps(all_states, indent=2)

            prompt = f"""You are a fact-checking validator for an autonomous company OS.

Shared brain context (all agent states):
{context_summary}

Agent "{source_agent_id}" produced this output:
{json.dumps(output, indent=2) if isinstance(output, dict) else output}

Check whether this output is:
- Consistent with the shared brain context
- Factually plausible (no invented data contradicting known facts)
- Complete enough for its purpose

Return ONLY a JSON object with this exact format:
{{"valid": true or false, "reason": "brief explanation"}}

Return only the JSON, nothing else."""

            response = self.think(
                prompt,
                system="You are a rigorous fact-checking validator. Be concise and specific.",
            )

            clean = response.replace("```json", "").replace("```", "").strip()
            result = json.loads(clean)

            if "valid" not in result:
                result = {"valid": False, "reason": "Validator returned malformed response"}

            print(f"[VALIDATOR] Result for {source_agent_id}: valid={result['valid']}")
            self.write({"last_validation": {"source": source_agent_id, **result}})
            return result

        except json.JSONDecodeError as e:
            print(f"[VALIDATOR] Error parsing Claude response: {e}")
            return {"valid": False, "reason": f"Failed to parse validation response: {e}"}
        except Exception as e:
            print(f"[VALIDATOR] Error during validation: {e}")
            return {"valid": False, "reason": str(e)}

    def run(self, context):
        source = context.get("source_agent_id", "unknown")
        output = context.get("output", {})
        return self.validate(output, source)
