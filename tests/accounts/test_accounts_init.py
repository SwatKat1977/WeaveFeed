import asyncio
import importlib
import unittest
from unittest.mock import AsyncMock, patch, MagicMock
import types
import inspect
import textwrap

import os
os.environ["WEAVEFEED_TEST_MODE"] = "1"

import services.accounts.__init__ as accounts

class TestDatabaseConfig(unittest.TestCase):
    def test_defaults(self):
        # No env vars
        for key in list(os.environ.keys()):
            if key.startswith("WEAVEFEED_ACCOUNTS_DB_"):
                os.environ.pop(key)

        cfg = accounts.DatabaseConfig()
        self.assertEqual(cfg.DB_USER, "__INVALID__")
        self.assertEqual(cfg.DB_PASSWORD, "__INVALID__")
        self.assertEqual(cfg.DB_NAME, "__INVALID__")
        self.assertEqual(cfg.DB_HOST, "127.0.0.1")
        self.assertEqual(cfg.DB_PORT, 5432)

    def test_env_overrides(self):
        os.environ["WEAVEFEED_ACCOUNTS_DB_USER"] = "bob"
        os.environ["WEAVEFEED_ACCOUNTS_DB_PASSWORD"] = "pw"
        os.environ["WEAVEFEED_ACCOUNTS_DB_NAME"] = "dbname"
        os.environ["WEAVEFEED_ACCOUNTS_DB_HOST"] = "dbhost"
        os.environ["WEAVEFEED_ACCOUNTS_DB_PORT"] = "7777"

        import services.accounts.__init__ as accounts_reload
        importlib.reload(accounts_reload)
        cfg = accounts_reload.DatabaseConfig()
        self.assertEqual(cfg.DB_USER, "bob")
        self.assertEqual(cfg.DB_PASSWORD, "pw")
        self.assertEqual(cfg.DB_NAME, "dbname")
        self.assertEqual(cfg.DB_HOST, "dbhost")
        self.assertEqual(cfg.DB_PORT, 7777)


class TestCancelBackgroundTasks(unittest.IsolatedAsyncioTestCase):
    async def test_no_task(self):
        if hasattr(accounts.app, "background_task"):
            delattr(accounts.app, "background_task")
        await accounts.cancel_background_tasks()  # no crash

    async def test_with_task(self):
        async def dummy():
            await asyncio.sleep(0)
        t = asyncio.create_task(dummy())
        accounts.app.background_task = t
        await accounts.cancel_background_tasks()
        self.assertTrue(t.cancelled())


