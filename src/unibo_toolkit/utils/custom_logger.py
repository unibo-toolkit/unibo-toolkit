"""Custom structured logger for UniBo toolkit."""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class LogItem:
    """A single log item (key-value pair)."""

    name: str
    value: str

    def __str__(self):
        return f'{self.name}="{self.value}"'


@dataclass
class MultiItem:
    """Collection of log items."""

    items: Dict[str, str]

    @property
    def all(self) -> List[LogItem]:
        return [LogItem(name, value) for name, value in self.items.items()]


class CustomLogger:
    """Structured logger with key-value pair support.

    This logger formats messages as structured logs without emojis,
    making them suitable for production logging systems.

    Example:
        >>> logger = CustomLogger("unibo_toolkit.scrapers")
        >>> logger.info("Course fetched", course_id=6796, title="AI")
        # Output: msg="Course fetched" course_id="6796" title="AI"
    """

    def __init__(self, name: str, **items: Any):
        """Initialize custom logger.

        Args:
            name: Logger name (typically module name)
            **items: Default items to include in all log messages
        """
        self.name = name
        self.logger = logging.getLogger(name)
        self.items: List[LogItem] = []
        if items:
            self.items = self.__transform_items(items).all

    def __send_message(self, message: str, level: int, items: List[LogItem]) -> None:
        """Send formatted log message.

        Args:
            message: Log message
            level: Log level (INFO, DEBUG, etc.)
            items: Additional key-value items
        """
        log = 'msg="' + message + '"' + (" " + " ".join(map(str, items)) if items else "")
        self.logger.log(level, log)

    @staticmethod
    def __transform_items(items: Dict[str, Any]) -> MultiItem:
        """Transform items dict to MultiItem.

        Args:
            items: Dictionary of items

        Returns:
            MultiItem instance
        """
        return MultiItem({key: str(value) for key, value in items.items()})

    def info(self, message: str, **items: Any) -> None:
        """Log info message.

        Args:
            message: Log message
            **items: Additional key-value pairs
        """
        self.__send_message(message, logging.INFO, self.items + self.__transform_items(items).all)

    def debug(self, message: str, **items: Any) -> None:
        """Log debug message.

        Args:
            message: Log message
            **items: Additional key-value pairs
        """
        self.__send_message(message, logging.DEBUG, self.items + self.__transform_items(items).all)

    def warning(self, message: str, **items: Any) -> None:
        """Log warning message.

        Args:
            message: Log message
            **items: Additional key-value pairs
        """
        self.__send_message(
            message, logging.WARNING, self.items + self.__transform_items(items).all
        )

    def error(self, message: str, **items: Any) -> None:
        """Log error message.

        Args:
            message: Log message
            **items: Additional key-value pairs
        """
        self.__send_message(message, logging.ERROR, self.items + self.__transform_items(items).all)

    def critical(self, message: str, **items: Any) -> None:
        """Log critical message.

        Args:
            message: Log message
            **items: Additional key-value pairs
        """
        self.__send_message(
            message, logging.CRITICAL, self.items + self.__transform_items(items).all
        )

    def with_items(self, **items: Any) -> None:
        """Add default items to this logger.

        Args:
            **items: Items to add as defaults
        """
        self.items.extend(self.__transform_items(items).all)

    def clear(self) -> None:
        """Clear all default items."""
        self.items.clear()


def get_logger(name: str, **items: Any) -> CustomLogger:
    """Get a custom logger instance.

    Args:
        name: Logger name (typically __name__)
        **items: Default items for all log messages

    Returns:
        CustomLogger instance

    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Operation completed", duration=1.23)
    """
    return CustomLogger(name, **items)
