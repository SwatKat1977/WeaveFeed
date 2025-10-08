import http
import unittest
import logging
from unittest.mock import AsyncMock, patch, MagicMock
from quart import Quart, Blueprint
import api as accounts_api
from api import auth_api

class TestCreateRoutes(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.logger = logging.getLogger("test_logger")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.NullHandler())

        self.app = Quart(__name__)

    @patch("api.create_auth_bp")  # <-- patch the alias used inside api/__init__.py
    async def test_create_routes_registers_auth_blueprint(self, mock_create_auth_bp):
        # Build a fake auth blueprint with a real route so we can verify mount point
        fake_auth_bp = Blueprint("auth_api", __name__)

        mock_state_object = MagicMock()

        @fake_auth_bp.route("/ping")
        async def ping():
            return "ok"

        mock_create_auth_bp.return_value = fake_auth_bp

        # Call function under test
        blueprint = accounts_api.create_routes(self.logger, mock_state_object)

        # Basic assertions
        self.assertIsInstance(blueprint, Blueprint)
        self.assertEqual(blueprint.name, "api_routes")
        mock_create_auth_bp.assert_called_once_with(self.logger)

        # Mount in an app and verify the composed route exists
        app = Quart(__name__)
        app.register_blueprint(blueprint, url_prefix="/accounts")

        routes = [rule.rule for rule in app.url_map.iter_rules()]
        self.assertIn("/accounts/auth/ping", routes)

        # (Optional) actually hit the route to be extra sure
        client = app.test_client()
        resp = await client.get("/accounts/auth/ping")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(await resp.get_data(as_text=True), "ok")

    @patch("services.accounts.api.auth_api.AuthApiView.login_password", new_callable=AsyncMock)
    async def test_login_password_route_is_callable(self, mock_login_password):
        # Arrange: patch login_password to return a dummy response
        mock_login_password.return_value = ("ok", http.HTTPStatus.OK)

        # Register the real blueprint
        bp = auth_api.create_blueprint(self.logger)
        self.app.register_blueprint(bp, url_prefix="/auth")

        # Act: hit the route
        client = self.app.test_client()
        response = await client.post("/auth/login_password", json={"username_or_email": "bob", "password": "secret"})

        # Assert
        self.assertEqual(response.status_code, http.HTTPStatus.OK)
        self.assertEqual(await response.get_data(as_text=True), "ok")

        # Ensure our mock was called
        mock_login_password.assert_awaited_once()

    async def test_blueprint_registers_signup_route(self):
        app = Quart(__name__)
        bp = auth_api.create_blueprint(self.logger)
        app.register_blueprint(bp, url_prefix="/auth")

        client = app.test_client()
        routes = [rule.rule for rule in app.url_map.iter_rules()]
        self.assertIn("/auth/signup_password", routes)
