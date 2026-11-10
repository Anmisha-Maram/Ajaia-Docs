import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.seed import DEMO_PASSWORD


@pytest.fixture(scope="module")
def _lifespan():
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def login_as(_lifespan):
    def _login(email):
        c = TestClient(app)
        assert c.post("/api/login", json={"email": email, "password": DEMO_PASSWORD}).status_code == 200
        return c

    return _login


def make_doc(client, title="Shared test"):
    return client.post("/api/docs", json={"title": title}).json()["id"]


def share(client, doc_id, email, role):
    return client.post(f"/api/docs/{doc_id}/shares", json={"email": email, "role": role})


def test_share_flow_end_to_end(login_as):
    alice, bob, carol = (login_as(f"{n}@ajaia.test") for n in ("alice", "bob", "carol"))
    doc_id = make_doc(alice)

    # Before sharing, Bob can't see it.
    assert bob.get(f"/api/docs/{doc_id}").status_code == 404

    # Share as viewer: read yes, write no.
    r = share(alice, doc_id, "bob@ajaia.test", "viewer")
    assert r.status_code == 201 and r.json()["role"] == "viewer"
    assert bob.get(f"/api/docs/{doc_id}").json()["role"] == "viewer"
    assert bob.put(f"/api/docs/{doc_id}", json={"html": "<p>x</p>"}).status_code == 403

    # Upgrade to editor (same endpoint): write yes, delete and share no.
    assert share(alice, doc_id, "BOB@ajaia.test ", "editor").status_code == 201
    assert bob.put(f"/api/docs/{doc_id}", json={"html": "<p>edited</p>"}).status_code == 200
    assert bob.delete(f"/api/docs/{doc_id}").status_code == 403
    assert share(bob, doc_id, "carol@ajaia.test", "viewer").status_code == 403

    # Shows up under "shared", not "owned", for Bob; Carol still sees nothing.
    listing = bob.get("/api/docs").json()
    assert any(d["id"] == doc_id and d["role"] == "editor" for d in listing["shared"])
    assert all(d["id"] != doc_id for d in listing["owned"])
    assert carol.get(f"/api/docs/{doc_id}").status_code == 404

    # Owner sees the share list, then revokes.
    shares = alice.get(f"/api/docs/{doc_id}/shares").json()["shares"]
    assert [(s["email"], s["role"]) for s in shares] == [("bob@ajaia.test", "editor")]
    bob_id = shares[0]["user_id"]
    assert alice.delete(f"/api/docs/{doc_id}/shares/{bob_id}").status_code == 200
    assert bob.get(f"/api/docs/{doc_id}").status_code == 404


def test_share_validation(login_as):
    alice = login_as("alice@ajaia.test")
    doc_id = make_doc(alice)
    assert share(alice, doc_id, "nobody@ajaia.test", "viewer").status_code == 404
    assert share(alice, doc_id, "alice@ajaia.test", "viewer").status_code == 400  # self
    assert share(alice, doc_id, "bob@ajaia.test", "admin").status_code == 422  # bad role
    assert share(alice, doc_id, "   ", "viewer").status_code == 400


def test_strangers_cannot_see_or_manage_shares(login_as):
    alice = login_as("alice@ajaia.test")
    bob = login_as("bob@ajaia.test")
    doc_id = make_doc(alice)
    assert bob.get(f"/api/docs/{doc_id}/shares").status_code == 404
    assert share(bob, doc_id, "carol@ajaia.test", "viewer").status_code == 404
    assert bob.delete(f"/api/docs/{doc_id}/shares/1").status_code == 404


def test_deleting_document_removes_its_shares(login_as, _lifespan):
    from app import db

    alice = login_as("alice@ajaia.test")
    doc_id = make_doc(alice)
    share(alice, doc_id, "bob@ajaia.test", "viewer")
    alice.delete(f"/api/docs/{doc_id}")
    with db.pool.connection() as conn:
        n = conn.execute("SELECT count(*) AS n FROM shares WHERE document_id = %s", (doc_id,)).fetchone()["n"]
    assert n == 0