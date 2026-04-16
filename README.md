# auralogger (Python)

Command-line client for [Auralogger](https://auralogger.com): `init`, `server-check`, `client-check`, `test-serverlog`, `test-clientlog`, and `get-logs`, plus the `aura_log` helper for Python apps.

```text
├── LICENSE
├── pyproject.toml
├── README.md
```

## Package naming (Node vs Python)

- Python distribution name: `auralogger` (install with `pip install auralogger`)
- Node distribution name: `auralogger-cli` (install with `npm install auralogger-cli`)
- Both expose the CLI command `auralogger`, but package names on package indexes are intentionally different.

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

```bash
cd /path/to/my-app
auralogger init
# add printed lines to .env, then:
auralogger server-check
```

`server-check` and `client-check` now follow the same credential UX as `init`: if token or user secret is missing after `.env` load, the CLI prompts for missing values before running checks.

The **`aura_log()`** library function reads **`os.environ` only**; it does not load `.env` files. In a web app, load env in your own startup code or rely on your host.

## Naming parity with Node

Python keeps snake_case naming, but key public names map directly to Node concepts:

| Node symbol | Python symbol(s) |
|-------------|------------------|
| `AuraServer` | `AuraServer` and `aura_log(...)` |
| `AuraServer.log(...)` | `AuraServer.log(...)` and `aura_log(...)` |
| `AuraServer.closeSocket(...)` | `AuraServer.close_socket(...)` and `close_aura_log_socket()` |
| `fetchProjAuthConfig(...)` | `fetch_proj_auth_config(...)` (`fetch_proj_auth_payload(...)` remains supported) |
| `AuraClient` / `clientlog(...)` | `AuraClient`, `client_log(...)`, and typed `auralog(ClientLogInputs(...))` |

Client SDK quickstart:

```python
from auralogger.client import AuraClient, ClientLogInputs, auralog

AuraClient.sync_from_secret("project-token")
auralog(
    ClientLogInputs(
        type="info",
        message="hello from client sdk",
        location="example/client",
        data={"source": "python"},
    )
)
```

## Using the generated `auralog(...)` helper

After `auralogger init`, paste the server snippet into your app (for example `your_server_auralog_file.py`), then use it like this:

```python
from your_server_auralog_file import auralog

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

`auralogger init` now has two Node-parity UX branches:

- If token + user secret + session are already in env, it prints an "already configured" success path and Python server integration snippet without re-calling `proj_auth`.
- Otherwise it fetches `proj_auth`, prints copy-paste env lines, and then prints the same integration snippet plus a frontend pointer (`auralogger-cli/client`).

## Requirements

Python 3.8+, `websocket-client`, and `python-dotenv` (declared in `pyproject.toml`).

## Contributor setup

Install editable package + development tooling (currently Ruff):

```bash
cd python
pip install -e ".[dev]"
```
