from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from unibo_toolkit.models import Curriculum


@dataclass
class Classroom:
    """A classroom or teaching location.

    Attributes:
        title: Classroom name/identifier (e.g., "Aula A", "Lab 2")
        address: Full address of the location
        additional_info: Extra location details
        latitude: Latitude coordinate
        longitude: Longitude coordinate
    """

    title: str
    address: Optional[str] = None
    additional_info: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    def __str__(self) -> str:
        """String representation of the classroom."""
        if self.address:
            return f"{self.title} ({self.address})"
        return self.title


@dataclass
class TimetableEvent:
    """A single timetable event (lecture/class/lab session).

    This class represents an individual teaching event with comprehensive
    support for all 146 group patterns found across UniBo courses.

    Attributes:
        title: Event title/subject name
        start: Start datetime
        end: End datetime
        professor: Professor/instructor name
        module_code: Course module code (cod_modulo)
        credits: CFU/ECTS credits
        time_display: Human-readable time display
        teaching_period: Teaching period info (periodo)
        calendar_period: Calendar period classification
        classrooms: List of classroom locations
        is_remote: Whether the event is remote/online
        teams_link: Microsoft Teams link for remote events
        notes: Additional notes
        group_id: Group/class identifier (supports 146 patterns)
        cod_sdoppiamento: Raw cod_sdoppiamento value for reference
    """

    title: str
    start: datetime
    end: datetime
    professor: Optional[str] = None
    module_code: Optional[str] = None
    credits: Optional[int] = None
    time_display: Optional[str] = None
    teaching_period: Optional[str] = None
    calendar_period: Optional[str] = None
    classrooms: List[Classroom] = field(default_factory=list)
    is_remote: bool = False
    teams_link: Optional[str] = None
    notes: Optional[str] = None
    group_id: Optional[str] = None
    cod_sdoppiamento: Optional[str] = None

    def __post_init__(self):
        """Auto-extract group_id if not set."""
        if self.group_id is None and self.cod_sdoppiamento:
            self.group_id = self.extract_group_id(
                self.cod_sdoppiamento,
                self.title
            )

    @staticmethod
    def extract_group_id(cod_sdoppiamento: str, title: str = "") -> Optional[str]:
        """Extract group/class identifier from event data.

        Universal extraction supporting all 146 patterns found across
        185 UniBo courses analyzed (71% coverage).

        Supported pattern categories (9 total):
        1. Surname ranges: A-L, M-Z, A-K, L-Z (~10,000 occurrences)
        2. Short surname codes: AK, LZ, BO, RN (~2,000 occurrences)
        3. Single letter groups: A, B, C, D (~1,400 occurrences)
        4. Dotted groups: G.A, G.B (~600 occurrences)
        5. Class notation: CL.A, CL.B (~1,200 occurrences)
        6. Prefixed groups: GR. A, GR. B (~500 occurrences)
        7. Numeric groups: 1, 2, C1, BO1 (~600 occurrences)
        8. Location codes: BO, RN, CE, IMOLA (~1,400 occurrences)
        9. Fraction groups: AK -A, LZ -C (~50 occurrences)

        Args:
            cod_sdoppiamento: The cod_sdoppiamento field (e.g., "00819_1--CL.A")
            title: Event title (fallback, optional)

        Returns:
            Group identifier or None if not found

        Examples:
            >>> TimetableEvent.extract_group_id("00819_1--CL.A", "PROGRAMMING")
            'CL.A'
            >>> TimetableEvent.extract_group_id("08793--A-L", "MEDICINE")
            'A-L'
            >>> TimetableEvent.extract_group_id("08793_AK--AK", "MEDICINE / (AK)")
            'AK'
            >>> TimetableEvent.extract_group_id("12345--BO", "PHYSICS")
            'BO'
            >>> TimetableEvent.extract_group_id("12345", "ALGEBRA")
            None
        """
        # Method 1: From cod_sdoppiamento (primary, most reliable)
        if '--' in cod_sdoppiamento:
            suffix = cod_sdoppiamento.split('--')[-1].strip()

            # Validation 1: Not same as module base code
            module_base = cod_sdoppiamento.split('_')[0]
            if suffix == module_base:
                return None

            # Validation 2: Reasonable length
            if len(suffix) > 10 or not suffix:
                return None

            # Validation 3: Contains at least one letter or digit
            if not re.search(r'[A-Z0-9]', suffix, re.IGNORECASE):
                return None

            return suffix

        # Method 2: From title (fallback)
        # Try to extract group markers from title
        patterns = [
            r'\(CL\.([A-Z])\)',  # (CL.A)
            r'\(([A-Z])\)',      # (A)
            r'\(G\.([A-Z])\)',   # (G.A)
            r'\(([A-Z]{2,3})\)', # (AK), (LZ), (BO)
        ]

        for pattern in patterns:
            match = re.search(pattern, title)
            if match:
                return match.group(0).strip('()')

        return None

    @property
    def duration_minutes(self) -> int:
        """Calculate event duration in minutes.

        Returns:
            Duration in minutes
        """
        delta = self.end - self.start
        return int(delta.total_seconds() / 60)

    @property
    def primary_classroom(self) -> Optional[Classroom]:
        """Get first/primary classroom.

        Returns:
            First classroom or None if no classrooms
        """
        return self.classrooms[0] if self.classrooms else None

    def __str__(self) -> str:
        """String representation of the event."""
        date_str = self.start.strftime("%Y-%m-%d %H:%M")
        group_str = f" [{self.group_id}]" if self.group_id else ""
        return f"{self.title}{group_str} @ {date_str}"


