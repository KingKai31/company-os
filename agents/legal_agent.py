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

            print(f"[LEGAL] Generating Terms of Service for {company_name}...")

            tos_prompt = f"""You are a startup legal advisor. Generate a Terms of Service document for:

Company name: {company_name}
Product: {product}
Task: {legal_task}

Write a complete Terms of Service with clear section headers.
Use plain language suitable for a SaaS startup.
Include: acceptance, use of service, user obligations, liability limits, termination, and governing law.
Start with the header "TERMS OF SERVICE"."""

            terms_of_service = self.think(
                tos_prompt,
                system="You are a legal document specialist for early-stage startups.",
                max_tokens=3000,
            )

            print(f"[LEGAL] Generating Refund Policy for {company_name}...")

            refund_prompt = f"""You are a startup legal advisor. Generate a Refund Policy document for:

Company name: {company_name}
Product: {product}

Write a complete Refund Policy with clear section headers.
Use plain language suitable for a SaaS startup.
Include: eligibility, refund window, process for requesting refunds, exceptions, and contact information.
Start with the header "REFUND POLICY"."""

            refund_policy_doc = self.think(
                refund_prompt,
                system="You are a legal document specialist for early-stage startups.",
                max_tokens=2000,
            )

            os.makedirs("output", exist_ok=True)
            safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in company_name.lower())
            file_path = os.path.join("output", f"{safe_name}_legal_documents.txt")

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"LEGAL DOCUMENTS — {company_name}\n")
                f.write("=" * 50 + "\n\n")
                f.write("TERMS OF SERVICE\n")
                f.write("-" * 50 + "\n\n")
                f.write(terms_of_service.strip())
                f.write("\n\n")
                f.write("=" * 50 + "\n\n")
                f.write("REFUND POLICY\n")
                f.write("-" * 50 + "\n\n")
                f.write(refund_policy_doc.strip())
                f.write("\n")

            combined = terms_of_service + "\n" + refund_policy_doc
            confidence = self.score_confidence(combined[:1500])

            result = {
                "status": "complete",
                "company_name": company_name,
                "product": product,
                "file_path": file_path,
                "terms_of_service": True,
                "refund_policy": True,
                "confidence": confidence,
            }

            self.write(result)
            print(f"[LEGAL] Terms of Service generated — terms_of_service=True")
            print(f"[LEGAL] Refund Policy generated — refund_policy=True")
            print(f"[LEGAL] Documents saved to: {file_path}")
            return result

        except Exception as e:
            print(f"[LEGAL] Error: {e}")
            self.write({"status": "error", "error": str(e)})
            return {"status": "error", "error": str(e)}
