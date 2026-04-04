import pytest
from app import create_app
from models import db as _db


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
    })
    with app.app_context():
        _db.create_all()
        yield app


@pytest.fixture
def session(app):
    with app.app_context():
        yield _db.session


def test_init_creates_trips_table(app):
    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(_db.engine)
        assert "trips" in inspector.get_table_names()


def test_init_creates_users_table(app):
    with app.app_context():
        from sqlalchemy import inspect
        inspector = inspect(_db.engine)
        assert "users" in inspector.get_table_names()


def test_get_summary_empty(app):
    with app.app_context():
        import db
        summary = db.get_summary()
    assert summary["total_miles"] == 0
    assert summary["total_co2_kg"] == 0
    assert summary["total_trips"] == 0
    assert summary["top_mode"] == "—"
    assert summary["by_mode"] == []
    assert summary["by_car"] == []
    assert len(summary["over_time"]) == 12


def test_insert_and_summary(app):
    with app.app_context():
        import db
        db.insert_trip("2026-01-15", "Home", "Work", "bike", "4Runner", 5.0, 2.5, "")
        summary = db.get_summary()
    assert summary["total_trips"] == 1
    assert summary["total_miles"] == pytest.approx(5.0)
    assert summary["total_co2_kg"] == pytest.approx(2.5)
    assert summary["top_mode"] == "bike"


def test_summary_by_mode_ordered_by_miles(app):
    with app.app_context():
        import db
        db.insert_trip("2026-01-10", "A", "B", "bike", None, 10.0, 0.0, "")
        db.insert_trip("2026-01-11", "A", "B", "walk", None, 3.0,  0.0, "")
        db.insert_trip("2026-01-12", "A", "B", "bike", None, 5.0,  0.0, "")
        summary = db.get_summary()
    modes = [r["mode"] for r in summary["by_mode"]]
    assert modes[0] == "bike"
    assert modes[1] == "walk"


def test_summary_by_car_excludes_null(app):
    with app.app_context():
        import db
        db.insert_trip("2026-01-10", "A", "B", "bike", None,       5.0, 0.0, "")
        db.insert_trip("2026-01-11", "A", "B", "walk", "4Runner",  3.0, 1.0, "")
        summary = db.get_summary()
    assert len(summary["by_car"]) == 1
    assert summary["by_car"][0]["car_name"] == "4Runner"


def test_delete_trip(app):
    with app.app_context():
        import db
        from models import Trip
        db.insert_trip("2026-01-15", "Home", "Work", "bike", None, 5.0, 0.0, "")
        trip_id = Trip.query.first().id
        db.delete_trip(trip_id)
        assert Trip.query.count() == 0


def test_get_all_trips_ordered_most_recent_first(app):
    with app.app_context():
        import db
        db.insert_trip("2026-01-10", "A", "B", "bike", None, 3.0, 0.0, "")
        db.insert_trip("2026-01-15", "A", "B", "walk", None, 5.0, 0.0, "")
        trips = db.get_all_trips()
    assert trips[0].date == "2026-01-15"
    assert trips[1].date == "2026-01-10"


def test_over_time_has_12_weeks(app):
    with app.app_context():
        import db
        summary = db.get_summary()
    assert len(summary["over_time"]) == 12
    for week in summary["over_time"]:
        assert "week" in week and "miles" in week and "trips" in week and "by_mode" in week
