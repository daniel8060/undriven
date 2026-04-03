import pytest
import db


@pytest.fixture
def tmp_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()


def test_init_db_creates_table(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", str(tmp_path / "test.db"))
    db.init_db()
    conn = db._connect()
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='trips'"
    ).fetchall()
    assert len(rows) == 1


def test_get_summary_empty(tmp_db):
    summary = db.get_summary()
    assert summary["total_miles"] == 0
    assert summary["total_co2_kg"] == 0
    assert summary["total_trips"] == 0
    assert summary["top_mode"] == "—"
    assert summary["by_mode"] == []
    assert summary["by_car"] == []
    assert len(summary["over_time"]) == 12


def test_insert_and_summary(tmp_db):
    db.insert_trip(
        date="2026-01-15",
        start_loc="Home",
        end_loc="Work",
        mode="bike",
        car_name="4Runner",
        miles=5.0,
        co2_kg=2.5,
        notes="",
    )
    summary = db.get_summary()
    assert summary["total_trips"] == 1
    assert summary["total_miles"] == pytest.approx(5.0)
    assert summary["total_co2_kg"] == pytest.approx(2.5)
    assert summary["top_mode"] == "bike"


def test_summary_by_mode_ordered_by_miles(tmp_db):
    db.insert_trip("2026-01-10", "A", "B", "bike", None, 10.0, 0.0, "")
    db.insert_trip("2026-01-11", "A", "B", "walk", None, 3.0, 0.0, "")
    db.insert_trip("2026-01-12", "A", "B", "bike", None, 5.0, 0.0, "")

    summary = db.get_summary()
    modes = [r["mode"] for r in summary["by_mode"]]
    assert modes[0] == "bike"   # 15.0 mi total
    assert modes[1] == "walk"   # 3.0 mi total


def test_summary_by_car_excludes_blank(tmp_db):
    db.insert_trip("2026-01-10", "A", "B", "bike", None, 5.0, 0.0, "")
    db.insert_trip("2026-01-11", "A", "B", "walk", "4Runner", 3.0, 1.0, "")

    summary = db.get_summary()
    assert len(summary["by_car"]) == 1
    assert summary["by_car"][0]["car_name"] == "4Runner"


def test_over_time_has_12_weeks(tmp_db):
    summary = db.get_summary()
    assert len(summary["over_time"]) == 12
    for week in summary["over_time"]:
        assert "week" in week
        assert "miles" in week
        assert "trips" in week
        assert "by_mode" in week