@dataclass
class Timetable:
    """Complete timetable for a course year.

    Contains all events for a specific academic year of a course,
    with methods for filtering and grouping events.

    Attributes:
        course_id: Course identifier
        course_title: Course name
        academic_year: Year of study (1, 2, 3, etc.)
        start_date: Start date of timetable range
        end_date: End date of timetable range
        events: List of timetable events (sorted by start time)
        has_timetable: Whether timetable exists
        fetch_successful: Whether fetch was successful
        endpoint_used: Which API endpoint was used
    """

    course_id: int
    course_title: str
    academic_year: int
    start_date: datetime
    end_date: datetime
    events: List[TimetableEvent] = field(default_factory=list)
    has_timetable: bool = True
    fetch_successful: bool = True
    endpoint_used: Optional[str] = None

    def __post_init__(self):
        """Sort events by start time."""
        if self.events:
            self.events.sort(key=lambda e: e.start)

    @property
    def event_count(self) -> int:
        """Total number of events.

        Returns:
            Number of events in this timetable
        """
        return len(self.events)

    @property
    def unique_courses(self) -> List[str]:
        """Get unique course titles.

        Returns:
            Sorted list of unique course/subject names
        """
        return sorted(set(e.title for e in self.events))

    @property
    def professors(self) -> List[str]:
        """Get all unique professors.

        Returns:
            Sorted list of unique professor names
        """
        return sorted(set(
            e.professor for e in self.events if e.professor
        ))

    @property
    def available_groups(self) -> List[str]:
        """Get list of available group IDs.

        Returns sorted list of unique group identifiers found in events.

        Examples:
            - Class notation: ['CL.A', 'CL.B', 'CL.C']
            - Surname ranges: ['A-L', 'M-Z']
            - Location codes: ['BO', 'CE', 'RN']
            - Mixed: ['A', 'B', 'BO', 'RN']

        Returns:
            Sorted list of group identifiers
        """
        groups = set()
        for event in self.events:
            if event.group_id:
                groups.add(event.group_id)
        return sorted(list(groups))

    def get_events_by_course(self, course_title: str) -> List[TimetableEvent]:
        """Filter events by course title.

        Args:
            course_title: Course/subject title to filter by

        Returns:
            List of events matching the title
        """
        return [e for e in self.events if e.title == course_title]

    def get_events_by_group(self, group_id: str) -> List[TimetableEvent]:
        """Filter events by group ID.

        Args:
            group_id: Group identifier (e.g., 'CL.A', 'A-L', 'AK', 'BO')

        Returns:
            List of events for the specified group

        Examples:
            >>> events_a = timetable.get_events_by_group('CL.A')
            >>> events_ak = timetable.get_events_by_group('AK')
            >>> events_bo = timetable.get_events_by_group('BO')
        """
        return [e for e in self.events if e.group_id == group_id]

    def get_common_events(self) -> List[TimetableEvent]:
        """Get events without group division (common for all students).

        Returns events that don't have a group_id (no filtering).

        Returns:
            List of common events
        """
        return [e for e in self.events if e.group_id is None]

    def get_events_in_range(
        self,
        start: datetime,
        end: datetime
    ) -> List[TimetableEvent]:
        """Get events within a specific date range.

        Args:
            start: Start datetime (inclusive)
            end: End datetime (inclusive)

        Returns:
            List of events in the specified range
        """
        return [e for e in self.events if start <= e.start <= end]

    def split_by_group(self) -> Dict[str, List[TimetableEvent]]:
        """Split timetable by groups.

        Returns:
            Dict mapping group IDs to their events.
            Includes 'common' key for events without group assignment.

        Examples:
            >>> grouped = timetable.split_by_group()
            >>> # Class notation course:
            >>> grouped.keys()  # ['CL.A', 'CL.B', 'common']
            >>> # Surname range course:
            >>> grouped.keys()  # ['A-L', 'M-Z', 'common']
            >>> # Location-based course:
            >>> grouped.keys()  # ['BO', 'CE', 'RN', 'common']
        """
        result: Dict[str, List[TimetableEvent]] = {}

        for event in self.events:
            if event.group_id:
                if event.group_id not in result:
                    result[event.group_id] = []
                result[event.group_id].append(event)
            else:
                if 'common' not in result:
                    result['common'] = []
                result['common'].append(event)

        return result

    def __str__(self) -> str:
        """String representation of timetable."""
        return (
            f"Timetable(course={self.course_title}, "
            f"year={self.academic_year}, events={self.event_count})"
        )


