"""Parser for extracting subjects from UniBo timetable HTML pages."""

from __future__ import annotations

from typing import List, Optional

from bs4 import BeautifulSoup

from unibo_toolkit.utils.custom_logger import get_logger
from unibo_toolkit.models import Subject

logger = get_logger(__name__)


class SubjectsParser:
    """Parser for extracting subjects from HTML timetable pages."""

    @staticmethod
    def parse_subjects(html: str, academic_year: int) -> List[Subject]:
        """Parse subjects from timetable HTML page.

        Extracts subjects from checkbox inputs in the timetable filter form.

        Args:
            html: HTML content of timetable page
            academic_year: Year of study (1, 2, 3, etc.)

        Returns:
            List of Subject objects

        Example HTML:
            <input type="checkbox"
                   name="insegnamenti"
                   value="2025-000-400513--I|B1944"
                   id="insegnamento_B1944" />
            <label for="insegnamento_B1944">AMERICA AND THE WORLD</label>
        """
        soup = BeautifulSoup(html, "html.parser")
        subjects = []

        # Find all subject checkboxes
        checkboxes = soup.find_all("input", {"name": "insegnamenti", "type": "checkbox"})

        for checkbox in checkboxes:
            value = checkbox.get("value", "")
            if not value:
                continue

            # Find associated label
            checkbox_id = checkbox.get("id", "")
            title = ""
            if checkbox_id:
                label = soup.find("label", {"for": checkbox_id})
                if label:
                    title = label.get_text(strip=True)

            # Parse value: "2025-000-400513--I|B1944"
            subject = SubjectsParser._parse_subject_value(value, title, academic_year)
            if subject:
                subjects.append(subject)

        return subjects

    @staticmethod
    def _parse_subject_value(value: str, title: str, academic_year: int) -> Optional[Subject]:
        """Parse subject from checkbox value.

        Args:
            value: Checkbox value (e.g., "2025-000-400513--I|B1944")
            title: Subject title from label
            academic_year: Year of study

        Returns:
            Subject object or None if parsing fails

        Value format: "{year}-{???}-{subject_code}--{???}|{module_id}"
        """
        if not value or "|" not in value:
            return None

        try:
            # Split by pipe to get module_id
            parts = value.split("|")
            if len(parts) != 2:
                return None

            left_part = parts[0]
            module_id = parts[1]

            # Extract subject code from left part
            # Format: "2025-000-400513--I"
            # We want "400513"
            subject_code = SubjectsParser._extract_subject_code(left_part)

            if not subject_code:
                return None

            return Subject(
                title=title,
                subject_code=subject_code,
                module_id=module_id,
                value=value,
                academic_year=academic_year,
            )

        except Exception as e:
            logger.warning("Failed to parse subject value", value=value, error=str(e))
            return None

    @staticmethod
    def _extract_subject_code(left_part: str) -> Optional[str]:
        """Extract subject code from left part of value.

        Args:
            left_part: Left part before pipe (e.g., "2025-000-400513--I")

        Returns:
            Subject code (e.g., "400513") or None

        Examples:
            >>> SubjectsParser._extract_subject_code("2025-000-400513--I")
            "400513"
            >>> SubjectsParser._extract_subject_code("2025-000-400513")
            "400513"
        """
        # Pattern: extract numbers after second dash and before optional "--"
        # "2025-000-400513--I" → "400513"
        # "2025-000-400513" → "400513"

        # Remove everything after "--" if present
        if "--" in left_part:
            left_part = left_part.split("--")[0]

        # Split by dash and get last numeric part
        parts = left_part.split("-")
        if len(parts) >= 3:
            # Should be: ["2025", "000", "400513"]
            code = parts[-1]
            if code.isdigit():
                return code

        return None

    @staticmethod
    def count_subjects(html: str) -> int:
        """Count number of subjects in HTML.

        Quick utility to check how many subjects are available.

        Args:
            html: HTML content

        Returns:
            Number of subjects found
        """
        soup = BeautifulSoup(html, "html.parser")
        checkboxes = soup.find_all("input", {"name": "insegnamenti", "type": "checkbox"})
        return len(checkboxes)

    @staticmethod
    def has_subjects(html: str) -> bool:
        """Check if HTML page contains subjects.

        Args:
            html: HTML content

        Returns:
            True if subjects found, False otherwise
        """
        return SubjectsParser.count_subjects(html) > 0
