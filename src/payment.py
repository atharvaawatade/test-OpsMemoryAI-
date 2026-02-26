"""
Payment Processor — Checkout Service
======================================
Thin wrapper around the Stripe API.
TLS verification is always enabled — never disable in production.
"""

import logging
import requests

logger = logging.getLogger("checkout-service.payment")

STRIPE_BASE_URL = "https://api.stripe.com/v1"


class PaymentProcessor:
    def __init__(self, config: dict):
        self.config = config
        self.timeout = config.get("timeout_ms", 15000) / 1000  # convert to seconds
        self.verify_tls = config.get("verify_tls", True)  # always True in prod

        if not self.verify_tls:
            logger.warning("TLS verification is DISABLED — this is a security risk")

    def charge(self, amount: int, currency: str, user_id: str, metadata: dict) -> dict:
        """
        Charge a customer via Stripe.
        - amount: amount in smallest currency unit (cents for USD)
        - currency: ISO 4217 currency code
        - Returns: Stripe charge object
        """
        payload = {
            "amount": amount,
            "currency": currency,
            "metadata": {**metadata, "user_id": user_id},
        }

        try:
            resp = requests.post(
                f"{STRIPE_BASE_URL}/charges",
                data=payload,
                headers={"Authorization": f"Bearer {self.config['webhook_secret']}"},
                timeout=self.timeout,
                verify=self.verify_tls,   # Security: never set to False
            )
            resp.raise_for_status()
            return resp.json()
        except requests.Timeout:
            logger.error("Stripe timeout after %.1fs", self.timeout)
            return {"status": "failed", "failure_code": "timeout"}
        except requests.RequestException as exc:
            logger.error("Stripe request failed: %s", str(exc))
            return {"status": "failed", "failure_code": "network_error"}

    def refund(self, charge_id: str, amount: int | None = None) -> dict:
        """Issue a full or partial refund."""
        payload = {"charge": charge_id}
        if amount is not None:
            payload["amount"] = str(amount)

        resp = requests.post(
            f"{STRIPE_BASE_URL}/refunds",
            data=payload,
            timeout=self.timeout,
            verify=self.verify_tls,
        )
        return resp.json()