@dataclass
class TimetableCollection:
    """Collection of timetables organized by academic year and curriculum.

    Structure mirrors the UniBo website organization:
    - Collection contains multiple academic years
    - Each year contains multiple curricula
    - Each curriculum contains events

    Attributes:
        years: Dictionary mapping year number to AcademicYearTimetable

    Example:
        >>> collection = TimetableCollection()
        >>>
        >>> # Add timetable for Year 1, Curriculum "B69-000"
        >>> year1 = collection.get_or_create_year(1)
        >>> from unibo_toolkit.models.curriculum import Curriculum
        >>> curriculum = Curriculum(code="B69-000", label="Advanced")
        >>> curriculum_tt = CurriculumTimetable(
        ...     curriculum=curriculum,
        ...     events=[...]
        ... )
        >>> year1.add_curriculum_timetable(curriculum_tt)
        >>>
        >>> # Access data
        >>> year1_events = collection.get_year(1).get_all_events()
        >>> specific_curriculum = collection.get_curriculum(year=1, code="B69-000")
    """

    years: Dict[int, AcademicYearTimetable] = field(default_factory=dict)

    def get_or_create_year(self, year: int) -> AcademicYearTimetable:
        """Get or create an AcademicYearTimetable.

        Args:
            year: Academic year number

        Returns:
            AcademicYearTimetable for the specified year
        """
        if year not in self.years:
            self.years[year] = AcademicYearTimetable(year=year)
        return self.years[year]

    def get_year(self, year: int) -> Optional[AcademicYearTimetable]:
        """Get timetable for a specific year.

        Args:
            year: Academic year number

        Returns:
            AcademicYearTimetable or None if year not found
        """
        return self.years.get(year)

    def get_curriculum(self, year: int, code: str) -> Optional[CurriculumTimetable]:
        """Get timetable for specific year and curriculum.

        Args:
            year: Academic year number
            code: Curriculum code (e.g., "B69-000")

        Returns:
            CurriculumTimetable or None if not found
        """
        year_tt = self.get_year(year)
        if year_tt:
            return year_tt.get_curriculum(code)
        return None

    def add_curriculum_timetable(
        self,
        year: int,
        curriculum_timetable: CurriculumTimetable
    ) -> None:
        """Add a curriculum timetable to the collection.

        Args:
            year: Academic year number
            curriculum_timetable: CurriculumTimetable to add
        """
        year_tt = self.get_or_create_year(year)
        year_tt.add_curriculum_timetable(curriculum_timetable)

    def get_all_years(self) -> List[int]:
        """Get list of all years in the collection.

        Returns:
            Sorted list of year numbers
        """
        return sorted(self.years.keys())

    def get_all_curricula(self, year: Optional[int] = None) -> List["Curriculum"]:
        """Get all curricula, optionally filtered by year.

        Args:
            year: Optional year to filter by

        Returns:
            List of Curriculum objects
        """
        if year is not None:
            year_tt = self.get_year(year)
            return year_tt.get_all_curricula() if year_tt else []

        # All curricula across all years
        curricula_set = set()
        for year_tt in self.years.values():
            curricula_set.update(year_tt.get_all_curricula())
        return list(curricula_set)

    def get_all_events(
        self,
        year: Optional[int] = None,
        curriculum_code: Optional[str] = None
    ) -> List[TimetableEvent]:
        """Get all events, optionally filtered by year and/or curriculum.

        Args:
            year: Filter by academic year (e.g., 1, 2, 3)
            curriculum_code: Filter by curriculum code (e.g., "B69-000")

        Returns:
            List of matching events

        Example:
            >>> # All events
            >>> all_events = collection.get_all_events()
            >>> # Year 1 only
            >>> year1_events = collection.get_all_events(year=1)
            >>> # Specific curriculum across all years
            >>> curriculum_events = collection.get_all_events(curriculum_code="B69-000")
            >>> # Specific year and curriculum
            >>> specific = collection.get_all_events(year=1, curriculum_code="B69-000")
        """
        if year is not None and curriculum_code is not None:
            # Specific year and curriculum
            curriculum_tt = self.get_curriculum(year, curriculum_code)
            return curriculum_tt.events if curriculum_tt else []

        elif year is not None:
            # Specific year, all curricula
            year_tt = self.get_year(year)
            return year_tt.get_all_events() if year_tt else []

        elif curriculum_code is not None:
            # Specific curriculum, all years
            events = []
            for year_tt in self.years.values():
                curriculum_tt = year_tt.get_curriculum(curriculum_code)
                if curriculum_tt:
                    events.extend(curriculum_tt.events)
            return events

        else:
            # All events
            events = []
            for year_tt in self.years.values():
                events.extend(year_tt.get_all_events())
            return events

    def __len__(self) -> int:
        """Return total number of events across all years and curricula."""
        return len(self.get_all_events())

    def __str__(self) -> str:
        """String representation."""
        return f"TimetableCollection: {len(self.years)} years, {len(self)} total events"


