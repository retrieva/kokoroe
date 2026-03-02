"""Logging utilities for the auto_red_teaming_prompt package.

This module centralizes logging setup for CLI entry points while keeping
the library code free from global configuration. Library modules should
create loggers via ``logging.getLogger(__name__)`` and avoid calling
``basicConfig``.
"""

import json
import logging
from logging import Handler, Logger
from typing import Any, Optional


class _JsonFormatter(logging.Formatter):
    """Minimal JSON formatter without external dependencies.

    The output includes common fields and preserves ``extra`` keys when
    ``LoggerAdapter`` or ``extra=...`` is used.
    """

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401 - override
        payload: dict[str, Any] = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": self.formatTime(record, self.datefmt),
        }

        # Attach common optional fields when present
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        # Include extra attributes (exclude default LogRecord fields)
        default_fields = set(vars(logging.makeLogRecord({})).keys())
        for key, value in record.__dict__.items():
            if key not in default_fields and key not in payload:
                # Ensure JSON serializable best-effort
                try:
                    json.dumps(value)
                    payload[key] = value
                except Exception:
                    payload[key] = repr(value)

        return json.dumps(payload, ensure_ascii=False)


def setup_logging(
    level: str | int = "INFO",
    json_format: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """Configure root logging for CLI applications.

    - Library code should NOT call this. Only CLI entry points should.
    - Subsequent calls replace existing handlers to avoid duplicate logs.

    Args:
        level: Log level name or int (e.g., "DEBUG", logging.INFO).
        json_format: If True, emit logs as JSON lines.
        log_file: If provided, logs are written to this file; otherwise stderr.

    """
    # Translate level name to int when needed
    numeric_level = logging.getLevelName(level) if isinstance(level, str) else level
    if isinstance(numeric_level, str):  # Unknown name -> default INFO
        numeric_level = logging.INFO

    root = logging.getLogger()
    root.setLevel(numeric_level)

    # Clear existing handlers to prevent duplication when reconfigured
    for h in list(root.handlers):
        root.removeHandler(h)

    formatter: logging.Formatter
    if json_format:
        formatter = _JsonFormatter()
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    if log_file:
        handler: Handler = logging.FileHandler(log_file)
    else:
        handler = logging.StreamHandler()  # stderr by default

    handler.setFormatter(formatter)
    root.addHandler(handler)


def get_logger(name: Optional[str] = None) -> Logger:
    """Return a module or package logger.

    This is a small convenience wrapper; equivalent to logging.getLogger.
    """
    return logging.getLogger(name or __name__)
