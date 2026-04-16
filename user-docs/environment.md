# Environment variables (Python)

**Library / `aura_log`:** reads **`os.environ` only**. It does not read `.env` files. Use your framework or host to inject variables (Django settings, FastAPI + `python-dotenv` in *your* app entrypoint, systemd, etc.).

**CLI (`auralogger` command):** before each command, it loads **`.env`** then **`.env.local`** from the **current working directory** (same pattern as the Node CLI). So `auralogger server-check` in your project root picks up the same files you use locally.

## Primary variables (align with Node)

| Variable | Description |
|----------|-------------|
| `AURALOGGER_PROJECT_TOKEN` | Project-scoped token used by the CLI and server SDK to authenticate and look up your project. Treat as **private** (server-side apps and CI only). |
| `AURALOGGER_USER_SECRET` | **Server-side / CI secret only.** Required for server-side logging and fetching logs. Never expose this value in public repos or client bundles. |
| `AURALOGGER_PROJECT_SESSION` | Session string from `proj_auth` (printed by `auralogger init`). Optional for `aura_log` if the API is reachable and `proj_auth` can hydrate. |
| `AURALOGGER_PROJECT_ID` | Internal project id from `proj_auth`. Optional for `aura_log` when hydration runs. |
| `AURALOGGER_PROJECT_STYLES` | JSON string of style entries for terminal coloring. Optional for `get-logs` and `aura_log` when styles can be fetched via `proj_auth`. |

## Getting values

1. Run **`auralogger init`**.
2. If **`AURALOGGER_PROJECT_TOKEN`** or **`AURALOGGER_USER_SECRET`** is unset, the CLI prompts for missing values.
3. Copy the printed lines into `.env` / your environment.

## Commands vs runtime

| Context | What is required |
|---------|------------------|
| **`auralogger init`** | Loads `.env` / `.env.local` first. Optional: `AURALOGGER_PROJECT_TOKEN` and `AURALOGGER_USER_SECRET` in env to skip prompts. |
| **`auralogger server-check`** | Prompts for missing token/secret when needed, then sends a single **server-side** test log to verify connectivity. |
| **`auralogger test-serverlog`** | Prompts for missing token/secret, runs `auralogger.sync_from_secret(...)`, sends 5 logs, then closes the cached socket. |
| **`auralogger get-logs`** | `AURALOGGER_PROJECT_TOKEN` and `AURALOGGER_USER_SECRET`; styles from env or fetched once via `proj_auth` for that run. |
| **`aura_log()`** | `AURALOGGER_PROJECT_TOKEN` and `AURALOGGER_USER_SECRET`; id/session/styles from env or from a cached `proj_auth` fetch. Otherwise console-only with a one-time stderr hint. |

## Optional

| Variable | Purpose |
|----------|---------|
| `AURALOGGER_API_URL` | Override HTTP API base (`/api/*`). |
| `AURALOGGER_WS_URL` | Override WebSocket base. |
