"""Public API barrel (mirrors node/src/index.ts)."""

from auralogger.aura_log import AuraServer, aura_log, close_aura_log_socket
from auralogger.backend_origin import (
    build_create_browser_logs_url,
    build_proj_auth_url,
    build_project_logs_url,
)
from auralogger.client.client_log import (
    AuraClient,
    ClientLogInputs,
    auralog,
    client_log,
    close_client_log_socket,
)
from auralogger.commands.client_check import run_client_check
from auralogger.commands.init import run_init
from auralogger.commands.server_check import run_server_check
from auralogger.commands.test_clientlog import run_test_clientlog
from auralogger.commands.test_serverlog import run_test_serverlog
from auralogger.get_logs import run_get_logs
from auralogger.get_logs_filters import ApiLogFilter, normalize_and_validate_filters
from auralogger.http_utils import parse_error_body
from auralogger.log import log
from auralogger.log_styles import (
    DEFAULT_LOG_STYLE_SPEC,
    build_style_entries_from_api,
    resolve_log_style_spec,
    style_map_from_config_entries,
)
from auralogger.parser import ParsedFilter, ParsedGetLogsCommand, parse_command
from auralogger.proj_auth import fetch_proj_auth_config, fetch_proj_auth_payload

__all__ = [
    "aura_log",
    "close_aura_log_socket",
    "AuraServer",
    "AuraClient",
    "ClientLogInputs",
    "auralog",
    "client_log",
    "close_client_log_socket",
    "log",
    "run_get_logs",
    "normalize_and_validate_filters",
    "ApiLogFilter",
    "parse_error_body",
    "run_init",
    "run_server_check",
    "run_client_check",
    "run_test_serverlog",
    "run_test_clientlog",
    "DEFAULT_LOG_STYLE_SPEC",
    "build_style_entries_from_api",
    "resolve_log_style_spec",
    "style_map_from_config_entries",
    "fetch_proj_auth_config",
    "fetch_proj_auth_payload",
    "build_proj_auth_url",
    "build_project_logs_url",
    "build_create_browser_logs_url",
    "parse_command",
    "ParsedFilter",
    "ParsedGetLogsCommand",
]
