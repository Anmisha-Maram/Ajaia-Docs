import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.seed import DEMO_PASSWORD


@pytest.fixture(scope="module")
def _lifespan():
    # Starts the app once (opens the DB pool). Extra clients below skip startup
    # but share the pool, and each has its own cookie jar = its own signed-in user.
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def login_as(_lifespan):
    def _login(email):
        c = TestClient(app)
        r = c.post("/api/login", json={"email": email, "password": DEMO_PASSWORD})
        assert r.status_code == 200
        return c

    return _login


def make_doc(client, title="Test doc"):
    r = client.post("/api/docs", json={"title": title})
    assert r.status_code == 201
    return r.json()["id"]


def test_requires_login(_lifespan):
    assert TestClient(app).get("/api/docs").status_code == 401


def test_create_rename_edit_reopen_preserves_formatting(login_as):
    alice = login_as("alice@ajaia.test")
    doc_id = make_doc(alice, "Plan")
    html = "<h1>Title</h1><p><strong>bold</strong> <em>it</em> <u>under</u></p><ul><li>a</li></ul><ol><li>b</li></ol>"

    r = alice.put(f"/api/docs/{doc_id}", json={"title": "Plan v2", "html": html})
    assert r.status_code == 200
    assert r.json() == {"version": 2, "title": "Plan v2"}

    doc = alice.get(f"/api/docs/{doc_id}").json()
    assert doc["title"] == "Plan v2"
    assert doc["html"] == html
    assert doc["role"] == "owner"


def test_default_title_and_listing(login_as):
    alice = login_as("alice@ajaia.test")
    r = alice.post("/api/docs", json={})
    assert r.json()["title"] == "Untitled document"
    listing = alice.get("/api/docs").json()
    assert any(d["id"] == r.json()["id"] and d["role"] == "owner" for d in listing["owned"])


def test_title_validation(login_as):
    alice = login_as("alice@ajaia.test")
    doc_id = make_doc(alice)
    assert alice.put(f"/api/docs/{doc_id}", json={"title": "   "}).status_code == 400
    assert alice.put(f"/api/docs/{doc_id}", json={"title": "x" * 121}).status_code == 400
    assert alice.post("/api/docs", json={"title": ""}).status_code == 400
    assert alice.put(f"/api/docs/{doc_id}", json={}).status_code == 400


def test_html_is_sanitized(login_as):
    alice = login_as("alice@ajaia.test")
    doc_id = make_doc(alice)
    dirty = '<p onclick="x()">hi</p><script>alert(1)</script><a href="javascript:alert(1)">l</a><img src=x onerror=alert(1)>'
    alice.put(f"/api/docs/{doc_id}", json={"html": dirty})
    saved = alice.get(f"/api/docs/{doc_id}").json()["html"]
    for bad in ("script", "onclick", "javascript:", "onerror", "<img"):
        assert bad not in saved, saved
    assert "hi" in saved


def test_stale_version_gets_409(login_as):
    alice = login_as("alice@ajaia.test")
    doc_id = make_doc(alice)
    v = alice.get(f"/api/docs/{doc_id}").json()["version"]
    assert alice.put(f"/api/docs/{doc_id}", json={"html": "<p>1</p>", "base_version": v}).status_code == 200
    assert alice.put(f"/api/docs/{doc_id}", json={"html": "<p>2</p>", "base_version": v}).status_code == 409
    assert alice.get(f"/api/docs/{doc_id}").json()["html"] == "<p>1</p>"


def test_strangers_get_404_not_403(login_as):
    alice = login_as("alice@ajaia.test")
    bob = login_as("bob@ajaia.test")
    doc_id = make_doc(alice, "Private")
    assert bob.get(f"/api/docs/{doc_id}").status_code == 404
    assert bob.put(f"/api/docs/{doc_id}", json={"title": "hax"}).status_code == 404
    assert bob.delete(f"/api/docs/{doc_id}").status_code == 404
    listing = bob.get("/api/docs").json()
    assert all(d["id"] != doc_id for d in listing["owned"] + listing["shared"])


def test_viewer_and_editor_rights(login_as, _lifespan):
    from app import db

    alice = login_as("alice@ajaia.test")
    bob = login_as("bob@ajaia.test")
    doc_id = make_doc(alice, "Shared doc")
    bob_id = bob.get("/api/me").json()["id"]

    def share(role):
        with db.pool.connection() as conn:
            conn.execute(
                "INSERT INTO shares (document_id, user_id, role) VALUES (%s, %s, %s) "
                "ON CONFLICT (document_id, user_id) DO UPDATE SET role = EXCLUDED.role",
                (doc_id, bob_id, role),
            )

    share("viewer")
    assert bob.get(f"/api/docs/{doc_id}").json()["role"] == "viewer"
    assert bob.put(f"/api/docs/{doc_id}", json={"html": "<p>x</p>"}).status_code == 403

    share("editor")
    assert bob.put(f"/api/docs/{doc_id}", json={"html": "<p>edited</p>"}).status_code == 200
    assert bob.delete(f"/api/docs/{doc_id}").status_code == 403  # only the owner deletes

    listing = bob.get("/api/docs").json()
    assert any(d["id"] == doc_id and d["role"] == "editor" for d in listing["shared"])
    assert all(d["id"] != doc_id for d in listing["owned"])


def test_owner_can_delete(login_as):
    alice = login_as("alice@ajaia.test")
    doc_id = make_doc(alice)
    assert alice.delete(f"/api/docs/{doc_id}").status_code == 200
    assert alice.get(f"/api/docs/{doc_id}").status_code == 404
