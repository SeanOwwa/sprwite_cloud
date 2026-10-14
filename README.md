# Spwrite Cloud

A full-stack web application for long-form fiction writers (novels), built in
Python. Spwrite gives writers a focused manuscript editor with a project-based
structure (projects → folders → documents) and is being built with planned
AI-assisted writing features.

> Status: early development. The data layer, service layer, and specs are in
> place; the API and editor UI are in progress.

---

## Tech Stack

| Area | Technology |
|------|------------|
| Language | Python 3.12+ |
| Web framework / server | FastAPI (ASGI), Uvicorn |
| UI | NiceGUI (Python-driven web UI, mounted on FastAPI) |
| ORM / models | SQLModel (on top of SQLAlchemy) |
| Database | SQLite (local dev) → PostgreSQL / Supabase (production) |
| HTTP client (UI → API) | httpx (async) |
| Testing | pytest |
| Config | python-dotenv (`.env`) |

---

## Architecture

Spwrite is a **layered modular monolith**. The guiding principle is a clean,
one-way flow that is easy to debug: each layer has a single responsibility and
only depends on the layer below it.

```
┌───────────────────────────────────────────────────────────┐
│  UI  (NiceGUI)              src/ui/                         │
│  Renders pages, handles input, talks to the API over HTTP.  │
│  No DB access, no business logic.                           │
├───────────────────────────────────────────────────────────┤
│  API (FastAPI)             src/api/                         │
│  HTTP endpoints: validate input, call services, return JSON.│
│  No direct DB access.                                        │
├───────────────────────────────────────────────────────────┤
│  Services                  src/services/                   │
│  ALL business logic + ALL database access.                  │
│  The single source of truth for reading/writing data.       │
├───────────────────────────────────────────────────────────┤
│  Models                    src/models/                     │
│  SQLModel table definitions + shared BaseModel.             │
├───────────────────────────────────────────────────────────┤
│  Core                      src/core/                       │
│  Engine, session, configuration (database.py).              │
└───────────────────────────────────────────────────────────┘
```

**Dependency direction (one-way):**

```
UI ──HTTP──> API ──calls──> Services ──uses──> Models ──> Core (DB)
```

### Why it's structured this way
- **Only the service layer touches the database.** Any data-correctness bug is
  isolated to one layer.
- **The UI only speaks HTTP** to the API, so the frontend is decoupled and could
  be replaced (e.g. with a separate JS frontend) without touching business logic.
- **Portable database.** The database is chosen via a single `DATABASE_URL`
  environment variable, so switching SQLite → PostgreSQL/Supabase is a one-line
  change with no code edits.

### Project layout

```
spwrite_cloud/
├── app.py                       # Entry point: FastAPI app + NiceGUI mount
├── src/
│   ├── core/
│   │   └── database.py          # Engine, session, create_db_and_tables()
│   ├── models/
│   │   ├── based_model.py       # BaseModel: shared audit fields (abstract)
│   │   └── project_model.py     # Project, Folder, Document
│   ├── services/
│   │   └── project_service.py   # ProjectService: all DB logic
│   ├── api/
│   │   ├── router.py            # Aggregates route modules
│   │   └── routes/
│   │       └── project_api.py   # Project/folder/document endpoints
│   └── ui/
│       └── pages/
│           ├── dashboard.py     # Project list
│           └── editor.py        # Manuscript editor + sidebar
├── test/                        # pytest tests
├── specs/                       # Spec, design, and task documents
├── requirements.txt
├── .example.env                 # Template for your local .env
└── .env                         # Your local config (gitignored)
```

---

## Data Model

```
Project
 ├── Folder        (proj_id)
 │     └── Document (proj_id, fold_id)
 └── Document       (proj_id, fold_id = NULL  → loose, directly in the project)
```

- A **Project** is a novel.
- A **Folder** groups documents within a project.
- A **Document** holds the written text. It can live **inside a folder**
  (`fold_id` set) or **loose at the project level** (`fold_id` is `NULL`).

All tables inherit a shared `BaseModel` with audit fields: `id`, `created`,
`updated`, `created_by`, `updated_by`, `version`, `is_del` (soft delete).
Orderable items (`Folder`, `Document`) also carry a `position` field.

---

## Getting Started (Developers)

### Prerequisites
- Python 3.12 or newer
- `pip` and `venv`

### 1. Fork the repository
Click **Fork** (top-right on GitHub) to create your own copy under your account.
Contributors work from their fork, not the main repository.

### 2. Clone your fork
```bash
git clone https://github.com/<your-username>/spwrite_cloud.git
cd spwrite_cloud
```

### 3. Add the upstream remote
Point `upstream` at the original repo so you can pull in the latest changes:
```bash
git remote add upstream https://github.com/<original-owner>/spwrite_cloud.git
git remote -v   # verify: origin = your fork, upstream = original
```
Keep your fork up to date later with:
```bash
git fetch upstream
git checkout main
git merge upstream/main
```

### 4. Create and activate a virtual environment
```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 5. Install dependencies
```bash
pip install -r requirements.txt
```

### 6. Configure environment
Copy the example env file and adjust if needed:
```bash
cp .example.env .env
```
Default `.env` contents (local SQLite):
```
DATABASE_URL="sqlite:///spwrite.db"
API_BASE_URL="http://127.0.0.1:8000/api"
```
> To use PostgreSQL/Supabase later, change `DATABASE_URL` only — no code changes.
> Example: `postgresql+psycopg://USER:PASSWORD@HOST:5432/postgres`

### 7. Run the app
```bash
python -m uvicorn app:app --reload
```
Then open:
- App (NiceGUI): http://127.0.0.1:8000/
- API docs (Swagger UI): http://127.0.0.1:8000/docs

The database tables are created automatically on startup via
`create_db_and_tables()`.

### 8. Run the tests
```bash
pytest -v
```

---

## Development Notes

- **Add business logic in the service layer** (`src/services/`), never in the UI
  or directly in an API route. The UI and API call services.
- **Every query must filter soft-deleted rows** (`is_del == False`).
- **Use `fold_id.is_(None)`** for NULL checks in queries, not `== None`.
- **Keep the UI decoupled**: pages fetch from the API over HTTP (async `httpx`),
  they do not import models or query the database directly.
- **Database schema changes**: during development, delete `spwrite.db` and let it
  recreate (`create_db_and_tables()` does not alter existing tables). Use a
  migration tool (e.g. Alembic) once there is real data.

---

## Specs & Design

Planning documents live in `specs/`:
- `sidebar_spec.md` — feature requirements and architecture (what/why)
- `sidebar_design.md` — technical design (how)
- `sidebar_tasks.md` — implementation task checklist

---

## Contributing

See the GitHub Project board and issues for available tasks. Each task is a
small, self-contained unit of work. When picking one up:
1. Create a branch from `main`.
2. Follow the architecture rules in **Development Notes**.
3. Add/update tests in `test/`.
4. Open a pull request referencing the issue.
