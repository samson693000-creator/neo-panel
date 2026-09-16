# -*- coding: utf-8 -*-
"""Lightweight schema patches for SQLite/Postgres (no Alembic)."""
from __future__ import annotations

import logging

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger("migrate")

PAYMENT_COLUMNS: dict[str, str] = {
    "order_id": "VARCHAR(64) DEFAULT ''",
    "amount_net": "NUMERIC(18, 2) DEFAULT 0",
    "amount_gross": "NUMERIC(18, 2) DEFAULT 0",
    "commission_amount": "NUMERIC(18, 2) DEFAULT 0",
    "yoomoney_operation_id": "VARCHAR(64)",
    "failure_reason": "TEXT DEFAULT ''",
    "processed_at": "TIMESTAMP",
}


def _sync_patch(conn) -> None:
    inspector = inspect(conn)
    tables = set(inspector.get_table_names())
    if "payments" not in tables:
        return

    existing = {col["name"] for col in inspector.get_columns("payments")}
    for name, ddl in PAYMENT_COLUMNS.items():
        if name in existing:
            continue
        conn.execute(text(f"ALTER TABLE payments ADD COLUMN {name} {ddl}"))
        logger.info("payments: added column %s", name)

    conn.execute(
        text(
            "UPDATE payments SET order_id = 'p' || id "
            "WHERE order_id IS NULL OR order_id = ''"
        )
    )
    conn.execute(
        text(
            "UPDATE payments SET amount_net = amount, amount_gross = amount "
            "WHERE (amount_net IS NULL OR amount_net = 0) AND amount IS NOT NULL"
        )
    )

    indexes = {idx["name"] for idx in inspector.get_indexes("payments")}
    if "uq_payments_order_id" not in indexes:
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_order_id "
                "ON payments (order_id)"
            )
        )
    if "uq_payments_yoomoney_operation_id" not in indexes:
        conn.execute(
            text(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_payments_yoomoney_operation_id "
                "ON payments (yoomoney_operation_id)"
            )
        )


async def patch_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(_sync_patch)
