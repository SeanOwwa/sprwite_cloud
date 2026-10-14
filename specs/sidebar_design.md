# Technical Design — Sidebar: Folders & Documents (Drag & Drop)

Companion to `sidebar_spec.md`. The spec defines **what/why**; this document
defines **how** — concrete modules, function signatures, data flow, algorithms,
and failure handling.

- **Status:** Draft
- **Scope:** Editor sidebar tree, create folder/document, drag-and-drop move/reorder
- **Related:** `sidebar_spec.md`

---

## 1. Overview

The sidebar renders a project's folders and documents as an ordered, drag-and-
drop tree. Creates and moves are persisted through FastAPI → service → DB, and
the UI re-fetches the tree after each change.

```
Browser (NiceGUI UI) ──HTTP(httpx)──> FastAPI routes ──> services ──> SQLModel ──> SQLite/Postgres
      ▲                                                                                 │
      └──────────────────────── JSON (ProjectTree DTO) ────────────────────────────────┘
```

---

## 2. Module Map

| File | Responsibility | New / Changed |
|------|----------------|---------------|
| `src/models/based_model.py` | `BaseModel` audit fields | **new** |
| `src/models/project_model.py` | `Project/Folder/Document` inherit base; `position` | changed |
| `src/schemas/project_schema.py` | `DocumentRead/FolderRead/ProjectTree` DTOs | **new** |
| `src/services/project_service.py` | all DB logic (CRUD + move/reorder + renumber) | **new** |
| `src/api/routes/project_api.py` | HTTP endpoints → service calls | changed |
| `src/core/database.py` | `get_session()` dependency | changed (ensure present) |
| `src/ui/pages/editor.py` | sidebar tree, dialogs, drag/drop wiring | changed |
| `src/ui/pages/dashboard.py` | project cards link with `?project_id=` | changed |
| `test/test_sidebar.py` | service + ordering tests | **new** |

---

## 3. Data Model (concrete)

### 3.1 `based_model.py`

```python
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field

def utcnow() -> datetime:
    return datetime.now(timezone.utc)

class BaseModel(SQLModel):            # NO table=True
    id: int | None = Field(default=None, primary_key=True)
    created: datetime = Field(default_factory=utcnow)
    updated: datetime = Field(default_factory=utcnow)
    created_by: int | None = Field(default=None)
    updated_by: int | None = Field(default=None)
    version: int = Field(default=1)
    is_del: bool = Field(default=False)
```

### 3.2 `project_model.py`

```python
from sqlalchemy import Column, Text
from sqlmodel import Field, Relationship
from src.models.based_model import BaseModel

class Project(BaseModel, table=True):
    title: str
    author: str
    cover: str | None = None
    folders: list["Folder"] = Relationship(back_populates="project")
    documents: list["Document"] = Relationship(back_populates="project")

class Folder(BaseModel, table=True):
    proj_id: int = Field(foreign_key="project.id")
    name: str
    position: int = Field(default=0)
    project: Project | None = Relationship(back_populates="folders")
    documents: list["Document"] = Relationship(back_populates="folder")

class Document(BaseModel, table=True):
    proj_id: int = Field(foreign_key="project.id")
    fold_id: int | None = Field(default=None, foreign_key="folder.id")
    name: str
    written_text: str = Field(default="", sa_column=Column(Text))
    position: int = Field(default=0)
    folder: Folder | None = Relationship(back_populates="documents")
    project: Project | None = Relationship(back_populates="documents")
```

### 3.3 Indexes (performance + predictable ordering)

Add indexes to the columns used for filtering/ordering:

```python
proj_id: int = Field(foreign_key="project.id", index=True)
fold_id: int | None = Field(default=None, foreign_key="folder.id", index=True)
```

Rationale: tree queries filter by `proj_id`/`fold_id` and order by `position`;
indexing the foreign keys keeps these fast as data grows.

---

## 4. DTOs (`src/schemas/project_schema.py`)

Non-table SQLModel classes used for API responses so the UI never imports table
models.

```python
from sqlmodel import SQLModel

class DocumentRead(SQLModel):
    id: int
    name: str
    fold_id: int | None
    position: int

class FolderRead(SQLModel):
    id: int
    name: str
    position: int
    documents: list[DocumentRead] = []

class ProjectTree(SQLModel):
    folders: list[FolderRead]
    loose_documents: list[DocumentRead]
```

