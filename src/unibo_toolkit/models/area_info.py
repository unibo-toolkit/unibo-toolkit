"""Area information model."""

from dataclasses import dataclass

from unibo_toolkit.enums import Area, CourseType


@dataclass
class AreaInfo:
    """Information about an academic area.

    Attributes:
        area: Academic area enum
        course_count: Number of courses in this area
        course_type: Type of courses (Bachelor/Master/SingleCycleMaster)
    """

    area: Area
    course_count: int
    course_type: CourseType
