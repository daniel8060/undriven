from datetime import datetime, timedelta

from sqlalchemy import func

from models import Trip, db


def insert_trip(
    date: str,
    start_loc: str,
    end_loc: str,
    mode: str,
    car_name: str | None,
    miles: float,
    co2_kg: float,
    notes: str,
) -> Trip:
    trip = Trip(
        date=date,
        start_loc=start_loc,
        end_loc=end_loc,
        mode=mode,
        car_name=car_name or None,
        miles=miles,
        co2_kg=co2_kg,
        notes=notes or "",
    )
    db.session.add(trip)
    db.session.commit()
    return trip


def get_all_trips() -> list[Trip]:
    return Trip.query.order_by(Trip.date.desc(), Trip.id.desc()).all()


def get_trip(trip_id: int) -> Trip:
    return db.get_or_404(Trip, trip_id)


def delete_trip(trip_id: int) -> None:
    trip = db.get_or_404(Trip, trip_id)
    db.session.delete(trip)
    db.session.commit()


def get_summary() -> dict:
    total_miles  = db.session.query(func.coalesce(func.sum(Trip.miles),  0)).scalar()
    total_co2_kg = db.session.query(func.coalesce(func.sum(Trip.co2_kg), 0)).scalar()
    total_trips  = db.session.query(func.count(Trip.id)).scalar()

    by_mode_rows = (
        db.session.query(
            Trip.mode,
            func.sum(Trip.miles).label("miles"),
            func.count(Trip.id).label("trips"),
        )
        .group_by(Trip.mode)
        .order_by(func.sum(Trip.miles).desc())
        .all()
    )
    by_mode = [{"mode": r.mode, "miles": r.miles, "trips": r.trips} for r in by_mode_rows]

    by_car_rows = (
        db.session.query(
            Trip.car_name,
            func.sum(Trip.miles).label("miles"),
            func.sum(Trip.co2_kg).label("co2_kg"),
        )
        .filter(Trip.car_name.isnot(None), Trip.car_name != "")
        .group_by(Trip.car_name)
        .order_by(func.sum(Trip.miles).desc())
        .all()
    )
    by_car = [{"car_name": r.car_name, "miles": r.miles, "co2_kg": r.co2_kg} for r in by_car_rows]

    # Last 12 weeks — aggregated in Python to keep the SQL simple
    today      = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())
    weeks      = []

    for i in range(11, -1, -1):
        wstart = week_start - timedelta(weeks=i)
        wend   = wstart + timedelta(days=6)

        trip_count = Trip.query.filter(
            Trip.date >= wstart.isoformat(),
            Trip.date <= wend.isoformat(),
        ).count()

        mode_rows = (
            db.session.query(
                Trip.mode,
                func.coalesce(func.sum(Trip.miles), 0).label("miles"),
            )
            .filter(Trip.date >= wstart.isoformat(), Trip.date <= wend.isoformat())
            .group_by(Trip.mode)
            .all()
        )

        by_mode_week = {r.mode: round(r.miles, 2) for r in mode_rows}
        weeks.append({
            "week":    wstart.strftime("%b %d"),
            "miles":   round(sum(by_mode_week.values()), 2),
            "trips":   trip_count,
            "by_mode": by_mode_week,
        })

    return {
        "total_miles":  total_miles,
        "total_co2_kg": total_co2_kg,
        "total_trips":  total_trips,
        "top_mode":     by_mode[0]["mode"] if by_mode else "—",
        "by_mode":      by_mode,
        "by_car":       by_car,
        "over_time":    weeks,
    }
