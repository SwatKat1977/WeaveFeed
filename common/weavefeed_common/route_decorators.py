"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""


def route_not_using_db(func):
    """
    Decorator to mark a route handler as not requiring database access.

    When applied, this sets an internal attribute `_not_using_db = True`
    on the function, which can later be checked by middleware or routing
    logic to skip database setup/teardown for this route.

    Args:
        func (Callable): The route handler function to decorate.

    Returns:
        Callable: The same function with the `_not_using_db` attribute set.
    """
    func._not_using_db = True
    return func
