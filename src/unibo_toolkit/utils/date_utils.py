"""Date and academic year utilities for UniBo timetables."""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

# Maximum allowed difference (in days) between `start` and `end` accepted by
# the timetable API. Larger ranges are rejected with HTTP 503.
# Both `start` and `end` are inclusive.
MAX_API_RANGE_DAYS = 45

# Safety margin (in months) added on each side of the academic year when the
# extended range is requested.
EXTENDED_RANGE_MONTHS = 4


def _add_months(date: datetime, months: int) -> datetime:
    """Shift a datetime by a number of months, clamping the day to the month length.

    Args:
        date: Datetime to shift
        months: Number of months to add (negative to subtract)

    Returns:
        Shifted datetime with the same time of day

    Example:
        >>> _add_months(datetime(2027, 7, 31), 4)
        datetime(2027, 11, 30)
    """
    month_index = date.month - 1 + months
    year = date.year + month_index // 12
    month = month_index % 12 + 1
    day = min(date.day, calendar.monthrange(year, month)[1])
    return date.replace(year=year, month=month, day=day)


def get_academic_year_range(
    reference_date: Optional[datetime] = None, extended: bool = False
) -> Tuple[datetime, datetime]:
    """Calculate academic year date range.

    UniBo academic year runs from September to July (with January exam period).

    Args:
        reference_date: Reference date (default: today)
        extended: If True, extends range by ±EXTENDED_RANGE_MONTHS (4) months for safety

    Returns:
        Tuple of (start_date, end_date)

    Examples:
        >>> # February 2026 → academic year 2025/2026
        >>> get_academic_year_range(datetime(2026, 2, 15))
        (datetime(2025, 9, 1), datetime(2026, 7, 31))

        >>> # October 2025 → academic year 2025/2026
        >>> get_academic_year_range(datetime(2025, 10, 1))
        (datetime(2025, 9, 1), datetime(2026, 7, 31))

        >>> # Extended range (±4 months)
        >>> get_academic_year_range(datetime(2026, 2, 15), extended=True)
        (datetime(2025, 5, 1), datetime(2026, 11, 30))
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

    # Extended range: safety margin for events slightly outside the academic year.
    # The API keeps no data for past academic years and has none for future ones,
    # so a wider margin only adds empty requests.
    if extended:
        start_date = _add_months(start_date, -EXTENDED_RANGE_MONTHS)
        end_date = _add_months(end_date, EXTENDED_RANGE_MONTHS)

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
    reference_date: Optional[datetime] = None, extended: bool = True
) -> Tuple[str, str]:
    """Get date range for timetable API request.

    Args:
        reference_date: Reference date (default: today)
        extended: Use extended range (±4 months)

    Returns:
        Tuple of (start_date_str, end_date_str) in YYYY-MM-DD format

    Example:
        >>> get_api_date_range(datetime(2026, 2, 15))
        ('2025-05-01', '2026-11-30')
    """
    start_date, end_date = get_academic_year_range(reference_date, extended)
    return format_date_for_api(start_date), format_date_for_api(end_date)


def split_date_range(
    start_date: str, end_date: str, max_days: int = MAX_API_RANGE_DAYS
) -> List[Tuple[str, str]]:
    """Split an inclusive date range into non-overlapping chunks accepted by the API.

    The timetable API returns whole days for both `start` and `end`, so consecutive
    chunks start the day after the previous chunk ends.

    Args:
        start_date: Range start (YYYY-MM-DD), inclusive
        end_date: Range end (YYYY-MM-DD), inclusive
        max_days: Maximum difference in days between a chunk's start and end

    Returns:
        List of (start, end) tuples in YYYY-MM-DD format, ordered chronologically

    Raises:
        ValueError: If end_date is before start_date or max_days is negative

    Example:
        >>> split_date_range("2026-10-07", "2026-12-31")
        [('2026-10-07', '2026-11-21'), ('2026-11-22', '2026-12-31')]
    """
    if max_days < 0:
        raise ValueError("max_days must be non-negative")

    start = datetime.fromisoformat(start_date)
    end = datetime.fromisoformat(end_date)
    if end < start:
        raise ValueError(f"end_date {end_date} is before start_date {start_date}")

    chunks = []
    chunk_start = start
    while chunk_start <= end:
        chunk_end = min(chunk_start + timedelta(days=max_days), end)
        chunks.append((format_date_for_api(chunk_start), format_date_for_api(chunk_end)))
        chunk_start = chunk_end + timedelta(days=1)

    return chunks


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
        if "+" in date_str:
            date_str = date_str.split("+")[0]
        elif date_str.endswith("Z"):
            date_str = date_str[:-1]
        elif len(date_str) > 19 and date_str[19] == "-":
            # Negative UTC offset: "2026-02-15T10:00:00-05:00"
            date_str = date_str[:19]

        return datetime.fromisoformat(date_str)
    except ValueError:
        # Fallback: try without microseconds
        return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
