"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime


class CreatedUpdatedTimestampMixin:
    """
    SQLAlchemy mixin that adds standard timestamp fields to a model.

    Provides automatic tracking of record creation and last update times.
    Both fields are stored as timezone-aware UTC datetimes.

    Attributes:
        created_at (datetime): Timestamp when the record was created.
            Automatically set to the current UTC time when the row is first
            inserted. Cannot be null.
        updated_at (datetime): Timestamp when the record was last updated.
            Automatically set to the current UTC time on insert and refreshed
            whenever the row is updated. Cannot be null.
    """
    # pylint: disable=too-few-public-methods
    created_at = Column(DateTime,
                        default=lambda: datetime.now(timezone.utc),
                        nullable=False)
    updated_at = Column(DateTime,
                        default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc),
                        nullable=False)
