# auralogger (Python)

Command-line client for [Auralogger](https://auralogger.com): `init`, `server-check`, `client-check`, `test-serverlog`, `test-clientlog`, and `get-logs`, plus the `aura_log` helper for Python apps.

## Install

From [PyPI](https://pypi.org/) (once published):

```bash
pip install auralogger
```

From a developer checkout of this project (path must point at the folder that contains `pyproject.toml`):

```bash
pip install -e ./python
```

## Project directory (important)

The CLI uses **your shell’s current working directory** as the project root. It loads **`.env`** and **`.env.local`** from that directory before each command (same idea as the Node `auralogger` CLI).

Configuration is **environment variables** only — see **`user-docs/environment.md`** for **`AURALOGGER_PROJECT_TOKEN`**, **`AURALOGGER_USER_SECRET`**, and the publishable `AURALOGGER_PROJECT_*` keys. There is no `auralogger.config.json`.

**Wire contract (matches Node):** `proj_auth` is **`POST /api/{project_token}/proj_auth`** with the token in the path only. **`get-logs`** uses **`POST /api/{project_token}/logs`** with headers **`secret`** and **`user_secret`** both set to your **user secret**. The server ingest socket is **`WS /{project_token}/create_log`** with **`Authorization: Bearer <user_secret>`**. Set **`AURALOGGER_PROJECT_TOKEN`** and **`AURALOGGER_USER_SECRET`**; legacy **`AURALOGGER_PROJECT_SECRET`** is treated as the user secret (with a deprecation warning) if **`AURALOGGER_USER_SECRET`** is unset.

```bash
cd /path/to/my-app
auralogger init
# add printed lines to .env, then:
auralogger server-check
```

The **`aura_log()`** library function reads **`os.environ` only**; it does not load `.env` files. In a web app, load env in your own startup code or rely on your host.

## Naming parity with Node

Python keeps snake_case naming, but key public names map directly to Node concepts:

| Node symbol | Python symbol(s) |
|-------------|------------------|
| `AuraServer` | `AuraServer` and `aura_log(...)` |
| `AuraServer.log(...)` | `AuraServer.log(...)` and `aura_log(...)` |
| `AuraServer.closeSocket(...)` | `AuraServer.close_socket(...)` and `close_aura_log_socket()` |
| `fetchProjAuthConfig(...)` | `fetch_proj_auth_config(...)` (`fetch_proj_auth_payload(...)` remains supported) |
| `AuraClient` / `clientlog(...)` | Not yet exposed as a Python library API |

## Commands

```text
auralogger init
auralogger server-check
auralogger client-check
auralogger test-serverlog
auralogger test-clientlog
auralogger get-logs [filters...]
```

Filter syntax: **`user-docs/commands.md`**.

## Requirements

Python 3.8+, `websocket-client`, and `python-dotenv` (declared in `pyproject.toml`).

## Contributor setup

Install editable package + development tooling (currently Ruff):

```bash
cd python
pip install -e ".[dev]"
```

## Publishing (maintainers)

Releases are automated through `.github/workflows/python-publish.yml`.

- The workflow runs on GitHub release publish events only when the tag matches `python-v*` (for example, `python-v0.1.1`), or through manual `workflow_dispatch`.
- Configure repository secret `PYPI_API_TOKEN` with a PyPI API token.
- Before tagging, bump `version` in `python/pyproject.toml` and update `python/CHANGELOG.md`.

Manual fallback from this directory, after configuring PyPI credentials (`twine`):

```bash
python -m pip install build twine
python -m build
twine upload dist/*
```

End users only need `pip install auralogger` once the release is on PyPI.
