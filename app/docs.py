from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from . import db
from .auth import current_user
from .sanitize import clean_html

router = APIRouter(prefix="/api/docs", tags=["documents"])

MAX_TITLE = 120
MAX_HTML = 1_000_000
ROLE_RANK = {"viewer": 1, "editor": 2, "owner": 3}


class CreateDoc(BaseModel):
    title: str | None = None


class UpdateDoc(BaseModel):
    title: str | None = None
    html: str | None = None
    base_version: int | None = None


def validate_title(title: str) -> str:
    title = title.strip()
    if not title:
        raise HTTPException(400, "Title cannot be empty.")
    if len(title) > MAX_TITLE:
        raise HTTPException(400, f"Title must be at most {MAX_TITLE} characters.")
    return title


def load_doc(conn, doc_id: int, user: dict, min_role: str = "viewer") -> tuple[dict, str]:
    """Return (document, caller's role) or raise.

    404 for people with no access at all, so a document's existence isn't leaked;
    403 for collaborators who lack the required role.
    """
    doc = conn.execute(
        "SELECT d.*, o.name AS owner_name, o.email AS owner_email "
        "FROM documents d JOIN users o ON o.id = d.owner_id WHERE d.id = %s",
        (doc_id,),
    ).fetchone()
    if not doc:
        raise HTTPException(404, "Document not found.")
    if doc["owner_id"] == user["id"]:
        role = "owner"
    else:
        share = conn.execute(
            "SELECT role FROM shares WHERE document_id = %s AND user_id = %s",
            (doc_id, user["id"]),
        ).fetchone()
        if not share:
            raise HTTPException(404, "Document not found.")
        role = share["role"]
    if ROLE_RANK[role] < ROLE_RANK[min_role]:
        raise HTTPException(403, "You do not have permission to do that.")
    return doc, role


@router.get("")
def list_docs(user=Depends(current_user), conn=Depends(db.get_conn)):
    owned = conn.execute(
        "SELECT d.id, d.title, d.updated_at, u.name AS owner_name, u.email AS owner_email, "
        "'owner' AS role FROM documents d JOIN users u ON u.id = d.owner_id "
        "WHERE d.owner_id = %s ORDER BY d.updated_at DESC, d.id DESC",
        (user["id"],),
    ).fetchall()
    shared = conn.execute(
        "SELECT d.id, d.title, d.updated_at, u.name AS owner_name, u.email AS owner_email, "
        "s.role AS role FROM shares s JOIN documents d ON d.id = s.document_id "
        "JOIN users u ON u.id = d.owner_id WHERE s.user_id = %s "
        "ORDER BY d.updated_at DESC, d.id DESC",
        (user["id"],),
    ).fetchall()
    return {"owned": owned, "shared": shared}


@router.post("", status_code=201)
def create_doc(body: CreateDoc, user=Depends(current_user), conn=Depends(db.get_conn)):
    title = validate_title(body.title) if body.title is not None else "Untitled document"
    row = conn.execute(
        "INSERT INTO documents (owner_id, title) VALUES (%s, %s) RETURNING id, title",
        (user["id"], title),
    ).fetchone()
    conn.commit()
    return row


@router.get("/{doc_id}")
def get_doc(doc_id: int, user=Depends(current_user), conn=Depends(db.get_conn)):
    doc, role = load_doc(conn, doc_id, user)
    return {
        "id": doc["id"], "title": doc["title"], "html": doc["html"],
        "version": doc["version"], "updated_at": doc["updated_at"],
        "owner_name": doc["owner_name"], "owner_email": doc["owner_email"], "role": role,
    }


@router.put("/{doc_id}")
def update_doc(doc_id: int, body: UpdateDoc, user=Depends(current_user), conn=Depends(db.get_conn)):
    doc, _ = load_doc(conn, doc_id, user, min_role="editor")
    if body.title is None and body.html is None:
        raise HTTPException(400, "Nothing to update.")
    title = validate_title(body.title) if body.title is not None else doc["title"]
    html = doc["html"]
    if body.html is not None:
        if len(body.html) > MAX_HTML:
            raise HTTPException(400, "Content is too large.")
        html = clean_html(body.html)

    # Optimistic locking: the version check is part of the UPDATE itself, so two
    # simultaneous saves can't both succeed.
    sql = (
        "UPDATE documents SET title = %s, html = %s, version = version + 1, "
        "updated_at = now() WHERE id = %s"
    )
    params = [title, html, doc_id]
    if body.base_version is not None:
        sql += " AND version = %s"
        params.append(body.base_version)
    row = conn.execute(sql + " RETURNING version, title", params).fetchone()
    if not row:
        conn.rollback()
        raise HTTPException(409, "This document was changed by someone else. Reload to get the latest version.")
    conn.commit()
    return row


@router.delete("/{doc_id}")
def delete_doc(doc_id: int, user=Depends(current_user), conn=Depends(db.get_conn)):
    load_doc(conn, doc_id, user, min_role="owner")
    conn.execute("DELETE FROM documents WHERE id = %s", (doc_id,))
    conn.commit()
    return {"ok": True}
