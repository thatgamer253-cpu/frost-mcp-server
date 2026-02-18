import stripe
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from .vault import Vault

class StripeService:
    """Wrapper for Stripe API to handle agent payouts."""
    
    def __init__(self, vault: Optional[Vault] = None):
        self.vault = vault or Vault()
        self.api_key = None
        self.account_id = None
        self._initialize_client()

    def _initialize_client(self):
        """Load keys from vault and init stripe."""
        keys = self.vault.get_stripe_keys()
        self.api_key = keys.get("api_key")
        self.account_id = keys.get("account_id")
        
        if self.api_key:
            stripe.api_key = self.api_key

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def get_balance(self) -> Dict[str, Any]:
        """Fetch real Stripe balance."""
        if not self.is_configured():
            return {"available": 0, "pending": 0, "currency": "usd", "error": "NOT_CONFIGURED"}
        
        try:
            balance = stripe.Balance.retrieve()
            available = sum(b.amount for b in balance.available) / 100
            pending = sum(b.amount for b in balance.pending) / 100
            currency = balance.available[0].currency if balance.available else "usd"
            return {
                "available": available,
                "pending": pending,
                "currency": currency
            }
        except Exception as e:
            return {"error": str(e)}

    def create_payout(self, amount: float, currency: str = "usd", description: str = "Agent Revenue Payout") -> Dict[str, Any]:
        """Trigger a payout to the linked bank account."""
        if not self.is_configured():
            return {"success": False, "error": "NOT_CONFIGURED"}
            
        try:
            # Amount must be in cents
            amount_cents = int(amount * 100)
            
            payout = stripe.Payout.create(
                amount=amount_cents,
                currency=currency,
                description=description,
                metadata={"engine": "Overlord", "agent": "Ambassador"}
            )
            
            return {
                "success": True,
                "payout_id": payout.id,
                "status": payout.status,
                "arrival_date": datetime.fromtimestamp(payout.arrival_date).isoformat()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_payment_link(self, product_name: str, amount: float, currency: str = "usd") -> Dict[str, Any]:
        """Create a Stripe Payment Link for a service."""
        if not self.is_configured():
            return {"success": False, "error": "NOT_CONFIGURED"}

        try:
            # Create a product
            product = stripe.Product.create(name=product_name)
            
            # Create a price
            price = stripe.Price.create(
                product=product.id,
                unit_amount=int(amount * 100),
                currency=currency,
            )
            
            # Create payment link
            link = stripe.PaymentLink.create(line_items=[{"price": price.id, "quantity": 1}])
            
            return {
                "success": True,
                "url": link.url,
                "product_id": product.id,
                "price_id": price.id,
                "link_id": link.id
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def log_payout(self, amount: float):
        """Log the transaction history."""
        log_file = "payout_history.log"
        entry = {
            "timestamp": datetime.now().isoformat(),
            "amount": amount,
            "status": "SETTLED"
        }
        with open(log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")
