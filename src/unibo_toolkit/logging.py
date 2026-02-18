"""Logging configuration for unibo_toolkit library."""

import logging
from typing import Any, Optional

from unibo_toolkit.utils.custom_logger import CustomLogger

_LOGGER_NAME = "UNIBO_TOOLKIT"
_logger_configured = False


def setup_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    handler: Optional[logging.Handler] = None,
) -> None:
    """Configure logging for unibo_toolkit library.

    By default, the library uses a NullHandler (no output). Call this function
    to enable logging to see debug information, warnings, and errors.

    Args:
        level: Log level - one of: DEBUG, INFO, WARNING, ERROR, CRITICAL
        format_string: Custom log format string. If None, uses structured format
        handler: Custom logging handler. If None, uses StreamHandler (console output)

    Example:
        Enable INFO level logging to console:
        >>> import unibo_toolkit
        >>> unibo_toolkit.setup_logging(level=logging.INFO)

        Enable DEBUG level with custom format:
        >>> unibo_toolkit.setup_logging(
        ...     level=logging.DEBUG,
        ...     format_string='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ... )

        Use custom handler (e.g., file logging):
        >>> import logging
        >>> file_handler = logging.FileHandler('unibo_toolkit.log')
        >>> unibo_toolkit.setup_logging(level=logging.DEBUG, handler=file_handler)
    """
    global _logger_configured

    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(level)

    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()

    # Create handler if not provided
    if handler is None:
        handler = logging.StreamHandler()

    # Set format - default to structured format for CustomLogger
    if format_string is None:
        format_string = "[%(levelname)s] %(name)s - %(message)s"

    formatter = logging.Formatter(format_string)
    handler.setFormatter(formatter)

    logger.addHandler(handler)
    _logger_configured = True


def get_logger(name: str, **items: Any) -> CustomLogger:
    """Get custom logger instance for a module.

    This function returns a CustomLogger that formats messages as
    structured logs with key-value pairs.

    Args:
        name: Module name (usually __name__)
        **items: Default items to include in all log messages

    Returns:
        CustomLogger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Course fetched", course_id=6796)
        # Output: msg="Course fetched" course_id="6796"
    """
    return CustomLogger(f"{_LOGGER_NAME}.{name}", **items)


# Initialize default logger with NullHandler (no output by default)
_default_logger = logging.getLogger(_LOGGER_NAME)
_default_logger.addHandler(logging.NullHandler())
_default_logger.setLevel(logging.WARNING)
