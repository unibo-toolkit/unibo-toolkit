"""Data models for UniBo courses."""

from unibo_toolkit.models.area_info import AreaInfo
from unibo_toolkit.models.course import Bachelor, BaseCourse, Master, SingleCycleMaster
from unibo_toolkit.models.curriculum import Curriculum
from unibo_toolkit.models.timetable import (
    AcademicYearTimetable,
    Classroom,
    CurriculumTimetable,
    Subject,
    Timetable,
    TimetableCollection,
    TimetableEvent,
)

__all__ = [
    "AcademicYearTimetable",
    "AreaInfo",
    "Bachelor",
    "BaseCourse",
    "Classroom",
    "Curriculum",
    "CurriculumTimetable",
    "Master",
    "SingleCycleMaster",
    "Subject",
    "Timetable",
    "TimetableCollection",
    "TimetableEvent",
]
