"""Date and academic year utilities for UniBo timetables."""

from datetime import datetime
from typing import Tuple


def get_academic_year_range(
    reference_date: datetime | None = None,
    extended: bool = False
) -> Tuple[datetime, datetime]:
    """Calculate academic year date range.

    UniBo academic year runs from September to July (with January exam period).

    **IMPORTANT BUG FIX**: Correctly handles dates before September.
    If current date is April 2026, we're still in academic year 2025/2026,
    NOT 2026/2027!

    Args:
        reference_date: Reference date (default: today)
        extended: If True, extends range by ±1 year for safety

    Returns:
        Tuple of (start_date, end_date)

    Examples:
        >>> # February 2026 → academic year 2025/2026
        >>> get_academic_year_range(datetime(2026, 2, 15))
        (datetime(2025, 9, 1), datetime(2026, 7, 31))

        >>> # October 2025 → academic year 2025/2026
        >>> get_academic_year_range(datetime(2025, 10, 1))
        (datetime(2025, 9, 1), datetime(2026, 7, 31))

        >>> # Extended range (±1 year)
        >>> get_academic_year_range(datetime(2026, 2, 15), extended=True)
        (datetime(2024, 9, 1), datetime(2027, 7, 31))
    """
    if reference_date is None:
        reference_date = datetime.now()

    current_month = reference_date.month
    current_year = reference_date.year

    # Determine academic year start
    # If we're in September or later, academic year started this year
    # If we're before September, academic year started last year
    if current_month >= 9:
        start_year = current_year
        end_year = current_year + 1
    else:
        start_year = current_year - 1
        end_year = current_year

    # Academic year dates
    # September 1 → July 31
    start_date = datetime(start_year, 9, 1)
    end_date = datetime(end_year, 7, 31, 23, 59, 59)

    # Extended range: ±1 year for capturing all possible events
    if extended:
        start_date = datetime(start_year - 1, 9, 1)
        end_date = datetime(end_year + 1, 7, 31, 23, 59, 59)

    return start_date, end_date


def format_date_for_api(date: datetime) -> str:
    """Format datetime for UniBo API.

    Args:
        date: Datetime to format

    Returns:
        Formatted date string (YYYY-MM-DD)

    Example:
        >>> format_date_for_api(datetime(2026, 2, 15))
        '2026-02-15'
    """
    return date.strftime("%Y-%m-%d")


def get_api_date_range(
    academic_year: int,
    reference_date: datetime | None = None,
    extended: bool = True
) -> Tuple[str, str]:
    """Get date range for timetable API request.

    Args:
        academic_year: Year of study (1, 2, 3, etc.)
        reference_date: Reference date (default: today)
        extended: Use extended range (±1 year)

    Returns:
        Tuple of (start_date_str, end_date_str) in YYYY-MM-DD format

    Example:
        >>> get_api_date_range(1, datetime(2026, 2, 15))
        ('2024-09-01', '2027-07-31')
    """
    start_date, end_date = get_academic_year_range(reference_date, extended)
    return format_date_for_api(start_date), format_date_for_api(end_date)


def parse_api_datetime(date_str: str) -> datetime:
    """Parse datetime from UniBo API response.

    The API returns datetimes in ISO format with timezone.

    Args:
        date_str: ISO datetime string from API

    Returns:
        Parsed datetime object

    Examples:
        >>> parse_api_datetime("2026-02-15T10:00:00+01:00")
        datetime(2026, 2, 15, 10, 0, 0)

        >>> parse_api_datetime("2026-02-15T10:00:00")
        datetime(2026, 2, 15, 10, 0, 0)
    """
    # Try parsing with timezone first
    try:
        # Remove timezone info for simplicity (we don't need it for timetables)
        if '+' in date_str:
            date_str = date_str.split('+')[0]
        elif date_str.endswith('Z'):
            date_str = date_str[:-1]

        return datetime.fromisoformat(date_str)
    except ValueError:
        # Fallback: try without microseconds
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
