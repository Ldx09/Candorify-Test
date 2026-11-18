"""Adds new columns to tables that already exist. create_all() only creates missing TABLES, so a database
made before a column was added (e.g. a local dev.db) would break without this. Safe to run on every start:
it only adds a column when it is missing, and never changes or deletes data. Works on SQLite and Postgres.

Nathalie: the same change for the shared Postgres database is
    ALTER TABLE bills ADD COLUMN IF NOT EXISTS payments TEXT;
    ALTER TABLE bills ADD COLUMN IF NOT EXISTS eob TEXT;
    ALTER TABLE users ADD COLUMN IF NOT EXISTS plan VARCHAR(20) DEFAULT 'free';
    ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_status VARCHAR(30);
    ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_renews_at TIMESTAMPTZ;
    ALTER TABLE users ADD COLUMN IF NOT EXISTS plan_cancel_at_period_end BOOLEAN DEFAULT FALSE;
    ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(255);
    ALTER TABLE users ADD COLUMN IF NOT EXISTS stripe_subscription_id VARCHAR(255);
"""
import logging

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

log = logging.getLogger("candorify.db")

# (table, column, SQL type) for every column added after the table was first created
NEW_COLUMNS = [
    ("bills", "payments", "TEXT"),   # who paid what (JSON), see app/models/payments.py
    ("bills", "eob", "TEXT"),        # insurance EOB totals (JSON), see app/models/eob.py
    ("users", "plan", "VARCHAR(20) DEFAULT 'free'"),            # Premium plan, see app/services/billing.py
    ("users", "plan_status", "VARCHAR(30)"),
    ("users", "plan_renews_at", "TIMESTAMP WITH TIME ZONE"),
    ("users", "plan_cancel_at_period_end", "BOOLEAN DEFAULT FALSE"),
    ("users", "stripe_customer_id", "VARCHAR(255)"),
    ("users", "stripe_subscription_id", "VARCHAR(255)"),
]


def add_missing_columns(engine: Engine) -> None:
    inspector = inspect(engine)
    for table, column, sql_type in NEW_COLUMNS:
        if not inspector.has_table(table):
            continue   # create_all makes it with every column
        if column in {c["name"] for c in inspector.get_columns(table)}:
            continue
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {sql_type}"))
        log.info("Added column %s.%s", table, column)