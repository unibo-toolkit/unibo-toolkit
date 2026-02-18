"""Subjects scraper for UniBo course subjects."""

import asyncio
from typing import Dict, List, Optional

from unibo_toolkit.clients import HTTPClient
from unibo_toolkit.logging import get_logger
from unibo_toolkit.models import Subject
from unibo_toolkit.utils.subjects_parser import SubjectsParser

logger = get_logger(__name__)


class SubjectsScraper:
    """Scraper for fetching course subjects from timetable HTML pages.

    Extracts subject information from the timetable filter checkboxes.

    Example:
        >>> async with SubjectsScraper() as scraper:
        ...     subjects_dict = await scraper.get_subjects(
        ...         course_site_url="https://corsi.unibo.it/magistrale/AI",
        ...         academic_years=[1, 2]
        ...     )
        ...     print(subjects_dict[1])  # Year 1 subjects
    """

    # Timetable page paths (language-dependent)
    TIMETABLE_PAGES = [
        "/orario-lezioni",  # Italian
        "/timetable",        # English
    ]

    def __init__(
        self,
        http_client: Optional[HTTPClient] = None,
        request_delay: float = 0.2,
    ):
        """Initialize subjects scraper.

        Args:
            http_client: Optional HTTP client. If None, creates own client.
            request_delay: Delay between requests in seconds (default: 0.2s)
        """
        self._external_client = http_client
        self._internal_client: Optional[HTTPClient] = None
        self.http_client: HTTPClient = http_client
        self.parser = SubjectsParser()
        self.request_delay = request_delay
        logger.debug("SubjectsScraper initialized", delay_seconds=request_delay)

    async def __aenter__(self):
        """Enter async context manager."""
        if self._external_client is None:
            self._internal_client = HTTPClient()
            await self._internal_client.__aenter__()
            self.http_client = self._internal_client
            logger.debug("Created internal HTTP client")
        else:
            self.http_client = self._external_client
            logger.debug("Using external HTTP client")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit async context manager."""
        if self._internal_client is not None:
            await self._internal_client.__aexit__(exc_type, exc_val, exc_tb)
            logger.debug("Closed internal HTTP client")
        return False

    def _build_timetable_page_url(
        self,
        course_site_url: str,
        page_path: str,
        academic_year: int,
    ) -> str:
        """Build timetable HTML page URL.

        Args:
            course_site_url: Base course URL
            page_path: Page path (/orario-lezioni or /timetable)
            academic_year: Academic year (1, 2, 3, etc.)

        Returns:
            Complete page URL

        Example:
            >>> url = scraper._build_timetable_page_url(
            ...     "https://corsi.unibo.it/magistrale/AI",
            ...     "/timetable",
            ...     1
            ... )
            >>> print(url)
            https://corsi.unibo.it/magistrale/AI/timetable?anno=1
        """
        base = course_site_url.rstrip("/")
        return f"{base}{page_path}?anno={academic_year}"

    async def fetch_subjects(
        self,
        course_site_url: str,
        academic_year: int,
    ) -> List[Subject]:
        """Fetch subjects for a single academic year.

        Tries both page paths (Italian and English) until one works.

        Args:
            course_site_url: Course site URL (corsi.unibo.it)
            academic_year: Year of study (1, 2, 3, etc.)

        Returns:
            List of Subject objects

        Raises:
            ValueError: If course_site_url is invalid
        """
        if not course_site_url:
            raise ValueError("course_site_url cannot be empty")

        logger.debug(
            "Fetching subjects",
            year=academic_year,
            course_url=course_site_url
        )

        # Try both page paths
        for page_path in self.TIMETABLE_PAGES:
            url = self._build_timetable_page_url(
                course_site_url,
                page_path,
                academic_year
            )

            try:
                logger.debug("Trying page path", page_path=page_path)
                html = await self.http_client.get(url)

                # Check if page has subjects
                if not self.parser.has_subjects(html):
                    logger.debug("No subjects found in page", page_path=page_path)
                    continue

                # Parse subjects
                subjects = self.parser.parse_subjects(html, academic_year)

                logger.info(
                    "Subjects fetched successfully",
                    year=academic_year,
                    subjects_count=len(subjects),
                    page_path=page_path
                )

                return subjects

            except Exception as e:
                logger.debug("Page path failed", page_path=page_path, error=str(e))
                continue

        # All page paths failed
        logger.warning("No subjects found", year=academic_year)
        return []

    async def get_subjects(
        self,
        course_site_url: str,
        academic_years: List[int],
    ) -> Dict[int, List[Subject]]:
        """Fetch subjects for multiple academic years.

        Fetches all years concurrently for better performance.

        Args:
            course_site_url: Course site URL
            academic_years: List of years to fetch (e.g., [1, 2, 3])

        Returns:
            Dictionary mapping year → list of subjects

        Example:
            >>> subjects_dict = await scraper.get_subjects(
            ...     course_site_url="https://corsi.unibo.it/magistrale/AI",
            ...     academic_years=[1, 2]
            ... )
            >>> print(len(subjects_dict[1]))  # Number of Year 1 subjects
            12
        """
        logger.info(
            "Fetching subjects for multiple years",
            years=str(academic_years)
        )

        # Fetch all years concurrently
        tasks = [
            self.fetch_subjects(
                course_site_url=course_site_url,
                academic_year=year,
            )
            for year in academic_years
        ]

        # Add delay between concurrent requests
        subjects_lists = []
        for task in tasks:
            subjects = await task
            subjects_lists.append(subjects)
            await asyncio.sleep(self.request_delay)

        # Build result dictionary
        result = {
            year: subjects
            for year, subjects in zip(academic_years, subjects_lists)
        }

        total_subjects = sum(len(subs) for subs in result.values())
        logger.info(
            "Subjects collection completed",
            total_subjects=total_subjects,
            years_count=len(academic_years)
        )

        return result
