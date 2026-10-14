# Sidebar Spec — Folders & Documents (with Drag & Drop)

Feature spec for the editor sidebar: create folders and documents, list them
together inside a project, and reorder / move them by drag and drop. Includes
the shared base model and the project architecture.

---

## 1. Goal

Give the writer a sidebar (left drawer) in the editor that shows the current
project's contents as a navigable, **reorderable** tree, with buttons to create
folders and documents.

**Core behaviors requested:**
- A **"New Folder"** button that creates a folder in the project.
- A **"New Document"** button that creates a document.
- Folders and loose documents are **listed together** at the top level (like a
  file explorer).
- Documents can live **inside a folder** or **loose at the project level**.
- **Drag and drop:**
  - A **folder** can be dragged up/down to reorder it in the top-level list.
  - A **document** can be dragged:
    - up/down to reorder within its current container,
    - **into** a folder (becomes a child of that folder),
    - **out of** a folder (becomes a loose, project-level document),
    - from one folder **into another** folder.

---

## 2. Architecture

The architecture is a **layered modular monolith**. The guiding principle is
**easy to debug**: each layer has one responsibility, data flows in one
direction, and a bug can be isolated to a single layer quickly.

### 2.1 Layers & responsibilities

```
┌──────────────────────────────────────────────────────────────┐
│  UI (NiceGUI)            src/ui/pages/                         │
│  - Renders pages, handles clicks/drag events                  │
│  - Talks to the backend over HTTP (httpx, async)              │
│  - NO database access, NO business logic                      │
├──────────────────────────────────────────────────────────────┤
│  API (FastAPI)           src/api/routes/                      │
│  - HTTP endpoints: validate input, map to service calls       │
│  - Returns consistent JSON envelopes                          │
│  - NO database access directly — calls services               │
├──────────────────────────────────────────────────────────────┤
│  Services                src/services/                        │
│  - ALL business logic + ALL database access                  │
│  - The single source of truth for how data is read/written    │
│  - Reusable by API now, by batch/ML jobs later                │
├──────────────────────────────────────────────────────────────┤
│  Models                  src/models/                          │
│  - SQLModel table definitions + shared BaseModel              │
│  - Pure data shape, no logic                                  │
├──────────────────────────────────────────────────────────────┤
│  Core                    src/core/                            │
│  - Engine, session, config (database.py)                      │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 Dependency direction (one-way)

```
UI ──HTTP──> API ──calls──> Services ──uses──> Models ──> Core(DB)
```

A layer may only depend on the layer below it. The UI never imports a model or
a service directly; the API never runs a query itself. This one-way flow is what
makes bugs easy to locate.

### 2.3 Why this is easy to debug

| Symptom | Where to look first |
|---------|---------------------|
| Wrong data on screen, correct in DB | UI layer (rendering / fetch) |
| API returns wrong JSON | API route (mapping) or the service it calls |
| Data saved wrong / query wrong | Service layer (the only place with DB code) |
| Table/column error on startup | Models / `create_db_and_tables` |
| Can't connect to DB | Core (`database.py`, `.env`) |

Because **only services touch the database**, any data correctness bug lives in
one layer. Because the **UI only speaks HTTP**, UI bugs can't corrupt data.

### 2.4 Conventions that aid debugging

- **Consistent response envelope** from every endpoint:
  ```json
  { "success": true,  "data": ... }
  { "success": false, "error": "message" }
  ```
- **Centralized error handling** via FastAPI `HTTPException` with clear status
  codes (400 validation, 404 not found, 409 conflict/version).
- **Request/action logging** in the service layer (what was created/moved and
  the resulting ids) so a trace of actions is visible in server output.
- **Read schemas (DTOs)** so the UI never depends on table internals (see §6.3).
- **No business logic in the UI** — the UI is replaceable (NiceGUI today, could
  be React later) without touching logic.

---

## 3. Data Model

### 3.1 Shared base model (`src/models/based_model.py`)

A reusable `BaseModel` holds the **audit / metadata** columns every table should
have. It is **abstract** — NO `table=True`. Only concrete models inherit it.

| Field | Type | Purpose |
|-------|------|---------|
| `id` | `int \| None` (PK) | Primary key |
| `created` | `datetime` | Set on insert (UTC) |
| `updated` | `datetime` | Last-modified time (bumped by the service layer on update) |
| `created_by` | `int \| None` | User who created the row — nullable until auth exists |
| `updated_by` | `int \| None` | User who last updated the row — nullable until auth exists |
| `version` | `int` | Optimistic-locking counter; increment on each update |
| `is_del` | `bool` | Soft-delete flag; queries must filter `is_del == False` |

```python
# src/models/based_model.py
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class BaseModel(SQLModel):          # NO table=True — abstract parent
    id: int | None = Field(default=None, primary_key=True)
    created: datetime = Field(default_factory=utcnow)
    updated: datetime = Field(default_factory=utcnow)
    created_by: int | None = Field(default=None)
    updated_by: int | None = Field(default=None)
    version: int = Field(default=1)
    is_del: bool = Field(default=False)