---

## 5. Service Layer (`src/services/project_service.py`)

All functions take an explicit `session: Session` (injected by the API via
`Depends(get_session)`), so the service is testable in isolation.

### 5.1 Signatures

```python
def create_folder(session, proj_id: int, name: str) -> Folder
def create_document(session, proj_id: int, name: str, fold_id: int | None = None) -> Document
def get_project_tree(session, proj_id: int) -> ProjectTree
def move_document(session, doc_id: int, fold_id: int | None, position: int) -> Document
def reorder_folder(session, folder_id: int, position: int) -> Folder
```

### 5.2 `get_project_tree`

```python
from sqlalchemy.orm import selectinload
from sqlmodel import select

def get_project_tree(session, proj_id: int) -> ProjectTree:
    folders = session.exec(
        select(Folder)
        .where(Folder.proj_id == proj_id, Folder.is_del == False)   # noqa: E712
        .order_by(Folder.position)
        .options(selectinload(Folder.documents))
    ).all()

    loose_docs = session.exec(
        select(Document)
        .where(
            Document.proj_id == proj_id,
            Document.fold_id.is_(None),
            Document.is_del == False,                                # noqa: E712
        )
        .order_by(Document.position)
    ).all()

    return ProjectTree(
        folders=[
            FolderRead(
                id=f.id, name=f.name, position=f.position,
                documents=[
                    DocumentRead(id=d.id, name=d.name, fold_id=d.fold_id, position=d.position)
                    for d in sorted(
                        (d for d in f.documents if not d.is_del),
                        key=lambda d: d.position,
                    )
                ],
            )
            for f in folders
        ],
        loose_documents=[
            DocumentRead(id=d.id, name=d.name, fold_id=d.fold_id, position=d.position)
            for d in loose_docs
        ],
    )
```

Notes:
- `is_del == False` filter is mandatory everywhere (soft delete).
- `fold_id.is_(None)` for the NULL check (never `== None`).
- `selectinload` loads folder documents in one extra query (no N+1), and keeps
  empty folders in the result.

### 5.3 Create functions

```python
def create_folder(session, proj_id: int, name: str) -> Folder:
    position = _next_position(session, Folder, proj_id=proj_id, fold_id=None)
    folder = Folder(proj_id=proj_id, name=name, position=position)
    session.add(folder)
    session.commit()
    session.refresh(folder)
    return folder

def create_document(session, proj_id, name, fold_id=None) -> Document:
    position = _next_position(session, Document, proj_id=proj_id, fold_id=fold_id)
    doc = Document(proj_id=proj_id, name=name, fold_id=fold_id, position=position)
    session.add(doc)
    session.commit()
    session.refresh(doc)
    return doc
```

New items append to the end of their container (`_next_position` = count of
existing siblings).

### 5.4 Move & reorder (the core algorithm)

`move_document` handles all four drag cases (reorder, into folder, out of folder,
folder→folder) by setting `fold_id` + `position` and renumbering.

```python
def move_document(session, doc_id, fold_id, position) -> Document:
    doc = session.get(Document, doc_id)
    if not doc or doc.is_del:
        raise ValueError("Document not found")

    source_fold = doc.fold_id
    doc.fold_id = fold_id
    doc.updated = utcnow()
    doc.version += 1
    session.add(doc)
    session.commit()

    # Renumber destination container with doc inserted at `position`.
    _renumber_container(session, doc.proj_id, fold_id, moved_id=doc.id, insert_at=position)
    # If it left a different container, renumber the source too.
    if source_fold != fold_id:
        _renumber_container(session, doc.proj_id, source_fold)

    session.refresh(doc)
    return doc
```

### 5.5 Renumbering helper

Gap-free integer renumbering, deterministic and easy to inspect.

