# Ajaia Docs

A lightweight collaborative document editor: rich-text editing, file import, and sharing with editor/viewer roles. Python (FastAPI) + Postgres + Quill.

**Live demo:** https://ajaia-docs-wyqi.onrender.com (free hosting, so the first load after a quiet period can take up to a minute)

## Run locally

Requires Python 3.12 and a running Postgres.

1. Create two databases, `ajaia` and `ajaia_test` (the tests use the second so they never touch real data), and a user that owns them.
2. Copy `.env.example` to `.env` and set `DATABASE_URL` to your `ajaia` database.
3. Install and start:
   ```
   python -m venv .venv
   .venv\Scripts\activate        # macOS/Linux: source .venv/bin/activate
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```
4. Open http://localhost:8000. Tables and demo users are created on startup.
5. Run the tests: `pytest`

The editor loads Quill from a CDN, so an internet connection is needed.

## Test accounts

`alice@ajaia.test`, `bob@ajaia.test`, `carol@ajaia.test`. The password for all three is `ajaia-demo`.

To try sharing: sign in as Alice, create a document, click Share, add `carol@ajaia.test` as "Can view", then sign in as Carol. The document appears under "Shared with me" and is read-only.

## Features

- Create, rename, edit, autosave and delete documents (bold, italic, underline, headings, bulleted and numbered lists)
- Upload `.txt`, `.md` or `.docx` (max 2 MB) to create a new editable document
- Share by email as editor or viewer, change the role, or revoke access; the dashboard separates owned and shared documents
- Postgres persistence; content is sanitized with an allow-list on every save
- Edit-conflict detection (a stale save is rejected instead of overwriting someone else's work)
- 28 automated tests

## Not included

Real-time co-editing, comments, version history, sign-up and password reset, and deployment.

## Layout

- `app/` FastAPI app (auth, documents, sharing, uploads, sanitizing)
- `db/schema.sql` database schema
- `static/` browser app
- `tests/` pytest suite