class TestCreateDbPool(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.cfg = accounts.DatabaseConfig()
        self.cfg.DB_USER = "u"
        self.cfg.DB_PASSWORD = "p"
        self.cfg.DB_NAME = "n"
        self.cfg.DB_HOST = "h"
        self.cfg.DB_PORT = 5432

    # 1️⃣ success immediately
    @patch("services.accounts.__init__.asyncpg.create_pool", new_callable=AsyncMock)
    async def test_success(self, mock_create):
        mock_pool = AsyncMock()
        mock_create.return_value = mock_pool
        res = await accounts.create_db_pool(self.cfg)
        self.assertIs(res, mock_pool)
        mock_create.assert_awaited_once()

    # 2️⃣ InvalidPasswordError triggers break + cancel + _exit
    @patch("services.accounts.__init__.cancel_background_tasks", new_callable=AsyncMock)
    @patch("services.accounts.__init__.os._exit", new_callable=MagicMock)
    async def test_invalid_password_error(self, mock_exit, mock_cancel):
        with patch("services.accounts.__init__.asyncpg.create_pool",
                   side_effect=accounts.asyncpg.InvalidPasswordError):
            await accounts.create_db_pool(self.cfg)
        mock_cancel.assert_awaited_once()
        mock_exit.assert_not_called()  # TEST_MODE prevents exit

    # 3️⃣ InvalidCatalogNameError triggers break + cancel
    @patch("services.accounts.__init__.cancel_background_tasks", new_callable=AsyncMock)
    @patch("services.accounts.__init__.os._exit", new_callable=MagicMock)
    async def test_invalid_catalog_error(self, mock_exit, mock_cancel):
        with patch("services.accounts.__init__.asyncpg.create_pool",
                   side_effect=accounts.asyncpg.InvalidCatalogNameError):
            await accounts.create_db_pool(self.cfg)
        mock_cancel.assert_awaited_once()
        mock_exit.assert_not_called()

    # 4️⃣ CannotConnectNowError triggers retry then cancel
    @patch("services.accounts.__init__.cancel_background_tasks", new_callable=AsyncMock)
    @patch("services.accounts.__init__.os._exit", new_callable=MagicMock)
    @patch("services.accounts.__init__.asyncio.sleep", new_callable=AsyncMock)
    async def test_cannot_connect_now_retry(self, mock_sleep, mock_exit, mock_cancel):
        with patch("services.accounts.__init__.asyncpg.create_pool",
                   side_effect=accounts.asyncpg.CannotConnectNowError):
            await accounts.create_db_pool(self.cfg, retries=2, base_delay=0.01)
        mock_sleep.assert_awaited()
        mock_cancel.assert_awaited_once()
        mock_exit.assert_not_called()

    # 5️⃣ TimeoutError triggers retry then cancel
    @patch("services.accounts.__init__.cancel_background_tasks", new_callable=AsyncMock)
    @patch("services.accounts.__init__.os._exit", new_callable=MagicMock)
    @patch("services.accounts.__init__.asyncio.sleep", new_callable=AsyncMock)
    async def test_timeout_error_retry(self, mock_sleep, mock_exit, mock_cancel):
        with patch("services.accounts.__init__.asyncpg.create_pool",
                   side_effect=asyncio.TimeoutError):
            await accounts.create_db_pool(self.cfg, retries=2, base_delay=0.01)
        mock_sleep.assert_awaited()
        mock_cancel.assert_awaited_once()
        mock_exit.assert_not_called()

    # 6️⃣ OSError triggers retry then cancel
    @patch("services.accounts.__init__.cancel_background_tasks", new_callable=AsyncMock)
    @patch("services.accounts.__init__.os._exit", new_callable=MagicMock)
    @patch("services.accounts.__init__.asyncio.sleep", new_callable=AsyncMock)
    async def test_oserror_retry(self, mock_sleep, mock_exit, mock_cancel):
        with patch("services.accounts.__init__.asyncpg.create_pool",
                   side_effect=OSError("boom")):
            await accounts.create_db_pool(self.cfg, retries=2, base_delay=0.01)
        mock_sleep.assert_awaited()
        mock_cancel.assert_awaited_once()
        mock_exit.assert_not_called()

    # 7️⃣ PostgresError triggers retry then cancel
    @patch("services.accounts.__init__.cancel_background_tasks", new_callable=AsyncMock)
    @patch("services.accounts.__init__.os._exit", new_callable=MagicMock)
    @patch("services.accounts.__init__.asyncio.sleep", new_callable=AsyncMock)
    async def test_postgres_error_retry(self, mock_sleep, mock_exit, mock_cancel):
        with patch("services.accounts.__init__.asyncpg.create_pool",
                   side_effect=accounts.asyncpg.PostgresError("fail")):
            await accounts.create_db_pool(self.cfg, retries=2, base_delay=0.01)
        mock_sleep.assert_awaited()
        mock_cancel.assert_awaited_once()
        mock_exit.assert_not_called()

    # 8️⃣ app is None -> skips cancel
    @patch("services.accounts.__init__.cancel_background_tasks", new_callable=AsyncMock)
    @patch("services.accounts.__init__.os._exit", new_callable=MagicMock)
    @patch("services.accounts.__init__.asyncio.sleep", new_callable=AsyncMock)
    async def test_app_is_none_skips_cancel(self, mock_sleep, mock_exit, mock_cancel):
        original_app = accounts.app
        try:
            with patch("services.accounts.__init__.app", None), \
                 patch("services.accounts.__init__.asyncpg.create_pool",
                        side_effect=OSError("fail")):
                await accounts.create_db_pool(self.cfg, retries=1)
            mock_cancel.assert_not_awaited()
            mock_exit.assert_not_called()
        finally:
            accounts.app = original_app

class TestRequestHooks(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # fake pool
        self.mock_pool = AsyncMock()
        self.mock_conn = AsyncMock()
        self.mock_pool.acquire.return_value = self.mock_conn
        accounts.app.db_pool = self.mock_pool

    async def test_acquire_connection_success(self):
        view_func = lambda: None

        accounts.app.view_functions["endpoint"] = view_func
        dummy_request = types.SimpleNamespace(endpoint="endpoint")
        dummy_g = types.SimpleNamespace()  # fake g context

        with patch.object(accounts, "request", dummy_request), \
                patch.object(accounts, "g", dummy_g):
            result = await accounts.acquire_connection()
        self.assertIsNone(result)
        self.mock_pool.acquire.assert_awaited()

    async def test_acquire_connection_skip_no_db(self):
        async def handler():
            pass
        handler._no_db = True
        accounts.app.view_functions["x"] = handler

        dummy_request = types.SimpleNamespace(endpoint="x")
        dummy_g = types.SimpleNamespace()  # fake g context

        with patch.object(accounts, "request", dummy_request), \
                patch.object(accounts, "g", dummy_g):
            result = await accounts.acquire_connection()

        self.assertIsNone(result)
        self.mock_pool.acquire.assert_not_called()

    async def test_acquire_connection_timeout(self):
        self.mock_pool.acquire.side_effect = asyncio.TimeoutError
        accounts.app.view_functions["e"] = lambda: None

        req = types.SimpleNamespace(endpoint="endpoint")
        with patch.object(accounts, "request", req):
            result = await accounts.acquire_connection()
        self.assertEqual(result[1], 503)

    async def test_release_connection_with_db(self):
        g = types.SimpleNamespace(db=self.mock_conn)
        with patch("services.accounts.__init__.g", g):
            resp = MagicMock()
            result = await accounts.release_connection(resp)
        self.mock_pool.release.assert_awaited_with(self.mock_conn)
        self.assertIs(result, resp)

    async def test_release_connection_without_db(self):
        g = types.SimpleNamespace()
        with patch("services.accounts.__init__.g", g):
            resp = MagicMock()
            result = await accounts.release_connection(resp)
        self.assertIs(result, resp)
        self.mock_pool.release.assert_not_called()

class TestLifecycleHooks(unittest.IsolatedAsyncioTestCase):
    @patch("services.accounts.__init__.SERVICE_APP")
    @patch("services.accounts.__init__.create_db_pool", new_callable=AsyncMock)
    async def test_startup_success(self, mock_dbpool, mock_service_app):
        mock_service_app.initialise = AsyncMock(return_value=True)
        mock_service_app.run = AsyncMock()

        await accounts.startup()

        mock_dbpool.assert_awaited()
        mock_service_app.run.assert_called_once()

    @patch("services.accounts.__init__.SERVICE_APP")
    @patch("services.accounts.__init__.create_db_pool", new_callable=AsyncMock)
    @patch("services.accounts.__init__.os._exit")
    async def test_startup_failure(self, mock_exit, mock_dbpool, mock_service_app):
        mock_service_app.initialise = AsyncMock(return_value=False)
        mock_service_app.run = AsyncMock()
        await accounts.startup()
        mock_exit.assert_called_once()

    @patch("services.accounts.__init__.SERVICE_APP")
    @patch("services.accounts.__init__.cancel_background_tasks", new_callable=AsyncMock)
    async def test_shutdown(self, mock_cancel, mock_service_app):
        # fake db pool with an async close()
        fake_pool = AsyncMock()
        accounts.app.db_pool = fake_pool

        # call shutdown directly
        await accounts.shutdown()

        # assertions
        mock_service_app.shutdown_event.set.assert_called_once()
        mock_cancel.assert_awaited_once()
        fake_pool.close.assert_awaited_once()

    @patch("services.accounts.__init__.SERVICE_APP")
    @patch("services.accounts.__init__.cancel_background_tasks", new_callable=AsyncMock)
    async def test_shutdown_app_is_none(self, mock_cancel, mock_service_app):
        class DummyApp:
            db_pool = AsyncMock()

        original_app = accounts.app
        try:
            # Patch app to dummy so "if app is not None" is True but harmless
            with patch("services.accounts.__init__.app", DummyApp()):
                await accounts.shutdown()
        finally:
            accounts.app = original_app

        mock_service_app.shutdown_event.set.assert_called_once()
        mock_cancel.assert_awaited_once()

    @patch("services.accounts.__init__.SERVICE_APP")
    @patch("services.accounts.__init__.cancel_background_tasks", new_callable=AsyncMock)
    async def test_shutdown_app_is_none_logs_warning(self, mock_cancel, mock_service_app):
        """Ensure shutdown() handles app being None and logs a warning."""
        original_app = accounts.app
        try:
            with patch("services.accounts.__init__.app", None):
                with patch("builtins.print") as mock_print:
                    await accounts.shutdown()
                    mock_print.assert_called_with(
                        "[WARN] app is None on shutdown, skipping cleanup"
                    )
        finally:
            accounts.app = original_app

        mock_service_app.shutdown_event.set.assert_called_once()
        mock_cancel.assert_not_awaited()
