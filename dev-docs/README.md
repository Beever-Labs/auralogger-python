# Dev Docs (Python CLI)

Contributor-oriented notes for the Python `auralogger` package.

## Start here

- `file-map.md`: quick map of what each important module does
- `routes.md`: HTTP + WebSocket routes and where they are used in this package

Auth contract (match Node / hosted API): **`POST /api/{project_token}/proj_auth`** — token in path only. **`POST /api/{project_token}/logs`** — headers **`secret`** and **`user_secret`** both set to the **user secret**. Server ingest WebSocket — **`Authorization: Bearer <user_secret>`** on **`/{project_token}/create_log`**.

## Related folders

- `user-docs/commands.md`: end-user setup and command reference (keep in sync when behavior changes)
- `docs/BDD/`: behavior specs
- `docs/infra/`: per-file infrastructure notes

## Contributing flow (quick)

1. Change code under `auralogger/`
2. Update `dev-docs/` (and `user-docs/` when user-visible behavior changes)
3. Run tests or smoke checks as appropriate for your change