```python
def _siblings(session, proj_id, fold_id):
    stmt = select(Document).where(
        Document.proj_id == proj_id, Document.is_del == False
    )
    stmt = stmt.where(Document.fold_id.is_(None)) if fold_id is None \
        else stmt.where(Document.fold_id == fold_id)
    return session.exec(stmt.order_by(Document.position)).all()

def _renumber_container(session, proj_id, fold_id, moved_id=None, insert_at=None):
    items = [d for d in _siblings(session, proj_id, fold_id)]
    if moved_id is not None and insert_at is not None:
        items = [d for d in items if d.id != moved_id]          # remove moved
        moved = session.get(Document, moved_id)
        insert_at = max(0, min(insert_at, len(items)))          # clamp
        items.insert(insert_at, moved)                          # reinsert at index
    for i, d in enumerate(items):                               # 0,1,2,...
        if d.position != i:
            d.position = i
            d.updated = utcnow()
            session.add(d)
    session.commit()
```

`reorder_folder` is the folder-level analogue (renumber folders at the top level
by `position`).

### 5.6 Transaction & concurrency notes
- Each service call commits once at the end of its logical operation.
- `version` is incremented on moves/updates to support future optimistic locking.
- v1 does not enforce version checks on write; that is a later enhancement.

---

## 6. API Layer (`src/api/routes/project_api.py`)

Thin wrappers: parse/validate, call the service, wrap the result.

```python
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel as Payload
from sqlmodel import Session
from src.core.database import get_session
from src.services import project_service as svc

router = APIRouter()

class NameBody(Payload):
    name: str

class DocBody(Payload):
    name: str
    fold_id: int | None = None

class MoveBody(Payload):
    fold_id: int | None = None
    position: int

class ReorderBody(Payload):
    position: int

@router.get("/tree/{project_id}")
def get_tree(project_id: int, session: Session = Depends(get_session)):
    return {"success": True, "data": svc.get_project_tree(session, project_id)}

@router.post("/{project_id}/folder", status_code=status.HTTP_201_CREATED)
def create_folder(project_id: int, body: NameBody, session: Session = Depends(get_session)):
    if not body.name.strip():
        raise HTTPException(400, "Name is required")
    f = svc.create_folder(session, project_id, body.name.strip())
    return {"success": True, "message": "Folder created", "id": f.id}

@router.post("/{project_id}/document", status_code=status.HTTP_201_CREATED)
def create_document(project_id: int, body: DocBody, session: Session = Depends(get_session)):
    if not body.name.strip():
        raise HTTPException(400, "Name is required")
    d = svc.create_document(session, project_id, body.name.strip(), body.fold_id)
    return {"success": True, "message": "Document created", "id": d.id}

@router.patch("/document/{doc_id}/move")
def move_document(doc_id: int, body: MoveBody, session: Session = Depends(get_session)):
    try:
        d = svc.move_document(session, doc_id, body.fold_id, body.position)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return {"success": True, "message": "Moved", "id": d.id}

@router.patch("/folder/{folder_id}/reorder")
def reorder_folder(folder_id: int, body: ReorderBody, session: Session = Depends(get_session)):
    f = svc.reorder_folder(session, folder_id, body.position)
    return {"success": True, "message": "Reordered", "id": f.id}
```

Mounting: `project_api.router` is included under `/project` by `api_router`,
which `app.py` mounts under `/api`. Full paths e.g. `GET /api/project/tree/{id}`.

---

## 7. UI Layer (`src/ui/pages/editor.py`)

### 7.1 Config & client

```python
import os, httpx
from dotenv import load_dotenv
load_dotenv()
API = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api")

async def _get(path):            return (await _client().get(f"{API}{path}")).json()
async def _post(path, json):     return (await _client().post(f"{API}{path}", json=json)).json()
async def _patch(path, json):    return (await _client().patch(f"{API}{path}", json=json)).json()
# _client() returns an httpx.AsyncClient (one per request/handler)
```

All handlers are `async` to avoid blocking NiceGUI's event loop on self-calls.

### 7.2 Page structure

```python
@ui.page("/editor_page")
async def editor_page(project_id: int | None = None):
    # left_drawer -> create buttons -> @ui.refreshable tree
    ...
```

- `project_id` comes from the query string (NiceGUI maps query params to handler
  args).
- The tree is a `@ui.refreshable` function that fetches `GET /tree/{id}` and
  builds sortable lists.

### 7.3 Rendering the tree (refreshable)

