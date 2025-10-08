"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
from enum import Enum


class ServiceDegradationStatus(Enum):
    """ Service degradation Status """

    # Everything is working fine
    HEALTHY = "healthy"

    # Some components are slow or experiencing minor issues
    DEGRADED = "degraded"

    # A major component is down, affecting service functionality
    CRITICAL = "critical"


class ComponentDegradationLevel(Enum):
    """ Component degradation Level """

    NONE = "none"
    PART_DEGRADED = "partial"
    FULLY_DEGRADED = "fully_degraded"
