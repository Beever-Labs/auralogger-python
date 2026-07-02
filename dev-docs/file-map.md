# File Map (Python CLI)

Use this as a "where to edit" guide.

- `auralogger/__init__.py`
  - Public API barrel re-exporting programmatic command runners, `fetch_proj_auth_payload`, `fetch_proj_auth_config`, the `Auralogger` logger class, and URL builders for embedders/tests

## Node → Python naming map

Use these pairs when keeping Python terminology close to Node while preserving Python style.

| Node symbol | Python symbol(s) |
|-------------|------------------|
| `AuraServer` | `auralogger` (class) and `aura_log(...)` |
| `AuraServer.log(...)` | `auralogger.log(...)` and `aura_log(...)` |
| `AuraServer.closeSocket(...)` | `auralogger.close_socket(...)` and `close_aura_log_socket()` |
| `fetchProjAuthConfig(...)` | `fetch_proj_auth_config(...)` (`fetch_proj_auth_payload(...)` remains supported) |

## CLI entrypoint

- `auralogger/cli_load_env.py`
  - Loads `.env` / `.env.local` from cwd (CLI only)

- `auralogger/cli.py`
  - Calls `load_cli_env_files()`, then routes `init`, `server-check`, `test-serverlog`, `get-logs`
  - Console script: `auralogger` → `auralogger.cli:_entrypoint` (`pyproject.toml`)

## Command implementations

- `auralogger/commands/init.py`
  - `auralogger init`
  - Early success path when token + user secret + session already exist; otherwise resolves token + secret, `POST /api/{project_token}/proj_auth` (token in path only), prints env block + Python server snippet

- `auralogger/commands/server_check.py`
  - `auralogger server-check`
  - Uses shared CLI context resolver (env/prompt + `proj_auth` hydration), then `WS /{project_token}/create_log` with `Authorization: Bearer <user_secret>` and one test JSON frame

- `auralogger/commands/test_serverlog.py`
  - `auralogger test-serverlog`
  - Resolves token + secret (env/prompt), configures runtime via `Auralogger.configure(...)` (session from env or `proj_auth`), sends 5 logs via `aura_log(...)`, then closes the cached socket

- `auralogger/commands/get_logs_cmd.py`
  - Thin wrapper → `get_logs.run_get_logs`

## Shared CLI resolution

- `auralogger/cli_auth.py` — env or interactive resolution for project token/user secret plus shared `resolve_project_context_for_cli_checks()`

## Namespaced compatibility exports

- `auralogger/server/__init__.py` — runtime re-exports (`auralogger` class, `aura_log`, `close_aura_log_socket`)
- `auralogger/utils/__init__.py` — URL/env/error utility re-exports for stable namespaced imports

## Configuration (os.environ)

- `auralogger/env_config.py`
  - `AURALOGGER_PROJECT_TOKEN`, `AURALOGGER_USER_SECRET`, `AURALOGGER_PROJECT_SESSION`, optional `NEXT_PUBLIC_*` / `VITE_*` aliases

## HTTP

- `auralogger/proj_auth.py` — `fetch_proj_auth_payload(project_token)` → `POST …/proj_auth`, no auth headers
- `auralogger/parser.py` — CLI filter tokens
- `auralogger/get_logs_filters.py` — validation
- `auralogger/get_logs.py` — `POST /api/{project_token}/logs` with `secret` + `user_secret` headers (user secret)

## URL / base resolution

- `auralogger/backend_origin.py`
  - `resolve_api_base_url`, `resolve_ws_base_url`, `build_proj_auth_url`, `build_project_logs_url`

## Runtime logger (library)

- `auralogger/server/aura_log.py`
  - Bearer WebSocket, path uses project token; `proj_auth` hydration for styles and session fallback; `configure()` / `sync_from_secret()` accept optional `session` (arg → env → `proj_auth`)

## Supporting modules

- `auralogger/utils/http_utils.py`, `auralogger/cli/log_print.py`, `auralogger/cli/log_styles.py`
