# Task List — Sidebar: Folders & Documents (Drag & Drop)

Actionable, ordered tasks derived from `sidebar_spec.md` and `sidebar_design.md`.
Work top to bottom; each task is small enough to finish and verify before the
next. Check boxes as you go.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done

---

## Phase 1 — Data Model

- [ ] **1.1 Create `src/models/based_model.py`**
  - Add `BaseModel(SQLModel)` with: `id`, `created`, `updated`, `created_by`,
    `updated_by`, `version`, `is_del`.
  - NO `table=True` on the base.
  - Add `utcnow()` helper for UTC defaults.
  - _Verify:_ `python -c "from src.models.based_model import BaseModel"` imports clean.

- [ ] **1.2 Update `src/models/project_model.py` (edit existing models)**
  - Change `Project/Folder/Document` to inherit `BaseModel` instead of `SQLModel`.
  - Remove the per-model `id` line (now inherited).
  - Add `position: int = Field(default=0)` to **Folder** and **Document** only
    (NOT Project).
  - Add `index=True` to `proj_id` and `fold_id`.
  - Keep all existing fields and relationships.
  - _Verify:_ models import without error.

- [ ] **1.3 Recreate the dev database**
  - Delete `spwrite.db` (schema changed; `create_all` won't alter tables).
  - _Verify:_ running the app recreates it with the new columns (check `echo`
    SQL shows `created`, `is_del`, `position`, etc.).

- [ ] **1.4 Decision: DTOs or not for v1?**
  - [ ] Option A: skip DTOs — services/API return models directly (simpler).
  - [ ] Option B: add DTOs (`src/schemas/project_schema.py`) for decoupling.
  - Record the choice here, the rest of the tasks follow it.

---

## Phase 2 — Service Layer (`src/services/project_service.py`)

> All functions take an explicit `session` so they're unit-testable.
> Every query filters `is_del == False`. Use `fold_id.is_(None)` for NULL checks.

- [ ] **2.1 `_next_position(session, Model, proj_id, fold_id)`** helper — returns
      count of existing (non-deleted) siblings in the container.

- [ ] **2.2 `create_folder(session, proj_id, name)`** — append at end position.

- [ ] **2.3 `create_document(session, proj_id, name, fold_id=None)`** — append.

- [ ] **2.4 `get_project_tree(session, proj_id)`**
  - Folders ordered by `position`, with documents via `selectinload`
    (empty folders included).
  - Loose documents (`fold_id IS NULL`) ordered by `position`.
  - Exclude `is_del`.
  - Return models (Option A) or `ProjectTree` DTO (Option B).

- [ ] **2.5 `_renumber_container(session, proj_id, fold_id, moved_id=None, insert_at=None)`**
  - Gap-free `0,1,2,…` renumber; supports inserting a moved item at an index.
  - Clamp `insert_at` into valid range.

- [ ] **2.6 `move_document(session, doc_id, fold_id, position)`**
  - Set new `fold_id`, bump `updated` + `version`.
  - Renumber destination; if container changed, renumber source too.
  - Raise `ValueError` if doc missing/deleted.

- [ ] **2.7 `reorder_folder(session, folder_id, position)`**
  - Renumber top-level folders.

---

## Phase 3 — Core / Session

- [ ] **3.1 Ensure `get_session()` exists in `src/core/database.py`**
  - `yield`-based session for FastAPI `Depends`.
  - _Verify:_ importable; used by API in Phase 4.

---

## Phase 4 — API Layer (`src/api/routes/project_api.py`)

> Thin wrappers: validate → call service → uniform JSON envelope.
> Fix the half-written `get_project_tree` endpoint already in this file.

- [ ] **4.1 Request body models** — `NameBody`, `DocBody`, `MoveBody`, `ReorderBody`.

- [ ] **4.2 `GET /tree/{project_id}`** → `svc.get_project_tree`.

- [ ] **4.3 `POST /{project_id}/folder`** (201) → validate non-blank name.

- [ ] **4.4 `POST /{project_id}/document`** (201) → validate non-blank name.

- [ ] **4.5 `PATCH /document/{doc_id}/move`** → map `ValueError` → 404.

- [ ] **4.6 `PATCH /folder/{folder_id}/reorder`**.

- [ ] **4.7 Confirm routing/prefixes** — endpoints resolve under
      `/api/project/...` (router prefix + app prefix).

- [ ] **4.8 Manual test in `/docs`**
  - Create a folder, create a doc (loose + in folder), fetch the tree,
    move a doc into/out of a folder, reorder a folder. Confirm responses.

---

## Phase 5 — Dashboard link

- [ ] **5.1 Project cards link to editor with id**
  - `ui.navigate.to(f"/editor_page?project_id={p['id']}")` on card click.

---

## Phase 6 — Editor UI (`src/ui/pages/editor.py`)

- [ ] **6.1 Add `API_BASE_URL` to `.env`** (`http://127.0.0.1:8000/api`) and read it.

- [ ] **6.2 Async HTTP helpers** — `_get/_post/_patch` using `httpx.AsyncClient`.

- [ ] **6.3 `editor_page(project_id: int | None = None)`** reads the query param.
  - Handle missing/invalid id (empty state or redirect to dashboard).

- [ ] **6.4 `@ui.refreshable render_tree()`**
  - Fetch `GET /tree/{id}`, render folders (expandable, nested docs) then loose
    docs. Replace the hardcoded "Project"/"Chapter 1" buttons.

- [ ] **6.5 "New Folder" button + dialog** → POST → `render_tree.refresh()`.

- [ ] **6.6 "New Document" button + dialog** (optional target folder, default
      loose) → POST → refresh.

- [ ] **6.7 Empty states** — "No folders or documents yet.", empty folder shows
      nothing/"(empty)".

---

## Phase 7 — Drag & Drop

- [ ] **7.1 CONFIRM NiceGUI sortable API** for installed version (`nicegui==3.18.0`)
  - Determine the drop event payload: moved id, source container, target
    container, new index. (Open Question #3 in the design.)
  - _Blocker for 7.2–7.4 until confirmed._

- [ ] **7.2 Make top-level list sortable** (folders + loose docs).

- [ ] **7.3 Make each folder's document list sortable** + accept drops from
      outside (into/out of folders).

- [ ] **7.4 `on_drop` handler** → compute `{fold_id, position}` → PATCH
      move/reorder → `render_tree.refresh()`.

---

## Phase 8 — Tests (`test/test_sidebar.py`)

- [ ] **8.1 In-memory engine fixture** (isolation).
- [ ] **8.2 Create sets incremental `position`.**
- [ ] **8.3 `get_project_tree`** — ordering, nesting, empty folders, `is_del`
      excluded, loose docs.
- [ ] **8.4 `move_document`** — reorder; into folder; out of folder;
      folder→folder (both containers renumbered).
- [ ] **8.5 `reorder_folder`** — top-level renumber.
- [ ] **8.6 Audit** — `move` bumps `version` and `updated`.
- [ ] _Verify:_ `.venv/bin/pytest` all green.

---

## Phase 9 — Polish / Verify

- [ ] **9.1 Error UX** — failed API calls show `ui.notify(type="negative")`;
      no optimistic refresh on failure.
- [ ] **9.2 Full manual run-through** against Acceptance Criteria (below).
- [ ] **9.3 Remove throwaway/debug code**; keep `echo=True` only if desired.

---

## Acceptance Criteria (from spec §12)

- [ ] `BaseModel` exists; models inherit it; `position` only on Folder/Document.
- [ ] `/editor_page?project_id=X` shows that project's folders + loose docs in
      saved order.
- [ ] Folders show nested docs in order; empty folders appear.
- [ ] New Folder / New Document appear without full page reload.
- [ ] Drag folder reorders at top level; persists on reload.
- [ ] Drag doc reorders within container; persists.
- [ ] Drag doc into a folder sets `fold_id`; persists.
- [ ] Drag doc out of a folder → loose (`fold_id = null`); persists.
- [ ] Drag doc between folders updates `fold_id`; persists.
- [ ] Soft-deleted items excluded from the tree.
- [ ] Blank names rejected.
- [ ] UI does no direct DB access and holds no business logic; all data ops go
      through services via FastAPI.

---

## Open Questions to resolve during build

1. Top-level ordering: folders-first (assumed) vs single interleaved order?
2. Click-a-document to open in editor — now, or a later spec? (assumed later)
3. NiceGUI sortable payload shape (Task 7.1) — confirm before wiring drag/drop.

---

## Dependencies / Ordering Notes

- Phase 1 → 2 → 4 is the backend spine; finish and test in `/docs` before UI.
- Phase 7 (drag/drop) depends on Task 7.1 being resolved first.
- Phase 8 tests can be written alongside Phase 2 (service) rather than at the end.
