from unittest.mock import patch
import pytest

from backend.models import Trip, TripSegment
from backend.sync import co2_for_car, log_trip, parse_car

CARS = {
    "4Runner": {"mpg": 18.0, "fuel_type": "gasoline"},
    "Corolla": {"mpg": 29.0, "fuel_type": "gasoline"},
}


def test_parse_car_valid():
    assert parse_car("4Runner", CARS) == "4Runner"


def test_parse_car_unknown_returns_none():
    assert parse_car("DeLorean", CARS) is None


def test_parse_car_blank_returns_none():
    assert parse_car("", CARS) is None
    assert parse_car("   ", CARS) is None


def test_co2_for_car_gasoline():
    assert co2_for_car("4Runner", 18.0, CARS) == pytest.approx(8.887, rel=1e-4)


def test_co2_for_car_higher_mpg():
    assert co2_for_car("Corolla", 29.0, CARS) == pytest.approx(8.887, rel=1e-4)


def test_co2_for_car_proportional():
    assert co2_for_car("4Runner", 18.0, CARS) == pytest.approx(
        co2_for_car("4Runner", 9.0, CARS) * 2, rel=1e-6
    )


def test_log_trip_inserts_and_returns_miles(session, user):
    with patch("backend.sync.driving_miles", return_value=5.0):
        miles = log_trip(
            session=session, date="2026-01-15", start="Home", end="Work",
            mode="bike", car_name=None, notes="test", user_id=user.id,
        )
    assert miles == pytest.approx(5.0)
    assert session.query(Trip).count() == 1
    assert session.query(Trip).first().car_name is None


def test_log_trip_with_car_calculates_co2(session, user):
    with patch("backend.sync.driving_miles", return_value=18.0):
        log_trip(
            session=session, date="2026-01-15", start="Home", end="Office",
            mode="train", car_name="4Runner", notes="", user_id=user.id,
            cars=CARS,
        )
    assert session.query(Trip).first().co2_kg == pytest.approx(8.887, rel=1e-4)


def test_log_trip_multi_segment(session, user):
    segments = [
        {"start": "Home", "end": "Station", "mode": "bike"},
        {"start": "Station", "end": "Office", "mode": "train"},
    ]
    with patch("backend.sync.driving_miles", side_effect=[2.0, 8.0]):
        miles = log_trip(
            session=session, date="2026-01-15", start="Home", end="Office",
            mode="bike", car_name=None, notes="multi", user_id=user.id,
            segments=segments,
        )
    assert miles == pytest.approx(10.0)
    trip = session.query(Trip).first()
    assert trip.start_loc == "Home"
    assert trip.end_loc == "Office"
    assert trip.miles == pytest.approx(10.0)
    segs = session.query(TripSegment).filter_by(trip_id=trip.id).order_by(TripSegment.position).all()
    assert len(segs) == 2
    assert segs[0].miles == pytest.approx(2.0)
    assert segs[1].miles == pytest.approx(8.0)
