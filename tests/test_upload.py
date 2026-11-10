import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.seed import DEMO_PASSWORD


@pytest.fixture(scope="module")
def alice():
    with TestClient(app) as c:
        assert c.post("/api/login", json={"email": "alice@ajaia.test", "password": DEMO_PASSWORD}).status_code == 200
        yield c


def upload(client, name, content):
    return client.post("/api/import", files={"file": (name, content)})


def test_requires_login():
    with TestClient(app) as c:
        assert upload(c, "a.txt", b"hi").status_code == 401


def test_txt_becomes_document_with_escaped_paragraphs(alice):
    r = upload(alice, "notes.txt", b"First para\n\nSecond <b>para</b>")
    assert r.status_code == 201
    assert r.json()["title"] == "notes"
    doc = alice.get(f"/api/docs/{r.json()['id']}").json()
    assert doc["html"] == "<p>First para</p><p>Second &lt;b&gt;para&lt;/b&gt;</p>"


def test_markdown_becomes_formatted_document(alice):
    r = upload(alice, "readme.md", b"# Hello\n\n- one\n- two\n\n**bold**")
    doc = alice.get(f"/api/docs/{r.json()['id']}").json()
    assert "<h1>Hello</h1>" in doc["html"]
    assert "<ul>" in doc["html"] and "<strong>bold</strong>" in doc["html"]


def test_markdown_scripts_are_sanitized(alice):
    r = upload(alice, "evil.md", b"hi <script>alert(1)</script> [x](javascript:alert(1))")
    html = alice.get(f"/api/docs/{r.json()['id']}").json()["html"]
    assert "script" not in html and "javascript:" not in html


def test_docx_is_converted(alice):
    # Build a minimal valid .docx in memory (no Word needed).
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        z.writestr("_rels/.rels",
            '<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        z.writestr("word/document.xml",
            '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>'
            '<w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Hello docx</w:t></w:r></w:p></w:body></w:document>')
    r = upload(alice, "report.docx", buf.getvalue())
    assert r.status_code == 201
    html = alice.get(f"/api/docs/{r.json()['id']}").json()["html"]
    assert "<strong>Hello docx</strong>" in html


def test_rejections(alice):
    assert upload(alice, "evil.exe", b"MZ").status_code == 415
    assert upload(alice, "noext", b"hi").status_code == 415
    assert upload(alice, "broken.docx", b"not a zip").status_code == 415
    assert alice.post("/api/import").status_code == 400
    assert upload(alice, "big.txt", b"x" * (2 * 1024 * 1024 + 1)).status_code == 413


def test_config_lists_supported_types(alice):
    cfg = alice.get("/api/config").json()
    assert cfg["supportedUploads"] == [".txt", ".md", ".docx"]