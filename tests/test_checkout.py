"""
Unit tests — Checkout Service
================================
Run with: pytest tests/ -v
"""

import pytest
from unittest.mock import patch, MagicMock
from src.db import Database
from src.payment import PaymentProcessor


class TestDatabase:

    def setup_method(self):
        self.db = Database({
            "host": "localhost", "port": 5432,
            "name": "checkout_test", "pool_size": 5
        })

    def test_archive_old_orders_returns_int(self):
        count = self.db.archive_old_orders("2020-01-01")
        assert isinstance(count, int)

    def test_reserve_inventory_calculates_total(self):
        items = [{"price_cents": 1000, "qty": 2}, {"price_cents": 500, "qty": 1}]
        result = self.db.reserve_inventory(items)
        assert result["success"] is True
        assert result["total_cents"] == 2500

    def test_reserve_inventory_empty(self):
        result = self.db.reserve_inventory([])
        assert result["total_cents"] == 0

    def test_create_order_returns_order_id(self):
        order = self.db.create_order("user_1", [], "pay_1", "rsv_1")
        assert order["order_id"].startswith("ord_")
        assert order["status"] == "confirmed"

    def test_get_order_returns_none_for_unknown(self):
        result = self.db.get_order("ord_nonexistent")
        assert result is None


class TestPaymentProcessor:

    def setup_method(self):
        self.payment = PaymentProcessor({
            "timeout_ms": 15000,
            "verify_tls": True,
            "webhook_secret": "test_secret"
        })

    def test_tls_verify_defaults_true(self):
        assert self.payment.verify_tls is True

    def test_timeout_converts_to_seconds(self):
        assert self.payment.timeout == 15.0

    @patch("src.payment.requests.post")
    def test_charge_returns_failed_on_timeout(self, mock_post):
        mock_post.side_effect = __import__("requests").Timeout()
        result = self.payment.charge(1000, "usd", "user_1", {})
        assert result["status"] == "failed"
        assert result["failure_code"] == "timeout"

    @patch("src.payment.requests.post")
    def test_charge_success(self, mock_post):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "succeeded", "id": "ch_test123"}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response
        result = self.payment.charge(1000, "usd", "user_1", {})
        assert result["status"] == "succeeded"
