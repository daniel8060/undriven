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
                id       INTEGER PRIMARY KEY,
                sheet_row INTEGER UNIQUE,
                date     TEXT,
                start_loc TEXT,
                end_loc  TEXT,
                mode     TEXT,
                cars_raw TEXT,
                miles    REAL,
                notes    TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trip_cars (
                id       INTEGER PRIMARY KEY,
                trip_id  INTEGER REFERENCES trips(id),
                car_name TEXT,
                occupants INTEGER,
                miles    REAL,
                co2_kg   REAL
            )
        """)


def get_known_sheet_rows() -> set:
    with _connect() as conn:
        rows = conn.execute("SELECT sheet_row FROM trips").fetchall()
    return {r["sheet_row"] for r in rows}


def insert_trip(
    sheet_row: int,
    date: str,
    start_loc: str,
    end_loc: str,
    mode: str,
    cars_raw: str,
    miles: float,
    notes: str,
    cars: list,  # list of {car_name, occupants, co2_kg}
):
    with _connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO trips (sheet_row, date, start_loc, end_loc, mode, cars_raw, miles, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (sheet_row, date, start_loc, end_loc, mode, cars_raw, miles, notes),
        )
        trip_id = cur.lastrowid
        for car in cars:
            conn.execute(
                """
                INSERT INTO trip_cars (trip_id, car_name, occupants, miles, co2_kg)
                VALUES (?, ?, ?, ?, ?)
                """,
                (trip_id, car["car_name"], car["occupants"], miles, car["co2_kg"]),
            )


def get_summary() -> dict:
    with _connect() as conn:
        total_row = conn.execute(
            "SELECT COALESCE(SUM(miles), 0) AS total_miles FROM trips"
        ).fetchone()
        total_miles = total_row["total_miles"]

        total_co2_row = conn.execute(
            "SELECT COALESCE(SUM(co2_kg), 0) AS total_co2_kg FROM trip_cars"
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
            FROM trip_cars
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
