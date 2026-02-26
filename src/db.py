"""
Database layer — Checkout Service
===================================
All database operations go through this module.
Never run raw DDL in application code — use migrations.
"""

import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger("checkout-service.db")


class Database:
    def __init__(self, config: dict):
        self.config = config
        self._pool = None  # Connection pool initialized lazily

    # ── Orders ────────────────────────────────────────────────────────────────

    def create_order(self, user_id: str, items: list, payment_id: str, reservation_id: str) -> dict:
        """Insert a confirmed order into the orders table."""
        order_id = f"ord_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        # INSERT INTO orders (id, user_id, payment_id, ...) VALUES (...)
        logger.info("Order %s created for user %s", order_id, user_id)
        return {"order_id": order_id, "status": "confirmed", "created_at": datetime.now(timezone.utc).isoformat()}

    def get_order(self, order_id: str) -> dict | None:
        """Fetch a single order by primary key."""
        # SELECT * FROM orders WHERE id = %s
        return None  # Stub — real impl queries DB

    # ── Inventory ─────────────────────────────────────────────────────────────

    def reserve_inventory(self, items: list) -> dict:
        """
        Atomically reserve stock for all items.
        Uses SELECT FOR UPDATE to prevent double-booking.
        """
        total_cents = sum(item.get("price_cents", 0) * item.get("qty", 1) for item in items)
        return {"success": True, "reservation_id": "rsv_demo", "total_cents": total_cents}

    def release_inventory(self, reservation_id: str) -> None:
        """Release a reservation on payment failure."""
        logger.warning("Releasing inventory reservation %s", reservation_id)

    # ── Maintenance ───────────────────────────────────────────────────────────

    def archive_old_orders(self, cutoff_date: str) -> int:
        """
        Archive orders older than cutoff_date to the orders_archive table.
        SAFE: uses INSERT INTO ... SELECT then DELETE with row-level locking.
        Returns count of archived rows.
        """
        # INSERT INTO orders_archive SELECT * FROM orders WHERE created_at < %s
        # DELETE FROM orders WHERE id IN (SELECT id FROM orders_archive WHERE archived_at > now() - interval '1 minute')
        logger.info("Archiving orders before %s", cutoff_date)
        return 0  # Stub — returns row count in real impl

    def execute(self, sql: str, params: tuple = ()) -> None:
        """Execute a raw SQL statement via the connection pool."""
        logger.debug("SQL: %s | params: %s", sql, params)

    def get_connection(self) -> Any:
        """Return a connection from the pool."""
        if self._pool is None:
            self._connect()
        return self._pool.getconn()  # type: ignore

    def _connect(self) -> None:
        """Initialize the connection pool."""
        logger.info(
            "Connecting to %s:%s/%s (pool_size=%s)",
            self.config["host"],
            self.config["port"],
            self.config["name"],
            self.config.get("pool_size", 10),
        )
