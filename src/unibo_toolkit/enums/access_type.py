"""Access type enumeration."""

from enum import Enum


class AccessType(Enum):
    """Enrollment access type for courses."""

    OPEN = "libero"
    LIMITED = "programmato"
