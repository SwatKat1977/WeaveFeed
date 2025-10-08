"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
import logging
from quart import Blueprint
from api.health_api_view import HealthApiView
from state_object import StateObject


def create_blueprint(logger: logging.Logger,
                     state_object: StateObject) -> Blueprint:
    """
    Creates and returns a Quart Blueprint for the Health Status API.

    This function initializes a `HealthApiView` instance and registers an
    asynchronous route `/health/status` for handling health check requests. The
    route is logged upon registration.

    Args:
        logger (logging.Logger): The logger instance used for logging API
                                 registration.
        state_object (StateObject): The application state object passed to the
                                    view.

    Returns:
        Blueprint: A Quart Blueprint instance with the registered health status
                   route.
    """
    view = HealthApiView(logger, state_object)

    blueprint = Blueprint('health_api', __name__)

    logger.debug("Registering Health Status API:")
    logger.debug("=> /health [GET]")

    @blueprint.route('/health', methods=['GET'])
    async def authenticate_request():
        return await view.health()

    return blueprint
