# Contributing to Spwrite Cloud

Thanks for contributing! This guide covers the development workflow: picking up
an issue, creating a branch, committing, and opening a pull request. For project
setup and architecture, see the [README](./README.md).

---

## TL;DR Workflow

```
1. Pick an issue on the Project board  →  assign it to yourself
2. Create a branch from main           →  feature/<issue#>-<short-slug>
3. Code  (follow the architecture rules)
4. Add/run tests                       →  pytest -v
5. Commit  (Conventional Commits)      →  feat: ... (#issue)
6. Push and open a PR against main     →  "Closes #<issue>"
7. Address review  →  merge
```

---

## 1. Pick up an issue

- Browse the **Project board** / **Issues** tab.
- Prefer issues labeled `good-first-issue` if you're new.
- **Assign the issue to yourself** so others know it's taken.
- Respect blockers: issues labeled `blocked` have a prerequisite noted in the
  issue body — don't start them until that's resolved.
- Work backend-first where possible: the data/service/API spine should land
  before the UI that depends on it.

---

## 2. Create a branch

Always branch from an up-to-date `main`. Never commit directly to `main`.

```bash
git checkout main
git pull origin main
git checkout -b feature/<issue#>-<short-slug>
```

**Branch naming:**

| Prefix | Use for | Example |
|--------|---------|---------|
| `feature/` | New functionality | `feature/42-create-folder-endpoint` |
| `fix/` | Bug fixes | `fix/51-tree-ordering` |
| `chore/` | Tooling, config, docs | `chore/18-add-ruff` |
| `test/` | Tests only | `test/33-move-document-cases` |

Keep the slug short and kebab-case. Include the issue number.

---

## 3. Code — follow the architecture rules

Spwrite is a layered monolith. Keep the layers clean (see README → Architecture):

- **Business logic + DB access live in `src/services/`** — never in the UI or
  directly inside an API route.
- **API routes** (`src/api/`) validate input and call services. No direct DB access.
- **UI** (`src/ui/`) talks to the API over HTTP (async `httpx`). It must not
  import models or query the database.
- **Every query filters soft-deleted rows** (`is_del == False`).
- **Use `fold_id.is_(None)`** for NULL checks, not `== None`.
- Match existing style and naming. Keep changes scoped to the issue.

---

## 4. Tests

- Add or update tests in `test/` for any logic you change (service functions
  especially).
- Use an isolated in-memory database in tests (`create_engine("sqlite://")`),
  never the real `spwrite.db`.
- Run the full suite before pushing:

```bash
pytest -v
```

All tests must pass before you open a PR.

---

## 5. Commit

Use **Conventional Commits** — a short type prefix + imperative summary.

```
<type>: <summary> (#<issue>)
```

| Type | For |
|------|-----|
| `feat` | New feature |
| `fix` | Bug fix |
| `test` | Adding/updating tests |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `chore` | Tooling, deps, config |
| `docs` | Documentation only |

**Examples:**
```bash
git commit -m "feat: add POST /folder endpoint (#42)"
git commit -m "fix: exclude soft-deleted docs from tree (#51)"
git commit -m "test: cover move_document between folders (#33)"
```

Guidelines:
- Keep commits focused; prefer small, logical commits over one giant one.
- Reference the issue number so GitHub links the commit to the issue.
- Don't commit secrets or local files (`.env`, `spwrite.db`, `.venv/` are
  gitignored — keep it that way).

---

## 6. Push and open a Pull Request

```bash
git push -u origin feature/<issue#>-<short-slug>
```

Then open a PR **against `main`**. Using the GitHub CLI:

```bash
gh pr create --base main --title "feat: add create-folder endpoint" \
  --body "Closes #42"
```

**In the PR description, include:**
- A short summary of what changed and why.
- `Closes #<issue>` (auto-closes the issue when merged).
- What you tested (and anything intentionally left out of scope).
- Screenshots/GIFs for UI changes.

**PR checklist (put this in the description):**
```
- [ ] Follows the layer architecture (logic in services, UI via HTTP)
- [ ] Tests added/updated and `pytest -v` passes
- [ ] No secrets or local files committed
- [ ] Linked to its issue (Closes #...)
```

---

## 7. Review & merge

- Address review comments with **new commits** on the same branch (push again;
  the PR updates automatically).
- Keep the discussion on the PR/issue so it's traceable.
- Once approved and green, the PR is merged into `main`. Delete the branch after
  merge.

---

## Keeping your branch current

If `main` moves while you work, update your branch:

```bash
git checkout main
git pull origin main
git checkout feature/<issue#>-<short-slug>
git merge main        # resolve conflicts if any, then commit
```

---

## Questions

Open a discussion or comment on the relevant issue. When in doubt about where
code belongs, re-read the **Architecture** section of the README — the layer
boundaries answer most "where does this go?" questions.
