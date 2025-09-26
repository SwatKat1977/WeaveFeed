from datetime import datetime, timezone
from http import HTTPStatus
import json
import logging
import sys
import unittest
import uuid
from unittest.mock import AsyncMock, patch, MagicMock
from quart import jsonify, Quart, Response, g
from api.auth_api import create_blueprint
from services.accounts.api.auth_api_view import AuthApiView
import api.auth_api_view as auth_api_view
from passlib.hash import bcrypt


class TestCreateBlueprint(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        # Create a test logger
        self.logger = logging.getLogger("test_logger")
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(logging.NullHandler())
        self.auth_view = AuthApiView(self.logger)

    @patch("api.auth_api.AuthApiView")
    async def test_create_blueprint_registers_route_and_calls_view(self, mock_auth_view_cls):
        # Mock the AuthApiView instance
        mock_view_instance = MagicMock()
        mock_view_instance.signup_password = AsyncMock(
            return_value=Response(json.dumps({"status": "ok"}), mimetype="application/json")
        )
        mock_auth_view_cls.return_value = mock_view_instance

        # Create the Quart app and register the blueprint
        app = Quart(__name__)
        blueprint = create_blueprint(self.logger)
        app.register_blueprint(blueprint, url_prefix="/auth")

        # Use Quart test client to call the route
        test_client = app.test_client()
        response = await test_client.post("/auth/signup_password")

        # Verify response
        self.assertEqual(response.status_code, 200)
        data = await response.get_json()
        self.assertEqual(data, {"status": "ok"})

        # Verify AuthApiView was constructed with logger
        mock_auth_view_cls.assert_called_once_with(self.logger)

        # Verify signup_password was called
        mock_view_instance.signup_password.assert_awaited_once()

    @patch("api.auth_api.AuthApiView")
    async def test_logging_occurs(self, mock_auth_view_cls):
        mock_view_instance = MagicMock()
        mock_view_instance.signup_password = AsyncMock(return_value="done")
        mock_auth_view_cls.return_value = mock_view_instance

        # Capture logs
        log_stream = []
        class ListHandler(logging.Handler):
            def emit(self, record):
                log_stream.append(record.getMessage())

        handler = ListHandler()
        self.logger.addHandler(handler)

        app = Quart(__name__)
        blueprint = create_blueprint(self.logger)
        app.register_blueprint(blueprint, url_prefix="/auth")

        test_client = app.test_client()
        await test_client.post("/auth/signup_password")

        # Check debug logs
        self.assertIn("Registering Auth API routes:", log_stream)
        self.assertIn("=> /auth/signup_password [POST]", log_stream)

        self.logger.removeHandler(handler)

    # ---------- signup_password ----------

    async def test_signup_password_validation_error(self):
        # Missing required fields -> pydantic ValidationError -> 400
        app = Quart(__name__)
        mock_db = MagicMock()
        mock_db.fetchrow = AsyncMock()

        async with app.test_request_context(
            "/signup_password", method="POST", json={}
        ):
            g.db = mock_db
            resp, status = await self.auth_view.signup_password()

        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        data = await resp.get_json()
        self.assertIn("error", data)

    @patch.object(AuthApiView, "_create_user", new_callable=AsyncMock)
    async def test_signup_password_conflict_existing_user(self, mock_create_user):
        # DB returns an existing row -> 409, and _create_user NOT called
        app = Quart(__name__)
        mock_db = MagicMock()
        mock_db.fetchrow = AsyncMock(return_value={"id": "something"})

        payload = {"username": "alice", "email": "a@example.com", "password": "pw123"}

        async with app.test_request_context(
            "/signup_password", method="POST", json=payload
        ):
            g.db = mock_db
            resp, status = await self.auth_view.signup_password()

        self.assertEqual(status, HTTPStatus.CONFLICT)
        data = await resp.get_json()
        self.assertEqual(data, {"error": "User already exists"})
        mock_create_user.assert_not_called()

    @patch.object(AuthApiView, "_create_user", new_callable=AsyncMock)
    async def test_signup_password_success(self, mock_create_user):
        # DB finds no existing -> create -> 201, returns full payload
        app = Quart(__name__)
        created_id = uuid.uuid4()
        mock_create_user.return_value = created_id

        mock_db = MagicMock()
        mock_db.fetchrow = AsyncMock(return_value=None)

        payload = {"username": "alice", "email": "a@example.com", "password": "pw123"}

        async with app.test_request_context(
            "/signup_password", method="POST", json=payload
        ):
            g.db = mock_db
            resp, status = await self.auth_view.signup_password()

        self.assertEqual(status, HTTPStatus.CREATED)
        data = await resp.get_json()
        self.assertEqual(
            data,
            {
                "message": "User created (password)",
                "user_id": str(created_id),
                "username": "alice",
                "email": "a@example.com",
            },
        )
        mock_create_user.assert_awaited_once_with("alice", "a@example.com", "pw123")

    # ---------- signup_google ----------

    async def test_signup_google_validation_error(self):
        # Missing required fields -> pydantic ValidationError -> 400
        app = Quart(__name__)
        mock_db = MagicMock()
        mock_db.fetchrow = AsyncMock()

        async with app.test_request_context(
            "/signup/google", method="POST", json={}
        ):
            g.db = mock_db
            resp, status = await self.auth_view.signup_google()

        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        data = await resp.get_json()
        self.assertIn("error", data)

    @patch.object(AuthApiView, "_create_user", new_callable=AsyncMock)
    async def test_signup_google_conflict_existing_provider(self, mock_create_user):
        # Provider already linked -> 409, _create_user NOT called
        app = Quart(__name__)
        mock_db = MagicMock()
        mock_db.fetchrow = AsyncMock(return_value={"user_id": "u123"})

        payload = {
            "provider_uid": "g-uid-1",
            "access_token": "aaa",
            "refresh_token": "rrr",
            "expires_at": None,
        }

        async with app.test_request_context(
            "/signup/google", method="POST", json=payload
        ):
            g.db = mock_db
            resp, status = await self.auth_view.signup_google()

        self.assertEqual(status, HTTPStatus.CONFLICT)
        data = await resp.get_json()
        self.assertEqual(data, {"error": "Account already linked"})
        mock_create_user.assert_not_called()

    patch.object(AuthApiView, "_create_user", new_callable=AsyncMock)

    @patch.object(AuthApiView, "_create_user", new_callable=AsyncMock)
    async def test_signup_google_success_fallback_email(self, mock_create_user):
        app = Quart(__name__)
        mock_create_user.return_value = uuid.uuid4()

        mock_db = MagicMock()
        mock_db.fetchrow = AsyncMock(return_value=None)

        payload = {
            "provider_uid": "abc123",
            "access_token": "aaa",
            "refresh_token": None,
            "expires_at": None,
        }

        async with app.test_request_context("/signup/google", method="POST", json=payload):
            g.db = mock_db
            resp, status = await self.auth_view.signup_google()

        self.assertEqual(status, HTTPStatus.CREATED)
        data = await resp.get_json()
        self.assertIn("user_id", data)

        # Assert _create_user was awaited once
        mock_create_user.assert_awaited_once()

        # Get the awaited args robustly across Python versions
        call = mock_create_user.await_args
        try:
            # Python 3.11+: await_args is a Call with .args/.kwargs
            kwargs = call.kwargs
        except AttributeError:
            # Older: await_args is a tuple (args, kwargs)
            _, kwargs = call

        # All parameters were passed as kwargs
        self.assertEqual(kwargs["username"], "google_abc123")
        self.assertEqual(kwargs["email"], "abc123@googleuser.fake")
        self.assertFalse(kwargs.get("email_verified", False))
        # password omitted (treated as None)
        self.assertTrue("password" not in kwargs or kwargs["password"] is None)



    async def test_signup_google_success_with_verified_email(self):
        app = Quart(__name__)

        # async DB mocks
        mock_db = MagicMock()
        mock_db.fetchrow = AsyncMock(return_value=None)
        mock_db.execute = AsyncMock()

        # Resolve the EXACT module your instance was created from
        sut_mod = sys.modules[self.auth_view.__class__.__module__]

        # Dummy model to preserve extra fields (email, email_verified)
        class DummyOAuth:
            def __init__(self, **data):
                for k, v in data.items():
                    setattr(self, k, v)

        with patch.object(sut_mod, "OAuthSignupRequest") as mock_oauth_model, \
                patch.object(sut_mod.AuthApiView, "_create_user",
                             new_callable=AsyncMock) as mock_create_user:
            mock_oauth_model.side_effect = lambda **kw: DummyOAuth(**kw)
            mock_create_user.return_value = uuid.uuid4()

            payload = {
                "provider_uid": "xyz789",
                "access_token": "tok",
                "refresh_token": "ref",
                "expires_at": None,
                "email": "verified@example.com",
                "email_verified": True,
            }

            async with app.test_request_context("/signup/google", method="POST", json=payload):
                g.db = mock_db
                resp, status = await self.auth_view.signup_google()

        # Assertions
        self.assertEqual(status, HTTPStatus.CREATED)
        data = await resp.get_json()
        self.assertIn("user_id", data)

        mock_create_user.assert_awaited_once()

        # _create_user was called with kwargs only
        call = mock_create_user.await_args
        kwargs = call.kwargs if hasattr(call, "kwargs") else call[1]
        self.assertEqual(kwargs["username"], "google_xyz789")
        self.assertEqual(kwargs["email"], "verified@example.com")
        self.assertTrue(kwargs["email_verified"])
        self.assertTrue("password" not in kwargs or kwargs["password"] is None)

    async def test_create_user_without_password_unverified(self):
        app = Quart(__name__)
        # Arrange
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        username = "nopw_user"
        email = "nopw@example.com"

        with patch.object(auth_api_view.bcrypt, "hash") as mock_hashpw:
            # Act
            async with app.test_request_context("/x", method="POST"):
                g.db = mock_db
                returned_id = await self.auth_view._create_user(
                    username=username,
                    email=email,
                    # password omitted -> None
                    email_verified=False,
                )

        # Assert: bcrypt should NOT be called when no password is provided
        mock_hashpw.assert_not_called()

        # DB execute was awaited once
        mock_db.execute.assert_awaited_once()
        call = mock_db.execute.await_args
        args = call.args if hasattr(call, "args") else call[0]

        # SQL string sanity check (don’t match the whole string to avoid brittleness)
        self.assertIn("INSERT INTO users", args[0])

        # Arg positions:
        # 0 = SQL, 1 = user_id, 2 = username, 3 = email, 4 = password_hash, 5 = email_is_verified, 6 = timestamp
        user_id_arg = args[1]
        self.assertIsInstance(user_id_arg, uuid.UUID)
        self.assertEqual(returned_id, user_id_arg)

        self.assertEqual(args[2], username)
        self.assertEqual(args[3], email)
        self.assertIsNone(args[4])                 # password_hash is None
        self.assertEqual(args[5], False)         # email_verified -> "FALSE"

        ts = args[6]
        self.assertIsInstance(ts, datetime)
        self.assertEqual(ts.tzinfo, timezone.utc)  # timestamp is timezone-aware UTC

    async def test_create_user_with_password_verified(self):
        app = Quart(__name__)
        # Arrange
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()
        username = "pw_user"
        email = "pw@example.com"
        password = "s3cr3t"

        # Make bcrypt deterministic & fast
        with patch.object(auth_api_view.bcrypt, "hash", return_value=b"hashedpw") as mock_hashpw:

            # Act
            async with app.test_request_context("/x", method="POST"):
                g.db = mock_db
                returned_id = await self.auth_view._create_user(
                    username=username,
                    email=email,
                    password=password,
                    email_verified=True,
                )

        # Assert bcrypt usage
        mock_hashpw.assert_called_once()
        # hashpw called with password bytes and salt bytes
        args_hash = mock_hashpw.call_args.args if hasattr(mock_hashpw.call_args, "args") else mock_hashpw.call_args[0]
        self.assertEqual(args_hash[0], password)

        # DB execute was awaited once
        mock_db.execute.assert_awaited_once()
        call = mock_db.execute.await_args
        args = call.args if hasattr(call, "args") else call[0]

        # SQL check
        self.assertIn("INSERT INTO users", args[0])

        user_id_arg = args[1]
        self.assertIsInstance(user_id_arg, uuid.UUID)
        self.assertEqual(returned_id, user_id_arg)

        self.assertEqual(args[2], username)
        self.assertEqual(args[3], email)
        self.assertEqual(args[4], b"hashedpw")
        self.assertEqual(args[5], True)

        ts = args[6]
        self.assertIsInstance(ts, datetime)
        self.assertEqual(ts.tzinfo, timezone.utc)

    async def test_create_auth_provider_with_tokens_and_expiry(self):
        app = Quart(__name__)

        # Arrange input
        user_id = uuid.uuid4()
        provider = "google"
        provider_uid = "prov-123"
        access_token = "access-xyz"
        refresh_token = "refresh-abc"
        expires_at = datetime(2030, 1, 1, tzinfo=timezone.utc)

        # Async DB mock
        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        # Act
        async with app.test_request_context("/x", method="POST"):
            g.db = mock_db
            await self.auth_view._create_auth_provider(
                user_id=user_id,
                provider=provider,
                provider_uid=provider_uid,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
            )

        # Assert DB was awaited once with expected positional args
        mock_db.execute.assert_awaited_once()
        call = mock_db.execute.await_args
        args = call.args if hasattr(call, "args") else call[0]

        # args layout:
        # 0 = SQL
        # 1 = id (new uuid), 2 = user_id, 3 = provider, 4 = provider_uid,
        # 5 = access_token, 6 = refresh_token, 7 = expires_at, 8 = timestamp (UTC)
        self.assertIn("INSERT INTO auth_providers", args[0])

        self.assertIsInstance(args[1], uuid.UUID)         # generated id
        self.assertEqual(args[2], user_id)
        self.assertEqual(args[3], provider)
        self.assertEqual(args[4], provider_uid)
        self.assertEqual(args[5], access_token)
        self.assertEqual(args[6], refresh_token)
        self.assertEqual(args[7], expires_at)

        ts = args[8]
        self.assertIsInstance(ts, datetime)
        self.assertEqual(ts.tzinfo, timezone.utc)

    async def test_create_auth_provider_with_none_refresh_and_expiry(self):
        app = Quart(__name__)

        # Arrange input with optionals set to None
        user_id = uuid.uuid4()
        provider = "github"
        provider_uid = "gh-999"
        access_token = "tkn"
        refresh_token = None
        expires_at = None

        mock_db = MagicMock()
        mock_db.execute = AsyncMock()

        # Act
        async with app.test_request_context("/x", method="POST"):
            g.db = mock_db
            await self.auth_view._create_auth_provider(
                user_id=user_id,
                provider=provider,
                provider_uid=provider_uid,
                access_token=access_token,
                refresh_token=refresh_token,
                expires_at=expires_at,
            )

        # Assert DB awaited with the correct args (including Nones)
        mock_db.execute.assert_awaited_once()
        call = mock_db.execute.await_args
        args = call.args if hasattr(call, "args") else call[0]

        self.assertIn("INSERT INTO auth_providers", args[0])
        self.assertIsInstance(args[1], uuid.UUID)         # new id
        self.assertEqual(args[2], user_id)
        self.assertEqual(args[3], provider)
        self.assertEqual(args[4], provider_uid)
        self.assertEqual(args[5], access_token)
        self.assertIsNone(args[6])                        # refresh_token None
        self.assertIsNone(args[7])                        # expires_at None

        ts = args[8]
        self.assertIsInstance(ts, datetime)
        self.assertEqual(ts.tzinfo, timezone.utc)

    async def test_login_password_invalid_json_body(self):
        """Should return 400 if request JSON is invalid"""
        app = Quart(__name__)

        async with app.test_request_context(
            path="/auth/login_password",
            method="POST",
            json=None,  # simulate missing/invalid JSON
        ):
            response, status = await self.auth_view.login_password()
            self.assertEqual(status, HTTPStatus.BAD_REQUEST)
            self.assertIn("error", (await response.get_json()))


    async def test_login_password_user_not_found(self):
        """Should return 401 if no user exists"""
        app = Quart(__name__)
        fake_db = AsyncMock()
        fake_db.fetchrow.return_value = None

        async with app.test_request_context(
            path="/auth/login_password",
            method="POST",
            json={"username_or_email": "bob", "password": "secret"},
        ):
            g.db = fake_db
            response, status = await self.auth_view.login_password()
            self.assertEqual(status, HTTPStatus.UNAUTHORIZED)
            self.assertIn("Invalid credentials", (await response.get_json())["error"])

    async def test_login_password_inactive_user(self):
        """Should return 403 if user is inactive"""
        app = Quart(__name__)

        fake_user = {
            "id": uuid.uuid4(),
            "username": "bob",
            "email": "bob@example.com",
            "password_hash": bcrypt.hash("secret"),
            "is_active": False,
            "is_verified": False,
        }
        fake_db = AsyncMock()
        fake_db.fetchrow.return_value = fake_user

        async with app.test_request_context(
            path="/auth/login_password",
            method="POST",
            json={"username_or_email": "bob", "password": "secret"},
        ):
            g.db = fake_db
            response, status = await self.auth_view.login_password()
            self.assertEqual(status, HTTPStatus.FORBIDDEN)
            self.assertIn("Account disabled", (await response.get_json())["error"])

    async def test_login_password_wrong_password(self):
        """Should return 401 if password does not match"""
        app = Quart(__name__)
        fake_user = {
            "id": uuid.uuid4(),
            "username": "bob",
            "email": "bob@example.com",
            "password_hash": bcrypt.hash("secret"),
            "is_active": True,
            "is_verified": False,
        }
        fake_db = AsyncMock()
        fake_db.fetchrow.return_value = fake_user

        async with app.test_request_context(
            path="/auth/login_password",
            method="POST",
            json={"username_or_email": "bob", "password": "wrong"},
        ):
            g.db = fake_db
            response, status = await self.auth_view.login_password()
            self.assertEqual(status, HTTPStatus.UNAUTHORIZED)
            self.assertIn("Invalid credentials", (await response.get_json())["error"])

    async def test_login_password_successful_login(self):
        """Should return 200 and user details if login succeeds"""
        app = Quart(__name__)
        user_id = uuid.uuid4()
        fake_user = {
            "id": user_id,
            "username": "bob",
            "email": "bob@example.com",
            "password_hash": bcrypt.hash("secret"),
            "is_active": True,
            "is_verified": True,
        }
        fake_db = AsyncMock()
        fake_db.fetchrow.return_value = fake_user
        fake_db.execute.return_value = None  # simulate update last_login

        async with app.test_request_context(
            path="/auth/login_password",
            method="POST",
            json={"username_or_email": "bob", "password": "secret"},
        ):
            g.db = fake_db
            response, status = await self.auth_view.login_password()
            self.assertEqual(status, HTTPStatus.OK)

            body = await response.get_json()
            self.assertEqual(body["user_id"], str(user_id))
            self.assertEqual(body["username"], "bob")
            self.assertEqual(body["email"], "bob@example.com")
            self.assertTrue(body["is_verified"])
            self.assertEqual(body["message"], "Login successful")