@dataclass
class Subject:
    """A course subject/module.

    Represents a subject or teaching module extracted from the
    course timetable HTML page.

    Attributes:
        title: Subject name
        subject_code: Subject code number
        module_id: Module identifier (may contain group info)
        value: Full value from checkbox input
        academic_year: Year of study (1, 2, 3, etc.)
    """

    title: str
    subject_code: str
    module_id: str
    value: str
    academic_year: Optional[int] = None

    @staticmethod
    def parse_group_from_module_id(module_id: str) -> Optional[str]:
        """Extract group ID from module_id.

        Supports all 146 group patterns found across UniBo courses:
        - Surname ranges: A-L, M-Z, A-K, LZ
        - Class notation: CL.A, CL.B
        - Single letters: A, B, C, D
        - Location codes: BO, RN, CE
        - And more...

        Args:
            module_id: Module identifier (e.g., "11929_1--CL.A", "B1944")

        Returns:
            Group identifier or None

        Examples:
            >>> Subject.parse_group_from_module_id("11929_1--CL.A")
            'CL.A'
            >>> Subject.parse_group_from_module_id("08793_AK--AK")
            'AK'
            >>> Subject.parse_group_from_module_id("12345--A-L")
            'A-L'
            >>> Subject.parse_group_from_module_id("B1944")
            None
        """
        if '--' not in module_id:
            return None

        suffix = module_id.split('--')[-1].strip()

        # Validation: not same as module base code
        module_base = module_id.split('_')[0]
        if suffix == module_base:
            return None

        # Validation: reasonable length and content
        if len(suffix) > 10 or not suffix:
            return None

        return suffix

    @property
    def group_id(self) -> Optional[str]:
        """Get group identifier if subject is split by groups/classes.

        Returns the raw group identifier (e.g., 'CL.A', 'A-L', 'AK', 'BO').

        Returns:
            Group identifier or None
        """
        return self.parse_group_from_module_id(self.module_id)

    @property
    def base_subject_code(self) -> str:
        """Get base subject code without group suffix.

        Returns:
            Base subject code

        Example:
            >>> subject = Subject(..., module_id="11929_1--CL.A", ...)
            >>> subject.base_subject_code
            '11929'
        """
        # Remove group suffix
        base = self.module_id.split('--')[0]
        # Remove module number
        base = base.split('_')[0]
        return base

    def __str__(self) -> str:
        """String representation of subject."""
        group_str = f" [{self.group_id}]" if self.group_id else ""
        return f"{self.title} ({self.subject_code}){group_str}"


