from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from . import auth, db, docs, sharing, uploads
from .seed import seed_users


@asynccontextmanager
async def lifespan(_app: FastAPI):
    pool = db.open_pool()
    db.init_schema()
    with pool.connection() as conn:
        seed_users(conn)
    yield
    db.close_pool()


app = FastAPI(title="Ajaia Docs", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(docs.router)
app.include_router(sharing.router)
app.include_router(uploads.router)


@app.get("/api/health")
def health(conn=Depends(db.get_conn)):
    conn.execute("SELECT 1")
    return {"status": "ok", "database": "connected"}


STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")