# Submission

**Live app:** https://ajaia-docs-wyqi.onrender.com (free hosting; the first load after a quiet period can take up to a minute)
**Code:** https://github.com/Anmisha-Maram/Ajaia-Docs

## Included
| Item | File or location |
|---|---|
| Source code | `app/`, `static/`, `db/`, `tests/` |
| Setup and run instructions | `README.md` |
| Architecture note | `ARCHITECTURE.md` |
| AI workflow note | `AI_WORKFLOW.md` |
| Video link | `VIDEO_URL.txt` |

## Test accounts
`alice@ajaia.test`, `bob@ajaia.test`, `carol@ajaia.test`. Password for all: `ajaia-demo`.
To see sharing: sign in as Alice, create a document, click Share, add Carol as "Can view", then sign in as Carol.

## Status
**Working:** create, rename, edit, autosave, reopen and delete documents; bold, italic, underline, headings, bulleted and numbered lists; .txt/.md/.docx upload; sharing as editor or viewer with revoke; owned vs shared lists; Postgres persistence; validation and error handling; 28 automated tests; live deployment.

**Not included:** real-time co-editing, comments, version history, sign-up and password reset.

**Next with 2 to 4 more hours:** version history, Markdown export, a browser smoke test, bundling Quill locally.