@dataclass
class CurriculumTimetable:
    """Timetable for a specific curriculum within an academic year.

    This represents the schedule for one curriculum (study track) within
    a specific year of a course.

    Attributes:
        curriculum: The curriculum this timetable belongs to
        events: List of timetable events for this curriculum

    Example:
        >>> from unibo_toolkit.models.curriculum import Curriculum
        >>> curriculum = Curriculum(code="B69-000", label="Advanced Track")
        >>> timetable = CurriculumTimetable(
        ...     curriculum=curriculum,
        ...     events=[event1, event2, ...]
        ... )
        >>> print(len(timetable.events))
        42
    """

    curriculum: "Curriculum"  # Forward reference
    events: List[TimetableEvent] = field(default_factory=list)

    def add_event(self, event: TimetableEvent) -> None:
        """Add an event to this curriculum's timetable."""
        self.events.append(event)

    def get_events_by_subject(self, subject: str) -> List[TimetableEvent]:
        """Get all events for a specific subject."""
        return [e for e in self.events if e.title == subject]

    def get_unique_subjects(self) -> List[str]:
        """Get list of unique subjects in this curriculum."""
        return list(set(e.title for e in self.events))

    def __len__(self) -> int:
        """Return number of events."""
        return len(self.events)

    def __str__(self) -> str:
        """String representation."""
        return f"CurriculumTimetable({self.curriculum}, {len(self.events)} events)"


@dataclass
class AcademicYearTimetable:
    """Timetable for a specific academic year, organized by curricula.

    This represents all timetables for one academic year (e.g., Year 1),
    with separate schedules for each curriculum.

    Attributes:
        year: Academic year number (1, 2, 3, etc.)
        curricula: Dictionary mapping curriculum code to CurriculumTimetable

    Example:
        >>> year_timetable = AcademicYearTimetable(year=1)
        >>> year_timetable.add_curriculum_timetable(curriculum_tt)
        >>> print(year_timetable.get_curriculum("B69-000"))
        CurriculumTimetable(curriculum=Curriculum(...), events=[...])
    """

    year: int
    curricula: Dict[str, CurriculumTimetable] = field(default_factory=dict)

    def add_curriculum_timetable(self, curriculum_timetable: CurriculumTimetable) -> None:
        """Add a curriculum timetable to this year."""
        code = curriculum_timetable.curriculum.code
        self.curricula[code] = curriculum_timetable

    def get_curriculum(self, code: str) -> Optional[CurriculumTimetable]:
        """Get timetable for a specific curriculum by code."""
        return self.curricula.get(code)

    def get_all_curricula(self) -> List[Curriculum]:
        """Get list of all curricula in this year."""
        return [ct.curriculum for ct in self.curricula.values()]

    def get_all_events(self) -> List[TimetableEvent]:
        """Get all events across all curricula in this year."""
        events = []
        for curriculum_tt in self.curricula.values():
            events.extend(curriculum_tt.events)
        return events

    def __len__(self) -> int:
        """Return number of curricula."""
        return len(self.curricula)

    def __str__(self) -> str:
        """String representation."""
        return f"Year {self.year}: {len(self.curricula)} curricula, {len(self.get_all_events())} total events"
