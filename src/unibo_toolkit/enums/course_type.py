"""Course type enumeration."""

from enum import Enum


class CourseType(Enum):
    """Types of degree courses available at UniBo."""

    BACHELOR = "bachelor"
    MASTER = "master"
    SINGLE_CYCLE_MASTER = "single_cycle_master"
