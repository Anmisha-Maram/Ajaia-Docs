from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from . import db
from .security import new_session_token, verify_password

router = APIRouter(prefix="/api", tags=["auth"])

COOKIE_NAME = "session"
SESSION_SECONDS = 7 * 24 * 3600


class LoginBody(BaseModel):
    email: str
    password: str


def current_user(request: Request, conn=Depends(db.get_conn)) -> dict:
    """Dependency: the signed-in user, or a 401."""
    token = request.cookies.get(COOKIE_NAME)
    user = None
    if token:
        user = conn.execute(
            "SELECT u.id, u.email, u.name FROM sessions s "
            "JOIN users u ON u.id = s.user_id WHERE s.token = %s",
            (token,),
        ).fetchone()
    if not user:
        raise HTTPException(status_code=401, detail="Please sign in.")
    return user


@router.post("/login")
def login(body: LoginBody, response: Response, conn=Depends(db.get_conn)):
    email = body.email.strip().lower()
    row = conn.execute("SELECT * FROM users WHERE email = %s", (email,)).fetchone()
    # Same message for unknown email and wrong password, so accounts can't be probed.
    if not row or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    token = new_session_token()
    conn.execute("INSERT INTO sessions (token, user_id) VALUES (%s, %s)", (token, row["id"]))
    conn.commit()  # commit before responding so the very next request can see the session
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", max_age=SESSION_SECONDS)
    return {"id": row["id"], "email": row["email"], "name": row["name"]}


@router.post("/logout")
def logout(request: Request, response: Response, conn=Depends(db.get_conn)):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        conn.execute("DELETE FROM sessions WHERE token = %s", (token,))
        conn.commit()
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.get("/me")
def me(user=Depends(current_user)):
    return user