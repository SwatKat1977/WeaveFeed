"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from .base import Base
from .created_updated_timestamp_mixin import CreatedUpdatedTimestampMixin


class UserProfile(CreatedUpdatedTimestampMixin, Base):
    """
    SQLAlchemy model for storing additional user profile information.

    Each profile is uniquely linked to a user account and contains
    optional display information along with audit timestamps.

    Attributes:
        id (UUID): Primary key, unique identifier for the profile.
        user_id (UUID): Foreign key reference to the associated user
            (`users.id`). Enforced as unique so each user has at most
            one profile. Cascade delete ensures the profile is removed
            if the user is deleted.
        display_name (str): Optional human-friendly name shown in the UI.
            Limited to 64 characters.
        created_at (datetime): Timestamp when the profile was created.
            Defaults to current UTC time.
        updated_at (datetime): Timestamp when the profile was last updated.
            Automatically refreshed on modification.
    """
    # pylint: disable=too-few-public-methods
    __tablename__ = "user_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True),
                     ForeignKey("users.id", ondelete="CASCADE"),
                     unique=True, nullable=False)
    display_name = Column(String(64))