```python
@ui.refreshable
async def render_tree():
    data = (await _get(f"/project/tree/{project_id}"))["data"]
    # top-level sortable: folders (each an expandable item with a nested
    # sortable list of its documents), then loose documents.
    # Each row carries data-id and data-type for drop handling.
```

### 7.4 Create flows

```python
async def new_folder():
    name = await prompt_dialog("Folder name")
    if not name: return
    await _post(f"/project/{project_id}/folder", {"name": name})
    render_tree.refresh()

async def new_document(fold_id=None):
    name = await prompt_dialog("Document name")
    if not name: return
    await _post(f"/project/{project_id}/document", {"name": name, "fold_id": fold_id})
    render_tree.refresh()
```

### 7.5 Drag & drop wiring

- Use NiceGUI sortable support (Sortable.js). Each sortable list emits a drop
  event with: moved item id, source list (folder id or "root"), target list,
  new index.
- Handler maps that to an API call:

```python
async def on_drop(item_type, item_id, target_fold_id, new_index):
    if item_type == "document":
        await _patch(f"/project/document/{item_id}/move",
                     {"fold_id": target_fold_id, "position": new_index})
    else:  # folder
        await _patch(f"/project/folder/{item_id}/reorder", {"position": new_index})
    render_tree.refresh()
```

`target_fold_id` is `None` when dropped at the top level.

---

## 8. Data Flow Sequences

### 8.1 Load editor
```
UI editor_page(project_id)
  -> GET /api/project/tree/{id}
     -> svc.get_project_tree(session, id)
        -> SELECT folders (ordered) + selectinload docs
        -> SELECT loose docs (fold_id IS NULL, ordered)
     <- ProjectTree DTO
  <- { success, data }
UI renders sortable tree
```

### 8.2 Drag a document into a folder
```
UI on_drop("document", 20, target_fold_id=1, new_index=0)
  -> PATCH /api/project/document/20/move { fold_id:1, position:0 }
     -> svc.move_document: set fold_id=1, bump updated/version, commit
        -> _renumber_container(dest=folder 1, insert doc@0)
        -> _renumber_container(source=top level)   # it left the top level
  <- { success }
UI render_tree.refresh() -> re-fetch -> re-render
```

---

## 9. Error Handling

| Layer | Strategy |
|-------|----------|
| API | `HTTPException` with 400 (validation), 404 (not found), 409 (future: version conflict) |
| Service | Raise `ValueError` for not-found / invalid; API maps to HTTP codes |
| UI | Check `success`; on failure show `ui.notify(..., type="negative")` and do not refresh optimistically |

Response envelope is uniform: `{ "success": bool, "data"|"message"|"error": ... }`.

---

## 10. Testing (`test/test_sidebar.py`)

Use an in-memory SQLite engine (isolation). Cover:

- `create_folder` / `create_document` set incremental `position`.
- `get_project_tree` returns folders ordered, docs nested & ordered, loose docs
  ordered, empty folders present, `is_del` excluded.
- `move_document`:
  - reorder within container renumbers 0..n gap-free,
  - into folder sets `fold_id` + position,
  - out of folder sets `fold_id=None`,
  - folder→folder renumbers both source and destination.
- `reorder_folder` renumbers top-level folders.
- `move_document` bumps `version` and `updated`.

---

## 11. Migration / Rollout

- Dev: delete `spwrite.db`; `create_db_and_tables()` recreates with new columns.
- Prod (later): Alembic migration adding audit columns + `position`, backfilling
  `position` by current id order per container, defaulting `is_del=false`,
  `version=1`.

---

## 12. Open Questions

1. Top-level ordering: folders-first grouping (v1) vs single interleaved order?
   Design assumes **folders-first**.
2. Does clicking a document load it into the editor now, or in a later spec?
   Assumed **later spec** (click = select/notify for now).
3. NiceGUI sortable: confirm the exact event payload shape in the installed
   version before wiring §7.5 (drop index + container identification).

---

## 13. Decision Log

- **Service holds all DB access** → single place for data bugs (debuggability).
- **Gap-free integer renumber on drop** → simple, inspectable ordering (vs
  fractional ranking) for v1.
- **`position` on orderable models, not `BaseModel`** → base stays general.
- **DTOs for responses** → UI decoupled from table models; stable API contract.
- **Soft delete (`is_del`)** → recoverable deletes; requires filtering everywhere.
