import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_reports_database_connected(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "database": "connected"}


def test_schema_created(client):
    from app import db

    with db.pool.connection() as conn:
        tables = {r["tablename"] for r in conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'")}
    assert {"users", "sessions", "documents", "shares"} <= tables