```

**Why `position` is NOT in `BaseModel`:** ordering is not general metadata. It
applies only to items in an ordered list (folders, documents). Putting it in the
base would force it onto every future table (users, settings, …) where it is
meaningless. So `position` is declared on the orderable models only.

**Cautions:**
- `updated`/`version` only auto-set on INSERT via defaults. To bump them on every
  change, update them explicitly in the service layer (or add SQLAlchemy
  `onupdate`).
- Soft delete means **every query must filter `is_del == False`** or deleted rows
  reappear.
- Adding these columns changes the schema → delete `spwrite.db` and let it
  recreate during development (Alembic migrations later, once there's real data).

### 3.2 Concrete models (`src/models/project_model.py`)

All inherit `BaseModel` (get `id` + audit fields for free).

| Model | Own fields (beyond BaseModel) | Meaning |
|-------|-------------------------------|---------|
| `Project` | `title, author, cover` | A novel — **no `position`** |
| `Folder` | `proj_id, name, position` | Folder; `position` = order at top level |
| `Document` | `proj_id, fold_id (nullable), name, written_text, position` | Document; `position` = order within container |

```python
class Project(BaseModel, table=True):
    title: str
    author: str
    cover: str | None = None
    # relationships...
    # NOTE: no position — a project is not an item in an ordered list

class Folder(BaseModel, table=True):
    proj_id: int = Field(foreign_key="project.id")
    name: str
    position: int = Field(default=0)   # order within the project top level
    # relationships...

class Document(BaseModel, table=True):
    proj_id: int = Field(foreign_key="project.id")
    fold_id: int | None = Field(default=None, foreign_key="folder.id")
    name: str
    written_text: str = Field(default="", sa_column=Column(Text))
    position: int = Field(default=0)   # order within its container
    # relationships...
```

**Container rule:**
- `Document.fold_id = None` → loose (directly in the project).
- `Document.fold_id = <folder id>` → inside that folder.

**Meaning of `position`** (scoped to a container):
- Folder → order among top-level items.
- Loose document → order among top-level items.
- Document in a folder → order among that folder's documents.

### 3.3 Required change summary

- **New file** `src/models/based_model.py` with `BaseModel`.
- `Project`, `Folder`, `Document` inherit `BaseModel` and drop their own `id`.
- Add `position` to `Folder` and `Document` only.
- `table=True` on the three concrete models; never on `BaseModel`.
- Recreate `spwrite.db`.

---

## 4. Sidebar Layout

```
┌──────────────────────────────┐
│  SPWRITE APP            [≡]   │
├──────────────────────────────┤
│  [+ New Folder] [+ New Doc]   │
├──────────────────────────────┤
│  ⠿ 📁 Act One            ▸    │   ← drag handle, folder (expandable)
│      ⠿ 📄 Opening Scene       │   ← doc inside folder (draggable)
│      ⠿ 📄 Inciting Incident   │
│  ⠿ 📁 Act Two                 │   ← empty folder still shown
│  ⠿ 📄 Loose Ideas             │   ← loose doc (draggable in/out)
│  ⠿ 📄 Character Notes         │
├──────────────────────────────┤
│  ‹ Back to Dashboard          │
└──────────────────────────────┘
```

`⠿` = drag handle. Dropping a doc onto a folder row drops it *into* that folder;
dropping at the top level makes it loose.

**Top-level ordering (v1 decision):** folders first (by `position`), then loose
documents (by `position`). Drag-reorder happens within each group. Interleaving
folders and loose docs in one shared order is a future enhancement.

---

## 5. Which project is loaded?

Editor route takes the project id as a query parameter:

```
/editor_page?project_id=1
```

- Dashboard cards link here with the clicked project's id.
- Editor reads `project_id`, loads that project's tree.
- Missing/invalid id → empty state or redirect to dashboard.

---

## 6. Backend / API

Logic in **services**, exposed via **FastAPI**, UI fetches over HTTP (async).

### 6.1 Service functions (`src/services/project_service.py`)

```
create_folder(proj_id, name) -> Folder
create_document(proj_id, name, fold_id=None) -> Document
get_project_tree(proj_id) -> ProjectTree

