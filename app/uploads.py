from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from . import db
from .auth import current_user
from .config import settings
from .importers import SUPPORTED, UnsupportedFile, import_file

router = APIRouter(prefix="/api", tags=["upload"])


@router.get("/config")
def config():
    return {"supportedUploads": list(SUPPORTED), "maxUploadMb": settings.max_upload_bytes // (1024 * 1024)}


@router.post("/import", status_code=201)
async def import_document(
    file: UploadFile | None = File(None),
    user=Depends(current_user),
    conn=Depends(db.get_conn),
):
    if file is None or not file.filename:
        raise HTTPException(400, f"Choose a file to upload ({', '.join(SUPPORTED)}).")
    data = await file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(413, f"File is too large (max {settings.max_upload_bytes // (1024 * 1024)} MB).")
    try:
        title, html = import_file(file.filename, data)
    except UnsupportedFile as exc:
        raise HTTPException(415, str(exc)) from exc
    row = conn.execute(
        "INSERT INTO documents (owner_id, title, html) VALUES (%s, %s, %s) RETURNING id, title",
        (user["id"], title, html),
    ).fetchone()
    conn.commit()
    return row