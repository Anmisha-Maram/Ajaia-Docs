# AI workflow note

## Tools
Claude, used in chat with file and shell tools, for planning, code, tests and documentation.

## Where AI sped things up
- Turning the open brief into a plan and a data model
- The file importers and the frontend
- Writing a large automated test suite (28 tests)

## What I changed or rejected
- A first version was built on Node and SQLite. I chose to move to Python and Postgres, and rebuilt it step by step.
- I rejected Docker for local Postgres because it was not installed on my machine, and used a direct Windows install.
- Postgres kept shutting down whenever I pressed Ctrl+C, because it was launched from the same terminal. I fixed this by starting it in its own hidden process.
- The tests were writing leftover documents into my real database. I added a separate test database and a test config that points to it.
- I decided against real-time collaboration and used version checks on saves instead.

## How I checked correctness
- Ran the automated tests after every step (28 passing).
- Tested the flow by hand in the browser: edit, refresh, share to a second account, upload files.
- Used two accounts side by side to check that viewers cannot write and strangers cannot see documents.
- Treated AI output as a draft: I ran it, read the errors, and fixed what broke instead of trusting it.
