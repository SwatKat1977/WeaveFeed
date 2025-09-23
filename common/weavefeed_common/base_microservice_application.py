"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
import abc
import asyncio
import logging
import typing


class BaseMicroserviceApplication(abc.ABC):
    """ Base microservice class. """
    __slots__ = ["_is_initialised", "_logger", "_shutdown_complete",
                 "_shutdown_event"]

    def __init__(self):
        self._is_initialised: bool = False
        self._logger: typing.Optional[logging.Logger] = None
        self._shutdown_event: asyncio.Event = asyncio.Event()
        self._shutdown_complete: asyncio.Event = asyncio.Event()

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

    @property
    def shutdown_event(self) -> asyncio.Event:
        """
        Event used to signal the shutdown of the service.

        This event should be awaited or checked by background tasks to
        gracefully stop operations when the application is shutting down.
        """
        return self._shutdown_event

    @property
    def shutdown_complete(self) -> asyncio.Event:
        """
        Event that indicates the service has completed its shutdown process.

        This should be set when all shutdown tasks and cleanup procedures have
        finished, allowing other components (like the main app) to know when
        it's safe to exit.
        """
        return self._shutdown_complete

    async def initialise(self) -> bool:
        """
        Microservice initialisation.  It should return a boolean
        (True => Successful, False => Unsuccessful), upon success
        self._is_initialised is set to True.

        Returns:
            Boolean: True => Successful, False => Unsuccessful.
        """
        if await self._initialise() is True:
            self._is_initialised = True
            return True

        await self.stop()

        return False

    async def run(self) -> None:
        """
        Start the microservice.
        """

        if not self._is_initialised:
            self._logger.warning("Microservice is not initialised. Exiting run loop.")
            return

        self._logger.info("Microservice starting main loop.")

        try:
            while True:
                if self.shutdown_event.is_set():
                    break

                await self._main_loop()
                await asyncio.sleep(0.1)

        except KeyboardInterrupt:
            self._logger.debug("Service: Keyboard interrupt received.")
            self._shutdown_event.set()

        except asyncio.CancelledError:
            self._logger.debug("Service: Cancellation received.")
            raise

        finally:
            self._logger.info("Exiting microservice run loop...")
            await self.stop()
            self._logger.info("Shutdown complete.")

    async def stop(self) -> None:
        """
        Stop the microservice, it will wait until shutdown has been marked as
        completed before calling the shutdown method.
        """

        self._logger.info("Stopping microservice...")
        self._logger.info('Waiting for microservice shutdown to complete')

        self._shutdown_event.set()

        await self._shutdown()
        self._shutdown_complete.set()

        self._logger.info('Microservice shutdown complete...')

    async def _initialise(self) -> bool:
        """
        Microservice initialisation.  It should return a boolean
        (True => Successful, False => Unsuccessful).

        Returns:
            Boolean: True => Successful, False => Unsuccessful.
        """
        return True

    @abc.abstractmethod
    async def _main_loop(self) -> None:
        """ Abstract method for main microservice loop. """

    @abc.abstractmethod
    async def _shutdown(self):
        """ Abstract method for microservice shutdown. """
