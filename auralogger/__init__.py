"""Public API barrel (mirrors node/src/index.ts)."""

from auralogger.aura_log import aura_log, close_aura_log_socket
from auralogger.commands.init import run_init
from auralogger.commands.server_check import run_server_check
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

__all__ = [
    "aura_log",
    "close_aura_log_socket",
    "log",
    "run_get_logs",
    "normalize_and_validate_filters",
    "ApiLogFilter",
    "parse_error_body",
    "run_init",
    "run_server_check",
    "DEFAULT_LOG_STYLE_SPEC",
    "build_style_entries_from_api",
    "resolve_log_style_spec",
    "style_map_from_config_entries",
    "parse_command",
    "ParsedFilter",
    "ParsedGetLogsCommand",
]
