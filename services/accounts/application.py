"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
import asyncio
import logging
import os
import sys
from weavefeed_common import __version__
from weavefeed_common.configuration.configuration import Configuration
from weavefeed_common.base_microservice_application \
    import BaseMicroserviceApplication
from weavefeed_common.logging_consts import LOGGING_DATETIME_FORMAT_STRING, \
                                            LOGGING_DEFAULT_LOG_LEVEL, \
                                            LOGGING_LOG_FORMAT_STRING
from api import create_routes
from configuration_layout import CONFIGURATION_LAYOUT
from state_object import StateObject


class Application(BaseMicroserviceApplication):
    """ ITEMS Accounts Service """

    def __init__(self, quart_instance):
        super().__init__()
        self._quart_instance = quart_instance
        self._config = None
        self._state_object: StateObject = StateObject()

        self._logger = logging.getLogger(__name__)
        log_format = logging.Formatter(LOGGING_LOG_FORMAT_STRING,
                                       LOGGING_DATETIME_FORMAT_STRING)
        console_stream = logging.StreamHandler(sys.stdout)
        console_stream.setFormatter(log_format)
        self._logger.setLevel(LOGGING_DEFAULT_LOG_LEVEL)
        self._logger.propagate = True
        self._logger.addHandler(console_stream)

    async def _initialise(self) -> bool:
        self._logger.info("WeaveFeed Account Microservice %s",
                          __version__)
        self._logger.info("https://github.com/SwatKat1977/WeaveFeed")

        # Acceptable values
        truths: set = {"1", "true", "yes", "on"}
        falses: set = {"0", "false", "no", "off"}

        config_file = os.getenv("WEAVEFEED_ACCOUNTS_CONFIG_FILE", None)
        raw_required = os.getenv("WEAVEFEED_ACCOUNTS_CONFIG_FILE_REQUIRED",
                                 "false").strip().lower()

        if raw_required in truths:
            config_file_required: bool = True
        elif raw_required in falses:
            config_file_required: bool = False
        else:
            print(f"[FATAL ERROR] Invalid value for "
                  f"WEAVEFEED_ACCOUNTS_CONFIG_FILE_REQUIRED: '{raw_required}'",
                  flush=True)
            return False

        if not config_file and config_file_required:
            print("[FATAL ERROR] Configuration file missing!", flush=True)
            return False

        self._config = Configuration()
        self._config.configure(CONFIGURATION_LAYOUT,
                               config_file,
                               config_file_required)

        try:
            self._config.process_config()

        except ValueError as ex:
            self._logger.critical("Configuration error : %s", ex)
            return False

        self._logger.setLevel(self._config.get_entry("logging", "log_level"))

        self._display_configuration_details()

        # Set the version string on state object.
        self._state_object.version = __version__

        self._quart_instance.register_blueprint(create_routes(self._logger))

        return True

    async def _main_loop(self) -> None:
        """ Abstract method for main application. """
        await asyncio.sleep(0.1)

    async def _shutdown(self):
        """ Shutdown logic. """

    def _display_configuration_details(self):
        self._logger.info("Configuration")
        self._logger.info("=============")
        self._logger.info("[logging]")
        self._logger.info("=> Logging log level              : %s",
                          self._config.get_entry("logging", "log_level"))
