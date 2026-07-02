# Auralogger CLI — setup and commands (Python)

User-facing reference: how to install, configure, and run the `auralogger` CLI.

Full variable reference: **[`environment.md`](environment.md)**.

## Setup

- **Python**: version 3.8 or newer.
- **Install:** `pip install auralogger`

The CLI loads **`.env`** and **`.env.local`** from your **current working directory** before each command. Run commands from the project root where those files live.

```bash
auralogger <command> [args...]
```

## Environment variables

Default API/WebSocket hosts need no URL config unless you override them. See **[`environment.md`](environment.md)** for `AURALOGGER_PROJECT_*` and optional base URLs.

## Commands overview

- `auralogger init` — authenticate and print copy-paste env lines.
- `auralogger server-check` — verify WebSocket connectivity.
- `auralogger test-serverlog` — send 5 server logger test logs.
- `auralogger get-logs [filters...]` — fetch and print logs.

For application logging from Python, import **`auralogger`** (the logger class) and **`aura_log`** from the **`auralogger`** package (see **`README.md`** in this folder).

If you run an unknown command, the CLI exits with code `1`, prints that the command was not recognized, and shows usage plus valid commands so you can retry quickly.

---

## `auralogger init`

**Flags:** none.

**Credentials:** `AURALOGGER_PROJECT_TOKEN` and `AURALOGGER_USER_SECRET` if both set in env; otherwise interactive prompts for whatever is missing. `AURALOGGER_PROJECT_SESSION` is never prompted — it is fetched from `proj_auth` and printed for copy-paste when not already in env.

Prints env lines for the project token, user secret, and session. Project id and styles are not in the copy block; runtime code hydrates them via `proj_auth` when needed.

The printed Python snippet calls `Auralogger.configure(project_token, user_secret, session=project_session)` (or token + session only when encryption is disabled). Session precedence at configure time: explicit arg → `AURALOGGER_PROJECT_SESSION` from env → `proj_auth`.

```bash
auralogger init
```

---

## `auralogger server-check`

**Credentials:** if `AURALOGGER_PROJECT_TOKEN` or `AURALOGGER_USER_SECRET` is missing after CLI `.env` load, the CLI prompts for missing values (same behavior as `init`). Sends a single **server-side** test log to verify connectivity from your environment.

```bash
auralogger server-check
```

---

## `auralogger get-logs`

**Requirements:** `AURALOGGER_PROJECT_TOKEN`, `AURALOGGER_USER_SECRET`, and `AURALOGGER_PROJECT_STYLES` (or equivalent style resolution via `proj_auth` for that run).

### Filter syntax

```text
-<field> [--<op>] <json-value-token>
```

- `field` starts with `-`.
- `op` is optional and starts with `--`.
- The value must be valid JSON.
- For `maxcount` and `nextpage`, the value must be a JSON number.
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
| `nextpage` | `eq` | `eq` | JSON number (cursor returned by the previous response) |
| `session` | `eq` | `eq` | JSON array of session strings. If `AURALOGGER_PROJECT_SESSION` is set and you omit `-session`, the CLI prepends this filter for you. |
| `data.<path>` | `eq` | `eq` | JSON array |

### Examples

```bash
auralogger get-logs -type '["error","warn"]' -maxcount 50
auralogger get-logs -message '["timeout"]' -nextpage 18423 -maxcount 30
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

## `auralogger test-serverlog`

**Credentials:** prompts for missing `AURALOGGER_PROJECT_TOKEN` / `AURALOGGER_USER_SECRET` values, runs `Auralogger.configure(project_token, user_secret)` (session from env or `proj_auth`), then sends 5 logs via `aura_log(...)`, waits briefly, and closes the cached socket.

```bash
auralogger test-serverlog
```

---

## Configuring the logger (`Auralogger.configure`)

Application code should call `Auralogger.configure(...)` once at startup (the `init` command prints a ready-made helper). Arguments:

| Argument | Source when omitted |
|----------|---------------------|
| `project_token` | `AURALOGGER_PROJECT_TOKEN` (or `NEXT_PUBLIC_` / `VITE_` alias) |
| `user_secret` | `AURALOGGER_USER_SECRET` |
| `session` | `AURALOGGER_PROJECT_SESSION` (or `NEXT_PUBLIC_` / `VITE_` alias), then `proj_auth` |

```python
from auralogger import Auralogger

# Encrypted project — session from env or proj_auth when session arg is empty.
Auralogger.configure(project_token, user_secret, session=project_session)

# Non-encrypted project — token + optional session only.
Auralogger.configure(project_token, session=project_session)
```

`Auralogger.sync_from_secret(project_token, user_secret, session=...)` accepts the same optional `session` argument with identical precedence.

---

## Typical first-time flow

```bash
cd /path/to/your/project
auralogger init
# paste printed lines into .env, then:
auralogger server-check
auralogger get-logs -maxcount 20
```
