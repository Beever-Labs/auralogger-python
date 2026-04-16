"""Public API barrel (mirrors node/src/index.ts)."""

from auralogger.cli.commands.init import run_init
from auralogger.cli.commands.server_check import run_server_check
from auralogger.cli.commands.test_serverlog import run_test_serverlog
from auralogger.cli.get_logs import run_get_logs
from auralogger.cli.get_logs_filters import ApiLogFilter, normalize_and_validate_filters
from auralogger.cli.log_styles import (
    DEFAULT_LOG_STYLE_SPEC,
    build_style_entries_from_api,
    resolve_log_style_spec,
    style_map_from_config_entries,
)
from auralogger.server.aura_log import auralogger, aura_log, close_aura_log_socket
from auralogger.server.proj_auth import fetch_proj_auth_config, fetch_proj_auth_payload
from auralogger.utils.backend_origin import build_proj_auth_url, build_project_logs_url
from auralogger.utils.http_utils import parse_error_body
from auralogger.utils.parser import ParsedFilter, ParsedGetLogsCommand, parse_command

__all__ = [
    "aura_log",
    "close_aura_log_socket",
    "auralogger",
    "run_get_logs",
    "normalize_and_validate_filters",
    "ApiLogFilter",
    "parse_error_body",
    "run_init",
    "run_server_check",
    "run_test_serverlog",
    "DEFAULT_LOG_STYLE_SPEC",
    "build_style_entries_from_api",
    "resolve_log_style_spec",
    "style_map_from_config_entries",
    "fetch_proj_auth_config",
    "fetch_proj_auth_payload",
    "build_proj_auth_url",
    "build_project_logs_url",
    "parse_command",
    "ParsedFilter",
    "ParsedGetLogsCommand",
]
