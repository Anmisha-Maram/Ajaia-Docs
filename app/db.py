from pathlib import Path

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import settings

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "db" / "schema.sql"

pool: ConnectionPool | None = None


def open_pool(url: str | None = None) -> ConnectionPool:
    global pool
    pool = ConnectionPool(url or settings.database_url, min_size=1, max_size=5,
                          kwargs={"row_factory": dict_row}, open=True)
    pool.wait(timeout=15)
    return pool


def close_pool() -> None:
    global pool
    if pool is not None:
        pool.close()
        pool = None


def init_schema() -> None:
    with pool.connection() as conn:
        conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))


def get_conn():
    """FastAPI dependency: one pooled connection per request, committed on success."""
    with pool.connection() as conn:
        yield conn