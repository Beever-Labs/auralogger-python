# Dev Docs (Python CLI)

Contributor-oriented notes for the Python `auralogger` package.

## Python package repo

- Source/publishing repo: [Beever-Labs/auralogger-python](https://github.com/Beever-Labs/auralogger-python)

## Project description

`auralogger` (Python): command-line tool for Auralogger: `init`, `server-check`, `test-serverlog`, and `get-logs`, plus the `aura_log` helper for Python apps.

```text
├── LICENSE
├── pyproject.toml
├── README.md
```

## Package naming (Node vs Python)

- Python distribution name: `auralogger` (`pip install auralogger`)
- Node distribution name: `auralogger-cli` (`npm install auralogger-cli`)
- Both expose the CLI command `auralogger`, but package-index names are intentionally different.

## Start here

- `file-map.md`: quick map of what each important module does
- `routes.md`: HTTP + WebSocket routes and where they are used in this package

Auth contract (match Node / hosted API): **`POST /api/{project_token}/proj_auth`** — token in path only. **`POST /api/{project_token}/logs`** — headers **`secret`** and **`user_secret`** both set to the **user secret**. Server ingest WebSocket — **`Authorization: Bearer <user_secret>`** on **`/{project_token}/create_log`**.

## Publishing setup (maintainers)

- Automated release workflow: `.github/workflows/python-publish.yml`
- Trigger: GitHub release publish for tags matching `python-v*` (for example, `python-v0.1.1`) or manual `workflow_dispatch`
- Required secret: `PYPI_API_TOKEN`
- Before release: bump `version` in `pyproject.toml` and update `CHANGELOG.md`
- Manual fallback:
  - `python -m pip install build twine`
  - `python -m build`
  - `twine upload dist/*`

## Related folders

- `user-docs/commands.md`: end-user setup and command reference (keep in sync when behavior changes)
- `docs/BDD/`: behavior specs
- `docs/infra/`: per-file infrastructure notes

## Contributing flow (quick)

1. Change code under `auralogger/`
2. Update `dev-docs/` (and `user-docs/` when user-visible behavior changes)
3. Run tests or smoke checks as appropriate for your change

## Smoke tests (local)

### 1) Credentials for tests

Local smoke scripts auto-load **`python/.env.example`** (via `python-dotenv`).

Minimum for remote streaming:

- `AURALOGGER_PROJECT_TOKEN`
- `AURALOGGER_USER_SECRET` (encrypted ingest)

### 2) Install editable (dev)

From the repo root (PowerShell-friendly):

```bash
cd python
pip install -e .
```

### 3) Run smoke logger

```bash
cd python
python tests/smoke_aura_log.py smoke
```

Expected:

- You see colored/styled log lines printed locally.
- If credentials are valid and the backend is reachable, logs also stream over WebSocket (any network/config errors will print to stderr).
