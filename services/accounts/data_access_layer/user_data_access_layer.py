"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
from datetime import datetime, timezone
import uuid
import asyncpg
from weavefeed_common.service_health_enums import ComponentDegradationLevel
from weavefeed_common.base_data_access_layer import BaseDataAccessLayer
from state_object import StateObject


class UserDataAccessLayer(BaseDataAccessLayer):

    def __init__(self, db, logger, state_object: StateObject):
        super().__init__(db, logger)
        self._state_object: StateObject = state_object

    async def check_user_exists(self, username: str, email: str):
        """
        Check if a user with the given username or email already exists.
        Returns the user's record if found, otherwise None.
        """
        try:

            existing = await self._db.fetchrow(
                """
                SELECT id FROM users
                WHERE username = $1 OR email = $2
                """,
                username, email
            )
            if existing:
                self._logger.debug("User already exists for username=%s "
                                   "or email=%s", username, email)
            return existing

        except asyncpg.PostgresError as ex:
            self._logger.exception("Database error while checking user "
                                   "existence: %s", ex)
            self._state_object.database_health = \
                ComponentDegradationLevel.FULLY_DEGRADED
            self._state_object.database_health_state_str = \
                f"Database error while checking user existence: {ex}"
            return None

        except Exception as ex:
            self._logger.exception("Unexpected error checking user existence: "
                                   "%s", ex)
            self._state_object.database_health = \
                ComponentDegradationLevel.PART_DEGRADED
            self._state_object.database_health_state_str = \
                f"Unexpected error checking user existence: {ex}"
            return None

    async def create_user(self,
                          username: str,
                          email: str,
                          password_hash: str,
                          verified: bool):
        user_id = uuid.uuid4()
        now = datetime.now(timezone.utc)

        try:
            async with (self._db.transaction()):
                # Update health at the start (assuming DB connection is fine so far)
                if self._state_object.database_health != \
                        ComponentDegradationLevel.FULLY_DEGRADED:
                    self._state_object.database_health = ComponentDegradationLevel.NONE
                    self._state_object.database_health_state_str = "Database operational"

                # Check for duplicates (extracted function)
                existing = await self.check_user_exists(username, email)
                if existing:
                    self._logger.warning("Attempt to create duplicate user: %s / %s", username, email)
                    return None

                # Insert new user
                await self._db.execute(
                    """
                    INSERT INTO users(id, username, email, password_hash,
                                      is_active, is_verified, created_at, updated_at)
                    VALUES ($1, $2, $3, $4, TRUE, $5, $6, $6)
                    """,
                    user_id, username, email, password_hash, verified, now
                )

                self._logger.info("Created user %s (%s)", username, user_id)
                return user_id

        except asyncpg.PostgresConnectionError:
            self._logger.exception("Database connection error during user creation.")
            self._state_object.database_health = \
                ComponentDegradationLevel.FULLY_DEGRADED
            self._state_object.database_health_state_str = "Database unreachable"
            return None

        except asyncpg.PostgresError as e:
            self._logger.exception("Database error during user creation: %s", e)
            self._state_object.database_health = \
                ComponentDegradationLevel.FULLY_DEGRADED
            self._state_object.database_health_state_str = \
                "Database operation failed"
            return None

        except Exception as e:
            self._logger.exception("Unexpected error creating user: %s", e)
            self._state_object.service_health = \
                ComponentDegradationLevel.FULLY_DEGRADED
            self._state_object.service_health_state_str = \
                "Service experienced unexpected failure"
            return None

    async def get_by_email_or_username(self,
                                       identifier: str):
        """
        Fetch a user record by email or username.
        Returns the record if found, otherwise None.
        Updates StateObject to reflect database health.
        """
        try:
            user = await self._db.fetchrow(
                """
                SELECT id, username, email, password_hash, is_active,
                       is_verified
                FROM users
                WHERE username = $1 OR email = $1
                """,
                identifier,
            )

            if user:
                self._logger.info("User lookup successful for identifier: %s",
                                  identifier)
                if self._state_object.database_health != \
                        ComponentDegradationLevel.FULLY_DEGRADED:
                    self._state_object.database_health = \
                        ComponentDegradationLevel.NONE
                    self._state_object.database_health_state_str = \
                        "Database operational"
                return user
            else:
                self._logger.warning("User not found for identifier: %s",
                                     identifier)
                if self._state_object.database_health != \
                        ComponentDegradationLevel.FULLY_DEGRADED:
                    self._state_object.database_health = \
                        ComponentDegradationLevel.NONE
                    self._state_object.database_health_state_str = \
                        "Database operational (no match)"
                return None

        except asyncpg.PostgresConnectionError:
            self._logger.exception(
                "Database connection error during user lookup.")
            self._state_object.database_health = \
                ComponentDegradationLevel.FULLY_DEGRADED
            self._state_object.database_health_state_str = \
                "Database unreachable"
            return None

        except asyncpg.PostgresError as ex:
            self._logger.exception("Database query error during user lookup: "
                                   "%s", ex)
            self._state_object.database_health = \
                ComponentDegradationLevel.PART_DEGRADED
            self._state_object.database_health_state_str = \
                "Database operation failed"
            return None

        except Exception as ex:
            self._logger.exception("Unexpected error fetching user: %s", ex)
            self._state_object.service_health = \
                ComponentDegradationLevel.FULLY_DEGRADED
            self._state_object.service_health_state_str = \
                "Service experienced unexpected failure"
            return None
