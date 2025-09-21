"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
import asyncio
import os
from quart import g, Quart, request
from application import Application
import asyncpg


# Quart application instance
app = Quart(__name__)

SERVICE_APP: Application = Application(app)


class DatabaseConfig:
    DB_USER = os.getenv("WEAVEFEED_ACCOUNTS_DB_USER", "__INVALID__")
    DB_PASSWORD = os.getenv("WEAVEFEED_ACCOUNTS_DB_PASSWORD", "__INVALID__")
    DB_NAME = os.getenv("WEAVEFEED_ACCOUNTS_DB_NAME", "__INVALID__")
    DB_HOST = os.getenv("WEAVEFEED_ACCOUNTS_DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("WEAVEFEED_ACCOUNTS_DB_PORT", 5432))


async def cancel_background_tasks():
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

    # clean, just call helper
    app.db_pool = await create_db_pool(DatabaseConfig)


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

    """
    task = getattr(app, "background_task", None)
    if task:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    """

    await app.db_pool.close()


@app.before_request
async def acquire_connection():
    view_func = app.view_functions.get(request.endpoint)
    if getattr(view_func, "_no_db", False):
        return  # skip DB acquire

    try:
        g.db = await app.db_pool.acquire(timeout=2.0)

    except asyncio.TimeoutError:
        return {"error": "Service unavailable"}, 503


@app.after_request
async def release_connection(response):
    db = getattr(g, "db", None)
    if db is not None:
        await app.db_pool.release(db)
    return response


async def create_db_pool(config) -> asyncpg.pool.Pool:
    """
    Create and return an asyncpg pool with proper error handling.
    """
    try:
        return await asyncpg.create_pool(
            user=config.DB_USER,
            password=config.DB_PASSWORD,
            database=config.DB_NAME,
            host=config.DB_HOST,
            port=config.DB_PORT,
            min_size=1,
            max_size=10,
            timeout=5.0
        )

    except asyncpg.InvalidPasswordError:
        print("[FATAL] Database authentication failed (check user/password).")

    except asyncpg.InvalidCatalogNameError:
        print(f"[FATAL] Database '{config.DB_NAME}' does not exist.")

    except asyncpg.CannotConnectNowError:
        print("[FATAL] Database is starting up or cannot accept connections "
              "right now.")

    except asyncio.TimeoutError:
        print("[FATAL] Database connection timed out.")

    except OSError as ex:
        print(f"[FATAL] Network/connection error: {ex}")

    except asyncpg.PostgresError as ex:
        print(f"[FATAL] General Postgres error: {ex}")

    if app is not None:
        await cancel_background_tasks()

    os._exit(1)  # exit on failure
