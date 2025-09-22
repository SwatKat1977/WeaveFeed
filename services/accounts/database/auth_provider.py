"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
import uuid
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from .base import Base
from .created_updated_timestamp_mixin import CreatedUpdatedTimestampMixin


class AuthProvider(CreatedUpdatedTimestampMixin, Base):
    """
    SQLAlchemy model for linking a user account to an external authentication provider
    (e.g., Google, GitHub, Facebook).

    Each record stores the provider details, associated tokens, and lifecycle timestamps.
    A user can have multiple providers, but each provider UID must be unique across the
    system.

    Attributes:
        id (UUID): Primary key, unique identifier for the auth provider record.
        user_id (UUID): Foreign key reference to the associated user (`users.id`).
            Cascade delete ensures auth provider entries are removed if the user is deleted.
        provider (str): The name of the provider (e.g., "google").
        provider_uid (str): The unique identifier for the user from the provider.
            Must be unique in combination with `provider`.
        access_token (str): The access token issued by the provider for API calls.
        refresh_token (str): Optional refresh token for renewing access.
        expires_at (datetime): Expiration time of the access token, if provided.
        created_at (datetime): Timestamp when the record was created.
            Defaults to current UTC time.
        updated_at (datetime): Timestamp when the record was last updated.
            Automatically refreshed on modification.

    Table constraints:
        uq_provider_uid: Ensures uniqueness of `(provider, provider_uid)` pairs.
    """
    # pylint: disable=too-few-public-methods
    __tablename__ = "auth_providers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True),
                     ForeignKey("users.id", ondelete="CASCADE"),
                     nullable=False)
    provider = Column(String(32), nullable=False)      # e.g. "google"
    provider_uid = Column(String(255), nullable=False) # unique provider ID
    access_token = Column(Text)
    refresh_token = Column(Text)
    expires_at = Column(DateTime)

    __table_args__ = (
        UniqueConstraint("provider", "provider_uid", name="uq_provider_uid"),
    )
