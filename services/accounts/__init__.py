"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
import asyncio
import os
import sys
from quart import Quart
from application import Application

# Quart application instance
app = Quart(__name__)

SERVICE_APP: Application = Application(app)


@app.before_serving
async def startup() -> None:
    """
    Code executed before Quart has began serving http requests.

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
    task = getattr(app, "background_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
