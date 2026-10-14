# Contributing to Spwrite Cloud

Thanks for contributing! This guide covers the development workflow: picking up
an issue, creating a branch, committing, and opening a pull request. For project
setup and architecture, see the [README](./README.md).

---

> This project uses a **fork-based workflow**. You work on your own fork and
> propose changes via pull requests to the original ("upstream") repository.
> `origin` = your fork, `upstream` = the original repo. See the README's
> *Getting Started* for forking and remote setup.

## TL;DR Workflow

```
1. Pick an issue on the Project board      →  assign it to yourself
2. Sync your fork with upstream            →  git fetch upstream && merge
3. Create a branch from upstream/main      →  feature/<issue#>-<short-slug>
4. Code  (follow the architecture rules)
5. Add/run tests                           →  pytest -v
6. Commit  (Conventional Commits)          →  feat: ... (#issue)
7. Push to your fork and open a PR          →  "Closes #<issue>"
8. Address review  →  maintainer merges
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

## 2. Sync your fork, then create a branch

First make sure your fork's `main` matches upstream, then branch off it. Never
commit directly to `main`.

```bash
# sync your fork's main with the original repo
git checkout main
git fetch upstream
git merge upstream/main
git push origin main          # keep your fork's main up to date too

# create your working branch
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

## 6. Push to your fork and open a Pull Request

Push the branch to **your fork** (`origin`):

```bash
git push -u origin feature/<issue#>-<short-slug>
```

Then open a PR from **your fork's branch → upstream `main`**. On GitHub, pushing
usually shows a "Compare & pull request" prompt. Using the GitHub CLI:

```bash
gh pr create --repo <original-owner>/spwrite_cloud --base main \
  --head <your-username>:feature/<issue#>-<short-slug> \
  --title "feat: add create-folder endpoint" \
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

- Address review comments with **new commits** on the same branch, then
  `git push origin <branch>` — the PR updates automatically.
- Keep the discussion on the PR/issue so it's traceable.
- Once approved and green, a **maintainer** merges the PR into upstream `main`.
  (As a contributor you don't merge your own PR into upstream.)
- Delete your branch after merge.

---

## Keeping your branch current

If upstream `main` moves while you work, pull those changes into your branch:

```bash
git fetch upstream
git checkout feature/<issue#>-<short-slug>
git merge upstream/main        # resolve conflicts if any, then commit
```

---

## Questions

Open a discussion or comment on the relevant issue. When in doubt about where
code belongs, re-read the **Architecture** section of the README — the layer
boundaries answer most "where does this go?" questions.
