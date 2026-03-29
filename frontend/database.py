"""
database.py — SQLite helper for prediction history storage.
"""

import sqlite3
import os
from datetime import datetime

# Store DB next to this script (frontend/)
DB_PATH = os.path.join(os.path.dirname(__file__), "prediction_history.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # return dict-like rows
    return conn


def init_db():
    """Create the prediction_history table if it does not exist."""
    conn = _connect()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS prediction_history (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp      TEXT    NOT NULL,
            temperature    REAL    NOT NULL,
            vacuum         REAL    NOT NULL,
            pressure       REAL    NOT NULL,
            humidity       REAL    NOT NULL,
            predicted_power REAL   NOT NULL,
            scenario       TEXT    DEFAULT 'Manual'
        )
    """)
    conn.commit()
    conn.close()


def save_prediction(temperature: float, vacuum: float, pressure: float,
                    humidity: float, predicted_power: float,
                    scenario: str = "Manual") -> None:
    """Insert one prediction row into the database."""
    conn = _connect()
    conn.execute(
        """
        INSERT INTO prediction_history
            (timestamp, temperature, vacuum, pressure, humidity, predicted_power, scenario)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            round(temperature, 2),
            round(vacuum, 2),
            round(pressure, 2),
            round(humidity, 2),
            round(predicted_power, 2),
            scenario,
        )
    )
    conn.commit()
    conn.close()


def get_history(limit: int = 50):
    """Return the last `limit` predictions as a list of dicts (newest first)."""
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM prediction_history ORDER BY id DESC LIMIT ?",
        (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def clear_history():
    """Delete all rows from the table."""
    conn = _connect()
    conn.execute("DELETE FROM prediction_history")
    conn.commit()
    conn.close()
