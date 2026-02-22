"""HTML parsing utilities for UniBo course data."""

import re
from typing import List, Optional, Tuple

from bs4 import BeautifulSoup, Tag

from unibo_toolkit.enums import AccessType, Area, Campus, CourseType, Language
from unibo_toolkit.utils.custom_logger import get_logger
from unibo_toolkit.models import AreaInfo, Bachelor, BaseCourse, Master, SingleCycleMaster

logger = get_logger(__name__)


class CourseParser:
    """Parser for UniBo course HTML data."""

    BASE_URL = "https://www.unibo.it"
    CAMPUS_MAP = {
        "bologna": Campus.BOLOGNA,
        "cesena": Campus.CESENA,
        "forli": Campus.FORLI,
        "forlì": Campus.FORLI,
        "ravenna": Campus.RAVENNA,
        "rimini": Campus.RIMINI,
    }
    LANGUAGE_MAP = {
        "italiano": Language.IT,
        "italian": Language.IT,
        "inglese": Language.EN,
        "english": Language.EN,
        "francese": Language.FR,
        "french": Language.FR,
    }

    @staticmethod
    def parse_areas(html: str, course_type: CourseType) -> List[AreaInfo]:
        """Parse academic areas from page HTML.

        Args:
            html: HTML content from main course page
            course_type: Type of courses on this page

        Returns:
            List of AreaInfo objects with area and course count
        """
        soup = BeautifulSoup(html, "html.parser")
        buttons = soup.find_all("button", {"data-params": True})
        areas: List[AreaInfo] = []

        for btn in buttons:
            params = btn.get("data-params", "")
            if "schede=" not in params:
                continue

            # Extract area ID from "schede=N" parameter
            schede_str = params.split("schede=")[1].split("&")[0]
            try:
                schede_id = int(schede_str)
            except ValueError:
                continue

            # Get Area enum from ID
            area = Area.from_id(schede_id)
            if not area:
                continue

            # Extract course count
            number_span = btn.find("span", class_="number")
            if number_span:
                try:
                    count = int(number_span.get_text(strip=True))
                    areas.append(AreaInfo(area=area, course_count=count, course_type=course_type))
                except ValueError:
                    continue

        return areas

    @staticmethod
    def parse_course_list(
        html: str,
        year: int,
        category: str,
        area: Optional[Area] = None,
    ) -> List[BaseCourse]:
        """Parse HTML response containing course cards.

        Args:
            html: HTML content from /elenco endpoint
            year: Academic year
            category: Course category (lauree-magistrali or lauree-e-lauree-magistrali-a-ciclo-unico)
            area: Optional area filter

        Returns:
            List of parsed course objects (Bachelor, Master, or SingleCycleMaster)
        """
        soup = BeautifulSoup(html, "html.parser")
        course_items = soup.find_all("div", class_="item")
        courses: List[BaseCourse] = []

        for item in course_items:
            try:
                course = CourseParser._parse_course_card(item, year, category, area)
                if course:
                    courses.append(course)
            except Exception as e:
                logger.warning("Failed to parse course card", error=str(e))
                continue

        return courses

    @staticmethod
    def _parse_course_card(
        item: Tag,
        year: int,
        category: str,
        area: Optional[Area] = None,
    ) -> Optional[BaseCourse]:
        """Parse individual course card element.

        Args:
            item: BeautifulSoup Tag representing course card
            year: Academic year
            category: Course category path
            area: Optional area this course belongs to

        Returns:
            Course object (Bachelor/Master/SingleCycleMaster) or None if parsing fails
        """
        # Extract course ID and title from h3 element
        title_elem = item.find("h3")
        if not title_elem:
            return None

        course_id_str = title_elem.get("id", "")
        if not course_id_str or not course_id_str.isdigit():
            return None

        course_id = int(course_id_str)
        title = title_elem.get_text(strip=True)

        # Get text wrapper containing course details
        text_wrapper = item.find("div", class_="text-wrapper")
        if not text_wrapper:
            return None

        # Cache DOM traversal - find all paragraphs once
        paragraphs_cache = text_wrapper.find_all("p")

        # Extract all course details
        campus = CourseParser._extract_campus(paragraphs_cache)
        languages = CourseParser._extract_languages(paragraphs_cache)
        duration_years = CourseParser._extract_duration(paragraphs_cache, category)
        access_type, seats = CourseParser._extract_access_type(paragraphs_cache)

        # Get course URL
        link_elem = item.find("a", href=True)
        url = (
            link_elem["href"]
            if link_elem
            else f"{CourseParser.BASE_URL}/it/studiare/{category}/corso/{year}/{course_id}"
        )

        # Determine course type based on duration
        course_type = CourseParser._determine_course_type(duration_years)

        # Build course data dictionary
        course_data = {
            "course_id": course_id,
            "title": title,
            "campus": campus,
            "languages": languages,
            "duration_years": duration_years,
            "access_type": access_type,
            "year": year,
            "url": url,
            "area": area,
            "seats": seats,
        }

        # Create appropriate course type instance
        if course_type == CourseType.BACHELOR:
            return Bachelor(**course_data)
        elif course_type == CourseType.MASTER:
            return Master(**course_data)
        else:
            return SingleCycleMaster(**course_data)

    @staticmethod
    def _find_field_value(paragraphs: List, field_name: str) -> str:
        """Extract field value from cached paragraphs by searching for field name in span.

        Args:
            paragraphs: Cached list of paragraph elements
            field_name: Field name to search for (case-insensitive)

        Returns:
            Field value or empty string if not found
        """
        for p in paragraphs:
            span = p.find("span")
            if span and field_name.lower() in span.get_text(strip=True).lower():
                # Remove field label and return value
                full_text = p.get_text(strip=True)
                # Handle "Label: Value" format
                if ":" in full_text:
                    return full_text.split(":", 1)[1].strip()
                return full_text
        return ""

    @staticmethod
    def _extract_campus(paragraphs: List) -> Campus:
        """Extract campus location from cached paragraphs.

        Args:
            paragraphs: Cached list of paragraph elements

        Returns:
            Campus enum value (defaults to BOLOGNA if not found)
        """
        campus_text = CourseParser._find_field_value(
            paragraphs, "sede didattica"
        ) or CourseParser._find_field_value(paragraphs, "place of teaching")
        return CourseParser.CAMPUS_MAP.get(campus_text.lower(), Campus.BOLOGNA)

    @staticmethod
    def _extract_languages(paragraphs: List) -> List[Language]:
        """Extract languages of instruction from cached paragraphs.

        Args:
            paragraphs: Cached list of paragraph elements

        Returns:
            List of Language enums (e.g., [Language.IT] or [Language.EN, Language.IT])
        """
        language_text = CourseParser._find_field_value(
            paragraphs, "lingua"
        ) or CourseParser._find_field_value(paragraphs, "language")

        if not language_text:
            return [Language.IT]

        language_parts = [lang.strip().lower() for lang in language_text.split(",")]

        languages = []
        for lang_key in language_parts:
            lang = CourseParser.LANGUAGE_MAP.get(lang_key)
            if lang:
                languages.append(lang)

        return languages or [Language.IT]

    @staticmethod
    def _extract_duration(paragraphs: List, category: str) -> int:
        """Extract course duration in years from cached paragraphs.

        Args:
            paragraphs: Cached list of paragraph elements
            category: Course category path (used as fallback)

        Returns:
            Duration in years (2, 3, 5, or 6)
        """
        duration_text = CourseParser._find_field_value(
            paragraphs, "durata"
        ) or CourseParser._find_field_value(paragraphs, "duration")

        if duration_text:
            match = re.search(r"(\d+)", duration_text)
            if match:
                return int(match.group(1))

        if "magistrali-a-ciclo-unico" in category:
            return 5
        elif "magistrali" in category or "second-cycle" in category:
            return 2
        return 3

    @staticmethod
    def _extract_access_type(paragraphs: List) -> Tuple[AccessType, Optional[int]]:
        """Extract access type and number of seats from cached paragraphs.

        Args:
            paragraphs: Cached list of paragraph elements

        Returns:
            Tuple of (AccessType enum, number of seats or None)
        """
        access_text = CourseParser._find_field_value(
            paragraphs, "tipo di accesso"
        ) or CourseParser._find_field_value(paragraphs, "type of access")
        access_lower = access_text.lower()

        if "libero" in access_lower or "open access" in access_lower:
            return AccessType.OPEN, None

        # Check for limited access (IT: "programmato", EN: "restricted access")
        if "programmato" in access_lower or "restricted" in access_lower:
            # Extract number from:
            # IT: "X posti disponibili"
            # EN: "X places available"
            seats_match = re.search(r"(\d+)\s*(?:posti|places)", access_text, re.IGNORECASE)
            seats = int(seats_match.group(1)) if seats_match else None
            return AccessType.LIMITED, seats

        return AccessType.OPEN, None

    @staticmethod
    def _determine_course_type(duration: int) -> CourseType:
        """Determine course type based on duration.

        Args:
            duration: Course duration in years

        Returns:
            CourseType enum (BACHELOR, MASTER, or SINGLE_CYCLE_MASTER)
        """
        if duration >= 5:
            return CourseType.SINGLE_CYCLE_MASTER
        elif duration == 2:
            return CourseType.MASTER
        return CourseType.BACHELOR
