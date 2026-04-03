from unittest.mock import patch, call
import pytest
import sync


def test_parse_car_valid():
    assert sync.parse_car("4Runner") == "4Runner"


def test_parse_car_unknown_returns_none():
    assert sync.parse_car("DeLorean") is None


def test_parse_car_blank_returns_none():
    assert sync.parse_car("") is None
    assert sync.parse_car("   ") is None


def test_co2_for_car_gasoline():
    # 4Runner: 18 mpg, gasoline (8.887 kg/gal)
    # 18 miles → 1 gallon → 8.887 kg
    result = sync.co2_for_car("4Runner", 18.0)
    assert result == pytest.approx(8.887, rel=1e-4)


def test_co2_for_car_higher_mpg():
    # Corolla: 29 mpg, gasoline
    # 29 miles → 1 gallon → 8.887 kg
    result = sync.co2_for_car("Corolla", 29.0)
    assert result == pytest.approx(8.887, rel=1e-4)


def test_co2_for_car_proportional():
    result_half = sync.co2_for_car("4Runner", 9.0)
    result_full = sync.co2_for_car("4Runner", 18.0)
    assert result_full == pytest.approx(result_half * 2, rel=1e-6)


def test_log_trip_calls_driving_miles_and_insert(tmp_path, monkeypatch):
    import db
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()

    with patch("sync.driving_miles", return_value=5.0) as mock_dm:
        miles = sync.log_trip(
            date="2026-01-15",
            start="Home",
            end="Work",
            mode="bike",
            car_name=None,
            notes="test",
        )

    mock_dm.assert_called_once_with("Home", "Work")
    assert miles == pytest.approx(5.0)

    summary = db.get_summary()
    assert summary["total_trips"] == 1
    assert summary["total_miles"] == pytest.approx(5.0)
    assert summary["total_co2_kg"] == pytest.approx(0.0)


def test_log_trip_with_car_calculates_co2(tmp_path, monkeypatch):
    import db
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()

    with patch("sync.driving_miles", return_value=18.0):
        sync.log_trip(
            date="2026-01-15",
            start="Home",
            end="Office",
            mode="train",
            car_name="4Runner",
            notes="",
        )

    summary = db.get_summary()
    # 18 miles / 18 mpg = 1 gallon; 1 gallon × 8.887 kg/gal = 8.887 kg
    assert summary["total_co2_kg"] == pytest.approx(8.887, rel=1e-4)
