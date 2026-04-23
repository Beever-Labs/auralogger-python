<!-- Generated: 2026-04-23 UTC — ultra-detailed execution + integration reference -->
# Feature flows (CLI + SDK) — deep trace (Python)

This document is the **line-by-line behavioural map** for everything under `python/auralogger/`: how the CLI entrypoint dispatches, how each command and the SDK class talks to HTTP/WebSocket, where credentials live, which **optimisations** exist (proj_auth cache, batch flush, socket reuse, retry logic), and what the `encrypted` flag controls.

Companion docs: **[`routes.md`](routes.md)** (HTTP/WS paths + auth), **[`file-map.md`](file-map.md)** (edit locations), **[`../docs/BDD/`](../docs/BDD/)** (observable behaviour).

All paths below are relative to the **`python/auralogger/`** package root unless noted.

Node parity reference: `node/dev-docs/feature-flows.md` — both packages implement the same wire contract.

---

## Table of contents

1. [Credential matrix](#credential-matrix)
2. [Package bootstrap: `pyproject.toml` → `_entrypoint` → `main`](#package-bootstrap)
3. [Shared wire utilities](#shared-wire-utilities)
4. [Styling pipeline (`proj_auth` → terminal)](#styling-pipeline)
5. [Flow: `auralogger init`](#flow-auralogger-init)
6. [Flow: `auralogger get-logs`](#flow-auralogger-get-logs)
7. [Flow: `auralogger server-check`](#flow-auralogger-server-check)
8. [Flow: `auralogger test-serverlog`](#flow-auralogger-test-serverlog)
9. [Flow: `aura_log` / `auralogger.log` — core logging path](#flow-aura_log--auraloggerlog)
10. [Batch / flush subsystem](#batch--flush-subsystem)
11. [WebSocket connection management (`_ensure_ws`)](#websocket-connection-management)
12. [Class: `auralogger` (configure / sync / log / close)](#class-auralogger)
13. [Cross-cutting: `encrypted` flag, retry, thread safety](#cross-cutting)
14. [When you add a command](#when-you-add-a-command)
15. [Quick reference — optimisation checklist](#quick-reference--optimisation-checklist)

---

## Credential matrix

| Flow | Project token | User secret | Encrypted check | HTTP base | WS base |
|------|---------------|-------------|-----------------|-----------|---------|
| **`init`** | Path on `proj_auth`; env or prompt | Prompt/env (encrypted only); **not** sent on `proj_auth` | `encrypted` field from response (bool or `"true"` string) | `resolve_api_base_url()` | — |
| **`get-logs`** | Path on `/api/{token}/logs` | Headers `secret` + `user_secret` (encrypted path only) | `proj_auth` if secret not in env | `resolve_api_base_url()` | — |
| **`server-check`** | Path on `proj_auth` + WS URL | `Authorization: Bearer` header on WS | Always encrypted (Bearer WS) | `resolve_api_base_url()` for `proj_auth` | `resolve_ws_base_url()` |
| **`test-serverlog`** | `sync_from_secret`, then SDK path | Bearer on WS | `proj_auth` encrypted field | `resolve_api_base_url()` | `resolve_ws_base_url()` |
| **`aura_log` (SDK)** | Module-level override or env | Module-level override or env | `_encrypted` flag (set by `configure`/`sync_from_secret`) | `resolve_api_base_url()` for proj_auth | `resolve_ws_base_url()` for ingest |

**`encrypted` flag decoding** (applied in three places — all must agree):

```python
# server/aura_log.py: _read_encrypted_flag(raw)
enc = raw.get("encrypted")
if enc is None:
    enc = raw.get("encryption")   # back-compat alias
if enc is True or enc == "true":  # PostgREST may send the string "true"
    return True
if enc is False or enc == "false":
    return False
return True  # safe default
```

---

## Package bootstrap

### `pyproject.toml` → console script

```toml
[project.scripts]
auralogger = "auralogger.cli.cli:_entrypoint"
```

`pip install auralogger` wires the `auralogger` binary → `cli/cli.py:_entrypoint`.

### `_entrypoint()` — top-level exception wrapper

```python
# cli/cli.py
def _entrypoint() -> None:
    ensure_utf8_stdio()          # force UTF-8 on Windows for emoji output
    try:
        main()
    except SystemExit:
        raise                    # let sys.exit() pass through unchanged
    except Exception as exc:
        record_cli_failure()
        message = str(exc)
        print(red_bold("💥 That didn't work."), file=sys.stderr)
        print(dim("   ") + white(message), file=sys.stderr)
        fails = get_consecutive_failures()
        if fails >= 2 and random.random() < 0.45:
            print_aside(WOLVERINE_NUDGE_ASIDES)
        aside = pick_adaptive_fatal_aside(fails, message)
        print_aside_maybe(aside["emoji"], aside["line"], 0.08)
        err_kind = classify_error_for_aside(message)
        if err_kind in ("network", "auth-env") and random.random() < 0.42:
            print_aside(ENV_SETUP_RECOVERY_ASIDES)
        maybe_print_generic_spice()
        sys.exit(1)
```

`SystemExit` is re-raised so `sys.exit(1)` in the unknown-command path propagates cleanly. All other exceptions are caught here — no unhandled tracebacks reach the user.

### `main()` — argv dispatch

```python
# cli/cli.py
KNOWN_COMMANDS = {"init", "get-logs", "server-check", "test-serverlog"}

def main() -> None:
    ensure_utf8_stdio()
    load_cli_env_files()          # load .env / .env.local into os.environ (idempotent)

    args: List[str] = sys.argv[1:]
    command = args[0] if args else None

    if not command:
        print_usage()             # banner + aside, returns cleanly
        return

    if command not in KNOWN_COMMANDS:   # O(1) set lookup
        record_cli_failure()
        print(red("🤔 Hmm, never heard of ") + bold(command) + red("."), file=sys.stderr)
        t = pick_aside(BIN_UNKNOWN_COMMAND_TEMPLATES)
        print_aside_maybe(t["emoji"], format_aside_template(t["line"], {"cmd": command}), DEFAULT_SILENCE_ASIDE_CHANCE)
        print_usage(sys.stderr)
        sys.exit(1)

    note_command_dispatch(command)   # personality-state counter for repeat-intent nudges

    if command == "init":
        run_init()
        record_cli_success(command)
        return

    if command == "get-logs":
        run_get_logs_command(args)   # passes full argv so parse_command sees "get-logs" at [0]
        record_cli_success(command)
        return

    if command == "server-check":
        run_server_check()
        record_cli_success(command)
        return

    if command == "test-serverlog":
        run_test_serverlog()
        record_cli_success(command)
        return
```

- `load_cli_env_files()` runs at every dispatch path — dotenv merge is idempotent for fixed cwd.
- Python CLI has **4 commands** (no `client-check`, no `test-clientlog` — browser path not in Python).
- `get-logs` receives the **full `args` array** (including `"get-logs"` at index 0) because `parse_command(argv)` expects `argv[0] == "get-logs"`.

### `load_cli_env_files` (disk → `os.environ`)

```python
# cli/cli_load_env.py
def load_cli_env_files(cwd: Optional[str] = None) -> None:
    base = cwd or os.getcwd()
    _load_dotenv(os.path.join(base, ".env"))
    _load_dotenv(os.path.join(base, ".env.local"), override=True)

def ensure_utf8_stdio() -> None:
    # Reconfigures sys.stdout / sys.stderr to UTF-8 on Windows
    # Prevents UnicodeEncodeError for emoji output on legacy Windows code pages
```

The **runtime logger** (`aura_log` / `auralogger.log`) does **not** call `load_cli_env_files` — library code must not mutate environment on import. Credentials must be injected via `auralogger.configure()` or already be in `os.environ` when `aura_log()` is called.

---

## Shared wire utilities

### URL builders — `utils/backend_origin.py`

```python
DEFAULT_AURALOGGER_ORIGIN     = "https://api.auralogger.com"
DEFAULT_AURALOGGER_WEB_ORIGIN = "https://auralogger.com"

def resolve_api_base_url() -> str:
    from_env = os.environ.get("AURALOGGER_API_URL", "").strip()
    if from_env:
        return trim_trailing_slash(from_env)
    return DEFAULT_AURALOGGER_WEB_ORIGIN      # used for HTTP /api/* routes

def resolve_ws_base_url() -> str:
    from_env = os.environ.get("AURALOGGER_WS_URL", "").strip()
    if from_env:
        return trim_trailing_slash(from_env)
    return http_origin_to_ws_base(DEFAULT_AURALOGGER_ORIGIN)
    # http_origin_to_ws_base("https://api.auralogger.com") → "wss://api.auralogger.com"

def build_proj_auth_url(api_base_url, project_token) -> str:
    # POST /api/{encodeURIComponent(token)}/proj_auth — no auth headers
    return f"{trim_trailing_slash(api_base_url)}/api/{_encode_path_token(project_token)}/proj_auth"

def build_project_logs_url(api_base_url, project_token) -> str:
    # POST /api/{encodeURIComponent(token)}/logs — headers secret + user_secret
    return f"{trim_trailing_slash(api_base_url)}/api/{_encode_path_token(project_token)}/logs"
```

Same host split as Node: HTTP routes use `WEB_ORIGIN` (`auralogger.com`); WS ingest uses `api.auralogger.com` → `wss://api.auralogger.com`.

### Token / secret readers — `utils/env_config.py`

```python
def get_resolved_project_token() -> Optional[str]:
    # AURALOGGER_PROJECT_TOKEN → NEXT_PUBLIC_AURALOGGER_PROJECT_TOKEN → VITE_AURALOGGER_PROJECT_TOKEN
    return _trim_env_any((ENV_PROJECT_TOKEN, ENV_NEXT_PUBLIC_PROJECT_TOKEN, ENV_VITE_PROJECT_TOKEN))

def get_resolved_user_secret() -> Optional[str]:
    return _trim_env(ENV_USER_SECRET)    # single key — no public variants

def get_resolved_session() -> Optional[str]:
    return _trim_env_any((ENV_PROJECT_SESSION, ENV_NEXT_PUBLIC_PROJECT_SESSION, ENV_VITE_PROJECT_SESSION))

def try_parse_resolved_styles() -> Optional[List[Any]]:
    # AURALOGGER_PROJECT_STYLES / NEXT_PUBLIC_… / VITE_… → JSON.parse → list or None
    raw = _trim_env_any(STYLES_KEYS)
    if raw is None:
        return None
    parsed = json.loads(raw)
    return parsed if isinstance(parsed, list) else None

def is_full_runtime_env_configured() -> bool:
    # Fast-path gate for init — True when token + user_secret + session all present
    return bool(
        get_resolved_project_token()
        and get_resolved_user_secret()
        and get_resolved_session()
    )
```

### `proj_auth` shared helper — `server/proj_auth.py`

```python
def fetch_proj_auth_payload(project_token: str) -> Dict[str, Any]:
    url = build_proj_auth_url(resolve_api_base_url(), project_token)
    req = urllib.request.Request(url, data=b"", method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            raw_body = resp.read()
            headers = resp.headers
    except urllib.error.HTTPError as e:
        status, raw_body, headers = e.code, e.read(), e.headers
    except urllib.error.URLError as e:
        raise ValueError(f"Can't reach Auralogger right now — check network. ({e.reason}) {ENV_RECOVERY_HINT_PLAIN}")

    if status < 200 or status >= 300:
        raise ValueError(parse_error_body(status, headers.get("content-type",""), raw_body))

    auth_response = json.loads(raw_body.decode("utf8"))
    if not isinstance(auth_response, dict):
        raise ValueError("Authentication response had an unexpected shape.")
    return auth_response  # raw dict — callers decode encrypted/styles/session etc.
```

`fetch_proj_auth_config` is an alias for Node-parity naming. Both names are in the public API.

**Used by:** `cli_auth.resolve_project_context_for_cli_checks`, `commands/init.run_init`, `aura_log._fetch_proj_auth_cached`, `auralogger.configure`, `auralogger.sync_from_secret`.

### HTTP error extraction — `utils/http_utils.py`

```python
def parse_error_body(status: int, content_type: str, raw: bytes) -> str:
    if "application/json" not in content_type:
        return f"Request failed with status {status}."
    body = json.loads(raw.decode("utf8"))
    if isinstance(body, dict) and isinstance(body.get("error"), str) and body["error"].strip():
        return body["error"].strip()
    return f"Request failed with status {status}."
```

---

## Styling pipeline

### Style spec normalisation — `cli/log_styles.py`

```python
DEFAULT_LOG_STYLE_SPEC = {
    "icon": "🔹",
    "type-color":     [200, 160, 255],
    "location-color": [63, 102, 191],
    "time-color":     [210, 200, 255],
    "message-color":  [220, 200, 255],
    "text-color":     [250, 245, 255],
}

BUILTIN_TYPE_STYLE_OVERRIDES = {
    "ERROR":   {"icon": "❌", "type-color": [255,80,80],   "message-color": [255,140,140], ...},
    "FAIL":    {"icon": "💥", "type-color": [255,40,120],  ...},
    "SUCCESS": {"icon": "✅", "type-color": [0,255,200],   ...},
    "INFO":    {"icon": "ℹ️",  "type-color": [80,200,255],  ...},
    "WARNING": {"icon": "⚠️",  "type-color": [255,220,0],   ...},
    ...
}

def resolve_log_style_spec(log_type: str, config_styles: Any) -> Dict[str, Any]:
    # 1. Deep-copy DEFAULT_LOG_STYLE_SPEC as base
    # 2. Look up BUILTIN_TYPE_STYLE_OVERRIDES[UPPERCASE(log_type)] and merge on top
    # 3. Walk config_styles list for entry matching log_type (API styles)
    # 4. Merge API entry on top — API overrides builtins
    # Returns: spec dict with icon, type-color, message-color, location-color, time-color, text-color
```

`build_style_entries_from_api` sorts rows by `importance` field before building the lookup map, stabilising precedence when the API sends rows out of order.

### Terminal render — `cli/log_print.py`

```python
def print_log(log: Mapping[str, Any], config_styles: Any = None) -> None:
    spec = resolve_log_style_spec(log.get("type", ""), config_styles)

    created = _format_created_at_time_only(log.get("created_at"))
    # Parses ISO 8601 → UTC time-of-day string "HH:MM:SS"; graceful on bad input

    # Line 1: dim(rgb(time, time-color))    rgb(location, location-color)
    line1 = f"{_dim(_rgb(created, spec['time-color']))}    {_rgb(loc, spec['location-color'])}"

    # Line 2: icon  rgb(type, type-color)  rgb(message, message-color)
    message_line = f"{icon} {_rgb(type_disp, spec['type-color'])} {_rgb(msg, spec['message-color'])}"

    # Line 3 (optional): dim(rgb(data, text-color)) — only if data is non-empty string
    parts = [line1, message_line]
    if data is not None and str(data).strip():
        parts.append(_dim(_rgb(str(data), spec.get("text-color"))))

    _print_stdout_line("\n".join(parts))
    # _print_stdout_line(): tries print(), falls back to buffer.write(encode(errors="replace"))
    #   — prevents UnicodeEncodeError on Windows legacy consoles
```

`_rgb(text, rgb)` emits `\033[38;2;R;G;Bm{text}\033[0m` (true-color ANSI). If `rgb` is not a valid `[R,G,B]` list it passes `text` through unchanged — style failures never crash printing.

---

## Flow: `auralogger init`

### Entry and fast-path

```python
# commands/init.py
def run_init() -> None:
    ensure_utf8_stdio()

    # Repeat-intent nudge shown randomly when user runs init a second time
    if get_command_attempt_count("init") >= 2:
        print_aside_maybe(INIT_REPEAT_INTENT_ASIDES, 0.12)

    # Fast-path A: token + user_secret + session all in env → skip proj_auth + prompts
    if is_full_runtime_env_configured():
        print_already_configured_success(encrypted=True)
        maybe_print_generic_spice()
        return
```

### Credential resolution

```python
    has_project_token  = get_resolved_project_token() is not None
    project_token_was_in_env = has_project_token
    has_user_secret    = get_resolved_user_secret() is not None
    user_secret_was_in_env = has_user_secret
    has_session        = get_resolved_session() is not None
    session_was_in_env = has_session

    print_init_welcome_banner()

    if has_project_token and not has_session:
        # Token spotted but no session — hint: fetching the rest from proj_auth
        print_aside(INIT_STRANGE_TOKEN_ASIDES)

    project_token = resolve_project_token_for_init()
    # resolve_project_token_for_init():
    #   t = get_resolved_project_token()  → env lookup (primary, next_public, vite)
    #   if t: return t
    #   return prompt_for_project_token()  → prints hint aside, then input()
```

### HTTP: `fetch_proj_auth_payload`

```python
    raw = fetch_proj_auth_payload(project_token)
    # POST /api/{encoded_token}/proj_auth — no auth headers
    # raw = {project_id, session, styles, encrypted, name/project_name, ...}

    payload = build_init_payload(raw, project_token)
    # build_init_payload():
    #   styles_raw = raw.get("styles"); api_rows = styles_raw if list else []
    #   enc = raw.get("encrypted"); if not bool: enc = raw.get("encryption")
    #   return {
    #     "project_token": project_token,
    #     "project_id":    raw.get("project_id"),
    #     "session":       raw.get("session"),
    #     "styles":        build_style_entries_from_api(api_rows),  ← normalised list
    #     "encrypted":     enc if isinstance(enc, bool) else True,
    #   }
```

### Post-hydration fast-paths (once encrypted flag known)

```python
    encrypted = payload["encrypted"]

    # Fast-path B: non-encrypted + token + session already in env
    if not encrypted and has_project_token and has_session:
        print_already_configured_success(encrypted=False)
        maybe_print_generic_spice()
        return

    # Fast-path C: encrypted + all three already in env
    if encrypted and has_project_token and has_user_secret and has_session:
        print_already_configured_success(encrypted=True)
        maybe_print_generic_spice()
        return

    user_secret = ""
    if encrypted:
        user_secret = resolve_user_secret_for_init()
        # → get_resolved_user_secret() or prompt_for_user_secret() → input()
```

### Output

```python
    print_post_init_summary(payload, project_token_was_in_env, user_secret_was_in_env, session_was_in_env, user_secret)
    # 1. print_copy_paste_env_block():
    #      for each of token/secret/session not already in env:
    #        print formatted DOTENV line: KEY="value"
    #      prints "was already set — omitted" notes for pre-existing keys
    #      encrypted=False: omits user_secret line entirely
    # 2. print_init_helper_snippets(encrypted):
    #      syntax-highlighted Python snippet: import, configure(), auralog() wrapper
    #      encrypted=False variant: configure(project_token) only (no secret arg)
    #      usage snippet with example auralog() calls
```

---

## Flow: `auralogger get-logs`

### Entry

```python
# commands/get_logs_cmd.py → cli/get_logs.py
def run_get_logs(argv: List[str]) -> None:
    ensure_utf8_stdio()

    # Personality: nudge if running get-logs before init ever succeeded
    if not get_resolved_project_token() and get_successful_run_count("init") == 0:
        print_aside_maybe(GET_LOGS_SKIPPED_SETUP_INTENT_ASIDES, 0.12)

    print("📜 get-logs — opening the archive…")
    a = pick_aside(GET_LOGS_OPEN_ASIDES)
    print_aside_maybe(a["emoji"], a["line"], 0.12)
    project_token = resolve_project_token_for_init()
    # → env or input() prompt
```

### Auth + styles resolution (env short-circuit = optimisation)

```python
    user_secret = ""
    config_styles = try_parse_resolved_styles()    # env fast-path for styles

    if get_resolved_user_secret() is not None:
        # Secret already in env → assume encrypted, skip proj_auth
        user_secret = resolve_user_secret_for_init()
    else:
        # No secret in env → proj_auth to discover encrypted flag + styles
        print("🔐 Authenticating with Auralogger…")
        try:
            raw = fetch_proj_auth_payload(project_token)
            encrypted = raw.get("encrypted")
            if encrypted:
                user_secret = resolve_user_secret_for_init()   # env or prompt
            if config_styles is None:
                rows = raw.get("styles") if isinstance(raw.get("styles"), list) else []
                config_styles = build_style_entries_from_api(rows)
        except ValueError as e:
            # Network/auth failure: still proceed; prompt for secret
            print(f"⚠️ Couldn't reach Auralogger for auth ({e}). Using env config if available.")
            user_secret = resolve_user_secret_for_init()

    if config_styles is None:
        config_styles = build_style_entries_from_api([])    # empty → builtins only
```

If both `AURALOGGER_USER_SECRET` and `AURALOGGER_PROJECT_STYLES` are in env — **zero extra HTTP calls** before fetching logs.

If `proj_auth` fails, `get-logs` still proceeds — uses default terminal colours.

### Filter parsing → API filter JSON

```python
    parsed = parse_command(argv)
    # parse_command() in utils/parser.py:
    #   assert argv[0] == "get-logs"
    #   scan for -field [--op] <json-token> triples
    #   return ParsedCommand(filters=[ParsedFilter(field, op, value)])

    filters = with_default_session_filter(
        normalize_and_validate_filters(parsed.filters),
        get_resolved_session(),
    )
    # get_logs_filters.py:
    #   for each filter:
    #     default_op = defaultOpForField(field)  e.g. "type"→"in", "time"→"since"
    #     allowed_ops = allowedOpsForField(field)
    #     raise ValueError if op not in allowed list
    #     clamp: maxcount → min(max(0, floor(v)), 100)
    #            nextpage → floor(v)
    #     emit {field, value, op?}  (op omitted when equal to default)
```

### HTTP: `_post_logs`

```python
def _post_logs(base_url, project_token, user_secret, filters):
    route = build_project_logs_url(base_url, project_token)
    body = json.dumps({"filters": filters}).encode("utf8")
    headers = {"Content-Type": "application/json"}
    if user_secret:
        headers["secret"] = user_secret       # primary auth header
        headers["user_secret"] = user_secret  # compat alias — both sent always

    req = urllib.request.Request(route, data=body, method="POST", headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print("⚠️ POST /api/{token}/logs returned 404 — wrong API host, old backend, or route not deployed. Check AURALOGGER_API_URL.")
            return {"logs": []}, True      # soft-fail: empty result, no traceback
        # non-404 HTTP error → parse_error_body + raise ValueError
        # 401/403 → append ENV_RECOVERY_HINT_PLAIN
    except urllib.error.URLError as e:
        raise ValueError(f"Can't reach Auralogger to fetch logs — check connection. ({e.reason})")

    body_parsed = json.loads(raw.decode("utf8"))
    if not isinstance(body_parsed, dict):
        raise ValueError("The log list didn't look right. Weird — try again.")
    return body_parsed, False
```

### Rendering loop

```python
    print("📦 Fetching logs…")
    logs = body.get("logs") if isinstance(body.get("logs"), list) else []
    if len(logs) == 0:
        if not logs_endpoint_not_found:
            print("👻 Nothing matched — try looser filters or bigger -maxcount")
            print_aside(GET_LOGS_EMPTY_ASIDES)
        return

    printed = 0
    for item in logs:
        if isinstance(item, dict):     # type guard — skips garbage array entries silently
            print_log(item, config_styles)
            printed += 1
    if printed > 0:
        t = pick_aside(GET_LOGS_SUCCESS_TEMPLATES)
        print_aside(t["emoji"], format_aside_template(t["line"], {"n": printed}))
        nextpage = body.get("nextpage")
        if isinstance(nextpage, int):
            print(f"📄 More results: auralogger get-logs -nextpage {nextpage}")
```

---

## Flow: `auralogger server-check`

### Sequence

```python
# commands/server_check.py
def run_server_check() -> None:
    ensure_utf8_stdio()
    context = resolve_project_context_for_cli_checks()
    # cli_auth.py — resolve_project_context_for_cli_checks():
    #   project_token = resolve_project_token_for_init()  → env or prompt
    #   user_secret   = resolve_user_secret_for_init()    → env or prompt
    #   raw = fetch_proj_auth_payload(project_token)      → POST proj_auth
    #   project_id   = raw["project_id"].strip()
    #   project_name = (raw.get("name") or raw.get("project_name") or "").strip()
    #   session      = raw["session"].strip()
    #   if not project_id or not session: raise ValueError
    #   return CliProjectContext(project_token, user_secret, project_id, project_name, session)

    ws_url = f"{resolve_ws_base_url()}/{quote(project_token, safe='-_.!~*()')}/create_log"
    auth_header = f"Authorization: Bearer {user_secret}"
```

### WebSocket send with retry loop

```python
    CONNECT_TIMEOUT_S = 5
    MAX_RETRIES = 2     # 3 total attempts

    def _send_attempt() -> None:
        try:
            ws = create_connection(ws_url, timeout=5, header=[auth_header])
        except WebSocketTimeoutException:
            raise ValueError("socket didn't open in time — check VPN, firewall, AURALOGGER_WS_URL")
        except Exception as e:
            raise ValueError(f"Server pipe wouldn't open ({e})")

        payload = {
            "type":       "info",
            "message":    "this is from cli server-check",
            "location":   "cli/server-check",
            "session":    session,
            "created_at": _iso_timestamp_with_micros(time.time() * 1000),
            "data":       json.dumps({"kind": "server-check"}),
        }
        # data field is a JSON string — same wire shape as AuraServer payloads

        try:
            ws.send(json.dumps(payload))
        except Exception as e:
            ws.close()
            raise ValueError(f"Log didn't send — {e}")
        ws.close()

    for attempt in range(1, MAX_RETRIES + 2):   # 1, 2, 3
        try:
            _send_attempt()
            break
        except Exception:
            if attempt > MAX_RETRIES:
                raise                # re-raise after exhausting retries
            print_aside(CHECK_RETRY_ASIDES)
            print(f"🔁 Retrying server-check (attempt {attempt+1}/{MAX_RETRIES+1})...")
            time.sleep(RETRY_WAIT_S)  # 0.7 s between attempts

    label = project_name or project_id
    print(f"🎉 Server logger is alive — a test log just took off for project {label}.")
```

Python `server-check` retries up to **3 total attempts** (0.7 s apart). Node `server-check` makes a **single attempt** with no retry.

---

## Flow: `auralogger test-serverlog`

```python
# commands/test_serverlog.py
def run_test_serverlog() -> None:
    ensure_utf8_stdio()
    project_token = resolve_project_token_for_init()   # env or prompt
    user_secret   = resolve_user_secret_for_init()     # env or prompt

    auralogger.sync_from_secret(project_token, user_secret)
    # sync_from_secret():
    #   raw = fetch_proj_auth_payload(project_token)    → POST proj_auth
    #   enc = _read_encrypted_flag(raw)                → bool
    #   if enc and not user_secret: raise RuntimeError
    #   _apply_runtime_config(project_token, user_secret, enc)
    #     → sets _override_project_token, _override_user_secret, _encrypted
    #     → resets _local_session_id, clears _hydration_cache_*
    #   validate project_id + session present in raw
    #   populate _hydration_cache_token / _hydration_cache_raw
    # After this call: first aura_log() will find cache already warm

    for i in range(1, 6):
        aura_log("info", f"test-serverlog log {i}/5", "cli/test-serverlog", {"i": i, "kind": "test-serverlog"})
        time.sleep(0.15)           # 150 ms between each log (allows batch window to partially fill)

    time.sleep(0.8)                # wait for the 30 ms flush timer to fire
    close_aura_log_socket()
    # close_aura_log_socket():
    #   _flush_buffer_now(token, secret)   → sends any remaining buffered payloads
    #   _close_ws_connection()             → ws.close()
    #   clears _hydration_cache_* entries
```

---

## Flow: `aura_log` / `auralogger.log`

This is the **core logging path** — every call from application code runs through here.

### Step 1 — resolve credentials (module globals win over env)

```python
# server/aura_log.py
def aura_log(type, message, location=None, data=None) -> None:
    project_token = _resolve_project_token_runtime()
    # if _override_project_token is not None and .strip():
    #     return _override_project_token.strip()
    # else:
    #     return get_resolved_project_token()  → AURALOGGER_PROJECT_TOKEN / NEXT_PUBLIC_… / VITE_…

    user_secret = _resolve_user_secret_runtime()
    # if _override_user_secret is not None and .strip():
    #     return _override_user_secret.strip()
    # else:
    #     return get_resolved_user_secret()  → AURALOGGER_USER_SECRET
```

### Step 2 — build local payload (always, even without token)

```python
    payload: Dict[str, Any] = {
        "type":       _normalize_type(type),
        # _normalize_type(): (raw or "").strip() → "unknown" if empty

        "message":    "" if message is None else str(message),

        "session":    _get_or_create_local_session(),
        # _get_or_create_local_session():
        #   if _local_session_id is None:
        #       _local_session_id = str(uuid.uuid4())
        #   return _local_session_id
        # NOTE: this is a process-local UUID, replaced by the real project session before send

        "created_at": _iso_timestamp_utc(),
        # datetime.now(timezone.utc) formatted as "YYYY-MM-DDTHH:MM:SS.microsecondsZ"
    }

    loc = _normalize_location(location)
    # _normalize_location(): None if not str or empty after strip
    if loc is not None:
        payload["location"] = loc

    data_str = _maybe_data(data)
    # _maybe_data():
    #   None     → None
    #   str      → str (pass-through)
    #   dict     → json.dumps(data) or None on serialisation error
    #   anything else (int, list, bool, …) → None (dropped silently)
    if data_str is not None:
        payload["data"] = data_str
```

### Step 3 — local console echo (always, even without network config)

```python
    styles = _styles_for_console(project_token, merged=None)
    # _styles_for_console():
    #   s = try_parse_resolved_styles()       → env fast-path (AURALOGGER_PROJECT_STYLES)
    #   if s is not None: return s
    #   if project_token:
    #       raw = _fetch_proj_auth_cached(project_token)  → cached HTTP, 3-retry
    #       if raw: rows = raw.get("styles", [])
    #               return build_style_entries_from_api(rows)
    #   return None                           → print_log falls back to builtins

    try:
        print_log(payload, styles)            # renders time + type + message + data to terminal
    except Exception as e:
        print(f"auralogger: failed to print log: {e}", file=sys.stderr)
    # print failure is swallowed — console echo must never raise
```

### Step 4 — early-exit guards (no network if not configured)

```python
    if not project_token:
        return    # console-only mode: no token → nothing to send

    if _encrypted and not user_secret:
        return    # encrypted mode with no secret → can't open WS
```

### Step 5 — hydrate runtime config (cached proj_auth)

```python
    merged = _merged_runtime_for_send(project_token)
    # _merged_runtime_for_send():
    #   pid    = get_resolved_project_id() from env, strip
    #   sess   = get_resolved_session() from env, strip
    #   styles = try_parse_resolved_styles() from env
    #
    #   need_fetch = not pid or not sess or styles is None
    #   if need_fetch:
    #       raw = _fetch_proj_auth_cached(project_token)
    #       # _fetch_proj_auth_cached() — see below; blocks under _hydrate_lock
    #       if raw is None:
    #           return None   → log was printed locally, but not sent
    #
    #       fill pid from raw["project_id"] if not already set
    #       fill sess from raw["session"] if not already set
    #       fill styles from build_style_entries_from_api(raw.get("styles",[]))
    #
    #   if not pid or not sess:
    #       return None   → proj_auth response incomplete; console-only for this log
    #
    #   if styles is None:
    #       styles = build_style_entries_from_api([])   → builtins only
    #
    #   return {"project_id": pid, "session": sess, "styles": styles}

    if merged is None:
        return    # proj_auth failed or returned incomplete data
```

### Step 6 — replace local session UUID with real project session, then enqueue

```python
    send_payload = payload.copy()
    send_payload["session"] = merged["session"]
    # The local UUID session is used only for console echo ordering.
    # The backend requires the real project session from proj_auth to attribute the log.

    _enqueue_payload_for_send(project_token, user_secret or "", send_payload)
    # → appends to _send_buffer, starts/resets 30 ms flush timer
    # → see Batch / flush subsystem
```

### `_fetch_proj_auth_cached` — locked single-flight with retry

```python
def _fetch_proj_auth_cached(project_token: str) -> Optional[Dict[str, Any]]:
    with _hydrate_lock:                       # threading.Lock — one concurrent fetch at a time
        # Cache hit: token matches and raw response is present
        if _hydration_cache_token == project_token and _hydration_cache_raw is not None:
            return _hydration_cache_raw       # zero HTTP — instant return

        raw = None
        for attempt in range(1, SDK_RETRY_ATTEMPTS + 1):   # 1..3
            try:
                raw = fetch_proj_auth_payload(project_token)
                break
            except ValueError:
                if attempt >= SDK_RETRY_ATTEMPTS:
                    return None               # all retries exhausted → console-only
                print(f"auralogger: proj_auth failed; retrying ({attempt+1}/3)...", stderr)
                threading.Event().wait(SDK_RETRY_DELAY_S)  # 0.5 s between retries

        if raw is None:
            return None
        _hydration_cache_token = project_token
        _hydration_cache_raw   = raw
        return raw
```

`_hydrate_lock` is held for the entire fetch + cache write. Concurrent `aura_log` calls from multiple threads block until the first fetch completes, then all read from the cache — equivalent to Node's `hydrateFromSecretPromise` single-flight pattern.

---

## Batch / flush subsystem

Python's logger **batches payloads** before sending over WebSocket. Node’s SDKs also batch payloads (JSON array per send); exact batch size/flush timers differ by implementation.

### Module-level state

```python
_send_buffer: list[Dict[str, Any]] = []     # pending unsent payloads
_flush_timer: Optional[threading.Timer] = None
_send_buffer_lock = threading.Lock()        # guards _send_buffer + _flush_timer

BATCH_FLUSH_INTERVAL_S = 0.03   # 30 ms coalesce window
BATCH_MAX_SIZE = 30             # force-flush threshold (max 30 payloads per frame)
```

### `_enqueue_payload_for_send`

```python
def _enqueue_payload_for_send(project_token, user_secret, payload):
    with _send_buffer_lock:
        _send_buffer.append(payload)
    _schedule_or_flush_buffer(project_token, user_secret)
```

### `_schedule_or_flush_buffer` — timer reset or immediate flush

```python
def _schedule_or_flush_buffer(project_token, user_secret):
    with _send_buffer_lock:
        if len(_send_buffer) >= BATCH_MAX_SIZE:
            should_flush = True                   # buffer full → flush now
        else:
            should_flush = False
            _cancel_flush_timer_locked()          # reset the window
            timer = threading.Timer(
                BATCH_FLUSH_INTERVAL_S,           # 30 ms
                _flush_buffer_now,
                args=(project_token, user_secret)
            )
            timer.daemon = True                   # won't block process exit
            timer.start()
            _flush_timer = timer
    if should_flush:
        _flush_buffer_now(project_token, user_secret)
```

Every `aura_log` call resets the 30 ms countdown. If 30 logs arrive before the timer fires, the batch flushes immediately — prevents unbounded buffer growth.

### `_flush_buffer_now` — snapshot, clear, send

```python
def _flush_buffer_now(project_token, user_secret):
    with _send_buffer_lock:
        if not _send_buffer:
            _cancel_flush_timer_locked()
            return
        batch = _send_buffer[:]     # snapshot — safe to release lock before sending
        _send_buffer = []
        _cancel_flush_timer_locked()
    _send_payload_async(project_token, user_secret, batch)
    # Called from threading.Timer callback (daemon thread) or synchronously from _schedule_or_flush
```

### `_send_payload_async` — serialize + send with retry

```python
def _send_payload_async(project_token, user_secret, payload_batch):
    body = json.dumps(payload_batch)    # entire batch serialised as a JSON array

    for attempt in range(1, SDK_RETRY_ATTEMPTS + 1):   # 1..3
        try:
            ws = _ensure_ws(project_token, user_secret)   # reuse or create socket
            ws.send(body)                                 # single ws.send() for the whole batch
            return
        except WebSocketTimeoutException as e:
            close_aura_log_socket()
            if attempt >= SDK_RETRY_ATTEMPTS:
                print(f"auralogger: websocket send failed (timeout): {e}", stderr)
                return
            print(f"auralogger: websocket send timeout; retrying ({attempt+1}/3)...", stderr)
            threading.Event().wait(SDK_RETRY_DELAY_S)   # 0.5 s
        except Exception as e:
            close_aura_log_socket()
            if attempt >= SDK_RETRY_ATTEMPTS:
                print(f"auralogger: websocket send failed: {e}", stderr)
                return
            print(f"auralogger: websocket send failed; retrying ({attempt+1}/3)...", stderr)
            threading.Event().wait(SDK_RETRY_DELAY_S)
```

`close_aura_log_socket()` is called on each failure before retry — resets `_ws` so `_ensure_ws` opens a fresh connection on the next attempt.

---

## WebSocket connection management

### `_ensure_ws` — reuse or create

```python
def _ensure_ws(project_token: str, user_secret: str):
    url = (
        _build_ws_url_no_auth(project_token)    # wss://…/{token}/create_browser_logs  (no encrypt)
        if not _encrypted else
        _build_ws_url(project_token)            # wss://…/{token}/create_log
    )

    if _ws is not None and _bound_url == url and _ws.connected:
        return _ws             # reuse: same URL and socket reports connected

    _close_ws_connection()     # close stale socket

    headers = [] if not _encrypted else [f"Authorization: Bearer {user_secret}"]
    conn = create_connection(
        url,
        timeout=CONNECT_TIMEOUT_S,   # 5 s
        header=headers,              # empty list for unencrypted; Bearer for encrypted
    )
    _ws = conn
    _bound_url = url
    return conn
```

`_build_ws_url` encodes with `quote(token, safe="")` (strict, encodes everything).  
`server_check._build_ws_url` uses `safe="-_.!~*'()"` — the SDK path is stricter to match Node's `encodeURIComponent` exactly.

### `_close_ws_connection`

```python
def _close_ws_connection() -> None:
    global _ws, _bound_url
    if _ws is not None:
        try:
            _ws.close()
        except Exception:
            pass    # ignore errors on close (socket may already be dead)
    _ws = None
    _bound_url = None
```

### `close_aura_log_socket` — flush + close + clear cache

```python
def close_aura_log_socket() -> None:
    project_token = _resolve_project_token_runtime()
    user_secret = _resolve_user_secret_runtime() or ""

    if project_token and (user_secret or not _encrypted):
        _flush_buffer_now(project_token, user_secret)   # drain pending payloads first
    else:
        with _send_buffer_lock:
            _send_buffer = []                           # drop if no credentials to send
            _cancel_flush_timer_locked()

    _close_ws_connection()
    _hydration_cache_token = None    # invalidate proj_auth cache for next configure()
    _hydration_cache_raw   = None
```

---

## Class: `auralogger`

Static-method wrapper over module-level state in `aura_log.py`. All persistent state is module-global; the class just groups the public API surface.

### `auralogger.configure`

```python
@staticmethod
def configure(project_token=None, user_secret=None) -> None:
    # 1. Resolve args: passed string → strip, else fall back to os.environ key
    resolved_token  = project_token.strip()  if isinstance(project_token, str)  else os.environ.get("AURALOGGER_PROJECT_TOKEN","").strip()
    resolved_secret = user_secret.strip()    if isinstance(user_secret, str)    else os.environ.get("AURALOGGER_USER_SECRET","").strip()

    if not resolved_token:
        _apply_runtime_config(resolved_token, resolved_secret)
        return    # no-op config: token empty → console-only until set

    # 2. Fetch proj_auth to discover encrypted flag (blocking HTTP call)
    raw = fetch_proj_auth_payload(resolved_token)
    enc = _read_encrypted_flag(raw)

    # 3. Apply overrides and invalidate cache
    _apply_runtime_config(resolved_token, resolved_secret, enc)

    if enc and not resolved_secret:
        return    # encrypted but no secret → console-only; don't populate cache

    # 4. Validate and pre-warm hydration cache so first aura_log() doesn't re-fetch
    project_id = (raw.get("project_id") or "").strip()
    session    = (raw.get("session") or "").strip()
    if not project_id or not session:
        raise ValueError("auralogger.configure: proj_auth response missing project id or session.")
    with _hydrate_lock:
        _hydration_cache_token = resolved_token
        _hydration_cache_raw   = raw
```

### `auralogger.sync_from_secret`

```python
@staticmethod
def sync_from_secret(project_token: str, user_secret: Optional[str] = None) -> None:
    trimmed = project_token.strip()
    if not trimmed:
        raise ValueError("auralogger.sync_from_secret: project token cannot be empty.")

    raw = fetch_proj_auth_payload(trimmed)    # blocking HTTP
    enc = _read_encrypted_flag(raw)

    resolved_secret = user_secret.strip() if isinstance(user_secret, str) else os.environ.get("AURALOGGER_USER_SECRET","").strip()
    if enc and not resolved_secret:
        raise RuntimeError("Missing AURALOGGER_USER_SECRET")   # stricter than configure()

    _apply_runtime_config(trimmed, resolved_secret, enc)

    project_id = (raw.get("project_id") or "").strip()
    session    = (raw.get("session") or "").strip()
    if not project_id or not session:
        raise ValueError("auralogger.sync_from_secret: proj_auth response missing project id or session.")

    with _hydrate_lock:
        _hydration_cache_token = trimmed
        _hydration_cache_raw   = raw
```

`configure` vs `sync_from_secret`:
- `configure` silently falls back to env when args are `None`; `sync_from_secret` requires an explicit token.
- `configure` skips cache population when encrypted + no secret (graceful console-only); `sync_from_secret` **raises** `RuntimeError` in the same condition.
- Use `configure` in application startup; use `sync_from_secret` when you need a guaranteed-ready SDK before logging begins (e.g. `test-serverlog`).

### `_apply_runtime_config`

```python
@staticmethod
def _apply_runtime_config(project_token, user_secret, enc=True) -> None:
    global _override_project_token, _override_user_secret, _encrypted
    global _hydration_cache_token, _hydration_cache_raw, _local_session_id
    _override_project_token = project_token
    _override_user_secret   = user_secret
    _encrypted              = enc
    _local_session_id       = None          # reset UUID so next log gets a fresh session
    with _hydrate_lock:
        _hydration_cache_token = None       # invalidate stale cache
        _hydration_cache_raw   = None
```

### `auralogger.log` and `auralogger.close_socket`

```python
@staticmethod
def log(type, message, location=None, data=None) -> None:
    aura_log(type, message, location, data)   # thin delegation to module function

@staticmethod
def close_socket(timeout_ms: int = 1000) -> None:
    _ = timeout_ms      # websocket-client has no async drain; timeout unused
    close_aura_log_socket()
```

---

## Cross-cutting

### `encrypted` flag — three decode sites

| Location | Decoding logic | Handles string `"true"` |
|----------|---------------|------------------------|
| `aura_log._read_encrypted_flag` | `enc is True or enc == "true"` | Yes |
| `commands/init.build_init_payload` | `enc if isinstance(enc, bool) else True` | No (bool-only; defaults True) |
| `cli/get_logs.run_get_logs` | `enc_raw is True or enc_raw == "true"` | Yes |

PostgREST may serialize boolean DB columns as the JSON string `"true"`. The stricter decoders (`_read_encrypted_flag`, `run_get_logs`) handle this; `build_init_payload` defaults to `True` for the `isinstance(enc, bool)` check.

### Thread safety map

| Resource | Guard | Notes |
|----------|-------|-------|
| `_send_buffer`, `_flush_timer` | `_send_buffer_lock` (`threading.Lock`) | Enqueue + flush coordination |
| `_hydration_cache_token`, `_hydration_cache_raw` | `_hydrate_lock` (`threading.Lock`) | proj_auth cache read/write |
| `_ws`, `_bound_url` | None | Accessed only by flush-timer threads (single active flush at a time in practice) |
| `_override_*`, `_encrypted` | None | Set once by `configure`/`sync_from_secret` before logging starts |

`_ensure_ws` is not lock-protected. If two flush-timer threads race, the second may reset a socket the first is about to write to; the retry logic in `_send_payload_async` recovers from the resulting exception.

### Retry summary

| Retry site | Max attempts | Delay | When reset |
|------------|-------------|-------|------------|
| `_fetch_proj_auth_cached` (SDK) | 3 | 0.5 s | per token; cache warms on success |
| `_send_payload_async` (WS send) | 3 | 0.5 s | per batch |
| `server_check._send_attempt` (CLI) | 3 | 0.7 s | per command run |
| `fetch_proj_auth_payload` (raw HTTP) | 1 (no retry) | — | callers wrap with retry |

### `project_name` resolution in `proj_auth` response

`resolve_project_context_for_cli_checks` reads `raw.get("name") or raw.get("project_name")` — prefers the newer `name` field, falls back to the older `project_name` key for backward compat with older API deployments. Same logic in `commands/init.build_init_payload`.

---

## When you add a command

1. Add the name string to **`KNOWN_COMMANDS`** set in `cli/cli.py` and an `if command ==` branch in `main()`.
2. Create a module in `cli/commands/your_command.py` with a `run_your_command()` function.
3. If your command needs project context (token + session), call `resolve_project_context_for_cli_checks()` from `cli_auth.py`.
4. If your command needs to send logs, use `aura_log()` or call `_enqueue_payload_for_send()` directly.
5. Update **[`routes.md`](routes.md)** for any new HTTP/WS endpoints.
6. Update **[`file-map.md`](file-map.md)** with the new module.
7. Add a BDD spec under **[`../docs/BDD/`](../docs/BDD/)**.
8. Update **[`../user-docs/commands.md`](../user-docs/commands.md)** for user-visible behaviour changes.

---

## Quick reference — optimisation checklist

| Mechanism | Where | What it saves |
|-----------|-------|---------------|
| `is_full_runtime_env_configured()` fast-path | `commands/init.run_init` | Skips `proj_auth` HTTP + all prompts |
| `get_resolved_user_secret()` short-circuit | `cli/get_logs.run_get_logs` | Skips `proj_auth` when secret already in env |
| `try_parse_resolved_styles()` short-circuit | `cli/get_logs.run_get_logs` | Skips `proj_auth` when styles already in env |
| `_fetch_proj_auth_cached` (lock + dict cache) | `server/aura_log.py` | One `proj_auth` fetch per process lifetime |
| Batch buffer (30 ms / 30 items) | `server/aura_log.py` | Coalesces burst logs into one WS frame |
| `_ensure_ws` reuse (`_ws.connected` check) | `server/aura_log.py` | Fewer WS handshakes across log bursts |
| Daemon timer for flush | `_schedule_or_flush_buffer` | Doesn't block process exit |
| `KNOWN_COMMANDS` set lookup | `cli/cli.py` | O(1) command validation before any sub-module import |
| `_suppress_websocket_client_noise()` at import | Module init | Silences websocket-client connection debug logs |
| `ensure_utf8_stdio()` | Every command entry | Prevents UnicodeEncodeError on Windows legacy consoles |
| `_send_payload_async` retry (3×) | `server/aura_log.py` | Recovers from transient WS failures without losing logs |
| `server-check` retry (3×, 0.7 s) | `commands/server_check.py` | Handles flaky connections during manual smoke test |
| `_maybe_data` guard | `server/aura_log.py` | Drops non-serialisable data silently; never throws |

---

*End of document.*
