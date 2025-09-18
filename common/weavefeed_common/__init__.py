"""
Copyright (C) 2025  WeaveFeed Development Team
SPDX-License-Identifier: AGPL-3.0-or-later

This file is part of WeaveFeed. See the LICENSE file in the project
root for full license details.
"""

# Semantic version components
MAJOR = 0
MINOR = 0
PATCH = 0

# e.g. "alpha", "beta", "rc1", or None
PRE_RELEASE = "POC #1"

# Version tuple for comparisons
VERSION = (MAJOR, MINOR, PATCH, PRE_RELEASE)

# Construct the string representation
__version__ = f"V{MAJOR}.{MINOR}.{PATCH}"

if PRE_RELEASE:
    __version__ += f"-{PRE_RELEASE}"
