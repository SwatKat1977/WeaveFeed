"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
import uuid
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from .base import Base
from .created_updated_timestamp_mixin import CreatedUpdatedTimestampMixin


class User(CreatedUpdatedTimestampMixin, Base):
    """
    SQLAlchemy model representing a user account.

    This table stores core authentication and account state information.
    Additional details (such as profile info or linked providers) are
    stored in related tables.

    Attributes:
        id (UUID): Primary key, unique identifier for the user.
        username (str): Unique username for login or display.
        email (str): Unique email address of the user. Indexed for quick lookup.
        password_hash (str): Securely hashed password. May be null if the
            user authenticates only through external providers.
        is_active (bool): Flag indicating whether the account is active.
            Defaults to True. Inactive users may be suspended or deactivated.
        is_verified (bool): Flag indicating whether the account’s email has
            been verified. Defaults to False.
        last_login (datetime): Timestamp of the user’s most recent login.
        created_at (datetime): Timestamp when the account was created.
            Defaults to current UTC time.
        updated_at (datetime): Timestamp when the account was last updated.
            Automatically refreshed on modification.
    """
    # pylint: disable=too-few-public-methods
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(32), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(128))  # nullable if only external auth
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    last_login = Column(DateTime)
