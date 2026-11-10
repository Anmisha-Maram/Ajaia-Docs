"""Turn an uploaded file into sanitized editor HTML."""
import html as html_lib
import io
import re
from pathlib import PurePath

import mammoth
import markdown

from .sanitize import clean_html

SUPPORTED = (".txt", ".md", ".docx")


class UnsupportedFile(Exception):
    pass


def _text_to_html(text: str) -> str:
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text.replace("\r\n", "\n")) if p.strip()]
    return "".join(
        "<p>" + html_lib.escape(p).replace("\n", "<br>") + "</p>" for p in paragraphs
    )


def import_file(filename: str, data: bytes) -> tuple[str, str]:
    """Return (title, sanitized_html). Raises UnsupportedFile for bad types or unreadable files."""
    path = PurePath(filename or "")
    ext = path.suffix.lower()
    if ext not in SUPPORTED:
        raise UnsupportedFile(
            f'Unsupported file type "{ext or "unknown"}". Supported: {", ".join(SUPPORTED)}'
        )
    if ext == ".txt":
        html = _text_to_html(data.decode("utf-8", errors="replace"))
    elif ext == ".md":
        html = markdown.markdown(data.decode("utf-8", errors="replace"))
    else:
        try:
            html = mammoth.convert_to_html(io.BytesIO(data)).value
        except Exception as exc:
            raise UnsupportedFile("Could not read this .docx file. It may be corrupted.") from exc
    title = (path.stem or "Imported document")[:120]
    return title, clean_html(html)
