import pytest
from datetime import date

from backend.db import delete_trip, get_all_trips, get_summary, insert_trip
from backend.models import Trip, TripSegment


def test_init_creates_trips_table(engine):
    from sqlalchemy import inspect
    inspector = inspect(engine)
    assert "trips" in inspector.get_table_names()


def test_init_creates_users_table(engine):
    from sqlalchemy import inspect
    inspector = inspect(engine)
    assert "users" in inspector.get_table_names()


def test_init_creates_trip_segments_table(engine):
    from sqlalchemy import inspect
    inspector = inspect(engine)
    assert "trip_segments" in inspector.get_table_names()


def test_get_summary_empty(session, user):
    summary = get_summary(session, user.id)
    assert summary["total_miles"] == 0
    assert summary["total_co2_kg"] == 0
    assert summary["total_trips"] == 0
    assert summary["top_mode"] == "\u2014"
    assert summary["by_mode"] == []
    assert summary["by_car"] == []
    assert len(summary["over_time"]) == 12


def test_insert_and_summary(session, user):
    insert_trip(session, "2026-01-15", "Home", "Work", "bike", "4Runner", 5.0, 2.5, "", user.id)
    summary = get_summary(session, user.id)
    assert summary["total_trips"] == 1
    assert summary["total_miles"] == pytest.approx(5.0)
    assert summary["total_co2_kg"] == pytest.approx(2.5)
    assert summary["top_mode"] == "bike"


def test_summary_by_mode_ordered_by_miles(session, user):
    insert_trip(session, "2026-01-10", "A", "B", "bike", None, 10.0, 0.0, "", user.id)
    insert_trip(session, "2026-01-11", "A", "B", "walk", None, 3.0, 0.0, "", user.id)
    insert_trip(session, "2026-01-12", "A", "B", "bike", None, 5.0, 0.0, "", user.id)
    summary = get_summary(session, user.id)
    modes = [r["mode"] for r in summary["by_mode"]]
    assert modes[0] == "bike"
    assert modes[1] == "walk"


def test_summary_by_car_excludes_null(session, user):
    insert_trip(session, "2026-01-10", "A", "B", "bike", None, 5.0, 0.0, "", user.id)
    insert_trip(session, "2026-01-11", "A", "B", "walk", "4Runner", 3.0, 1.0, "", user.id)
    summary = get_summary(session, user.id)
    assert len(summary["by_car"]) == 1
    assert summary["by_car"][0]["car_name"] == "4Runner"


def test_delete_trip(session, user):
    insert_trip(session, "2026-01-15", "Home", "Work", "bike", None, 5.0, 0.0, "", user.id)
    trip = session.query(Trip).first()
    assert delete_trip(session, trip.id, user.id) is True
    assert session.query(Trip).count() == 0


def test_get_all_trips_ordered_most_recent_first(session, user):
    insert_trip(session, "2026-01-10", "A", "B", "bike", None, 3.0, 0.0, "", user.id)
    insert_trip(session, "2026-01-15", "A", "B", "walk", None, 5.0, 0.0, "", user.id)
    trips = get_all_trips(session, user.id)
    assert trips[0].date == "2026-01-15"
    assert trips[1].date == "2026-01-10"


def test_over_time_has_12_weeks(session, user):
    summary = get_summary(session, user.id)
    assert len(summary["over_time"]) == 12
    for week in summary["over_time"]:
        assert "week" in week and "miles" in week and "trips" in week and "by_mode" in week


def test_over_time_trip_in_current_week(session, user):
    today = date(2026, 4, 3)
    insert_trip(session, "2026-03-30", "A", "B", "bike", None, 5.0, 0.0, "", user.id)
    summary = get_summary(session, user.id, today=today)
    current_week = summary["over_time"][-1]
    assert current_week["trips"] == 1
    assert current_week["miles"] == pytest.approx(5.0)
    assert current_week["by_mode"]["bike"] == pytest.approx(5.0)


def test_over_time_trip_in_prior_week(session, user):
    today = date(2026, 4, 3)
    insert_trip(session, "2026-03-23", "A", "B", "walk", None, 3.0, 0.0, "", user.id)
    summary = get_summary(session, user.id, today=today)
    prior_week = summary["over_time"][-2]
    assert prior_week["trips"] == 1
    assert prior_week["miles"] == pytest.approx(3.0)


def test_over_time_sunday_trip_stays_in_its_week(session, user):
    today = date(2026, 4, 6)
    insert_trip(session, "2026-04-05", "A", "B", "train", None, 7.0, 0.0, "", user.id)
    summary = get_summary(session, user.id, today=today)
    current_week = summary["over_time"][-1]
    prior_week = summary["over_time"][-2]
    assert current_week["trips"] == 0
    assert prior_week["trips"] == 1
    assert prior_week["miles"] == pytest.approx(7.0)


def test_summary_user_scoped(session, user):
    """Trips from other users should not appear in summary."""
    from backend.models import User
    other = User(username="other")
    other.set_password("pw")
    session.add(other)
    session.commit()
    insert_trip(session, "2026-01-15", "A", "B", "bike", None, 10.0, 0.0, "", other.id)
    insert_trip(session, "2026-01-15", "A", "B", "walk", None, 3.0, 0.0, "", user.id)
    summary = get_summary(session, user.id)
    assert summary["total_trips"] == 1
    assert summary["total_miles"] == pytest.approx(3.0)


def test_insert_trip_with_segments(session, user):
    segments = [
        {"start_loc": "Home", "end_loc": "Station", "mode": "bike", "miles": 2.0},
        {"start_loc": "Station", "end_loc": "Office", "mode": "train", "miles": 8.0},
    ]
    trip = insert_trip(
        session, "2026-01-15", "Home", "Office", "bike", None, 10.0, 0.0, "", user.id,
        segments=segments,
    )
    assert session.query(TripSegment).filter_by(trip_id=trip.id).count() == 2
    segs = session.query(TripSegment).filter_by(trip_id=trip.id).order_by(TripSegment.position).all()
    assert segs[0].start_loc == "Home"
    assert segs[0].end_loc == "Station"
    assert segs[0].mode == "bike"
    assert segs[1].start_loc == "Station"
    assert segs[1].end_loc == "Office"
    assert segs[1].mode == "train"


def test_delete_trip_cascades_to_segments(session, user):
    segments = [
        {"start_loc": "A", "end_loc": "B", "mode": "bike", "miles": 3.0},
        {"start_loc": "B", "end_loc": "C", "mode": "walk", "miles": 1.0},
    ]
    trip = insert_trip(
        session, "2026-01-15", "A", "C", "bike", None, 4.0, 0.0, "", user.id,
        segments=segments,
    )
    assert session.query(TripSegment).count() == 2
    delete_trip(session, trip.id, user.id)
    assert session.query(TripSegment).count() == 0
