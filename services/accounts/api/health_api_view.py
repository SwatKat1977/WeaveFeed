"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
import http
import json
import logging
import time
from quart import Response
from weavefeed_common.base_api_view import BaseApiView
from state_object import StateObject
from weavefeed_common.service_health_enums import (ServiceDegradationStatus,
                                                   ComponentDegradationLevel)


class HealthApiView(BaseApiView):
    """
    A view that provides health check information for the application.

    This includes the health status of core components like the database and
    microservices, system uptime, and application version.

    Attributes:
        _logger (logging.Logger): Logger instance for recording events.
        _state_object (StateObject): Shared state object containing health and
                                     version info.
    """

    def __init__(self, logger: logging.Logger,
                 state_object: StateObject) -> None:
        """
        Initializes the HealthApiView with logging and application state.

        Args:
            logger (logging.Logger): Logger for emitting structured health
                                     check logs.
            state_object (StateObject): Application-wide state for tracking
                                        health, startup time, etc.
        """
        self._logger = logger.getChild(__name__)
        self._state_object = state_object

    async def health(self):
        """
        Performs a health check and returns a JSON response with system status.

        Checks the health of the database and the microservice components,
        calculates system uptime, and reports any degraded statuses.

        Returns:
            quart.Response: A JSON-formatted HTTP response indicating the overall health,
                            dependency statuses, current issues (if any), uptime, and version.
        """
        uptime: int = int(time.time()) - self._state_object.startup_time
        issues: list = []

        # Check database health
        if self._state_object.database_health != \
                ComponentDegradationLevel.NONE:
            issues.append(
                {"component": "database",
                 "status": self._state_object.database_health.value,
                 "details": self._state_object.database_health_state_str})

        # Check microservice health
        if (self._state_object.service_health !=
                ComponentDegradationLevel.NONE):
            issues.append(
                {"component": "service",
                 "status": self._state_object.service_health.view,
                 "details": self._state_object.service_health_state_str})

        if issues:
            status = ServiceDegradationStatus.CRITICAL.value \
                if any(issue["status"] ==
                       ComponentDegradationLevel.FULLY_DEGRADED.value
                       for issue in issues)\
                else ServiceDegradationStatus.DEGRADED.value
        else:
            status = ServiceDegradationStatus.HEALTHY.value

        response: dict = {
            "status": status,
            "dependencies": {
                "database": self._state_object.database_health.value,
                "service": self._state_object.service_health.value
            },
            "issues": issues if issues else None,
            "uptime_seconds": uptime,
            "version": self._state_object.version
        }

        return Response(json.dumps(response),
                        status=http.HTTPStatus.OK,
                        content_type="application/json")
