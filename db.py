import sqlite3
from datetime import datetime, timedelta

DB_PATH = "trips.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    with _connect() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trips (
                id        INTEGER PRIMARY KEY,
                date      TEXT,
                start_loc TEXT,
                end_loc   TEXT,
                mode      TEXT,
                car_name  TEXT,
                miles     REAL,
                co2_kg    REAL,
                notes     TEXT
            )
        """)


def insert_trip(
    date: str,
    start_loc: str,
    end_loc: str,
    mode: str,
    car_name: str,
    miles: float,
    co2_kg: float,
    notes: str,
):
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO trips (date, start_loc, end_loc, mode, car_name, miles, co2_kg, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (date, start_loc, end_loc, mode, car_name, miles, co2_kg, notes),
        )


def get_summary() -> dict:
    with _connect() as conn:
        total_row = conn.execute(
            "SELECT COALESCE(SUM(miles), 0) AS total_miles FROM trips"
        ).fetchone()
        total_miles = total_row["total_miles"]

        total_co2_row = conn.execute(
            "SELECT COALESCE(SUM(co2_kg), 0) AS total_co2_kg FROM trips"
        ).fetchone()
        total_co2_kg = total_co2_row["total_co2_kg"]

        total_trips_row = conn.execute("SELECT COUNT(*) AS cnt FROM trips").fetchone()
        total_trips = total_trips_row["cnt"]

        by_mode_rows = conn.execute("""
            SELECT mode,
                   SUM(miles) AS miles,
                   COUNT(*)   AS trips
            FROM trips
            GROUP BY mode
            ORDER BY miles DESC
        """).fetchall()
        by_mode = [dict(r) for r in by_mode_rows]

        by_car_rows = conn.execute("""
            SELECT car_name,
                   SUM(miles)  AS miles,
                   SUM(co2_kg) AS co2_kg
            FROM trips
            WHERE car_name IS NOT NULL AND car_name != ''
            GROUP BY car_name
            ORDER BY miles DESC
        """).fetchall()
        by_car = [dict(r) for r in by_car_rows]

        # Last 12 weeks, week starting Monday
        today = datetime.utcnow().date()
        week_start = today - timedelta(days=today.weekday())  # this Monday
        weeks = []
        for i in range(11, -1, -1):
            wstart = week_start - timedelta(weeks=i)
            wend = wstart + timedelta(days=6)
            label = wstart.strftime("%b %d")
            row = conn.execute(
                """
                SELECT COALESCE(SUM(miles), 0) AS miles,
                       COUNT(*) AS trips
                FROM trips
                WHERE date >= ? AND date <= ?
                """,
                (wstart.isoformat(), wend.isoformat()),
            ).fetchone()
            weeks.append({"week": label, "miles": row["miles"], "trips": row["trips"]})

    top_mode = by_mode[0]["mode"] if by_mode else "—"

    return {
        "total_miles": total_miles,
        "total_co2_kg": total_co2_kg,
        "total_trips": total_trips,
        "top_mode": top_mode,
        "by_mode": by_mode,
        "by_car": by_car,
        "over_time": weeks,
    }
