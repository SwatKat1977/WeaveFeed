from datetime import datetime
from http import HTTPStatus
import logging
import typing
import uuid
from passlib.hash import bcrypt
from pydantic import BaseModel, EmailStr
import quart
from weavefeed_common.base_api_view import BaseApiView


# --- Request Models ---
class PasswordSignupRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class OAuthSignupRequest(BaseModel):
    provider_uid: str
    access_token: str
    refresh_token: typing.Optional[str]
    expires_at: typing.Optional[datetime]


class AuthApiView(BaseApiView):
    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger.getChild(__name__)

    async def signup_password(self):
        data = await quart.request.get_json()
        try:
            req = PasswordSignupRequest(**data)
        except Exception as e:
            return quart.jsonify({"error": str(e)}), HTTPStatus.BAD_REQUEST

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
        data = await quart.request.get_json()
        try:
            req = OAuthSignupRequest(**data)
        except Exception as e:
            return quart.jsonify({"error": str(e)}), 400

        # Check if this provider UID already exists
        existing = await g.db.fetchrow(
            "SELECT user_id FROM auth_providers WHERE provider=$1 AND provider_uid=$2",
            "google", req.provider_uid
        )
        if existing:
            return quart.jsonify({"error": "Account already linked"}), 409

        # Create a new user (no password for external auth)
        user_id = await create_user(username=f"google_{req.provider_uid}", email=f"{req.provider_uid}@googleuser.fake")

        # Link provider
        await create_auth_provider(user_id, "google", req.provider_uid, req.access_token,
                                   req.refresh_token, req.expires_at)

        return quart.jsonify({
            "message": "User created (google)",
            "user_id": str(user_id),
            "provider_uid": req.provider_uid,
        }), 201

    async def _create_user(self,
                           username: str,
                           email: str,
                           password: typing.Optional[str] = None) -> uuid.UUID:
        user_id = uuid.uuid4()
        password_hash = None

        if password:
            password_hash = bcrypt.hashpw(password.encode(),
                                          bcrypt.gensalt()).decode()

        await quart.g.db.execute(
            """
            INSERT INTO users(id, username, email, password_hash, is_active,
                              is_verified, created_at, updated_at)
            VALUES ($1, $2, $3, $4, TRUE, FALSE, $5, $5)
            """,
            user_id, username, email, password_hash, datetime.utcnow()
        )
        return user_id

    async def _create_auth_provider(self,
                                    user_id: uuid.UUID,
                                    provider: str,
                                    provider_uid: str,
                                    access_token: str,
                                    refresh_token: typing.Optional[str],
                                    expires_at: typing.Optional[datetime]):
        await quart.g.db.execute(
            """
            INSERT INTO auth_providers
            (id, user_id, provider, provider_uid, access_token, refresh_token,
             expires_at, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $8)
            """,
            uuid.uuid4(), user_id, provider, provider_uid, access_token,
            refresh_token, expires_at, datetime.utcnow()
        )
