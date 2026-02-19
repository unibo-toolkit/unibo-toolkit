"""Course data models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, List, Optional, Union

from unibo_toolkit.enums import AccessType, Area, Campus, CourseType, Language
from unibo_toolkit.utils.custom_logger import get_logger

logger = get_logger(__name__)

if TYPE_CHECKING:
    from unibo_toolkit.models.curriculum import Curriculum
    from unibo_toolkit.models.timetable import (
        AcademicYearTimetable,
        CurriculumTimetable,
        Subject,
        TimetableCollection,
    )


@dataclass
class BaseCourse(ABC):
    """Base class for all UniBo courses.

    This abstract class defines the common structure and fields
    for all course types at the University of Bologna.

    Attributes:
        course_id: Unique course identifier
        title: Course title (name does not change based on site language)
        campus: Campus location
        languages: Languages of instruction (IT, EN, FR)
        duration_years: Course duration in years
        access_type: Enrollment access type (open or limited)
        year: Academic year
        url: Full URL to course information page
        area: Academic area/field
        seats: Number of available seats (for limited access)
        course_site_url: URL to detailed course site (corsi.unibo.it)
    """

    course_id: int
    title: str
    campus: Campus
    languages: List[Language]
    duration_years: int
    access_type: AccessType
    year: int
    url: str
    area: Optional[Area] = None
    seats: Optional[int] = None
    course_site_url: Optional[str] = None

    # Timetable and subjects data (lazy-loaded)
    _timetables: Optional["TimetableCollection"] = field(default=None, repr=False)
    _subjects: Optional[Dict[int, List["Subject"]]] = field(default=None, repr=False)
    _available_curricula: Optional[List["Curriculum"]] = field(default=None, repr=False)

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

        except Exception as e:
            logger.warning("Failed to fetch course site URL", url=self.url, error=str(e))
            return None

    async def fetch_available_curricula(self) -> List["Curriculum"]:
        """Fetch and cache the available curricula for this course.

        This method fetches the list of available curricula (study tracks) from
        the timetable page. The list is cached in _available_curricula.

        If the curricula have already been fetched, returns the cached value
        without making an HTTP request.

        Returns:
            List of Curriculum objects. Empty list if no curricula available.

        Raises:
            ValueError: If course_site_url is not set

        Example:
            >>> course = await scraper.get_course_by_id(6796)
            >>> await course.fetch_site_url()
            >>> curricula = await course.fetch_available_curricula()
            >>> for curriculum in curricula:
            ...     print(f"{curriculum.code}: {curriculum.label}")
            B69-000: Advanced Track
            000-000: General Track
        """
        if not self.course_site_url:
            raise ValueError("course_site_url must be set. Call fetch_site_url() first.")

        # Return cached value if already fetched
        if self._available_curricula is not None:
            return self._available_curricula

        # Import here to avoid circular dependency
        from unibo_toolkit.scrapers import CourseScraper

        async with CourseScraper() as scraper:
            curricula = await scraper.get_available_curricula(self.course_site_url)
            self._available_curricula = curricula
            return curricula

    async def fetch_timetable(
        self,
        years: Union[int, List[int], str] = "all",
        curricula: Union["Curriculum", List["Curriculum"], str] = "all",
        extended_range: bool = True,
        fetch_subjects: bool = True,
    ) -> "TimetableCollection":
        """Fetch timetable(s) for this course.

        Args:
            years: Year(s) to fetch:
                   - Single year: 1, 2, 3, etc.
                   - Multiple years: [1, 2, 3]
                   - All years: "all" (default)
            curricula: Curriculum/curricula to fetch:
                      - Single curriculum: Curriculum object
                      - Multiple curricula: [Curriculum, Curriculum, ...]
                      - All curricula: "all" (default)
            extended_range: Use extended date range (±1 year)
            fetch_subjects: Also fetch subjects list (default: True)

        Returns:
            TimetableCollection with requested years and curricula

        Raises:
            ValueError: If course_site_url is not set

        Examples:
            >>> # Fetch all years and all curricula
            >>> await course.fetch_timetable()

            >>> # Fetch specific year for all curricula
            >>> await course.fetch_timetable(years=1)

            >>> # Fetch specific curriculum for all years
            >>> curricula = await course.fetch_available_curricula()
            >>> await course.fetch_timetable(curricula=curricula[0])

            >>> # Fetch specific year and specific curricula
            >>> await course.fetch_timetable(years=[1, 2], curricula=curricula[:2])
        """
        if not self.course_site_url:
            raise ValueError("course_site_url must be set. Call fetch_site_url() first.")

        # Import here to avoid circular dependency
        from unibo_toolkit.scrapers import TimetableScraper

        # Determine which years to fetch
        if years == "all":
            years_to_fetch = list(range(1, self.duration_years + 1))
        elif isinstance(years, int):
            years_to_fetch = [years]
        else:
            years_to_fetch = years

        # Determine which curricula to fetch
        if curricula == "all":
            # Fetch available curricula if not already cached
            curricula_to_fetch = await self.fetch_available_curricula()
        elif isinstance(curricula, list):
            curricula_to_fetch = curricula
        else:
            # Single curriculum object
            curricula_to_fetch = [curricula]

        # Fetch timetables
        async with TimetableScraper() as scraper:
            collection = await scraper.get_timetables(
                course_site_url=self.course_site_url,
                curricula=curricula_to_fetch,
                academic_years=years_to_fetch,
                extended_range=extended_range,
            )

            # Cache in course object
            self._timetables = collection

            # Optionally fetch subjects
            if fetch_subjects:
                await self.fetch_subjects(years=years_to_fetch)

            return collection

    async def fetch_subjects(
        self,
        years: Union[int, List[int], str] = "all",
    ) -> Dict[int, List["Subject"]]:
        """Fetch subjects list for this course.

        Args:
            years: Year(s) to fetch (same format as fetch_timetable)

        Returns:
            Dict mapping year → list of subjects

        Example:
            >>> subjects = await course.fetch_subjects(years=1)
            >>> print(subjects[1])  # List of Year 1 subjects
        """
        if not self.course_site_url:
            raise ValueError("course_site_url must be set. Call fetch_site_url() first.")

        # Import here to avoid circular dependency
        from unibo_toolkit.scrapers import SubjectsScraper

        # Determine years
        if years == "all":
            years_to_fetch = list(range(1, self.duration_years + 1))
        elif isinstance(years, int):
            years_to_fetch = [years]
        else:
            years_to_fetch = years

        # Fetch subjects
        async with SubjectsScraper() as scraper:
            subjects_dict = await scraper.get_subjects(
                course_site_url=self.course_site_url,
                academic_years=years_to_fetch,
            )

            # Cache in course object
            if self._subjects is None:
                self._subjects = {}
            self._subjects.update(subjects_dict)

            return subjects_dict

    # === GETTER METHODS ===

    def get_available_curricula(self) -> Optional[List["Curriculum"]]:
        """Get cached available curricula.

        Returns None if not fetched yet.

        Returns:
            List of available curricula or None
        """
        return self._available_curricula

    def get_timetable(self, year: int) -> Optional["AcademicYearTimetable"]:
        """Get cached timetable for specific year.

        Returns None if not fetched yet.

        Args:
            year: Academic year (1, 2, 3, etc.)

        Returns:
            AcademicYearTimetable for the specified year or None

        Note:
            This now returns AcademicYearTimetable instead of Timetable.
            Use get_curriculum_timetable() to get a specific curriculum's timetable.
        """
        if self._timetables is None:
            return None
        return self._timetables.get_year(year)

    def get_curriculum_timetable(
        self, year: int, curriculum_code: str
    ) -> Optional["CurriculumTimetable"]:
        """Get cached timetable for a specific curriculum in a specific year.

        Args:
            year: Academic year (1, 2, 3, etc.)
            curriculum_code: Curriculum code (e.g., "B69-000")

        Returns:
            CurriculumTimetable or None
        """
        if self._timetables is None:
            return None
        return self._timetables.get_curriculum(year, curriculum_code)

    def get_all_timetables(self) -> Optional["TimetableCollection"]:
        """Get all cached timetables.

        Returns None if not fetched yet.

        Returns:
            TimetableCollection or None
        """
        return self._timetables

    def get_subjects(self, year: int) -> Optional[List["Subject"]]:
        """Get cached subjects for specific year.

        Returns None if not fetched yet.

        Args:
            year: Academic year (1, 2, 3, etc.)

        Returns:
            List of subjects for the specified year or None
        """
        if self._subjects is None:
            return None
        return self._subjects.get(year)

    def get_all_subjects(self) -> Optional[Dict[int, List["Subject"]]]:
        """Get all cached subjects.

        Returns None if not fetched yet.

        Returns:
            Dictionary mapping year → subjects or None
        """
        return self._subjects

    # === PROPERTIES ===

    @property
    def has_timetables(self) -> bool:
        """Check if any timetables have been fetched.

        Returns:
            True if timetables are cached, False otherwise
        """
        return self._timetables is not None and len(self._timetables.years) > 0

    @property
    def has_subjects(self) -> bool:
        """Check if any subjects have been fetched.

        Returns:
            True if subjects are cached, False otherwise
        """
        return self._subjects is not None and len(self._subjects) > 0


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
