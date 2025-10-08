"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
from datetime import datetime, timezone
from http import HTTPStatus
import logging
import typing
import uuid
from passlib.hash import bcrypt
from pydantic import BaseModel, EmailStr, ValidationError
import quart
from weavefeed_common.base_api_view import BaseApiView
from data_access_layer.user_data_access_layer import (
    UserDataAccessLayer)
from data_services.user_data_service import UserDataService
from state_object import StateObject


# --- Request Models ---
class PasswordSignupRequest(BaseModel):
    """
    Request model for signing up with a username, email, and password.

    Attributes:
        username (str): The desired username for the new account.
        email (EmailStr): The email address of the user.
        password (str): The chosen password for the account.
    """
    username: str
    email: EmailStr
    password: str


class OAuthSignupRequest(BaseModel):
    """
    Request model for signing up using an OAuth provider.

    Attributes:
        provider_uid (str): Unique identifier from the OAuth provider.
        access_token (str): Access token issued by the provider.
        refresh_token (Optional[str]): Optional refresh token from the provider.
        expires_at (Optional[datetime]): Token expiration timestamp.
    """
    provider_uid: str
    access_token: str
    refresh_token: typing.Optional[str]
    expires_at: typing.Optional[datetime]


class PasswordLoginRequest(BaseModel):
    """
    Request body schema for logging in with a password-based account.

    Attributes:
        username_or_email (str): Either the username or email of the user.
        password (str): The plaintext password provided by the user. This will
            be validated against the stored password hash in the database.
    """
    username_or_email: str
    password: str


class AuthApiView(BaseApiView):
    """
    API view handling user authentication and signup logic.

    Provides endpoints for password-based signup and Google OAuth signup.
    """

    def __init__(self, logger: logging.Logger,
                 state_object: StateObject) -> None:
        """
        Initialize the Auth API view with a child logger.

        Args:
            logger (logging.Logger): Base logger instance.
        """
        self._logger = logger.getChild(__name__)
        self._state_object = state_object

    async def signup_password(self):
        """
        Handle user signup with username, email, and password.

        - Validates input JSON against PasswordSignupRequest.
        - Checks if username or email is already taken.
        - Creates a new user record in the database if valid.

        Returns:
            tuple: (JSON response, HTTP status code)
        """
        data = await quart.request.get_json()
        try:
            req = PasswordSignupRequest(**data)
        except ValidationError as ex:
            return quart.jsonify({"error": str(ex)}), HTTPStatus.BAD_REQUEST

        db = quart.g.db
        user_dal = UserDataAccessLayer(db, self._logger, self._state_object)
        user_service = UserDataService(user_dal, self._state_object)

        result = await user_service.signup_with_password(
            req.username, req.email, req.password
        )

        return quart.jsonify({k: v for k, v in result.items() \
                              if k != "status"}), result["status"]

    # @auth_bp.route("/signup/google", methods=["POST"])
    async def signup_google(self):
        """
        Handle user signup with Google OAuth.

        - Validates input JSON against OAuthSignupRequest.
        - Checks if the provider UID is already linked to a user.
        - Uses verified email if available, otherwise creates a placeholder.
        - Creates a new user record without requiring a password.

        Returns:
            tuple: (JSON response, HTTP status code)
        """
        data = await quart.request.get_json()

        try:
            req = OAuthSignupRequest(**data)

        except ValidationError as ex:
            return quart.jsonify({"error": str(ex)}), \
                   HTTPStatus.BAD_REQUEST

        # Check if this provider UID already exists
        existing = await quart.g.db.fetchrow(
            ("SELECT user_id FROM auth_providers WHERE provider=$1 AND "
             "provider_uid=$2"),
            "google", req.provider_uid
        )
        if existing:
            return quart.jsonify({"error": "Account already linked"}), \
                HTTPStatus.CONFLICT

        # Use verified email if available, else fallback
        email: typing.Optional[str] = None
        email_verified: bool = False
        if getattr(req, "email", None) and \
           getattr(req, "email_verified", False):
            email = req.email
            email_verified = True
        else:
            # Fallback to placeholder email
            email = f"{req.provider_uid}@googleuser.fake"
            email_verified = False

        # Create a new user (no password for external auth)
        user_id = await self._create_user(
            username=f"google_{req.provider_uid}",
            email=email,
            email_verified=email_verified,
        )

        return quart.jsonify({"user_id": user_id}), \
            HTTPStatus.CREATED

    async def login_password(self):
        """
        Handle user login via username/email and password.

        Steps:
            1. Parse and validate the request body against PasswordLoginRequest.
            2. Look up the user by username OR email in the database.
            3. Verify that the account is active and the password matches.
            4. Update the user's last_login timestamp.
            5. Return a success response with basic user details.

        Returns:
            JSON response with:
                - 200 OK: Login successful.
                - 400 Bad Request: Invalid request body.
                - 401 Unauthorized: Invalid credentials.
                - 403 Forbidden: Account disabled.
        """
        data = await quart.request.get_json()

        if not data:
            return quart.jsonify({"error": "Invalid or missing JSON body"}), \
                HTTPStatus.BAD_REQUEST

        try:
            req = PasswordLoginRequest(**data)
        except ValidationError as e:
            return quart.jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST

        # Find user by username OR email
        user = await quart.g.db.fetchrow(
            """
            SELECT id, username, email, password_hash, is_active, is_verified
            FROM users
            WHERE username = $1 OR email = $1
            """,
            req.username_or_email,
        )

        if not user:
            return quart.jsonify({"error": "Invalid credentials"}), \
                HTTPStatus.UNAUTHORIZED

        if not user["is_active"]:
            return quart.jsonify({"error": "Account disabled"}), \
                HTTPStatus.FORBIDDEN

        if not user["password_hash"] or not bcrypt.verify(
                req.password, user["password_hash"]):
            return quart.jsonify({"error": "Invalid credentials"}), \
                HTTPStatus.UNAUTHORIZED

        # Update last_login
        await quart.g.db.execute(
            "UPDATE users SET last_login=$1 WHERE id=$2",
            datetime.utcnow(), user["id"]
        )

        return quart.jsonify({
            "message": "Login successful",
            "user_id": str(user["id"]),
            "username": user["username"],
            "email": user["email"],
            "is_verified": user["is_verified"],
        }), HTTPStatus.OK

    async def _create_auth_provider(self,
                                    user_id: uuid.UUID,
                                    provider: str,
                                    provider_uid: str,
                                    access_token: str,
                                    refresh_token: typing.Optional[str],
                                    expires_at: typing.Optional[datetime]):
        """
        Link an authentication provider (e.g., Google) to a user account.

        Args:
            user_id (uuid.UUID): ID of the user being linked.
            provider (str): The provider name (e.g., "google").
            provider_uid (str): The provider-specific unique ID.
            access_token (str): OAuth access token.
            refresh_token (Optional[str]): Optional refresh token.
            expires_at (Optional[datetime]): Expiration time of the access token.
        """
        # pylint: disable=too-many-arguments, too-many-positional-arguments

        await quart.g.db.execute(
            """
            INSERT INTO auth_providers
            (id, user_id, provider, provider_uid, access_token, refresh_token,
             expires_at, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $8)
            """,
            uuid.uuid4(), user_id, provider, provider_uid, access_token,
            refresh_token, expires_at, datetime.now(timezone.utc)
        )
# 301