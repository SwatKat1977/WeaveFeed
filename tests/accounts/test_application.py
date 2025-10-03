# tests/test_application.py
import unittest
import logging
from http import HTTPStatus  # not used, but common in this repo
from unittest.mock import patch, MagicMock, AsyncMock, call
from quart import Quart, Blueprint
from contextlib import ExitStack
import os

# ⬇️ CHANGE THIS to your actual module path for the Application class.
import services.accounts.application as app_mod
from services.accounts.application import Application


class TestApplication(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.quart_app = Quart(__name__)

    # ---------- __init__ coverage ----------
    async def test_init_sets_logger_and_stream_handler(self):
        app = Application(self.quart_app)
        self.assertIs(app._quart_instance, self.quart_app)
        self.assertIsNone(app._config)
        self.assertIsInstance(app._logger, logging.Logger)
        # Default level from constants
        self.assertEqual(app._logger.level, app_mod.LOGGING_DEFAULT_LOG_LEVEL)
        # Has at least one StreamHandler
        self.assertTrue(any(isinstance(h, logging.StreamHandler) for h in app._logger.handlers))

    # ---------- _initialise: required config missing ----------
    @patch.dict(os.environ, {
        "WEAVEFEED_ACCOUNTS_CONFIG_FILE_REQUIRED": "true"
    }, clear=True)
    async def test_initialise_missing_required_config_prints_and_returns_false(self):
        app = Application(self.quart_app)
        with patch("builtins.print") as mock_print:
            ok = await app._initialise()
        self.assertFalse(ok)
        mock_print.assert_called_once_with("[FATAL ERROR] Configuration file missing!", flush=True)

    # ---------- _initialise: configuration ValueError path ----------
    @patch.dict(os.environ, {}, clear=True)
    async def test_initialise_configuration_error_logs_critical_and_returns_false(self):
        app = Application(self.quart_app)
        # Replace instance logger with a mock to capture calls
        app._logger = MagicMock()

        mock_cfg = MagicMock()
        mock_cfg.configure = MagicMock()
        mock_cfg.process_config.side_effect = ValueError("bad config")

        with patch.object(app_mod, "Configuration", return_value=mock_cfg):
            ok = await app._initialise()

        self.assertFalse(ok)
        app._logger.critical.assert_called_once()
        # ensure configure was called with expected signature
        mock_cfg.configure.assert_called_once_with(app_mod.CONFIGURATION_LAYOUT, None, False)

    # ---------- _initialise: success path ----------
    @patch.dict(os.environ, {}, clear=True)
    async def test_initialise_success_sets_level_displays_config_registers_routes(self):
        app = Application(self.quart_app)
        # Spy-able instance logger
        app._logger = MagicMock()

        # Mock Configuration instance behavior
        mock_cfg = MagicMock()
        mock_cfg.configure = MagicMock()
        mock_cfg.process_config = MagicMock()
        mock_cfg.get_entry = MagicMock(return_value="INFO")  # setLevel will be called with this

        fake_bp = Blueprint("api_routes", __name__)

        with ExitStack() as stack:
            stack.enter_context(patch.object(app_mod, "Configuration", return_value=mock_cfg))
            # Patch display method to ensure it is invoked (we also test it separately below)
            mock_display = stack.enter_context(patch.object(Application, "_display_configuration_details"))
            # Patch create_routes to return our fake blueprint
            mock_create_routes = stack.enter_context(patch.object(app_mod, "create_routes", return_value=fake_bp))
            # Avoid actually registering; just verify call
            mock_register = MagicMock()
            # Monkey-patch the bound method so we can assert
            self.quart_app.register_blueprint = mock_register  # type: ignore[attr-defined]

            ok = await app._initialise()

        self.assertTrue(ok)
        app._logger.setLevel.assert_called_once_with("INFO")
        mock_display.assert_called_once()
        mock_create_routes.assert_called_once_with(app._logger)
        mock_register.assert_called_once_with(fake_bp)

    # ---------- _main_loop ----------
    async def test_main_loop_sleeps(self):
        app = Application(self.quart_app)
        with patch("services.accounts.application.asyncio.sleep", new=AsyncMock()) as mock_sleep:
            await app._main_loop()
        mock_sleep.assert_awaited_once_with(0.1)

    # ---------- _shutdown ----------
    async def test_shutdown_noop(self):
        app = Application(self.quart_app)
        # Just ensure it doesn't raise and returns None
        result = await app._shutdown()
        self.assertIsNone(result)

    # ---------- _display_configuration_details ----------
    async def test_display_configuration_details_logs_expected_lines(self):
        app = Application(self.quart_app)
        app._logger = MagicMock()
        app._config = MagicMock()
        app._config.get_entry.return_value = "DEBUG"

        app._display_configuration_details()

        # Ordered calls to info
        app._logger.info.assert_has_calls([
            call("Configuration"),
            call("============="),
            call("[logging]"),
            call("=> Logging log level              : %s", "DEBUG"),
        ])
        app._config.get_entry.assert_called_once_with("logging", "log_level")
