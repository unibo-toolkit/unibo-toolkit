"""Timetable scraper for UniBo course timetables."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import aiohttp

from unibo_toolkit.clients import HTTPClient
from unibo_toolkit.logging import get_logger
from unibo_toolkit.models import (
    Curriculum,
    CurriculumTimetable,
    Timetable,
    TimetableCollection,
)
from unibo_toolkit.utils.date_utils import get_api_date_range, split_date_range
from unibo_toolkit.utils.timetable_parser import TimetableParser

logger = get_logger(__name__)


class TimetableScraper:
    """Scraper for fetching course timetables from UniBo API.

    Supports fetching timetables for single or multiple academic years,
    with configurable caching and date ranges.

    The API rejects ranges longer than 45 days, so every request is split into
    consecutive chunks that are fetched concurrently and merged.
    """

    # API endpoint patterns (language-dependent)
    TIMETABLE_ENDPOINTS = [
        "/orario-lezioni/@@orario_reale_json",  # Italian courses
        "/timetable/@@orario_reale_json",  # English courses
    ]

    # Default limit of simultaneous API requests issued by one scraper
    DEFAULT_MAX_CONCURRENT_REQUESTS = 10

    # Retries for transient errors (5xx, timeouts, dropped connections) per chunk.
    # Backoff before attempt N is RETRY_BACKOFF_SECONDS * N.
    MAX_RETRIES = 2
    RETRY_BACKOFF_SECONDS = 1.0

    @staticmethod
    def _is_transient_error(error: BaseException) -> bool:
        """Check whether a request error is worth retrying.

        Args:
            error: Exception raised by the HTTP request

        Returns:
            True for server errors (5xx), timeouts and connection problems;
            False for client errors such as 404 on a missing endpoint
        """
        if isinstance(error, aiohttp.ClientResponseError):
            return error.status >= 500
        return isinstance(
            error, (asyncio.TimeoutError, aiohttp.ClientConnectionError, aiohttp.ClientPayloadError)
        )

    def __init__(
        self,
        http_client: Optional[HTTPClient] = None,
        max_concurrent_requests: int = DEFAULT_MAX_CONCURRENT_REQUESTS,
    ):
        """Initialize timetable scraper.

        Args:
            http_client: Optional HTTP client. If None, creates own client.
            max_concurrent_requests: Maximum number of simultaneous API requests
        """
        self._max_concurrent_requests = max_concurrent_requests
        # Created lazily inside the running loop (required on Python < 3.10)
        self._request_semaphore: Optional[asyncio.Semaphore] = None
        self._external_client = http_client
        self._internal_client: Optional[HTTPClient] = None
        self.http_client: HTTPClient = http_client
        self.parser = TimetableParser()
        logger.debug("TimetableScraper initialized")

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

    @staticmethod
    def _build_timetable_url(
        course_site_url: str,
        endpoint: str,
        academic_year: int,
        start_date: str,
        end_date: str,
        curriculum: Optional[Curriculum] = None,
    ) -> Tuple[str, Dict]:
        """Build timetable API URL and query parameters.

        Args:
            course_site_url: Base course URL
            endpoint: API endpoint path
            academic_year: Academic year (1, 2, 3, etc.)
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            curriculum: Optional curriculum to filter by

        Returns:
            Tuple of (base_url, params_dict) for use with HTTPClient.get()

        Example:
            >>> url, params = scraper._build_timetable_url(
            ...     "https://corsi.unibo.it/magistrale/ComputerScience",
            ...     "/timetable/@@orario_reale_json",
            ...     1,
            ...     "2024-09-01",
            ...     "2027-07-31"
            ... )
            >>> print(url)
            https://corsi.unibo.it/magistrale/ComputerScience/timetable/@@orario_reale_json
            >>> print(params)
            {'anno': 1, 'curricula': '', 'start': '2024-09-01', 'end': '2027-07-31'}
        """
        base = course_site_url.rstrip("/")
        base_url = f"{base}{endpoint}"

        params = {
            "anno": academic_year,
            "curricula": curriculum.code if curriculum else "",
            "start": start_date,
            "end": end_date,
        }

        return base_url, params

    async def _fetch_chunk(self, url: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch one API-sized chunk, retrying transient errors.

        Args:
            url: Timetable endpoint URL
            params: Query parameters for a range within the API limit

        Returns:
            List of raw event dicts

        Raises:
            ValueError: If the response is not a valid timetable
            Exception: The last HTTP error if retries are exhausted or the error is permanent
        """
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                async with self._request_semaphore:
                    response_text = await self.http_client.get(url, params=params)
                break
            except Exception as e:
                if attempt == self.MAX_RETRIES or not self._is_transient_error(e):
                    raise
                logger.debug(
                    "Retrying timetable chunk",
                    range=f"{params['start']}..{params['end']}",
                    attempt=attempt + 1,
                    error=str(e),
                )
                await asyncio.sleep(self.RETRY_BACKOFF_SECONDS * (attempt + 1))

        json_data = json.loads(response_text)
        if not self.parser.validate_response(json_data):
            raise ValueError(f"Invalid response for range {params['start']}..{params['end']}")
        return json_data

    async def _fetch_raw_events(
        self,
        course_site_url: str,
        endpoint: str,
        academic_year: int,
        start_date: str,
        end_date: str,
        curriculum: Optional[Curriculum] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch raw events for a date range, splitting it into API-sized chunks.

        The first chunk is fetched alone to check that the endpoint exists; the
        remaining chunks are then fetched concurrently. If a chunk fails, the pending
        chunks are cancelled so no requests outlive the call.

        Args:
            course_site_url: Base course URL
            endpoint: API endpoint path
            academic_year: Academic year (1, 2, 3, etc.)
            start_date: Start date (YYYY-MM-DD), inclusive
            end_date: End date (YYYY-MM-DD), inclusive
            curriculum: Optional curriculum to filter by

        Returns:
            Concatenated list of raw event dicts from all chunks, in chronological order

        Raises:
            ValueError: If any chunk returns an invalid response
            Exception: Any HTTP/JSON error from a chunk request
        """
        if self._request_semaphore is None:
            self._request_semaphore = asyncio.Semaphore(self._max_concurrent_requests)

        requests = [
            self._build_timetable_url(
                course_site_url, endpoint, academic_year, chunk_start, chunk_end, curriculum
            )
            for chunk_start, chunk_end in split_date_range(start_date, end_date)
        ]

        # Probe the endpoint with the first chunk alone: if it fails (e.g. 404 on the
        # wrong language endpoint), the remaining chunks are never requested.
        events = await self._fetch_chunk(*requests[0])

        tasks = [
            asyncio.ensure_future(self._fetch_chunk(url, params)) for url, params in requests[1:]
        ]
        try:
            results = await asyncio.gather(*tasks)
        except BaseException:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            raise

        for chunk_events in results:
            events.extend(chunk_events)
        return events

    async def fetch_timetable(
        self,
        course_site_url: str,
        course_id: int,
        course_title: str,
        academic_year: int,
        extended_range: bool = True,
        reference_date: Optional[datetime] = None,
    ) -> Timetable:
        """Fetch timetable for a single academic year.

        Tries both API endpoints (Italian and English) until one works.

        Args:
            course_site_url: Course site URL (corsi.unibo.it)
            course_id: Course identifier
            course_title: Course name
            academic_year: Year of study (1, 2, 3, etc.)
            extended_range: Use extended date range (±4 months)
            reference_date: Reference date for academic year calculation

        Returns:
            Timetable object

        Raises:
            ValueError: If course_site_url is invalid
        """
        if not course_site_url:
            raise ValueError("course_site_url cannot be empty")

        # Get date range for API
        start_date, end_date = get_api_date_range(reference_date, extended=extended_range)

        logger.debug(
            "Fetching timetable",
            course=course_title,
            year=academic_year,
            date_range=f"{start_date} to {end_date}",
        )

        # Try both endpoints
        for endpoint in self.TIMETABLE_ENDPOINTS:
            try:
                logger.debug("Trying endpoint", endpoint=endpoint)
                json_data = await self._fetch_raw_events(
                    course_site_url, endpoint, academic_year, start_date, end_date
                )

                # Parse events and compute content hash
                events, content_hash = self.parser.parse_events(json_data)

                logger.info(
                    "Timetable fetched successfully",
                    course=course_title,
                    year=academic_year,
                    events_count=len(events),
                    content_hash=content_hash,
                    endpoint=endpoint,
                )

                return Timetable(
                    course_id=course_id,
                    course_title=course_title,
                    academic_year=academic_year,
                    start_date=datetime.fromisoformat(start_date),
                    end_date=datetime.fromisoformat(end_date),
                    events=events,
                    has_timetable=len(events) > 0,
                    fetch_successful=True,
                    endpoint_used=endpoint,
                )

            except Exception as e:
                logger.warning("Endpoint failed", endpoint=endpoint, error=str(e))
                continue

        # All endpoints failed
        logger.warning("No timetable found", course=course_title, year=academic_year)
        return Timetable(
            course_id=course_id,
            course_title=course_title,
            academic_year=academic_year,
            start_date=datetime.fromisoformat(start_date),
            end_date=datetime.fromisoformat(end_date),
            events=[],
            has_timetable=False,
            fetch_successful=False,
            endpoint_used=None,
        )

    async def get_curriculum_timetable(
        self,
        course_site_url: str,
        curriculum: Curriculum,
        academic_year: int,
        extended_range: bool = True,
        reference_date: Optional[datetime] = None,
    ) -> CurriculumTimetable:
        """Fetch timetable for a specific curriculum in an academic year.

        Args:
            course_site_url: Course site URL (corsi.unibo.it)
            curriculum: Curriculum object to fetch timetable for
            academic_year: Year of study (1, 2, 3, etc.)
            extended_range: Use extended date range (±4 months)
            reference_date: Reference date for academic year calculation

        Returns:
            CurriculumTimetable object with events for this curriculum

        Raises:
            ValueError: If course_site_url is invalid
        """
        if not course_site_url:
            raise ValueError("course_site_url cannot be empty")

        # Get date range for API
        start_date, end_date = get_api_date_range(reference_date, extended=extended_range)

        logger.debug(
            "Fetching curriculum timetable",
            curriculum=curriculum.code,
            year=academic_year,
            date_range=f"{start_date} to {end_date}",
        )

        # Try both endpoints
        for endpoint in self.TIMETABLE_ENDPOINTS:
            try:
                logger.debug("Trying endpoint", endpoint=endpoint)
                json_data = await self._fetch_raw_events(
                    course_site_url,
                    endpoint,
                    academic_year,
                    start_date,
                    end_date,
                    curriculum=curriculum,
                )

                # Parse events
                events, content_hash = self.parser.parse_events(json_data)

                logger.info(
                    "Curriculum timetable fetched successfully",
                    curriculum=curriculum.code,
                    year=academic_year,
                    events_count=len(events),
                    content_hash=content_hash,
                    endpoint=endpoint,
                )

                return CurriculumTimetable(
                    curriculum=curriculum,
                    events=events,
                    content_hash=content_hash,
                )

            except Exception as e:
                logger.warning("Endpoint failed", endpoint=endpoint, error=str(e))
                continue

        # All endpoints failed
        logger.warning(
            "No timetable found for curriculum", curriculum=curriculum.code, year=academic_year
        )
        return CurriculumTimetable(
            curriculum=curriculum,
            events=[],
            content_hash="",
        )

    async def get_timetables(
        self,
        course_site_url: str,
        curricula: List[Curriculum],
        academic_years: List[int],
        extended_range: bool = True,
        reference_date: Optional[datetime] = None,
    ) -> TimetableCollection:
        """Fetch timetables for multiple academic years and curricula.

        Creates a hierarchical collection: Collection → AcademicYear → Curriculum → Events
        Fetches all combinations of years and curricula concurrently for maximum performance.

        Args:
            course_site_url: Course site URL
            curricula: List of Curriculum objects to fetch
            academic_years: List of years to fetch (e.g., [1, 2, 3])
            extended_range: Use extended date range
            reference_date: Reference date for calculations

        Returns:
            TimetableCollection organized by year and curriculum

        Example:
            >>> collection = await scraper.get_timetables(
            ...     course_site_url="https://corsi.unibo.it/magistrale/AI",
            ...     curricula=[
            ...         Curriculum(code="B69-000", label="Advanced Track"),
            ...         Curriculum(code="000-000", label="General Track"),
            ...     ],
            ...     academic_years=[1, 2]
            ... )
            >>> year1 = collection.get_year(1)
            >>> print(len(year1.curricula))
            2
        """
        logger.info(
            "Fetching timetables for multiple years and curricula",
            curricula_count=len(curricula),
            years=str(academic_years),
        )

        # Create all fetch tasks (year x curriculum combinations)
        tasks = []
        for year in academic_years:
            for curriculum in curricula:
                task = self.get_curriculum_timetable(
                    course_site_url=course_site_url,
                    curriculum=curriculum,
                    academic_year=year,
                    extended_range=extended_range,
                    reference_date=reference_date,
                )
                tasks.append((year, task))

        # Fetch all combinations concurrently
        results = await asyncio.gather(*[task for _, task in tasks])

        # Build hierarchical collection
        collection = TimetableCollection()

        for (year, _), curriculum_timetable in zip(tasks, results):
            collection.add_curriculum_timetable(year, curriculum_timetable)

        total_events = len(collection.get_all_events())
        logger.info(
            "Timetables collection completed",
            total_events=total_events,
            years_count=len(academic_years),
            curricula_count=len(curricula),
        )

        return collection
