"""
Checkout Service — Main Application
====================================
Handles order creation, payment processing, and inventory reservation.
Protected by OpsMemory AI deployment gate.
"""

from flask import Flask, request, jsonify
from src.db import Database
from src.payment import PaymentProcessor
from src.config import load_config
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("checkout-service")

app = Flask(__name__)
config = load_config("config/checkout.yaml")
db = Database(config["database"])
payment = PaymentProcessor(config["payment"])


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "checkout-service", "version": "2.4.1"})


@app.route("/checkout", methods=["POST"])
def create_order():
    """Create a new order and process payment."""
    body = request.json
    if not body or "items" not in body or "user_id" not in body:
        return jsonify({"error": "Missing required fields: items, user_id"}), 400

    try:
        # Reserve inventory
        reservation = db.reserve_inventory(body["items"])
        if not reservation["success"]:
            return jsonify({"error": "Insufficient stock", "details": reservation}), 409

        # Process payment
        charge = payment.charge(
            amount=reservation["total_cents"],
            currency="usd",
            user_id=body["user_id"],
            metadata={"order_items": len(body["items"])}
        )

        if charge["status"] != "succeeded":
            db.release_inventory(reservation["reservation_id"])
            return jsonify({"error": "Payment failed", "code": charge["failure_code"]}), 402

        # Confirm order
        order = db.create_order(
            user_id=body["user_id"],
            items=body["items"],
            payment_id=charge["id"],
            reservation_id=reservation["reservation_id"]
        )

        logger.info("Order created: %s for user %s", order["order_id"], body["user_id"])
        return jsonify({"order_id": order["order_id"], "status": "confirmed"}), 201

    except Exception as exc:
        logger.error("Checkout failed: %s", str(exc))
        return jsonify({"error": "Internal error"}), 500


@app.route("/orders/<order_id>", methods=["GET"])
def get_order(order_id: str):
    """Retrieve an order by ID."""
    order = db.get_order(order_id)
    if not order:
        return jsonify({"error": "Order not found"}), 404
    return jsonify(order)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
