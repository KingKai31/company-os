import os
import uuid
from datetime import datetime
from dotenv import load_dotenv
from utils.shared_brain import write_state, read_state

load_dotenv()


class ApprovalGate:
    AGENT_ID = "approval_gate"

    def __init__(self):
        self.auto_approve = os.getenv("AUTO_APPROVE", "true").lower() == "true"

    def _load_state(self):
        return read_state(self.AGENT_ID)

    def _save_state(self, state):
        write_state(self.AGENT_ID, state)

    def approve(self, action, details):
        """
        Store a pending approval request and return approved/rejected status.
        Set AUTO_APPROVE=false in .env to require manual rejection via reject().
        """
        print(f"[APPROVAL] Request for action: {action}")

        try:
            state = self._load_state()
            pending = state.get("pending", [])
            history = state.get("history", [])

            approval_id = str(uuid.uuid4())[:8]
            request = {
                "id": approval_id,
                "action": action,
                "details": details,
                "requested_at": datetime.utcnow().isoformat(),
                "status": "pending",
            }

            pending.append(request)
            self._save_state({"pending": pending, "history": history})

            print(f"[APPROVAL] Pending approval stored (id: {approval_id})")

            if self.auto_approve:
                print(f"[APPROVAL] Auto-approve enabled — approving '{action}'")
                return self._resolve(approval_id, "approved", "Auto-approved for demo")

            print(f"[APPROVAL] Waiting for manual approval (id: {approval_id})")
            return {"status": "pending", "approval_id": approval_id, "action": action}

        except Exception as e:
            print(f"[APPROVAL] Error processing approval: {e}")
            return {"status": "rejected", "reason": str(e)}

    def _resolve(self, approval_id, status, reason=""):
        state = self._load_state()
        pending = state.get("pending", [])
        history = state.get("history", [])

        resolved = None
        remaining = []
        for req in pending:
            if req["id"] == approval_id:
                req["status"] = status
                req["reason"] = reason
                req["resolved_at"] = datetime.utcnow().isoformat()
                resolved = req
                history.append(req)
            else:
                remaining.append(req)

        self._save_state({"pending": remaining, "history": history})

        if resolved:
            print(f"[APPROVAL] {status.upper()}: {resolved['action']} — {reason}")
            return {"status": status, "approval_id": approval_id, "reason": reason}

        return {"status": "rejected", "reason": f"Approval id {approval_id} not found"}

    def reject(self, approval_id, reason="Manually rejected"):
        print(f"[APPROVAL] Rejecting approval {approval_id}")
        return self._resolve(approval_id, "rejected", reason)
