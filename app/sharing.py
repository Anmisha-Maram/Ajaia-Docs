from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from . import db
from .auth import current_user
from .docs import load_doc

router = APIRouter(prefix="/api/docs/{doc_id}/shares", tags=["sharing"])


class ShareBody(BaseModel):
    email: str
    role: Literal["viewer", "editor"]  # anything else is rejected with a 422


@router.get("")
def list_shares(doc_id: int, user=Depends(current_user), conn=Depends(db.get_conn)):
    load_doc(conn, doc_id, user, min_role="owner")
    shares = conn.execute(
        "SELECT u.id AS user_id, u.name, u.email, s.role FROM shares s "
        "JOIN users u ON u.id = s.user_id WHERE s.document_id = %s ORDER BY u.name",
        (doc_id,),
    ).fetchall()
    return {"shares": shares}


@router.post("", status_code=201)
def share_doc(doc_id: int, body: ShareBody, user=Depends(current_user), conn=Depends(db.get_conn)):
    """Grant access, or change the role if the person already has access."""
    doc, _ = load_doc(conn, doc_id, user, min_role="owner")
    email = body.email.strip().lower()
    if not email:
        raise HTTPException(400, "Enter an email to share with.")
    target = conn.execute(
        "SELECT id, name, email FROM users WHERE email = %s", (email,)
    ).fetchone()
    if not target:
        raise HTTPException(404, "No user with that email exists.")
    if target["id"] == doc["owner_id"]:
        raise HTTPException(400, "You already own this document.")
    conn.execute(
        "INSERT INTO shares (document_id, user_id, role) VALUES (%s, %s, %s) "
        "ON CONFLICT (document_id, user_id) DO UPDATE SET role = EXCLUDED.role",
        (doc_id, target["id"], body.role),
    )
    conn.commit()
    return {"user_id": target["id"], "name": target["name"], "email": target["email"], "role": body.role}


@router.delete("/{user_id}")
def revoke_share(doc_id: int, user_id: int, user=Depends(current_user), conn=Depends(db.get_conn)):
    load_doc(conn, doc_id, user, min_role="owner")
    conn.execute(
        "DELETE FROM shares WHERE document_id = %s AND user_id = %s", (doc_id, user_id)
    )
    conn.commit()
    return {"ok": True}