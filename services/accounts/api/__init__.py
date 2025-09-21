"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
import logging
import quart
from .auth_api import create_blueprint as create_auth_bp


def create_routes(logger: logging.Logger) -> quart.Blueprint:
    """
    Create and configure the API route blueprint for the application.

    This function initializes a Quart blueprint for the API routes and
    registers sub-blueprints.

    Args:
        logger (logging.Logger): Logger instance for logging within the APIS.

    Returns:
        quart.Blueprint: The configured API blueprint with registered
                         sub-routes.
    """
    api_bp = quart.Blueprint("api_routes", __name__)

    api_bp.register_blueprint(create_auth_bp(logger),
                              url_prefix="/auth")

    return api_bp
