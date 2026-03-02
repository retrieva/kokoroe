"""CLI logging helpers to avoid argument duplication across scripts.

Provides common logging arguments and initialization based on parsed args.
"""

from __future__ import annotations

import argparse
from typing import Literal, cast

from .logging import setup_logging

LogLevelName = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]


def add_logging_args(parser: argparse.ArgumentParser) -> None:
    """Add standard logging arguments to an ArgumentParser.

    Args:
        parser: Argument parser to which logging options will be added.

    """
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )
    parser.add_argument(
        "--log-format",
        type=str,
        default="text",
        choices=["text", "json"],
        help="Logging format (default: text)",
    )
    parser.add_argument(
        "--log-file",
        type=str,
        default=None,
        help="Optional log file path (default: stderr)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Shortcut for --log-level=DEBUG",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Shortcut for --log-level=ERROR",
    )


def resolve_log_level(args: argparse.Namespace) -> LogLevelName:
    """Resolve effective log level from parsed args."""
    if getattr(args, "verbose", False):
        return "DEBUG"
    if getattr(args, "quiet", False):
        return "ERROR"
    level = cast(str, getattr(args, "log_level", "INFO"))
    return cast(
        LogLevelName,
        level if level in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"} else "INFO",
    )


def init_logging_from_args(args: argparse.Namespace) -> LogLevelName:
    """Initialize logging based on parsed args and return the effective level."""
    level = resolve_log_level(args)
    setup_logging(level=level, json_format=(args.log_format == "json"), log_file=args.log_file)
    return level