# drag & drop
move_document(doc_id, fold_id: int | None, position: int) -> Document
reorder_folder(folder_id, position: int) -> Folder
```

- `get_project_tree`: folders (each with ordered documents) + loose documents,
  all filtered `is_del == False`, ordered by `position`. Use `selectinload` so
  empty folders are included. Use `Document.fold_id.is_(None)` for the NULL check
  — never `== None`.
- `move_document`: set new `fold_id` (null = project level) + new `position`, then
  **renumber siblings** in affected container(s) (see §7.3). Bump `updated`/`version`.
- `reorder_folder`: set new top-level `position`, renumber other folders.

### 6.2 Endpoints (`src/api/routes/project_api.py`)

| Method | Path | Body / Params | Purpose |
|--------|------|---------------|---------|
| `GET`  | `/api/project/tree/{project_id}` | path | Return ordered project tree |
| `POST` | `/api/project/{project_id}/folder` | `{ "name": str }` | Create folder |
| `POST` | `/api/project/{project_id}/document` | `{ "name": str, "fold_id": int\|null }` | Create document |
| `PATCH`| `/api/document/{doc_id}/move` | `{ "fold_id": int\|null, "position": int }` | Move/reorder document |
| `PATCH`| `/api/folder/{folder_id}/reorder` | `{ "position": int }` | Reorder folder |

PATCH for move/reorder (partial update of an existing resource) = correct REST.

### 6.3 Read schemas / DTOs (for decoupling + stable debugging)

```
DocumentRead  { id, name, fold_id, position }
FolderRead    { id, name, position, documents: list[DocumentRead] }
ProjectTree   { folders: list[FolderRead], loose_documents: list[DocumentRead] }
```

The UI consumes these shapes, not the table models.

```json
// GET tree
{
  "success": true,
  "data": {
    "folders": [
      { "id": 1, "name": "Act One", "position": 0,
        "documents": [ { "id": 10, "name": "Opening Scene", "fold_id": 1, "position": 0 } ] }
    ],
    "loose_documents": [ { "id": 20, "name": "Loose Ideas", "fold_id": null, "position": 0 } ]
  }
}

