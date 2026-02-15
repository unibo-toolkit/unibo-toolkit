"""Filtering utilities for timetable events."""

from datetime import datetime
from typing import Dict, List, Optional, Union

from unibo_toolkit.models import TimetableEvent


def filter_events(
    events: List[TimetableEvent],
    group_id: Optional[Union[str, List[str]]] = None,
    subject: Optional[str] = None,
    professor: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    only_remote: bool = False,
    only_in_person: bool = False,
) -> List[TimetableEvent]:
    """Filter timetable events by various criteria.

    Args:
        events: List of events to filter
        group_id: Filter by group ID or list of IDs. Supports all 146 patterns:
                  - Class notation: "CL.A", "CL.B"
                  - Surname ranges: "A-L", "M-Z", "A-K", "L-Z"
                  - Short codes: "AK", "LZ", "BO", "RN"
                  - Single letters: "A", "B", "C", "D"
                  - Location: "BO", "CE", "RN", "IMOLA"
                  - And more...
        subject: Filter by subject title (partial match, case-insensitive)
        professor: Filter by professor name (partial match, case-insensitive)
        start_date: Filter events starting after this date
        end_date: Filter events starting before this date
        only_remote: Only include remote/online events
        only_in_person: Only include in-person events

    Returns:
        Filtered list of events

    Examples:
        >>> # Filter by class notation (Engineering/CS courses)
        >>> events_a = filter_events(timetable.events, group_id="CL.A")

        >>> # Filter by surname range (Medicine courses)
        >>> events_ak = filter_events(timetable.events, group_id="A-L")

        >>> # Filter by location code
        >>> events_bo = filter_events(timetable.events, group_id="BO")

        >>> # Filter by multiple groups
        >>> events_ab = filter_events(timetable.events, group_id=["CL.A", "CL.B"])

        >>> # Filter by subject and date range
        >>> events = filter_events(
        ...     timetable.events,
        ...     subject="ALGEBRA",
        ...     start_date=datetime(2026, 2, 1),
        ...     end_date=datetime(2026, 2, 28)
        ... )

        >>> # Only remote events for specific group
        >>> remote_a = filter_events(
        ...     timetable.events,
        ...     group_id="CL.A",
        ...     only_remote=True
        ... )
    """
    filtered = events

    # Filter by group ID
    if group_id is not None:
        if isinstance(group_id, str):
            group_ids = [group_id]
        else:
            group_ids = group_id

        filtered = [e for e in filtered if e.group_id in group_ids]

    # Filter by subject
    if subject is not None:
        subject_lower = subject.lower()
        filtered = [
            e for e in filtered
            if subject_lower in e.title.lower()
        ]

    # Filter by professor
    if professor is not None:
        professor_lower = professor.lower()
        filtered = [
            e for e in filtered
            if e.professor and professor_lower in e.professor.lower()
        ]

    # Filter by date range
    if start_date is not None:
        filtered = [e for e in filtered if e.start >= start_date]

    if end_date is not None:
        filtered = [e for e in filtered if e.start <= end_date]

    # Filter by remote/in-person
    if only_remote:
        filtered = [e for e in filtered if e.is_remote]

    if only_in_person:
        filtered = [e for e in filtered if not e.is_remote]

    return filtered


def group_events_by_group(
    events: List[TimetableEvent]
) -> Dict[str, List[TimetableEvent]]:
    """Group events by group ID.

    Args:
        events: List of events

    Returns:
        Dict mapping group ID → events.
        Includes 'common' key for events without group assignment.

    Examples:
        >>> # Class notation course (Engineering/CS)
        >>> grouped = group_events_by_group(timetable.events)
        >>> print(grouped.keys())  # ['CL.A', 'CL.B', 'common']
        >>> print(len(grouped['CL.A']))  # 120 events

        >>> # Surname range course (Medicine)
        >>> grouped = group_events_by_group(timetable.events)
        >>> print(grouped.keys())  # ['A-L', 'M-Z', 'common']
        >>> print(len(grouped['A-L']))  # 200 events

        >>> # Location-based course
        >>> grouped = group_events_by_group(timetable.events)
        >>> print(grouped.keys())  # ['BO', 'CE', 'RN', 'common']
    """
    grouped: Dict[str, List[TimetableEvent]] = {}

    for event in events:
        key = event.group_id if event.group_id else 'common'

        if key not in grouped:
            grouped[key] = []

        grouped[key].append(event)

    return grouped


def get_unique_subjects(events: List[TimetableEvent]) -> List[str]:
    """Get unique subject titles from events.

    Args:
        events: List of events

    Returns:
        Sorted list of unique subject names

    Example:
        >>> subjects = get_unique_subjects(timetable.events)
        >>> print(subjects)
        ['ALGEBRA', 'CALCULUS', 'PROGRAMMING']
    """
    return sorted(set(e.title for e in events))


def get_unique_professors(events: List[TimetableEvent]) -> List[str]:
    """Get unique professors from events.

    Args:
        events: List of events

    Returns:
        Sorted list of unique professor names

    Example:
        >>> professors = get_unique_professors(timetable.events)
        >>> print(professors)
        ['Mario Rossi', 'Luigi Bianchi']
    """
    return sorted(set(
        e.professor for e in events if e.professor
    ))


def get_unique_groups(events: List[TimetableEvent]) -> List[str]:
    """Get unique group IDs from events.

    Args:
        events: List of events

    Returns:
        Sorted list of unique group identifiers

    Example:
        >>> groups = get_unique_groups(timetable.events)
        >>> print(groups)
        ['CL.A', 'CL.B']  # Or ['A-L', 'M-Z'] for Medicine, etc.
    """
    groups = set()
    for event in events:
        if event.group_id:
            groups.add(event.group_id)
    return sorted(list(groups))
