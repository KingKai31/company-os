import os
from utils.base_agent import BaseAgent


class LegalAgent(BaseAgent):
    def __init__(self):
        super().__init__("legal_agent")

    def run(self, context):
        print("[LEGAL] Reading company info from shared brain...")

        try:
            ceo_data = self.read("ceo_agent")
            orchestrator_data = self.read("orchestrator")

            strategy = ceo_data.get("strategy", {})
            company_name = strategy.get("company_name") or orchestrator_data.get("plan", {}).get(
                "company_name", "Company"
            )
            product = strategy.get("product", orchestrator_data.get("founder_input", ""))

            legal_task = (
                orchestrator_data.get("plan", {})
                .get("tasks", {})
                .get("legal_agent", "Generate legal documents")
            )

            print(f"[LEGAL] Generating Terms of Service and Refund Policy for {company_name}...")

            prompt = f"""You are a startup legal advisor. Generate legal documents for:

Company name: {company_name}
Product: {product}
Task: {legal_task}

Create two documents:
1. Terms of Service
2. Refund Policy

Format clearly with headers. Use plain language suitable for a SaaS startup.
Include standard clauses: acceptance, use of service, liability limits, termination, and refund conditions."""

            documents = self.think(
                prompt,
                system="You are a legal document specialist for early-stage startups.",
            )

            os.makedirs("output", exist_ok=True)
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in company_name.lower())
            file_path = os.path.join("output", f"{safe_name}_legal_documents.txt")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"LEGAL DOCUMENTS — {company_name}\n")
                f.write("=" * 50 + "\n\n")
                f.write(documents)

            confidence = self.score_confidence(documents[:1500])

            result = {
                "status": "complete",
                "company_name": company_name,
                "product": product,
                "file_path": file_path,
                "terms_of_service": "Terms of Service" in documents,
                "refund_policy": "Refund Policy" in documents or "Refund" in documents,
                "confidence": confidence,
            }

            self.write(result)
            print(f"[LEGAL] Documents saved to: {file_path}")
            return result

        except Exception as e:
            print(f"[LEGAL] Error: {e}")
            self.write({"status": "error", "error": str(e)})
            return {"status": "error", "error": str(e)}
