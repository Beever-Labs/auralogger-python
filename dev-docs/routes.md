# Routes Map (HTTP + WebSocket)

Routes used by the Python CLI/runtime and where to update them.

## Base URLs

- HTTP base (`/api/*`):
  - Env override: `AURALOGGER_API_URL`
  - Resolver: `auralogger/backend_origin.py` → `resolve_api_base_url()`

- WebSocket base:
  - Env override: `AURALOGGER_WS_URL`
  - Resolver: `auralogger/backend_origin.py` → `resolve_ws_base_url()`

Path segments use URL encoding consistent with Node `encodeURIComponent` (`auralogger/backend_origin.py` → `_encode_path_token` / `build_*_url`).

---

## HTTP routes in use

### `POST /api/{project_token}/proj_auth`

- Used by: `auralogger init`, `auralogger/commands/server_check.py`, style hydration in `get_logs.py` and `aura_log.py`
- Client: `auralogger/proj_auth.py` → `fetch_proj_auth_payload`
- Purpose: fetch project id, session, styles
- **No auth headers** — project token is only in the path.

### `POST /api/{project_token}/logs`

- Used by: `auralogger get-logs`
- Files: `auralogger/get_logs.py` (and `get_logs_cmd.py` for orchestration)
- Purpose: fetch logs using filters
- Headers: **`secret`** and **`user_secret`**, both set to the **user secret** (not the project token)
- Body: `{ "filters": [...] }`

---

## WebSocket routes in use

### `WS /{project_token}/create_log`

- Used by:
  - `auralogger/aura_log.py`
  - `auralogger/commands/server_check.py`
- Path segment: **project token** (ciphertext), not internal project id
- Headers: **`Authorization: Bearer <user_secret>`** only (no `secret:` custom header)

---

### `WS /{project_token}/create_browser_logs`

- Used by:
  - `auralogger/commands/client_check.py`
  - `auralogger/commands/test_clientlog.py`
- Path segment: **project token** (ciphertext), not internal project id
- Headers: **none required** (path-only auth)

---

## When adding new API/WS routes

1. Implement usage in the relevant module under `auralogger/`
2. If base resolution changes, update `auralogger/backend_origin.py`
3. Update this file (`python/dev-docs/routes.md`)
4. If user-visible behavior changes, update `python/user-docs/commands.md`
