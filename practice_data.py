"""The practice tables used by the SQL lessons, as pandas DataFrames.

    from practice_data import load_tables
    users, orders, events, employees = load_tables()
"""
import sqlite3
from pathlib import Path

import pandas as pd

SEED_FILE = Path(__file__).resolve().parent / "data" / "sql_practice.sql"
TABLES = ["users", "orders", "events", "employees"]


def connect():
    """A fresh in-memory copy of the practice database."""
    con = sqlite3.connect(":memory:")
    con.executescript(SEED_FILE.read_text(encoding="utf-8"))
    return con


def run_sql(query: str) -> pd.DataFrame:
    con = connect()
    try:
        return pd.read_sql_query(query, con)
    finally:
        con.close()


def load_tables():
    con = connect()
    try:
        return tuple(pd.read_sql_query(f"SELECT * FROM {t}", con) for t in TABLES)
    finally:
        con.close()


def load_capstone():
    """The larger capstone dataset: (users, events) with 8000 users."""
    data = Path(__file__).resolve().parent / "data"
    return pd.read_csv(data / "users.csv"), pd.read_csv(data / "events.csv")
