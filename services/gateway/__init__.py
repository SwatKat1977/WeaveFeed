"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
import asyncio
import os
from quart import Quart
from application import Application

# Quart application instance
app = Quart(__name__)

SERVICE_APP: Application = Application(app)

async def cancel_background_tasks():
    """
    Cancel and await the application's background task, if it exists.

    This function looks for a task stored on the global ``app`` object
    under the attribute ``background_task``. If found, it cancels the task
    and safely awaits its termination. Any ``asyncio.CancelledError``
    raised during cancellation is suppressed.

    This is typically called during application shutdown to ensure that
    background operations are gracefully stopped.

    Raises:
        asyncio.CancelledError: Only if the cancellation is not suppressed
            (unexpected behavior).
    """
    task = getattr(app, "background_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


@app.before_serving
async def startup() -> None:
    """
    Code executed before Quart has begun serving http requests.

    returns:
        None
    """
    if not await SERVICE_APP.initialise():
        os._exit(1)

    app.background_task = asyncio.create_task(SERVICE_APP.run())


@app.after_serving
async def shutdown() -> None:
    """
    Code executed after Quart has stopped serving http requests.

    returns:
        None
    """
    SERVICE_APP.shutdown_event.set()

    if app is not None:
        await cancel_background_tasks()
