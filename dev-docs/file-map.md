# File Map (Python CLI)

Use this as a "where to edit" guide.

- `auralogger/__init__.py`
  - Public API barrel re-exporting programmatic command runners, `fetch_proj_auth_payload`, `fetch_proj_auth_config`, `AuraServer`, and URL builders for embedders/tests

## Node → Python naming map

Use these pairs when keeping Python terminology close to Node while preserving Python style.

| Node symbol | Python symbol(s) |
|-------------|------------------|
| `AuraServer` | `AuraServer` and `aura_log(...)` |
| `AuraServer.log(...)` | `AuraServer.log(...)` and `aura_log(...)` |
| `AuraServer.closeSocket(...)` | `AuraServer.close_socket(...)` and `close_aura_log_socket()` |
| `fetchProjAuthConfig(...)` | `fetch_proj_auth_config(...)` (`fetch_proj_auth_payload(...)` remains supported) |
| `AuraClient` / `clientlog(...)` | Not yet exposed as a Python library surface (CLI checks exist) |

## CLI entrypoint

- `auralogger/cli_load_env.py`
  - Loads `.env` / `.env.local` from cwd (CLI only)

- `auralogger/cli.py`
  - Calls `load_cli_env_files()`, then routes `init`, `server-check`, `client-check`, `test-serverlog`, `test-clientlog`, `get-logs`
  - Console script: `auralogger` → `auralogger.cli:_entrypoint` (`pyproject.toml`)

## Command implementations

- `auralogger/commands/init.py`
  - `auralogger init`
  - Early success path when token + user secret + session already exist; otherwise resolves token + secret, `POST /api/{project_token}/proj_auth` (token in path only), prints Node-aligned env block + Python server snippet

- `auralogger/commands/server_check.py`
  - `auralogger server-check`
  - Uses shared CLI context resolver (env/prompt + `proj_auth` hydration), then `WS /{project_token}/create_log` with `Authorization: Bearer <user_secret>` and one test JSON frame

- `auralogger/commands/client_check.py`
  - `auralogger client-check`
  - Uses the same shared CLI context resolver as `server-check`, then `WS /{project_token}/create_browser_logs` with path-only auth and one test JSON frame

- `auralogger/commands/test_serverlog.py`
  - `auralogger test-serverlog`
  - Resolves token + secret (env/prompt), syncs runtime via `AuraServer.sync_from_secret(...)`, sends 5 logs via `aura_log(...)`, then closes the cached server socket

- `auralogger/commands/test_clientlog.py`
  - `auralogger test-clientlog`
  - Resolves project token (env/prompt), then `proj_auth`, single `create_browser_logs` socket, 5 JSON frames, close

- `auralogger/commands/get_logs_cmd.py`
  - Thin wrapper → `get_logs.run_get_logs`

## Shared CLI resolution

- `auralogger/cli_auth.py` — env or interactive resolution for project token/user secret plus shared `resolve_project_context_for_cli_checks()`

## Namespaced compatibility exports

- `auralogger/server/__init__.py` — server runtime re-exports (`AuraServer`, `aura_log`, `close_aura_log_socket`)
- `auralogger/client/__init__.py` — client SDK + CLI re-exports (`AuraClient`, `client_log`, typed `auralog`, plus check/test commands)
- `auralogger/client/client_log.py` — importable browser-ingest runtime (`AuraClient`) with token override, `proj_auth` hydration cache, socket reuse + idle close, and typed inputs
- `auralogger/utils/__init__.py` — URL/env/error utility re-exports for stable namespaced imports

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

- `auralogger/utils/http_utils.py`, `auralogger/cli/log_print.py`, `auralogger/cli/log_styles.py`
