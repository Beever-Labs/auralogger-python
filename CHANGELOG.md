# Changelog

All notable changes to the Python package are documented in this file.

## [Unreleased]

- **Breaking:** renamed the Python logger class **`AuraServer`** → **`auralogger`** (lowercase: `from auralogger import auralogger`). Node still uses the name `AuraServer`.
- Removed the browser/client SDK surface from this package (`auralogger.client`, `client-check`, `test-clientlog`). Use **`auralogger-cli`** (Node) for frontend logging; Python keeps the **`auralogger`** logger class / **`aura_log`** and the CLI above.
- Dropped the **`pydantic`** dependency (it was only required for the removed client typed log inputs).
- Added Python package release workflow for tag-based PyPI publishing.
- Added `dev` optional dependency group with Ruff for contributor linting.
- Improved CLI unknown-command output with explicit valid command list.
