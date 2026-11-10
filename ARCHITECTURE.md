# Architecture note

## Stack
- **Backend:** Python 3.12, FastAPI, plain `psycopg` (no ORM) with a connection pool
- **Database:** PostgreSQL (Neon for the live demo)
- **Editor:** Quill 2 in a vanilla JavaScript frontend served by FastAPI
- **Imports:** `mammoth` (.docx), `markdown` (.md), plain-text parser
- **Sanitizing:** `nh3` allow-list
- **Hosting:** Render (free web service) with Neon Postgres

## Data model
`users`, `sessions`, `documents` (owner, title, HTML, version), and `shares` (document, user, role of viewer or editor). The owner is the `owner_id` on the document. The schema is one idempotent SQL file applied on startup.

## Access rules in one place
`load_doc()` works out the caller's role (owner, editor, viewer) and enforces the minimum role an action needs. People with no access get a 404, so a document's existence isn't revealed. Collaborators without enough rights get a 403. Only the owner can share, revoke or delete.

## Key decisions
1. **Store HTML, sanitize on every write.** Imports from Markdown and Word already produce HTML, and the allow-list stops a collaborator from planting scripts that run in someone else's browser.
2. **Conflict detection instead of real-time editing.** Each save sends the version it started from, and the update only applies if the version still matches, so two saves can't silently overwrite each other.
3. **Seeded users, hashed passwords, cookie sessions.** No OAuth. It keeps the sharing flow easy to review without extra setup.
4. **Viewer and editor roles** instead of a plain share toggle, so the permission model is visible and testable.
5. **Plain SQL over an ORM** to keep the working version small and quick to build.
6. **A separate test database**, so automated tests never touch real data.

## Deliberately left out
Real-time co-editing, comments, version history, sign-up and password reset, richer formatting (fonts, colours, tables, images), and automated browser tests.

## With another 2 to 4 hours
Version history, Markdown export, a browser smoke test, bundling Quill instead of using a CDN, and monitoring plus backups for the hosted database.
