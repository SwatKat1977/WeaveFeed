"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
import logging
from quart import Blueprint
from api.auth_api_view import AuthApiView


def create_blueprint(logger: logging.Logger) -> Blueprint:
    """
    Creates and registers a Quart Blueprint for handling authentication.

    This function initializes a `View` object with the provided logger, and
    then defines an API endpoints for authentication.

    Args:
        logger (logging.Logger): A logger instance for logging messages.

    Returns:
        Blueprint: A Quart `Blueprint` object containing the registered route.
    """
    view = AuthApiView(logger)

    blueprint = Blueprint('auth_api', __name__)

    logger.debug("Registering Auth API routes:")

    logger.debug("=> /auth/signup_password [POST]")

    @blueprint.route("/signup_password", methods=["POST"])
    async def auth_signup_password_request():
        return await view.signup_password()

    return blueprint
