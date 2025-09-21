from datetime import datetime
import logging
import typing
import uuid
from passlib.hash import bcrypt
import quart
from weavefeed_common.base_api_view import BaseApiView


class AuthApiView(BaseApiView):

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger.getChild(__name__)

    async def create_user(self,
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

    async def create_auth_provider(self,
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
