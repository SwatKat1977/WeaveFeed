"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""
import abc
import logging


class BaseDataAccessLayer(abc.ABC):

    def __init__(self, db, logger: logging.Logger):
        self._db = db
        self._logger: logging.Logger = logger.getChild(__name__)
