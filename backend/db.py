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


def get_summary(session: Session, user_id: int, today: _date | None = None) -> dict:
    if today is None:
        today = _date.today()

    base = session.query(Trip).filter(Trip.user_id == user_id)

    total_miles = session.query(func.coalesce(func.sum(Trip.miles), 0)).filter(Trip.user_id == user_id).scalar()
    total_co2_kg = session.query(func.coalesce(func.sum(Trip.co2_kg), 0)).filter(Trip.user_id == user_id).scalar()
    total_trips = session.query(func.count(Trip.id)).filter(Trip.user_id == user_id).scalar()

    by_mode_rows = (
        session.query(
            Trip.mode,
            func.sum(Trip.miles).label("miles"),
            func.count(Trip.id).label("trips"),
        )
        .filter(Trip.user_id == user_id)
        .group_by(Trip.mode)
        .order_by(func.sum(Trip.miles).desc())
        .all()
    )
    by_mode = [{"mode": r.mode, "miles": r.miles, "trips": r.trips} for r in by_mode_rows]

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

        trip_count = (
            base.filter(Trip.date >= wstart.isoformat(), Trip.date <= wend.isoformat())
            .count()
        )

        mode_rows = (
            session.query(
                Trip.mode,
                func.coalesce(func.sum(Trip.miles), 0).label("miles"),
            )
            .filter(
                Trip.user_id == user_id,
                Trip.date >= wstart.isoformat(),
                Trip.date <= wend.isoformat(),
            )
            .group_by(Trip.mode)
            .all()
        )

        by_mode_week = {r.mode: round(r.miles, 2) for r in mode_rows}
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
