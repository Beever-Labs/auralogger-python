# Environment variables (Python)

**Library / `aura_log`:** reads **`os.environ` only**. It does not read `.env` files. Use your framework or host to inject variables (Django settings, FastAPI + `python-dotenv` in *your* app entrypoint, systemd, etc.).

**CLI (`auralogger` command):** before each command, it loads **`.env`** then **`.env.local`** from the **current working directory** (same pattern as the Node CLI). So `auralogger server-check` in your project root picks up the same files you use locally.

## Primary variables (align with Node)

| Variable | Description |
|----------|-------------|
| `AURALOGGER_PROJECT_TOKEN` | Ciphertext project token. Used in URL paths: `POST /api/{token}/proj_auth`, `POST /api/{token}/logs`, and `WS /{token}/create_log`. No `secret` header on `proj_auth`. |
| `AURALOGGER_USER_SECRET` | User secret. Sent as HTTP headers **`secret`** and **`user_secret`** on `POST /api/{token}/logs` (both set to this value). Sent on the server ingest WebSocket as **`Authorization: Bearer <user_secret>`**. |
| `AURALOGGER_PROJECT_SESSION` | Session string from `proj_auth` (printed by `auralogger init`). Optional for `aura_log` if the API is reachable and `proj_auth` can hydrate. |
| `AURALOGGER_PROJECT_ID` | Internal project id from `proj_auth`. Optional for `aura_log` when hydration runs. |
| `AURALOGGER_PROJECT_STYLES` | JSON string of style entries for terminal coloring. Optional for `get-logs` and `aura_log` when styles can be fetched via `proj_auth`. |

**Bundler aliases (same values as above):** `NEXT_PUBLIC_AURALOGGER_PROJECT_TOKEN`, `VITE_AURALOGGER_PROJECT_TOKEN`, and the matching `NEXT_PUBLIC_*` / `VITE_*` keys for id, session, and styles are read with the same precedence as the Node SDK.

## Legacy

If **`AURALOGGER_USER_SECRET`** is unset but **`AURALOGGER_PROJECT_SECRET`** is set, the library treats the legacy value as the **user secret** and prints a one-time deprecation notice on stderr. You still need **`AURALOGGER_PROJECT_TOKEN`** for path-based routes. Migrate to `AURALOGGER_USER_SECRET`.

Older names such as `AURALOGGER_SECRET_KEY` are **not** read.

## Getting values

1. Run **`auralogger init`**.
2. If **`AURALOGGER_PROJECT_TOKEN`** or **`AURALOGGER_USER_SECRET`** is unset, the CLI prompts for missing values.
3. Copy the printed lines into `.env` / your environment.

## Commands vs runtime

| Context | What is required |
|---------|------------------|
| **`auralogger init`** | Loads `.env` / `.env.local` first. Optional: `AURALOGGER_PROJECT_TOKEN` and `AURALOGGER_USER_SECRET` in env to skip prompts. |
| **`auralogger server-check`** | `AURALOGGER_PROJECT_TOKEN` and `AURALOGGER_USER_SECRET`; calls `proj_auth` then opens `WS …/create_log` with Bearer auth and sends a test log. |
| **`auralogger get-logs`** | `AURALOGGER_PROJECT_TOKEN` and `AURALOGGER_USER_SECRET`; styles from env or fetched once via `proj_auth` for that run. |
| **`aura_log()`** | `AURALOGGER_PROJECT_TOKEN` and `AURALOGGER_USER_SECRET`; id/session/styles from env or from a cached `proj_auth` fetch. Otherwise console-only with a one-time stderr hint. |

## Optional

| Variable | Purpose |
|----------|---------|
| `AURALOGGER_API_URL` | Override HTTP API base (`/api/*`). |
| `AURALOGGER_WS_URL` | Override WebSocket base. |
