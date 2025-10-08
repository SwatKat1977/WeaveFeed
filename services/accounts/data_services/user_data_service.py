"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
from passlib.hash import bcrypt
from http import HTTPStatus
from state_object import StateObject


class UserDataService:
    def __init__(self, user_dal, state_object: StateObject):
        self._user_dal = user_dal
        self._state_object = state_object

    async def signup_with_password(self, username, email, password):
        """
        Handles user signup logic:
         - Checks duplicates
         - Hashes password
         - Creates user in the database
        """
        existing = await self._user_dal.check_user_exists(username, email)
        if existing:
            return {
                "error": "User already exists",
                "status": HTTPStatus.CONFLICT
            }

        password_hash = bcrypt.hash(password)
        user_id = await self._user_dal.create_user(
            username=username,
            email=email,
            password_hash=password_hash,
            verified=False,
            state_object=self._state_object
        )

        if not user_id:
            return {
                "error": "Failed to create user",
                "status": HTTPStatus.INTERNAL_SERVER_ERROR
            }

        return {
            "message": "User created successfully",
            "user_id": str(user_id),
            "username": username,
            "email": email,
            "status": HTTPStatus.CREATED
        }

    async def login_with_password(self, username_or_email, password):
        """
        Handles user login logic:
         - Fetches user
         - Verifies credentials
        """
        user = await self._user_dal.get_by_email_or_username(username_or_email)
        if not user:
            return {"error": "Invalid credentials",
                    "status": HTTPStatus.UNAUTHORIZED}

        if not user["is_active"]:
            return {"error": "Account disabled",
                    "status": HTTPStatus.FORBIDDEN}

        if not user["password_hash"] or not bcrypt.verify(password,
                                                          user["password_hash"]):
            return {"error": "Invalid credentials",
                    "status": HTTPStatus.UNAUTHORIZED}

        return {
            "message": "Login successful",
            "user_id": str(user["id"]),
            "username": user["username"],
            "email": user["email"],
            "is_verified": user["is_verified"],
            "status": HTTPStatus.OK
        }
