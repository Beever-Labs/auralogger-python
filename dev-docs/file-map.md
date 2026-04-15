# File Map (Python CLI)

Use this as a "where to edit" guide.

- `auralogger/__init__.py`
  - Public API barrel re-exporting programmatic command runners, `fetch_proj_auth_payload`, and URL builders for embedders/tests

## CLI entrypoint

- `auralogger/cli_load_env.py`
  - Loads `.env` / `.env.local` from cwd (CLI only)

- `auralogger/cli.py`
  - Calls `load_cli_env_files()`, then routes `init`, `server-check`, `client-check`, `test-serverlog`, `test-clientlog`, `get-logs`
  - Console script: `auralogger` → `auralogger.cli:_entrypoint` (`pyproject.toml`)

## Command implementations

- `auralogger/commands/init.py`
  - `auralogger init`
  - Resolves project token + user secret, `POST /api/{project_token}/proj_auth` (token in path only), Node-aligned copy-paste env block

- `auralogger/commands/server_check.py`
  - `auralogger server-check`
  - `proj_auth` then `WS /{project_token}/create_log` with `Authorization: Bearer <user_secret>` and a test JSON frame

- `auralogger/commands/client_check.py`
  - `auralogger client-check`
  - `proj_auth` then `WS /{project_token}/create_browser_logs` with path-only auth and one test JSON frame

- `auralogger/commands/test_serverlog.py`
  - `auralogger test-serverlog`
  - Sends 5 logs via `aura_log(...)`, then closes the cached server socket

- `auralogger/commands/test_clientlog.py`
  - `auralogger test-clientlog`
  - `proj_auth`, single `create_browser_logs` socket, 5 JSON frames, close

- `auralogger/commands/get_logs_cmd.py`
  - Thin wrapper → `get_logs.run_get_logs`

## Shared CLI resolution

- `auralogger/cli_auth.py` — env or interactive resolution for project token and user secret

## Configuration (os.environ)

- `auralogger/env_config.py`
  - `AURALOGGER_PROJECT_TOKEN`, `AURALOGGER_USER_SECRET`, public `NEXT_PUBLIC_*` / `VITE_*` aliases, legacy `AURALOGGER_PROJECT_SECRET` → user secret with warning

## HTTP

- `auralogger/proj_auth.py` — `fetch_proj_auth_payload(project_token)` → `POST …/proj_auth`, no auth headers
- `auralogger/parser.py` — CLI filter tokens
- `auralogger/get_logs_filters.py` — validation
- `auralogger/get_logs.py` — `POST /api/{project_token}/logs` with `secret` + `user_secret` headers (user secret)

## URL / base resolution

- `auralogger/backend_origin.py`
  - `resolve_api_base_url`, `resolve_ws_base_url`, `build_proj_auth_url`, `build_project_logs_url`, `build_create_browser_logs_url`

## Runtime logger (library)

- `auralogger/aura_log.py`
  - Bearer WebSocket, path uses project token; optional `proj_auth` hydration (cached) for id/session/styles

## Supporting modules

- `auralogger/http_utils.py`, `log.py`, `log_print.py`, `log_styles.py`
