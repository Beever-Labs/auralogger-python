# Auralogger for Python (SDK + CLI)

 a real-time logging and observability SDK and CLI for streaming, storing, searching, and filtering application logs—beautifully visualized and accessible anywhere in the world across terminal, web, and any screen.

---

## Quick start

Run CLI commands from the directory that contains your `.env` or `.env.local` (or wherever you export `AURALOGGER_`* in the shell or CI). The CLI loads `.env` files from the **current working directory** — `cd` into the app first.

**Use a project virtualenv** (`python -m venv .venv`) so the CLI and library version match the repo you are in. Auralogger is **project-scoped** (credentials per app), not a global “install once and forget which folder you are in” tool.

### 1) Install

From PyPI:

```bash
pip install auralogger
```

```bash
auralogger
```

### 2) Run `init` (credentials + server snippet)

Get **private** credentials from [auralogger.com](https://auralogger.com), then run this in your app repo (where `.env` should live):

```bash
auralogger init
```

`auralogger init` walks you through anything missing, prints a **copy-paste block** for your `.env` (project token, user secret, session — each line skipped if already set), then prints a **small Python module** you can drop into your repo (for example `your_auralog_file.py`) with a ready-made `auralog(...)` helper .

### 3) Sanity-check connectivity

Before you sprinkle `auralog` everywhere, confirm the path works:

```bash
auralogger server-check
```

Optional: send a handful of test logs through the same path your app uses:

```bash
auralogger test-serverlog
```

If token or user secret is missing after `.env` is loaded, the CLI will prompt before running checks.

### 4) Send logs from code

Run `auralogger init` once and paste the printed module, or follow the shapes below.

**Encryption is optional per project.** If your project has **no encryption enabled**, you only need `AURALOGGER_PROJECT_TOKEN` and you can configure without a user secret. If your project **is encrypted**, you’ll configure with both `AURALOGGER_PROJECT_TOKEN` and `AURALOGGER_USER_SECRET`.

#### No encryption (recommended first): token only

```py
import os
from typing import Any, Dict, Literal, Optional
from auralogger import auralogger

def ensureConfigured() -> None:
    project_token = os.environ.get("AURALOGGER_PROJECT_TOKEN", "").strip()
    auralogger.configure(project_token)

def auralog(
    type: Literal["debug", "info", "warn", "error"],
    message: str,
    location: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> None:
    ensureConfigured()
    auralogger.log(type, message, location, data)
```

#### Encrypted projects: token + user secret

```py
import os
from typing import Any, Dict, Literal, Optional
from auralogger import auralogger

def ensureConfigured() -> None:
    project_token = os.environ.get('AURALOGGER_PROJECT_TOKEN', '').strip()
    user_secret = os.environ.get('AURALOGGER_USER_SECRET', '').strip()
    auralogger.configure(project_token, user_secret)
    # auralogger.configure()  — omit credentials to print locally only (no streaming for removing network delay and cost).
   

def auralog(
    type: Literal['debug', 'info', 'warn', 'error'],
    message: str,
    location: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> None:
    ensureConfigured()
    auralogger.log(
        type,
        message,
        location,
        data,
    )
```

```python
from your_auralog_file import auralog

auralog(
    "info",
    "Request completed",
    "api/orders#create",
    {"order_id": "ord_123", "status": 201},
)
# expected: [info] Request completed @ api/orders#create {"order_id": "ord_123", "status": 201}

auralog("warn", "Cache miss")
# expected: [warn] Cache miss

auralog("error", "Payment gateway timeout", data={"provider": "stripe"})
# expected: [error] Payment gateway timeout {"provider": "stripe"}
```

**Important:** the logging helper reads `**os.environ` only** — it does not load `.env` files by itself. In Django, FastAPI, Celery, etc., load env in your normal startup path (or rely on your host injecting variables).

### 5) Fetch logs in the terminal

```bash
auralogger get-logs -maxcount 20
```

Each run performs **one** HTTP request and prints the `logs` array from that response. Use `**-maxcount`** (capped at **100** in the CLI) and `**-skip`** to page manually across separate runs or a small script. Full filter grammar, every field, and examples are in **CLI commands (reference)** below.

---

## CLI commands (reference)

Subcommands for the `auralogger` entrypoint, then `**get-logs`** filters (same grammar as the Node CLI). Environment variable spellings: `[user-docs/environment.md](user-docs/environment.md)`.

### Invocation

```bash
auralogger <command> [arguments...]
```

Run `auralogger --help` to see all commands and options.

### Commands (only `get-logs` takes extra filter tokens)


| Command          | Arguments      | What it does                                                                                                                                                                                                                      |
| ---------------- | -------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `init`           | —              | Prompts for missing `AURALOGGER_PROJECT_TOKEN` / `AURALOGGER_USER_SECRET`, prints copy-paste `.env` lines (token, user secret, session), then a **Python** server integration snippet with `sync_from_secret` and `auralog(...)`. |
| `server-check`   | —              | One **server-side** test log over WebSocket; prompts for missing token or user secret if needed.                                                                                                                                  |
| `test-serverlog` | —              | Calls `sync_from_secret`, sends **5** logs via `aura_log`, then closes the cached socket.                                                                                                                                         |
| `get-logs`       | `[filters...]` | `POST` to project logs with token + user secret (env or prompt). If styles are not in env, the CLI resolves them for that run so terminal colors match the dashboard when possible.                                               |


### `get-logs` filter grammar

```text
-<field> [--<operator>] <json-value>
```

- The token after the field name must be **valid JSON**.
- `**maxcount`** and `**skip`**: value must be a JSON **number**.
- **All other fields**: value must be a JSON **array**.

**Paging:** one CLI invocation → one request → one page of logs. There is **no** automatic multi-page loop inside the CLI.

#### Fields and operators


| Field         | Allowed operators          | Default operator | Value shape                                                                                                                          |
| ------------- | -------------------------- | ---------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `type`        | `in`, `not-in`             | `in`             | JSON array of type strings                                                                                                           |
| `message`     | `contains`, `not-contains` | `contains`       | JSON array of substrings                                                                                                             |
| `location`    | `in`, `not-in`             | `in`             | JSON array of location strings                                                                                                       |
| `time`        | `since`, `from-to`         | `since`          | JSON array (e.g. `["10m"]` for `since`; use `from-to` with a pair when supported)                                                    |
| `order`       | `eq`                       | `eq`             | JSON array: `["newest-first"]` or `["oldest-first"]`                                                                                 |
| `maxcount`    | `eq`                       | `eq`             | JSON number, clamped to `0..100`                                                                                                     |
| `skip`        | `eq`                       | `eq`             | JSON number, floored, minimum `0`                                                                                                    |
| `session`     | `eq`                       | `eq`             | JSON array of session strings. If `AURALOGGER_PROJECT_SESSION` is set and you omit `-session`, the CLI prepends this filter for you. |
| `data.<path>` | `eq`                       | `eq`             | JSON array — filter on nested `data` using a dot path (e.g. `data.userId`)                                                           |


If you omit `--<operator>`, the default operator for that field is used (for example `-type '["error"]'` is the same as `-type --in '["error"]'`).

#### Examples

```bash
auralogger get-logs -type '["error","warn"]' -maxcount 50
auralogger get-logs -message '["timeout"]' -skip 20 -maxcount 30
auralogger get-logs -type --not-in '["info","debug"]' -time --since '["10m"]'
auralogger get-logs -data.userId '["06431f39-55e2-4289-80c8-5d0340a8b66e"]'
auralogger get-logs -order '["oldest-first"]' -maxcount 25
```

#### Common parse errors (filters)

- `Expected 'get-logs'`
- `Expected field at position N`
- `Missing value for field '…'`
- `Invalid JSON for field '…'`
- `Field '…' expects a JSON array token`
- `Field 'maxcount' expects a JSON number token` (and similarly for `skip`)
- `Invalid op '…' for field '…'`
- `Unknown filter field: …`

---

## Browser and frontends

This package is for **Python on the server**. For React, Vue, Next, Vite, or any code bundled for the browser, use the `**auralogger-cli`** npm package and its **client** entry — **project token only** there, never `AURALOGGER_USER_SECRET` in frontend bundles.

---

## When something does not work

- **Wrong directory** — Run the CLI from the folder that contains `.env`, or export variables in the shell.
- **Logs never reach the dashboard** — Confirm `AURALOGGER_PROJECT_TOKEN` and `AURALOGGER_USER_SECRET` are set for the process (or passed explicitly in your configure step). Logs always print locally — if they're not reaching the dashboard, check credentials and network; send/socket failures surface as stderr messages.
- `**get-logs` looks plain** — Optional style env vars are documented in `[user-docs/environment.md](user-docs/environment.md)`; the CLI can still resolve styling for a run when those are unset.

---

## Requirements

Python **3.8+**.