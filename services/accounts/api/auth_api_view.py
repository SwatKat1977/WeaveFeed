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
import bcrypt
from pydantic import BaseModel, EmailStr, ValidationError
import quart
from weavefeed_common.base_api_view import BaseApiView


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


class AuthApiView(BaseApiView):
    """
    API view handling user authentication and signup logic.

    Provides endpoints for password-based signup and Google OAuth signup.
    """

    def __init__(self, logger: logging.Logger) -> None:
        """
        Initialize the Auth API view with a child logger.

        Args:
            logger (logging.Logger): Base logger instance.
        """
        self._logger = logger.getChild(__name__)

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

        # Check uniqueness
        existing = await quart.g.db.fetchrow(
            "SELECT id FROM users WHERE email=$1 OR username=$2",
            req.email, req.username)

        if existing:
            return (quart.jsonify({"error": "User already exists"}),
                    HTTPStatus.CONFLICT)

        # Create user
        user_id = await self._create_user(req.username,
                                          req.email,
                                          req.password)

        return quart.jsonify({
            "message": "User created (password)",
            "user_id": str(user_id),
            "username": req.username,
            "email": req.email,
        }), HTTPStatus.CREATED

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

    async def _create_user(self,
                           username: str,
                           email: str,
                           password: typing.Optional[str] = None,
                           email_verified: bool=False) -> uuid.UUID:
        """
        Create a new user in the database.

        Args:
            username (str): The username for the new account.
            email (str): The email address of the user.
            password (Optional[str]): If provided, will be securely hashed.

        Returns:
            uuid.UUID: The unique identifier of the created user.
        """
        user_id = uuid.uuid4()
        password_hash = None

        if password:
            password_hash = bcrypt.hashpw(password.encode(),
                                          bcrypt.gensalt()).decode()

        email_is_verified: str = "FALSE" if not email_verified else "TRUE"

        await quart.g.db.execute(
            """
            INSERT INTO users(id, username, email, password_hash, is_active,
                              is_verified, created_at, updated_at)
            VALUES ($1, $2, $3, $4, FALSE, $5, $6, $6)
            """,
            user_id, username, email, password_hash, email_is_verified,
            datetime.now(timezone.utc)
        )
        return user_id

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
