from __future__ import annotations

import unittest
import importlib
from unittest.mock import Mock, patch

aura_log_module = importlib.import_module("auralogger.server.aura_log")


class WebsocketClientLoggerNoiseTests(unittest.TestCase):
    def test_suppress_websocket_client_noise_sets_warning_level(self) -> None:
        fake_logger = Mock()
        with patch.object(
            aura_log_module.logging, "getLogger", return_value=fake_logger
        ) as get_logger:
            aura_log_module._suppress_websocket_client_noise()

        get_logger.assert_called_once_with("websocket")
        fake_logger.setLevel.assert_called_once_with(aura_log_module.logging.WARNING)


if __name__ == "__main__":
    unittest.main()
