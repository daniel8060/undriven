import pytest
from app import create_app
from models import User, db as _db


@pytest.fixture
def app():
    app = create_app({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "WTF_CSRF_ENABLED": False,
    })
    with app.app_context():
        _db.create_all()
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user(app):
    with app.app_context():
        u = User(username="testuser")
        u.set_password("hunter2")
        _db.session.add(u)
        _db.session.commit()
        return u.id


def test_login_page_renders(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    assert b"Sign in" in resp.data


def test_login_success(client, user):
    resp = client.post("/login", data={"username": "testuser", "password": "hunter2", "next": ""},
                       follow_redirects=True)
    assert resp.status_code == 200
    assert b"Undriven" in resp.data  # landed on index


def test_login_wrong_password(client, user):
    resp = client.post("/login", data={"username": "testuser", "password": "wrong", "next": ""},
                       follow_redirects=True)
    assert resp.status_code == 200
    assert b"Invalid username or password" in resp.data


def test_login_unknown_user(client):
    resp = client.post("/login", data={"username": "nobody", "password": "x", "next": ""},
                       follow_redirects=True)
    assert b"Invalid username or password" in resp.data


def test_protected_route_redirects_when_anonymous(client):
    resp = client.get("/", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_protected_route_accessible_after_login(client, user):
    client.post("/login", data={"username": "testuser", "password": "hunter2", "next": ""})
    resp = client.get("/")
    assert resp.status_code == 200


def test_logout(client, user):
    client.post("/login", data={"username": "testuser", "password": "hunter2", "next": ""})
    resp = client.post("/logout", follow_redirects=False)
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
    # After logout, protected route redirects again
    resp2 = client.get("/", follow_redirects=False)
    assert resp2.status_code == 302


def test_create_user_cli(app):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["create-user", "cliuser"],
                           input="password1\npassword1\n")
    assert result.exit_code == 0
    assert "Created user 'cliuser'" in result.output
    with app.app_context():
        u = User.query.filter_by(username="cliuser").first()
        assert u is not None
        assert u.check_password("password1")


def test_create_user_cli_duplicate(app, user):
    runner = app.test_cli_runner()
    result = runner.invoke(args=["create-user", "testuser"],
                           input="password1\npassword1\n")
    assert result.exit_code != 0
