"""UniBo Toolkit - Python library for University of Bologna data scraping."""

from unibo_toolkit.clients import HTTPClient
from unibo_toolkit.enums import AccessType, Area, Campus, CourseType, Language
from unibo_toolkit.exceptions import (
    CourseNotFoundError,
    InvalidAreaError,
    ScraperError,
    UniboToolkitError,
    UnsupportedLanguageError,
)
from unibo_toolkit.logging import setup_logging
from unibo_toolkit.models import AreaInfo, Bachelor, BaseCourse, Master, SingleCycleMaster
from unibo_toolkit.scrapers import CourseScraper

__version__ = "0.2.0"

__all__ = [
    "__version__",
    "HTTPClient",
    "AccessType",
    "Area",
    "Campus",
    "CourseType",
    "Language",
    "AreaInfo",
    "Bachelor",
    "BaseCourse",
    "Master",
    "SingleCycleMaster",
    "CourseScraper",
    "setup_logging",
    "UniboToolkitError",
    "UnsupportedLanguageError",
    "CourseNotFoundError",
    "InvalidAreaError",
    "ScraperError",
]