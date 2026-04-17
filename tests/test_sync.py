from unittest.mock import patch
import pytest
from app import create_app
from models import db as _db
import sync

CARS = {
    "4Runner": {"mpg": 18.0, "fuel_type": "gasoline"},
    "Corolla":  {"mpg": 29.0, "fuel_type": "gasoline"},
}


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        _db.create_all()
        yield app


def test_parse_car_valid():
    assert sync.parse_car("4Runner", CARS) == "4Runner"


def test_parse_car_unknown_returns_none():
    assert sync.parse_car("DeLorean", CARS) is None


def test_parse_car_blank_returns_none():
    assert sync.parse_car("", CARS) is None
    assert sync.parse_car("   ", CARS) is None


def test_co2_for_car_gasoline():
    # 4Runner: 18 mpg, gasoline (8.887 kg/gal) → 18 miles = 1 gallon = 8.887 kg
    assert sync.co2_for_car("4Runner", 18.0, CARS) == pytest.approx(8.887, rel=1e-4)


def test_co2_for_car_higher_mpg():
    # Corolla: 29 mpg → 29 miles = 1 gallon = 8.887 kg
    assert sync.co2_for_car("Corolla", 29.0, CARS) == pytest.approx(8.887, rel=1e-4)


def test_co2_for_car_proportional():
    assert sync.co2_for_car("4Runner", 18.0, CARS) == pytest.approx(
        sync.co2_for_car("4Runner", 9.0, CARS) * 2, rel=1e-6
    )


def test_log_trip_inserts_and_returns_miles(app):
    with app.app_context():
        from models import Trip
        with patch("sync.driving_miles", return_value=5.0):
            miles = sync.log_trip(
                date="2026-01-15", start="Home", end="Work",
                mode="bike", car_name=None, notes="test",
            )
        assert miles == pytest.approx(5.0)
        assert Trip.query.count() == 1
        assert Trip.query.first().car_name is None


def test_log_trip_with_car_calculates_co2(app):
    with app.app_context():
        from models import Trip
        with patch("sync.driving_miles", return_value=18.0):
            sync.log_trip(
                date="2026-01-15", start="Home", end="Office",
                mode="train", car_name="4Runner", notes="",
                cars=CARS,
            )
        # 18 mi / 18 mpg = 1 gal × 8.887 kg/gal
        assert Trip.query.first().co2_kg == pytest.approx(8.887, rel=1e-4)
