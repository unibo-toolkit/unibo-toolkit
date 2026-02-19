"""Course scraper for UniBo website."""

import json
from typing import TYPE_CHECKING, List, Optional

from bs4 import BeautifulSoup

from unibo_toolkit.clients import HTTPClient
from unibo_toolkit.enums import Area, Campus, CourseType, Language
from unibo_toolkit.exceptions import UnsupportedLanguageError
from unibo_toolkit.logging import get_logger
from unibo_toolkit.models import AreaInfo, BaseCourse
from unibo_toolkit.utils import CourseParser

if TYPE_CHECKING:
    from unibo_toolkit.models import Curriculum

logger = get_logger(__name__)


class CourseScraper:
    """Web scraper for retrieving University of Bologna course data.

    This class handles fetching and parsing course information from
    the UniBo website, including areas, course listings, and detailed course pages.

    Supports hierarchical data retrieval:
    1. Get academic areas (categories)
    2. Get courses within specific areas
    3. Get individual course details
    """

    BASE_URL = "https://www.unibo.it"
    CATEGORY_PATHS = {
        "it": {
            "bachelor": "studiare/lauree-e-lauree-magistrali-a-ciclo-unico",
            "master": "studiare/lauree-magistrali",
            "single_cycle": "studiare/lauree-e-lauree-magistrali-a-ciclo-unico",
        },
        "en": {
            "bachelor": "study/first-and-single-cycle-degree",
            "master": "study/second-cycle-degree",
            "single_cycle": "study/first-and-single-cycle-degree",
        },
    }
    DEFAULT_AREA_DELAY = 0.0
    DEFAULT_COURSE_DELAY = 0.0
    SUPPORTED_LANGUAGES = [Language.EN, Language.IT]

    def __init__(
        self,
        http_client: Optional[HTTPClient] = None,
        area_delay: float = DEFAULT_AREA_DELAY,
        course_delay: float = DEFAULT_COURSE_DELAY,
    ):
        """Initialize the course scraper.

        Args:
            http_client: Optional HTTP client. If None, scraper creates and manages its own client
            area_delay: Delay in seconds between area fetch requests (default: 0.1s)
            course_delay: Delay in seconds between course list requests (default: 0.1s)

        Example:
            # Simple usage - scraper manages HTTP client automatically
            >>> async with CourseScraper() as scraper:
            ...     courses = await scraper.get_all_courses()

            # Advanced usage - bring your own HTTP client
            >>> async with HTTPClient() as client:
            ...     scraper = CourseScraper(client)
            ...     courses = await scraper.get_all_courses()
        """
        self._external_client = http_client
        self._internal_client: Optional[HTTPClient] = None
        self.http_client: HTTPClient = http_client  # Will be set in __aenter__ if None
        self.parser = CourseParser()
        self.area_delay = area_delay
        self.course_delay = course_delay
        self._current_year: Optional[int] = None
        logger.debug(
            "CourseScraper initialized",
            area_delay_seconds=area_delay,
            course_delay_seconds=course_delay,
        )

    async def __aenter__(self):
        """Enter async context manager."""
        if self._external_client is None:
            # Create and manage our own HTTP client
            self._internal_client = HTTPClient()
            await self._internal_client.__aenter__()
            self.http_client = self._internal_client
            logger.debug("Created internal HTTP client")
        else:
            # Use externally provided client
            self.http_client = self._external_client
            logger.debug("Using external HTTP client")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        if self._internal_client is not None:
            # Clean up our internal client
            await self._internal_client.__aexit__(exc_type, exc_val, exc_tb)
            logger.debug("Closed internal HTTP client")
        return False

    def _validate_language(self, language: Language) -> None:
        """Validate that the provided language is supported.

        Args:
            language: Language to validate

        Raises:
            UnsupportedLanguageError: If the language is not supported by UniBo website
        """
        if language not in self.SUPPORTED_LANGUAGES:
            raise UnsupportedLanguageError(
                language.value, [lang.value for lang in self.SUPPORTED_LANGUAGES]
            )

    async def _get_current_year(self) -> int:
        """Detect current academic year from UniBo website.

        Returns:
            Current academic year as integer

        Raises:
            ValueError: If year cannot be detected from website
        """
        if self._current_year is not None:
            return self._current_year

        logger.debug("Detecting current academic year from website")

        try:
            html = await self.http_client.get(f"{self.BASE_URL}/it/studiare/lauree-magistrali")
            soup = BeautifulSoup(html, "html.parser")
            catalog = soup.find("div", id="catalog-content")

            if catalog and catalog.get("data-year"):
                self._current_year = int(catalog["data-year"])
                logger.info("Academic year detected", year=self._current_year)
                return self._current_year
            else:
                logger.warning(
                    "Could not find data-year attribute, using fallback", fallback_year=2026
                )
                self._current_year = 2026  # TODO review
                return self._current_year

        except Exception as e:
            logger.error(
                "Failed to detect current year, using fallback", error=str(e), fallback_year=2026
            )
            self._current_year = 2026
            return self._current_year

    async def get_areas(
        self,
        course_type: Optional[CourseType] = None,
        language: Language = Language.IT,
    ) -> List[AreaInfo]:
        """Fetch academic areas with course counts.

        Args:
            course_type: Optional filter for course type (Master, Bachelor, or SingleCycleMaster)
            language: Language for the interface (IT or EN) - affects text content

        Returns:
            List of AreaInfo objects containing area and course count

        Raises:
            UnsupportedLanguageError: If language is not IT or EN
        """
        self._validate_language(language)
        logger.info(
            "Fetching academic areas",
            course_type=course_type.value if course_type else "all",
            language=language.value,
        )
        areas: List[AreaInfo] = []

        if course_type == CourseType.MASTER:
            paths_to_fetch = [("master", CourseType.MASTER)]
        elif course_type == CourseType.BACHELOR:
            paths_to_fetch = [("bachelor", CourseType.BACHELOR)]
        elif course_type == CourseType.SINGLE_CYCLE_MASTER:
            paths_to_fetch = [("single_cycle", CourseType.SINGLE_CYCLE_MASTER)]
        else:
            # Fetch all course types
            paths_to_fetch = [
                ("master", CourseType.MASTER),
                ("bachelor", CourseType.BACHELOR),
                ("single_cycle", CourseType.SINGLE_CYCLE_MASTER),
            ]

        for path_key, ctype in paths_to_fetch:
            category_path = self.CATEGORY_PATHS[language.value][path_key]
            url = f"{self.BASE_URL}/{language.value}/{category_path}"

            try:
                logger.debug("Fetching areas from URL", url=url, course_type=ctype.value)
                html = await self.http_client.get(url)
                page_areas = self.parser.parse_areas(html, ctype)
                areas.extend(page_areas)
                logger.debug("Areas found", count=len(page_areas), course_type=ctype.value)

            except Exception as e:
                logger.warning("Failed to fetch areas from URL", url=url, error=str(e))
                continue

        logger.info("Areas fetched", total_count=len(areas))
        return areas

    async def get_courses_by_area(
        self,
        area: Area,
        course_type: Optional[CourseType] = None,
        language: Language = Language.IT,
        with_site_urls: bool = True,
    ) -> List[BaseCourse]:
        """Fetch all courses in a specific academic area.

        Args:
            area: Academic area to fetch courses from
            course_type: Optional filter for course type
            language: Language for the interface (IT or EN) - affects course titles and descriptions
            with_site_urls: If True, fetch course site URLs (requires additional HTTP requests)

        Returns:
            List of course objects from the specified area

        Raises:
            UnsupportedLanguageError: If language is not IT or EN

        Note:
            The language parameter affects the text content returned by the server.
            For example:
            - Language.IT: course.title = "Tecnologie alimentari"
            - Language.EN: course.title = "Food Technology"

            However, the course_site_url language depends on the course's teaching language,
            not the language parameter. Italian-taught courses have Italian URLs
            (/magistrale/, /laurea/), while English-taught courses have English URLs
            (/2cycle/, /1cycle/). This reflects the actual structure of the UniBo website.
        """
        self._validate_language(language)
        year = await self._get_current_year()

        logger.info("Fetching courses from area", area=area.title_it, language=language.value)

        if course_type == CourseType.MASTER:
            categories_to_fetch = ["master"]
        elif course_type == CourseType.BACHELOR:
            categories_to_fetch = ["bachelor"]
        elif course_type == CourseType.SINGLE_CYCLE_MASTER:
            categories_to_fetch = ["single_cycle"]
        else:
            categories_to_fetch = ["master", "bachelor", "single_cycle"]

        all_courses: List[BaseCourse] = []

        for cat_key in categories_to_fetch:
            category_path = self.CATEGORY_PATHS[language.value][cat_key]
            url = f"{self.BASE_URL}/{language.value}/{category_path}/elenco"
            params = {"schede": str(area.area_id)}

            try:
                logger.debug(
                    "Fetching courses from URL", url=url, area_id=area.area_id, category=cat_key
                )
                html = await self.http_client.get(url, params=params)
                courses = self.parser.parse_course_list(html, year, category_path, area)
                all_courses.extend(courses)
                logger.debug("Courses found", count=len(courses), category=cat_key)

            except Exception as e:
                logger.warning("Failed to fetch courses from URL", url=url, error=str(e))
                continue

        if course_type:
            all_courses = [c for c in all_courses if c.get_course_type() == course_type]

        # Fetch course site URLs if requested
        if with_site_urls:
            logger.debug("Fetching course site URLs", courses_count=len(all_courses))
            for course in all_courses:
                await course.fetch_site_url()

        logger.info("Courses fetched from area", area=area.title_it, total_count=len(all_courses))
        return all_courses

    async def get_all_courses(
        self,
        course_type: Optional[CourseType] = None,
        area: Optional[Area] = None,
        language: Language = Language.IT,
        with_site_urls: bool = False,
    ) -> List[BaseCourse]:
        """Fetch all courses from University of Bologna.

        This method uses hierarchical fetching:
        1. Gets all areas
        2. Fetches courses from each area
        3. Aggregates results

        Args:
            course_type: Optional filter for course type
            area: Optional filter for specific academic area
            language: Language for the interface (IT or EN) - affects course titles and descriptions
            with_site_urls: If True, fetch course site URLs (requires additional HTTP requests)

        Returns:
            List of course objects matching the criteria

        Raises:
            UnsupportedLanguageError: If language is not IT or EN

        Note:
            The course_site_url language depends on the course's teaching language,
            not the language parameter. Italian-taught courses have Italian URLs,
            while English-taught courses have English URLs.
        """
        self._validate_language(language)
        logger.info(
            "Fetching all courses",
            course_type=course_type.name if course_type else "all",
            area=area.name if area else "all",
            language=language.value,
        )

        if area:
            return await self.get_courses_by_area(area, course_type, language, with_site_urls)

        areas = await self.get_areas(course_type, language)
        all_courses: List[BaseCourse] = []
        seen_course_ids = set()

        for area_info in areas:
            if course_type and area_info.course_type != course_type:
                continue

            try:
                # Use the area's course type to avoid fetching duplicates
                # If user specified course_type, use that; otherwise use area's type
                effective_type = course_type if course_type else area_info.course_type

                courses = await self.get_courses_by_area(
                    area_info.area, effective_type, language, with_site_urls
                )

                # Deduplicate by course_id (some courses belong to multiple areas)
                for course in courses:
                    if course.course_id not in seen_course_ids:
                        seen_course_ids.add(course.course_id)
                        all_courses.append(course)

            except Exception as e:
                logger.warning(
                    "Failed to fetch courses from area", area=area_info.area.title_it, error=str(e)
                )
                continue

        logger.info(
            "All courses fetched", total_count=len(all_courses), note="deduplicated by course ID"
        )
        return all_courses

    async def get_course_by_id(
        self,
        course_id: int,
        language: Language = Language.IT,
        with_site_url: bool = False,
    ) -> Optional[BaseCourse]:
        """Fetch detailed information for a specific course.

        Args:
            course_id: Unique identifier of the course
            language: Language for the interface (IT or EN) - affects course title and description
            with_site_url: If True, also fetch the course site URL

        Returns:
            Course object if found, None otherwise

        Raises:
            UnsupportedLanguageError: If language is not IT or EN
        """
        self._validate_language(language)
        logger.info("Searching for course by ID", course_id=course_id)
        all_courses = await self.get_all_courses(language=language)

        for course in all_courses:
            if course.course_id == course_id:
                logger.info("Course found", course_id=course_id, title=course.title)

                # Populate site URL if requested
                if with_site_url:
                    await course.fetch_site_url()

                return course

        logger.warning("Course not found", course_id=course_id)
        return None

    async def search_courses(
        self,
        query: str,
        campus: Optional[Campus] = None,
        course_type: Optional[CourseType] = None,
        area: Optional[Area] = None,
        language: Language = Language.IT,
        with_site_urls: bool = True,
    ) -> List[BaseCourse]:
        """Search for courses matching specific criteria.

        Args:
            query: Search query string (searches in course title)
            campus: Optional campus filter
            course_type: Optional course type filter
            area: Optional academic area filter
            language: Language for the interface (IT or EN) - affects course titles
            with_site_urls: If True, fetch course site URLs (requires additional HTTP requests)

        Returns:
            List of courses matching the search criteria

        Raises:
            UnsupportedLanguageError: If language is not IT or EN
        """
        self._validate_language(language)
        logger.info(
            "Searching courses",
            query=query,
            campus=campus.value if campus else "all",
            course_type=course_type.value if course_type else "all",
        )
        all_courses = await self.get_all_courses(course_type, area, language, with_site_urls)

        query_lower = query.lower()
        results: List[BaseCourse] = []

        for course in all_courses:
            # Search in course title
            if query_lower not in course.title.lower():
                continue

            if campus and course.campus != campus:
                continue

            results.append(course)

        logger.info("Search completed", results_count=len(results))
        return results

    async def get_available_curricula(self, course_site_url: str) -> List["Curriculum"]:
        """Fetch available curricula for a course from its timetable page.

        UniBo courses may have multiple curricula (study tracks/specializations).
        This method fetches the list of available curricula from the @@available_curricula endpoint.

        Args:
            course_site_url: URL to the course site (e.g., https://corsi.unibo.it/laurea/informatica)

        Returns:
            List of Curriculum objects. Empty list if no curricula are available.

        Example:
            >>> async with CourseScraper() as scraper:
            ...     curricula = await scraper.get_available_curricula(
            ...         "https://corsi.unibo.it/laurea/informatica"
            ...     )
            ...     for curriculum in curricula:
            ...         print(f"{curriculum.code}: {curriculum.label}")
            000-000: Generale
            B69-000: Percorso avanzato

        Note:
            - Italian courses use '/orario-lezioni' path
            - English courses use '/timetable' path
            - The endpoint returns JSON with curriculum data
        """
        if not course_site_url:
            logger.warning("Empty course_site_url provided")
            return []

        try:
            # Determine the path based on course URL structure
            # Italian courses: /laurea/, /magistrale/, /magistralecu/ -> orario-lezioni
            # English courses: /1cycle/, /2cycle/, /singlecycle/ -> timetable
            if any(x in course_site_url for x in ["/laurea/", "/magistrale/", "/magistralecu/"]):
                path = "orario-lezioni"
            elif any(x in course_site_url for x in ["/1cycle/", "/2cycle/", "/singlecycle/"]):
                path = "timetable"
            else:
                logger.warning("Unknown course URL pattern", course_site_url=course_site_url)
                return []

            curricula_url = f"{course_site_url}/{path}/@@available_curricula"

            logger.debug("Fetching available curricula", curricula_url=curricula_url)

            response = await self.http_client.get(curricula_url)

            # Parse JSON response
            data = json.loads(response)

            # Parse response to Curriculum objects
            # Format: [{"value": "B69-000", "label": "Percorso avanzato", "selected": false}, ...]
            from unibo_toolkit.models.curriculum import Curriculum

            curricula = []
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "value" in item:
                        value = item.get("value")
                        label = item.get("label", "")
                        selected = item.get("selected", False)

                        # Skip None/undefined values
                        if value is not None and value != "":
                            curriculum = Curriculum(
                                code=str(value), label=str(label), selected=selected
                            )
                            curricula.append(curriculum)

            logger.info(
                "Curricula fetched successfully",
                course_site_url=course_site_url,
                curricula_count=len(curricula),
            )

            return curricula

        except json.JSONDecodeError as e:
            logger.warning(
                "Failed to parse curricula JSON", course_site_url=course_site_url, error=str(e)
            )
            return []
        except Exception as e:
            logger.warning(
                "Failed to fetch curricula", course_site_url=course_site_url, error=str(e)
            )
            return []
