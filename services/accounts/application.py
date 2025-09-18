"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
import asyncio
import logging
from weavefeed_common.base_microservice_application \
    import BaseMicroserviceApplication
from weavefeed_common.logging_consts import LOGGING_DATETIME_FORMAT_STRING, \
                                            LOGGING_DEFAULT_LOG_LEVEL, \
                                            LOGGING_LOG_FORMAT_STRING


class Application(BaseMicroserviceApplication):
    """ ITEMS Accounts Service """

    def __init__(self, quart_instance):
        super().__init__()
        self._quart_instance = quart_instance

        self._logger = logging.getLogger(__name__)
        log_format = logging.Formatter(LOGGING_LOG_FORMAT_STRING,
                                       LOGGING_DATETIME_FORMAT_STRING)
        console_stream = logging.StreamHandler()
        console_stream.setFormatter(log_format)
        self._logger.setLevel(LOGGING_DEFAULT_LOG_LEVEL)
        self._logger.addHandler(console_stream)

    async def _initialise(self) -> bool:
        return True

    async def _main_loop(self) -> None:
        """ Abstract method for main application. """
        await asyncio.sleep(0.1)

    async def _shutdown(self):
        """ Shutdown logic. """
