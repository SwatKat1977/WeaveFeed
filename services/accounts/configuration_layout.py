"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
from weavefeed_common.configuration import configuration_setup

CONFIGURATION_LAYOUT = configuration_setup.ConfigurationSetup(
    {
        "logging": [
            configuration_setup.ConfigurationSetupItem(
                "log_level", configuration_setup.ConfigItemDataType.STRING,
                valid_values=['DEBUG', 'INFO'], default_value="INFO")
        ]
    }
)
