import unittest
import logging
from unittest.mock import patch
from quart import Quart, Blueprint
import api as accounts_api


class TestCreateRoutes(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.logger = logging.getLogger("test_logger")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.NullHandler())

    @patch("api.create_auth_bp")  # <-- patch the alias used inside api/__init__.py
    async def test_create_routes_registers_auth_blueprint(self, mock_create_auth_bp):
        # Build a fake auth blueprint with a real route so we can verify mount point
        fake_auth_bp = Blueprint("auth_api", __name__)

        @fake_auth_bp.route("/ping")
        async def ping():
            return "ok"

        mock_create_auth_bp.return_value = fake_auth_bp

        # Call function under test
        blueprint = accounts_api.create_routes(self.logger)

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
