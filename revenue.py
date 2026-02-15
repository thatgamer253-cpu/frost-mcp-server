import json
import os
from datetime import datetime
from payout_gateway import PayoutGateway

class RevenueManager:
    """
    Manages financial data, tracking earnings from various platforms.
    """
    def __init__(self, data_file='revenue_data.json'):
        self.data_file = data_file
        self.data = self._load_data()
        self.gateway = PayoutGateway()

    def _load_data(self):
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                try:
                    return json.load(f)
                except:
                    pass
        return {
            "pending_income": 0.0,
            "available_payout": 0.0,
            "total_earned": 0.0,
            "transactions": []
        }

    def _save_data(self):
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def record_job_start(self, job_id, platform, estimated_value):
        """Records a job as 'Work in Progress' / Pending."""
        self.data["pending_income"] += estimated_value
        self.data["transactions"].append({
            "id": f"TXN-{job_id}",
            "type": "Income (Pending)",
            "platform": platform,
            "amount": estimated_value,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "Pending"
        })
        self._save_data()

    def finalize_payment(self, job_id, amount):
        """Moves money from pending to available."""
        for txn in self.data["transactions"]:
            if txn["id"] == f"TXN-{job_id}" and txn["status"] == "Pending":
                txn["status"] = "Available"
                self.data["pending_income"] -= txn["amount"]
                self.data["available_payout"] += amount
                self.data["total_earned"] += amount
                break
        self._save_data()

    def process_marketplace_sale(self, project_id):
        """Autonomously finalizes one pending sale for a project."""
        for txn in self.data["transactions"]:
            if project_id in txn["id"] and txn["status"] == "Pending":
                amount = txn["amount"]
                # Move from pending to available
                txn["status"] = "Available"
                txn["date_finalized"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.data["pending_income"] -= amount
                self.data["available_payout"] += amount
                self.data["total_earned"] += amount
                self._save_data()
                return True, amount
        return False, 0

    def record_marketplace_sale(self, service_id, service_name, amount, agent_id):
        """Records a marketplace service sale."""
        self.data["available_payout"] += amount
        self.data["total_earned"] += amount
        self.data["transactions"].append({
            "id": f"MKT-{service_id}-{agent_id[:8]}",
            "type": "Marketplace Sale",
            "service": service_name,
            "agent_buyer": agent_id,
            "amount": amount,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "Available"
        })
        self._save_data()
        return True

    def request_payout(self, method="Stripe Instant"):
        """Triggers a real withdrawal via the configured gateway."""
        amount = self.data["available_payout"]
        if amount <= 0:
            return False, "No funds available for withdrawal."
        
        # Trigger Real Payout
        payout_result = self.gateway.send_instant_payout(amount)
        
        if payout_result["status"] == "success":
            self.data["available_payout"] = 0
            self.data["transactions"].append({
                "id": payout_result["id"],
                "type": "Withdrawal (Live)",
                "method": method,
                "amount": amount,
                "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "Completed"
            })
            self._save_data()
            return True, f"LIVE PAYOUT SUCCESSFUL: ${amount:.2f} transferred via {method}."
        else:
            return False, f"LIVE PAYOUT FAILED: {payout_result['message']}"
