"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
import asyncio
import os
import random
from quart import g, Quart, request
from application import Application
import asyncpg


# Quart application instance
app = Quart(__name__)

SERVICE_APP: Application = Application(app)


class DatabaseConfig:
    """
    Configuration container for database connection settings.

    The values are loaded from environment variables and provide
    fallbacks if the variables are not set. These settings are
    typically used for establishing a connection to the accounts
    database.

    Attributes:
        DB_USER (str): Database username. Defaults to "__INVALID__" if
            the environment variable `WEAVEFEED_ACCOUNTS_DB_USER`
            is not set.
        DB_PASSWORD (str): Database password. Defaults to "__INVALID__" if
            the environment variable `WEAVEFEED_ACCOUNTS_DB_PASSWORD`
            is not set.
        DB_NAME (str): Database name. Defaults to "__INVALID__" if
            the environment variable `WEAVEFEED_ACCOUNTS_DB_NAME`
            is not set.
        DB_HOST (str): Database host address. Defaults to "127.0.0.1" if
            the environment variable `WEAVEFEED_ACCOUNTS_DB_HOST`
            is not set.
        DB_PORT (int): Database port number. Defaults to 5432 if
            the environment variable `WEAVEFEED_ACCOUNTS_DB_PORT`
            is not set.
    """
    # pylint: disable=too-few-public-methods
    DB_USER = os.getenv("WEAVEFEED_ACCOUNTS_DB_USER", "__INVALID__")
    DB_PASSWORD = os.getenv("WEAVEFEED_ACCOUNTS_DB_PASSWORD", "__INVALID__")
    DB_NAME = os.getenv("WEAVEFEED_ACCOUNTS_DB_NAME", "__INVALID__")
    DB_HOST = os.getenv("WEAVEFEED_ACCOUNTS_DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("WEAVEFEED_ACCOUNTS_DB_PORT", "5432"))


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

    # clean, just call helper
    app.db_pool = await create_db_pool(DatabaseConfig)

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

    await app.db_pool.close()


@app.before_request
async def acquire_connection():
    """
    Acquire a database connection from the pool before handling a request.

    This function is registered as a ``before_request`` hook in the Quart
    application. For each incoming request, it attempts to acquire a database
    connection from the application's connection pool and stores it in the
    request context (``g.db``).

    If the request handler's view function is marked with the ``_no_db``
    attribute, the connection acquisition step is skipped. This allows
    certain endpoints to run without requiring a database.

    Returns:
        dict | None: If acquiring a connection times out, returns a JSON error
            response with a 503 status code. Otherwise, returns ``None`` to
            continue request processing.
    """
    view_func = app.view_functions.get(request.endpoint)
    if getattr(view_func, "_no_db", False):
        return  # skip DB acquire

    try:
        g.db = await app.db_pool.acquire(timeout=2.0)

    except asyncio.TimeoutError:
        return {"error": "Service unavailable"}, 503


@app.after_request
async def release_connection(response):
    """
    Release the database connection back to the connection pool.

    This function is registered as an ``after_request`` hook in the Quart
    application. After each request, it checks for a database connection
    stored in the ``g`` context (``g.db``). If a connection exists, it is
    released back to the application's connection pool.

    Args:
        response (quart.wrappers.Response): The response object generated
            by the request handler.

    Returns:
        quart.wrappers.Response: The same response object, unchanged.
    """
    db = getattr(g, "db", None)
    if db is not None:
        await app.db_pool.release(db)
    return response


async def create_db_pool(config,
                         retries: int=5,
                         base_delay: float=1.0
                         ) -> asyncpg.pool.Pool:
    """
    Create and return an asyncpg connection pool with retries and error
    handling.

    Attempts to create a database connection pool using the provided config.
    Supports exponential backoff with jitter for retry-able errors. If the
    pool cannot be created after the maximum number of retries, the application
    will cancel background tasks and exit with a fatal error.

    Args:
        config (DatabaseConfig): A configuration object containing database
            connection parameters (user, password, database, host, port).
        retries (int, optional): Maximum number of retry attempts before
            giving up. Defaults to 5.
        base_delay (float, optional): Base delay (in seconds) for exponential
            backoff. Defaults to 1.0.

    Returns:
        asyncpg.pool.Pool: A connection pool instance if successfully created.

    Raises:
        SystemExit: If all retries are exhausted and a pool cannot be created.
    """
    for attempt in range(1, retries + 1):
        try:
            pool = await asyncpg.create_pool(
                user=config.DB_USER,
                password=config.DB_PASSWORD,
                database=config.DB_NAME,
                host=config.DB_HOST,
                port=config.DB_PORT,
                min_size=1,
                max_size=10,
                timeout=5.0
            )

            print(f"[INFO] Connected to database {config.DB_NAME} "
                  f"on {config.DB_HOST}:{config.DB_PORT} (attempt {attempt})",
                  flush=True)

            return pool

        except asyncpg.InvalidPasswordError:
            print("[FATAL] Database authentication failed (check user/"
                  "password).", flush=True)
            break

        except asyncpg.InvalidCatalogNameError:
            print(f"[FATAL] Database '{config.DB_NAME}' does not exist.",
                  flush=True)
            break

        except asyncpg.CannotConnectNowError:
            print("[FATAL] Database is starting up or cannot accept connections "
                  "right now.", flush=True)

        except asyncio.TimeoutError:
            print("[FATAL] Database connection timed out.", flush=True)

        except OSError as ex:
            print(f"[FATAL] Database network/connection error: {ex}",
                  flush=True)

        except asyncpg.PostgresError as ex:
            print(f"[FATAL] Database general Postgres error: {ex}", flush=True)

        # Retry-able errors
        delay = base_delay * (2 ** (attempt - 1))  # exponential backoff
        jitter = random.uniform(0, 0.3 * delay)   # add jitter
        wait_time = delay + jitter

        if attempt < retries:
            print(f"[INFO] Retrying database connection in "
                  f"{wait_time:.1f}s...", flush=True)
            await asyncio.sleep(wait_time)
            continue

        print("[FATAL] All database retries exhausted. Could not connect!",
              flush=True)
        break

    if app is not None:
        await cancel_background_tasks()

    os._exit(1)  # exit on failure
