"""Custom exceptions for UniBo Toolkit."""

from __future__ import annotations

from typing import List


class UniboToolkitError(Exception):
    """Base exception for all UniBo Toolkit errors."""

    pass


class UnsupportedLanguageError(UniboToolkitError):
    """Raised when an unsupported language is provided.

    The UniBo website only supports Italian (IT) and English (EN) languages.
    Other languages like French (FR) are not available.

    Attributes:
        language: The unsupported language that was provided
        supported_languages: List of supported language codes
    """

    def __init__(self, language: str, supported_languages: List[str] = None):
        """Initialize the exception.

        Args:
            language: The unsupported language code
            supported_languages: Optional list of supported languages
        """
        self.language = language
        self.supported_languages = supported_languages or ["IT", "EN"]

        message = (
            f"Unsupported language: '{language}'. "
            f"Supported languages are: {', '.join(self.supported_languages)}"
        )
        super().__init__(message)


class CourseNotFoundError(UniboToolkitError):
    """Raised when a requested course cannot be found.

    Attributes:
        course_id: The ID of the course that was not found
    """

    def __init__(self, course_id: int):
        """Initialize the exception.

        Args:
            course_id: The ID of the course that was not found
        """
        self.course_id = course_id
        message = f"Course with ID {course_id} not found"
        super().__init__(message)


class InvalidAreaError(UniboToolkitError):
    """Raised when an invalid academic area is provided.

    Attributes:
        area_id: The ID of the invalid area
    """

    def __init__(self, area_id: int):
        """Initialize the exception.

        Args:
            area_id: The ID of the invalid area
        """
        self.area_id = area_id
        message = f"Invalid area ID: {area_id}"
        super().__init__(message)


class ScraperError(UniboToolkitError):
    """Raised when scraping operations fail.

    Attributes:
        url: The URL that failed to be scraped
        reason: The reason for the failure
    """

    def __init__(self, url: str, reason: str = None):
        """Initialize the exception.

        Args:
            url: The URL that failed
            reason: Optional reason for the failure
        """
        self.url = url
        self.reason = reason

        message = f"Failed to scrape {url}"
        if reason:
            message += f": {reason}"

        super().__init__(message)
