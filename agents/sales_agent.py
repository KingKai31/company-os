import json
import os
import smtplib
from email.mime.text import MIMEText

from dotenv import load_dotenv

from agents.approval_gate import ApprovalGate
from utils.base_agent import BaseAgent

load_dotenv()


def send_real_email(drafts, company_name):
    """Send one real demo email via Gmail SMTP. Never raises — logs and returns False on failure."""
    try:
        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")
        demo_email = os.getenv("DEMO_EMAIL")

        if not all([gmail_user, gmail_password, demo_email]):
            print("[SALES] Email skipped — set GMAIL_USER, GMAIL_APP_PASSWORD, DEMO_EMAIL in .env")
            return False

        draft = drafts[0] if drafts else {}
        subject = f"{company_name} — You have been selected as an early beta user"
        body = draft.get("body") or draft.get("content") or str(draft)

        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = gmail_user
        msg["To"] = demo_email

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(gmail_user, gmail_password)
            server.sendmail(gmail_user, [demo_email], msg.as_string())

        print(f"[SALES] Real email sent to {demo_email}")
        return True

    except Exception as e:
        print(f"[SALES] Email send failed (pipeline continues): {e}")
        return False


class SalesAgent(BaseAgent):
    def __init__(self):
        super().__init__("sales_agent")
        self.approval_gate = ApprovalGate()

    def run(self, context):
        print("[SALES] Reading product info from shared brain...")

        try:
            ceo_data = self.read("ceo_agent")
            orchestrator_data = self.read("orchestrator")

            strategy = ceo_data.get("strategy", {})
            company_name = strategy.get("company_name", "Our Company")
            product = strategy.get("product", "")
            target_market = strategy.get("target_market", "")

            sales_task = (
                orchestrator_data.get("plan", {})
                .get("tasks", {})
                .get("sales_agent", "Draft outreach emails")
            )

            print(f"[SALES] Generating 10 personalised outreach emails for {target_market}...")

            prompt = f"""You are a sales development representative for "{company_name}".

Product: {product}
Target market: {target_market}
Task: {sales_task}

Generate exactly 10 personalised cold outreach email drafts for different prospect personas.

Return ONLY a JSON array with this format:
[
    {{
        "prospect_name": "Full Name",
        "company": "Company Name",
        "role": "Job Title",
        "subject": "Email subject line",
        "body": "Full email body"
    }}
]

Return only the JSON array, nothing else."""

            response = self.think(
                prompt,
                system="You are an expert B2B sales copywriter. Write concise, personalised emails.",
                max_tokens=4000,
            )

            clean = response.replace("```json", "").replace("```", "").strip()
            try:
                drafts = json.loads(clean)
            except json.JSONDecodeError:
                print("[SALES] JSON parse failed — using plain text response")
                drafts = [
                    {
                        "prospect_name": "N/A",
                        "company": "N/A",
                        "role": "N/A",
                        "subject": "Outreach drafts (unparsed)",
                        "body": clean,
                    }
                ]

            print(f"[SALES] Generated {len(drafts)} email drafts — writing to shared brain...")
            self.write({"status": "drafts_ready", "drafts": drafts, "sent": False})

            print("[SALES] Requesting approval before sending emails...")
            approval = self.approval_gate.approve(
                action="send_sales_emails",
                details={
                    "company_name": company_name,
                    "email_count": len(drafts),
                    "recipients": [d.get("prospect_name") for d in drafts],
                },
            )

            email_sent = False
            if approval.get("status") == "approved":
                print("[SALES] Approved — sending real demo email...")
                email_sent = send_real_email(drafts, company_name)

            result = {
                "status": "complete" if approval.get("status") == "approved" else "pending_approval",
                "company_name": company_name,
                "drafts": drafts,
                "sent": email_sent,
                "approval": approval,
                "leads_identified": len(drafts),
                "target_customer_profile": target_market,
                "outreach_strategy": sales_task,
                "confidence": self.score_confidence(json.dumps(drafts[:2])),
            }

            self.write(result)
            print(f"[SALES] Complete — sent={result['sent']}")
            return result

        except Exception as e:
            print(f"[SALES] Error: {e}")
            self.write({"status": "error", "error": str(e)})
            return {"status": "error", "error": str(e)}
