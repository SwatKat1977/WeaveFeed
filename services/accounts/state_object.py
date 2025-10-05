"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
import time
from dataclasses import dataclass, field
from weavefeed_common.service_health_enums import ComponentDegradationLevel

@dataclass
class StateObject:
    """
    Represents the state of a service, including its health status, database
    status, version, and startup time.

    Attributes:
        service_health (ComponentDegradationLevel): The current health status
                                                    of the service.
        service_health_state_str (str): A descriptive string representing the
                                        service health state.
        database_health (ComponentDegradationLevel): The current health status
                                                     of the database.
        database_health_state_str (str): A descriptive string representing the
                                         database health state.
        version (str): The version of the service.
        startup_time (int): The timestamp (Unix time) when the service was
                            started.
    """
    service_health: ComponentDegradationLevel = ComponentDegradationLevel.NONE
    service_health_state_str: str = ""
    database_health: ComponentDegradationLevel = ComponentDegradationLevel.NONE
    database_health_state_str: str = ""
    version: str = ""
    startup_time: int = field(default_factory=lambda: int(time.time()))
