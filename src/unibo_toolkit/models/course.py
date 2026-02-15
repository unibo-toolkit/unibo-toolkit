"""Course data models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from unibo_toolkit.enums import AccessType, Area, Campus, CourseType, Language


@dataclass
class BaseCourse(ABC):
    """Base class for all UniBo courses.

    This abstract class defines the common structure and fields
    for all course types at the University of Bologna.

    Attributes:
        course_id: Unique course identifier
        title: Course title (name does not change based on site language)
        course_class: MIUR classification code (e.g., L-13, LM-6)
        campus: Campus location
        languages: Languages of instruction (IT, EN, FR)
        duration_years: Course duration in years
        access_type: Enrollment access type (open or limited)
        year: Academic year
        url: Full URL to course information page
        area: Academic area/field
        seats: Number of available seats (for limited access)
        director: Course director name
        course_site_url: URL to detailed course site (corsi.unibo.it)
    """

    course_id: int
    title: str
    course_class: str
    campus: Campus
    languages: List[Language]
    duration_years: int
    access_type: AccessType
    year: int
    url: str
    area: Optional[Area] = None
    seats: Optional[int] = None
    director: Optional[str] = None
    course_site_url: Optional[str] = None

    @abstractmethod
    def get_course_type(self) -> CourseType:
        """Returns the type of the course.

        Returns:
            CourseType: The specific type of this course
        """
        pass

    def has_site_url(self) -> bool:
        """Check if course site URL has been fetched.

        Returns:
            True if course_site_url is available, False otherwise
        """
        return self.course_site_url is not None

    async def fetch_site_url(self) -> Optional[str]:
        """Fetch and cache the course site URL.

        This method fetches the course page and extracts the detailed course site URL
        (corsi.unibo.it). The URL is cached in course_site_url.

        If the URL has already been fetched, returns the cached value without making
        an HTTP request.

        **Important Note:**
        The language of the returned URL depends on the course's teaching language,
        NOT the language used to fetch the course data. Italian-taught courses will
        have Italian URLs (/magistrale/, /laurea/), while English-taught courses will
        have English URLs (/2cycle/, /1cycle/). This is the actual structure of the
        UniBo website.

        Returns:
            The course site URL if found, None otherwise

        Example:
            >>> course = await scraper.get_course_by_id(6796)
            >>> site_url = await course.fetch_site_url()
            >>> print(site_url)  # https://corsi.unibo.it/magistrale/aegi
            >>>
            >>> # Second call uses cached value (no HTTP request)
            >>> site_url = await course.fetch_site_url()
        """
        # Return cached value if already fetched
        if self.course_site_url:
            return self.course_site_url

        # Import here to avoid circular dependency
        from bs4 import BeautifulSoup

        from unibo_toolkit.clients import HTTPClient

        try:
            async with HTTPClient() as client:
                html = await client.get(self.url)
                soup = BeautifulSoup(html, "html.parser")

                # Find "Sito web del corso" link
                corso_link = soup.find("a", href=lambda x: x and "corsi.unibo.it" in x)

                if corso_link:
                    self.course_site_url = corso_link["href"]
                    return self.course_site_url

            return None

        except Exception:
            # Silently fail - URL just won't be available
            return None


@dataclass
class Bachelor(BaseCourse):
    """Bachelor's degree course (Laurea Triennale).

    Represents a 3-year undergraduate degree program.
    """

    def get_course_type(self) -> CourseType:
        return CourseType.BACHELOR


@dataclass
class Master(BaseCourse):
    """Master's degree course (Laurea Magistrale).

    Represents a 2-year graduate degree program that requires
    a bachelor's degree for admission.
    """

    def get_course_type(self) -> CourseType:
        return CourseType.MASTER


@dataclass
class SingleCycleMaster(BaseCourse):
    """Single-cycle master's degree (Laurea Magistrale a Ciclo Unico).

    Represents a 5-6 year integrated degree program (e.g., Medicine, Law)
    that does not require a separate bachelor's degree.
    """

    def get_course_type(self) -> CourseType:
        return CourseType.SINGLE_CYCLE_MASTER
