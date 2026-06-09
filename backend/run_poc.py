#!/usr/bin/env python3
"""
Compatibility wrapper for the renamed backtest entrypoint.

Prefer running `python run_backtest.py`.
"""

import sys

from exceptions import DataGapError
from run_backtest import ensure_data, logger, main

__all__ = ["ensure_data", "main"]


if __name__ == "__main__":
    try:
        main()
    except DataGapError as error:
        logger.error("%s", error)
        sys.exit(1)
