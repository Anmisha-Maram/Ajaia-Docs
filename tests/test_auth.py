import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.security import hash_password, verify_password
from app.seed import DEMO_PASSWORD


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def login(client, email="alice@ajaia.test", password=DEMO_PASSWORD):
    return client.post("/api/login", json={"email": email, "password": password})


def test_password_hash_round_trip():
    stored = hash_password("secret")
    assert stored != "secret"
    assert verify_password("secret", stored)
    assert not verify_password("wrong", stored)
    assert hash_password("secret") != stored  # random salt


def test_login_me_logout_flow(client):
    assert client.get("/api/me").status_code == 401

    r = login(client)
    assert r.status_code == 200
    assert r.json()["email"] == "alice@ajaia.test"
    assert "password" not in r.text

    me = client.get("/api/me")
    assert me.status_code == 200
    assert me.json()["name"] == "Alice Johnson"

    assert client.post("/api/logout").status_code == 200
    assert client.get("/api/me").status_code == 401


def test_login_is_case_insensitive_on_email(client):
    assert login(client, email="  BOB@ajaia.test ").status_code == 200


def test_bad_credentials_rejected_with_same_message(client):
    wrong_pw = login(client, password="nope")
    unknown = login(client, email="nobody@ajaia.test")
    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json() == unknown.json()


def test_login_validation_error_on_missing_fields(client):
    assert client.post("/api/login", json={"email": "alice@ajaia.test"}).status_code == 422


def test_seed_is_idempotent(client):
    from app import db

    with TestClient(app):  # a second startup re-runs seeding; the query must run inside it
        assert db.pool is not None
        with db.pool.connection() as conn:
            n = conn.execute(
                "SELECT count(*) AS n FROM users WHERE email LIKE '%@ajaia.test'"
            ).fetchone()["n"]
    assert n == 3