// create / move / reorder
{ "success": true, "message": "...", "id": 5 }
```

---

## 7. Drag & Drop Behavior

### 7.1 Frontend (NiceGUI)
- Sortable list for the top level (folders + loose docs) and a sortable list
  inside each folder (Sortable.js-style drop events via NiceGUI's `on`).
- On drop, the UI computes `{ fold_id, position }` and calls the matching PATCH
  endpoint, then refreshes the tree.

### 7.2 The four document moves (all via `move_document`)
| Action | Resulting call |
|--------|----------------|
| Reorder within same container | `fold_id` unchanged, new `position` |
| Loose doc → into a folder | `fold_id = <folder>`, `position` = drop index |
| Doc → out of a folder | `fold_id = null`, `position` = drop index at top level |
| Doc → folder A to folder B | `fold_id = <B>`, `position` = drop index |

### 7.3 Position renumbering (keeps debugging sane)
After any move:
1. Determine the target container (folder id or "top level").
2. Insert the moved item at the drop index.
3. **Renumber** that container's items `0,1,2,…` and persist.
4. If the item left another container, renumber the source container too.

Gap-free integer renumbering avoids drift and makes stored order trivial to
inspect while debugging.

### 7.4 Constraints
- A folder cannot be dropped **inside** another folder (model is one level deep).
- A document belongs to exactly one folder or the top level.

---

## 8. UI Behavior (`src/ui/pages/editor.py`)

1. On load: read `project_id`, fetch tree via `GET /api/project/tree/{id}`
   (async + `httpx`), render create buttons + sortable tree. Replace the current
   hardcoded "Project" / "Chapter 1" buttons.
2. **New Folder** → dialog with name input → `POST .../folder` → refresh tree.
3. **New Document** → dialog with name input (+ optional target folder, default
   loose) → `POST .../document` → refresh tree.
4. **Drag/drop** → on drop, PATCH move/reorder → refresh tree.
5. **Click a document** → load its `written_text` into the editor (later spec).
6. Wrap tree rendering in `@ui.refreshable`; call `tree.refresh()` after any
   create/move so the sidebar updates without a full page reload.

---

## 9. Rules & Edge Cases

| Case | Expected behavior |
|------|-------------------|
| Empty project | "No folders or documents yet." |
| Empty folder | Still shown, expandable, valid drop target |
| Blank name on create | Reject with validation; no API call |
| Duplicate names | Allowed (names not unique) in v1 |
| Missing/invalid `project_id` | Empty state or redirect |
| Drop onto same spot | No-op (or harmless renumber) |
| Soft-deleted items (`is_del`) | Excluded from the tree |
| Top-level ordering | Folders first (by position), then loose docs |

---

## 10. Out of Scope (future specs)

- Editing/saving document content (the writing + autosave flow)
- Renaming / deleting folders and documents (soft delete via `is_del`)
- **Nested folders** (folders inside folders) — would need `parent_id` on `Folder`
- Interleaving folders and loose docs in one shared order
- Per-user ownership / auth (activates `created_by` / `updated_by`)
- Optimistic-locking enforcement using `version`
- Multi-user concurrent reordering

---

## 11. Build Order (suggested)

1. **Base model:** create `src/models/based_model.py` (`BaseModel`).
2. **Models:** inherit `BaseModel`, drop per-model `id`, add `position` to
   `Folder`/`Document`. Recreate `spwrite.db`. Update tests for audit/order fields.
3. **Services:** `create_folder`, `create_document`, `get_project_tree` (ordered,
   `is_del` filtered), `move_document`, `reorder_folder` (with renumbering).
   Fix the half-written `get_project_tree` endpoint.
4. **API:** tree + create + PATCH move/reorder, tested in `/docs`.
5. **Editor reads `project_id`** from the query string.
6. **Render ordered tree** (replace hardcoded buttons).
7. **Create buttons + dialogs** wired to POST endpoints.
8. **Drag & drop** wired to PATCH endpoints.
9. **`@ui.refreshable`** so the sidebar updates after any change.

---

## 12. Acceptance Criteria

- [ ] `BaseModel` exists; `Project`/`Folder`/`Document` inherit it; `position`
      only on `Folder`/`Document`.
- [ ] `/editor_page?project_id=X` shows that project's folders and loose docs in
      saved order.
- [ ] Folders show nested documents in order; empty folders still appear.
- [ ] "New Folder" / "New Document" create items that appear without full reload.
- [ ] Dragging a folder reorders it at the top level; order persists on reload.
- [ ] Dragging a document reorders it within its container; persists.
- [ ] Dragging a document into a folder sets `fold_id`; persists.
- [ ] Dragging a document out of a folder makes it loose (`fold_id = null`); persists.
- [ ] Dragging a document between folders updates `fold_id`; persists.
- [ ] Soft-deleted items do not appear in the tree.
- [ ] Blank names rejected.
- [ ] UI performs no direct DB access and holds no business logic; all data ops
      go through services via FastAPI.
