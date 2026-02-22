"""Web scrapers for UniBo data."""

from unibo_toolkit.scrapers.course import CourseScraper
from unibo_toolkit.scrapers.subjects import SubjectsScraper
from unibo_toolkit.scrapers.timetable import TimetableScraper

__all__ = ["CourseScraper", "SubjectsScraper", "TimetableScraper"]
