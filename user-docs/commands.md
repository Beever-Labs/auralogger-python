# Auralogger CLI — setup and commands (Python)

User-facing reference: how to install, configure, and run the `auralogger` CLI.

Full variable reference: **[`environment.md`](environment.md)**.

## Setup

- **Python**: version 3.8 or newer.
- **Install** (pick one):
  - From PyPI: `pip install auralogger` (when published).
  - From this repo: `pip install -e ./python` (directory that contains `pyproject.toml`).

The CLI loads **`.env`** and **`.env.local`** from your **current working directory** before each command. Run commands from the project root where those files live.

```bash
auralogger <command> [args...]
```

## Environment variables

Default API/WebSocket hosts need no URL config unless you override them. See **[`environment.md`](environment.md)** for `AURALOGGER_PROJECT_*` and optional base URLs.

## Commands overview

- `auralogger init` — authenticate and print copy-paste env lines.
- `auralogger server-check` — verify WebSocket connectivity.
- `auralogger client-check` — verify browser-ingest path-only socket connectivity.
- `auralogger test-serverlog` — send 5 server logger test logs.
- `auralogger test-clientlog` — send 5 browser-ingest test logs.
- `auralogger get-logs [filters...]` — fetch and print logs.

---

## `auralogger init`

**Flags:** none.

**Credentials:** `AURALOGGER_PROJECT_TOKEN` and `AURALOGGER_USER_SECRET` if both set in env; otherwise interactive prompts for whatever is missing. `POST /api/{project_token}/proj_auth` puts the token **in the URL path only** (no `secret` header).

Prints env lines aligned with the Node CLI (token, user secret, session, Next/Vite token aliases). Project id and styles are not in the copy block; runtime code hydrates them via `proj_auth` when needed.

```bash
auralogger init
```

---

## `auralogger server-check`

**Requirements:** `AURALOGGER_PROJECT_TOKEN`, `AURALOGGER_USER_SECRET` (after CLI `.env` load). Calls `proj_auth`, then opens `WS /{project_token}/create_log` with **`Authorization: Bearer <user_secret>`** and sends one test log frame.

```bash
auralogger server-check
```

---

## `auralogger get-logs [filters...]`

**Requirements:** `AURALOGGER_PROJECT_TOKEN`, `AURALOGGER_USER_SECRET`, and `AURALOGGER_PROJECT_STYLES` (or equivalent style resolution via `proj_auth` for that run).

### Filter syntax

```text
-<field> [--<op>] <json-value-token>
```

- `field` starts with `-`.
- `op` is optional and starts with `--`.
- The value must be valid JSON.
- For `maxcount` and `skip`, the value must be a JSON number.
- For all other fields, the value must be a JSON array.

### Fields and operators

| Field | Allowed ops | Default op | Value shape |
|-------|-------------|------------|-------------|
| `type` | `in`, `not-in` | `in` | JSON array |
| `message` | `contains`, `not-contains` | `contains` | JSON array |
| `location` | `in`, `not-in` | `in` | JSON array |
| `time` | `since`, `from-to` | `since` | JSON array |
| `order` | `eq` | `eq` | JSON array (`["newest-first"]` or `["oldest-first"]`) |
| `maxcount` | `eq` | `eq` | JSON number (clamped `0..100`) |
| `skip` | `eq` | `eq` | JSON number (floored, min `0`) |
| `data.<path>` | `eq` | `eq` | JSON array |

### Examples

```bash
auralogger get-logs -type '["error","warn"]' -maxcount 50
auralogger get-logs -message '["timeout"]' -skip 20 -maxcount 30
auralogger get-logs -type --not-in '["info","debug"]' -time --since '["10m"]'
auralogger get-logs -data.userId '["06431f39-55e2-4289-80c8-5d0340a8b66e"]'
```

### Common CLI errors

- `Expected 'get-logs'`
- `Expected field at position N`
- `Missing value for field 'x'`
- `Invalid JSON for field 'x'`
- `Field 'x' expects a JSON array token`
- `Field 'maxcount' expects a JSON number token`
- `Invalid op 'x' for field 'y'`
- `Unknown filter field: x`

---

## `auralogger client-check`

**Requirements:** `AURALOGGER_PROJECT_TOKEN`. Calls `proj_auth` to resolve `session`, then opens `WS /{project_token}/create_browser_logs` with **no auth headers** (path-only auth) and sends one test frame.

```bash
auralogger client-check
```

---

## `auralogger test-serverlog`

**Requirements:** same as real server logging (`AURALOGGER_PROJECT_TOKEN`, `AURALOGGER_USER_SECRET`, and reachable API when hydration is needed). Sends 5 logs via `aura_log(...)`, waits briefly, then closes the cached socket.

```bash
auralogger test-serverlog
```

---

## `auralogger test-clientlog`

**Requirements:** `AURALOGGER_PROJECT_TOKEN`. Calls `proj_auth` to resolve `session`, opens one `create_browser_logs` socket (path-only auth), sends 5 frames, then closes.

```bash
auralogger test-clientlog
```

---

## Typical first-time flow

```bash
cd /path/to/your/project
auralogger init
# paste printed lines into .env, then:
auralogger server-check
auralogger get-logs -maxcount 20
```
