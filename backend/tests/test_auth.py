import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from backend.auth import COOKIE_NAME
from backend.database import get_db
from backend.main import app
from backend.models import Base, User


@pytest.fixture
def client():
    # Use a single connection so all sessions share the same in-memory DB
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    connection = engine.connect()
    TestSession = sessionmaker(bind=connection)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    c = TestClient(app)
    yield c, TestSession
    app.dependency_overrides.clear()
    connection.close()
    engine.dispose()


def _create_user(TestSession, username="testuser", password="hunter2"):
    session = TestSession()
    u = User(username=username)
    u.set_password(password)
    session.add(u)
    session.commit()
    uid = u.id
    session.close()
    return uid


def test_login_success(client):
    c, TestSession = client
    _create_user(TestSession)
    resp = c.post("/api/login", json={"username": "testuser", "password": "hunter2"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert COOKIE_NAME in resp.cookies


def test_login_wrong_password(client):
    c, TestSession = client
    _create_user(TestSession)
    resp = c.post("/api/login", json={"username": "testuser", "password": "wrong"})
    assert resp.status_code == 401


def test_login_unknown_user(client):
    c, _ = client
    resp = c.post("/api/login", json={"username": "nobody", "password": "x"})
    assert resp.status_code == 401


def test_me_unauthenticated(client):
    c, _ = client
    resp = c.get("/api/me")
    assert resp.status_code == 401


def test_me_authenticated(client):
    c, TestSession = client
    _create_user(TestSession)
    c.post("/api/login", json={"username": "testuser", "password": "hunter2"})
    resp = c.get("/api/me")
    assert resp.status_code == 200
    assert resp.json()["username"] == "testuser"


def test_logout(client):
    c, TestSession = client
    _create_user(TestSession)
    c.post("/api/login", json={"username": "testuser", "password": "hunter2"})
    resp = c.post("/api/logout")
    assert resp.status_code == 200
    resp2 = c.get("/api/me")
    assert resp2.status_code == 401


def test_signup_success(client):
    c, _ = client
    resp = c.post("/api/signup", json={
        "username": "newuser", "password": "pass123", "password2": "pass123",
    })
    assert resp.status_code == 201
    assert COOKIE_NAME in resp.cookies


def test_signup_password_mismatch(client):
    c, _ = client
    resp = c.post("/api/signup", json={
        "username": "newuser", "password": "pass123", "password2": "different",
    })
    assert resp.status_code == 400


def test_signup_duplicate_username(client):
    c, TestSession = client
    _create_user(TestSession)
    resp = c.post("/api/signup", json={
        "username": "testuser", "password": "pass123", "password2": "pass123",
    })
    assert resp.status_code == 409
