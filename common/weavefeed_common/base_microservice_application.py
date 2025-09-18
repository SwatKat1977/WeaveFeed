"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
import asyncio
import logging


class BaseMicroserviceApplication:
    """ Base microservice class. """
    __slots__ = ["_is_initialised", "_logger", "_shutdown_requested"]

    @property
    def logger(self) -> logging.Logger:
        """
        Property getter for logger instance.

        returns:
            Returns the logger instance.
        """
        return self._logger

    @logger.setter
    def logger(self, logger : logging.Logger) -> None:
        """
        Property setter for logger instance.

        parameters:
            logger (logging.Logger) : Logger instance.
        """
        self._logger = logger

    def __init__(self):
        self._is_initialised : bool = False
        self._logger : logging.Logger = None
        self._shutdown_requested : bool = False

    def initialise(self) -> bool:
        """
        Application initialisation.  It should return a boolean
        (True => Successful, False => Unsuccessful), upon success
        self._is_initialised is set to True.

        returns:
            Boolean: True => Successful, False => Unsuccessful.
        """
        if self._initialise() is True:
            self._is_initialised = True
            init_status = True

        else:
            init_status = False

        return init_status

    async def run(self) -> None:
        """
        Start the application.
        """

        try:
            while not self._shutdown_requested and self._is_initialised:
                await self._main_loop()
                await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            self._logger.info("KeyboardInterrupt received. Stopping...")
            self.stop()

        self._logger.info("Exiting application entrypoint...")

    def stop(self) -> None:
        """
        Stop the application, it will wait until shutdown has been marked as
        completed before calling the shutdown method.
        """

        self._logger.info("Stopping application...")
        self._logger.info('Waiting for application shutdown to complete')

        self._shutdown_requested = True


        self._shutdown()

    def _initialise(self) -> bool:
        """
        Application initialisation.  It should return a boolean
        (True => Successful, False => Unsuccessful).

        returns:
            Boolean: True => Successful, False => Unsuccessful.
        """
        return True

    async def _main_loop(self) -> None:
        """ Abstract method for main application. """
        raise NotImplementedError("Requires implementing")

    def _shutdown(self) -> None:
        """ Abstract method for application shutdown. """
