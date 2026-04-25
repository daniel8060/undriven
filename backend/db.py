from datetime import date as _date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload

from backend.models import Trip, TripSegment


def insert_trip(
    session: Session,
    date: str,
    start_loc: str,
    end_loc: str,
    mode: str,
    car_name: str | None,
    miles: float,
    co2_kg: float,
    notes: str,
    user_id: int,
    segments: list[dict] | None = None,
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
        user_id=user_id,
    )
    session.add(trip)
    session.flush()  # get trip.id for segments

    if segments:
        for i, seg in enumerate(segments):
            session.add(TripSegment(
                trip_id=trip.id,
                position=i,
                start_loc=seg["start_loc"],
                end_loc=seg["end_loc"],
                mode=seg["mode"],
                miles=seg["miles"],
            ))

    session.commit()
    return trip


def get_all_trips(session: Session, user_id: int) -> list[Trip]:
    return (
        session.query(Trip)
        .options(selectinload(Trip.segments))
        .filter(Trip.user_id == user_id)
        .order_by(Trip.date.desc(), Trip.id.desc())
        .all()
    )


def get_trip(session: Session, trip_id: int, user_id: int) -> Trip | None:
    return session.query(Trip).filter_by(id=trip_id, user_id=user_id).first()


def delete_trip(session: Session, trip_id: int, user_id: int) -> bool:
    trip = session.query(Trip).filter_by(id=trip_id, user_id=user_id).first()
    if not trip:
        return False
    session.delete(trip)
    session.commit()
    return True


def _trip_legs(trip: Trip) -> list[tuple[str, float]]:
    """Return (mode, miles) pairs for a trip — segment-level if present, else parent."""
    if trip.segments:
        return [(s.mode, s.miles) for s in trip.segments]
    return [(trip.mode, trip.miles)]


def get_summary(session: Session, user_id: int, today: _date | None = None) -> dict:
    if today is None:
        today = _date.today()

    trips = (
        session.query(Trip)
        .options(selectinload(Trip.segments))
        .filter(Trip.user_id == user_id)
        .all()
    )

    total_co2_kg = session.query(func.coalesce(func.sum(Trip.co2_kg), 0)).filter(Trip.user_id == user_id).scalar()
    total_trips = len(trips)

    # Aggregate non-car legs only — these represent miles saved.
    mode_miles: dict[str, float] = {}
    mode_trip_counts: dict[str, int] = {}
    total_miles = 0.0
    for trip in trips:
        seen_modes: set[str] = set()
        for mode, miles in _trip_legs(trip):
            if mode == "car":
                continue
            total_miles += miles
            mode_miles[mode] = mode_miles.get(mode, 0.0) + miles
            seen_modes.add(mode)
        for m in seen_modes:
            mode_trip_counts[m] = mode_trip_counts.get(m, 0) + 1

    by_mode = sorted(
        [{"mode": m, "miles": mode_miles[m], "trips": mode_trip_counts.get(m, 0)} for m in mode_miles],
        key=lambda r: r["miles"], reverse=True,
    )

    by_car_rows = (
        session.query(
            Trip.car_name,
            func.sum(Trip.miles).label("miles"),
            func.sum(Trip.co2_kg).label("co2_kg"),
        )
        .filter(Trip.user_id == user_id, Trip.car_name.isnot(None), Trip.car_name != "")
        .group_by(Trip.car_name)
        .order_by(func.sum(Trip.miles).desc())
        .all()
    )
    by_car = [{"car_name": r.car_name, "miles": r.miles, "co2_kg": r.co2_kg} for r in by_car_rows]

    week_start = today - timedelta(days=today.weekday())
    weeks = []

    for i in range(11, -1, -1):
        wstart = week_start - timedelta(weeks=i)
        wend = wstart + timedelta(days=6)
        wstart_s, wend_s = wstart.isoformat(), wend.isoformat()

        trip_count = 0
        by_mode_week: dict[str, float] = {}
        for trip in trips:
            if not (wstart_s <= trip.date <= wend_s):
                continue
            trip_count += 1
            for mode, miles in _trip_legs(trip):
                if mode == "car":
                    continue
                by_mode_week[mode] = by_mode_week.get(mode, 0.0) + miles

        by_mode_week = {m: round(v, 2) for m, v in by_mode_week.items()}
        weeks.append({
            "week": wend.strftime("%b %d"),
            "miles": round(sum(by_mode_week.values()), 2),
            "trips": trip_count,
            "by_mode": by_mode_week,
        })

    return {
        "total_miles": total_miles,
        "total_co2_kg": total_co2_kg,
        "total_trips": total_trips,
        "top_mode": by_mode[0]["mode"] if by_mode else "\u2014",
        "by_mode": by_mode,
        "by_car": by_car,
        "over_time": weeks,
    }
