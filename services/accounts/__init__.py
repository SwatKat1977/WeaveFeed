"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
import asyncio
import sys
from quart import Quart
from application import Application

# Quart application instance
app = Quart(__name__)

application = Application(app)


@app.before_serving
async def startup() -> None:
    """
    Code executed before Quart has began serving http requests.

    returns:
        None
    """
    app.service_task = asyncio.ensure_future(application.run())


@app.after_serving
async def shutdown() -> None:
    """
    Code executed after Quart has stopped serving http requests.

    returns:
        None
    """
    application.stop()

if not application.initialise():
    sys.exit()
