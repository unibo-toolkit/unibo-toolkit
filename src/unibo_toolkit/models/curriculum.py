"""Curriculum data model for UniBo courses."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Curriculum:
    """Represents a curriculum (study track) within a course.

    A curriculum is a specific specialization or track within a degree program.
    For example, a Computer Science course might have curricula like:
    - "000-000": General Track
    - "B69-000": Advanced Programming Track
    - "C12-000": AI Specialization

    Attributes:
        code: Unique curriculum code (e.g., "B69-000")
        label: Human-readable name (e.g., "Advanced Track")
        selected: Whether this curriculum is selected by default (from API)

    Example:
        >>> curriculum = Curriculum(
        ...     code="B69-000",
        ...     label="Percorso avanzato"
        ... )
        >>> print(curriculum.code)
        'B69-000'
        >>> print(str(curriculum))
        'B69-000: Percorso avanzato'
    """

    code: str
    label: str
    selected: bool = False

    def __str__(self) -> str:
        """String representation for display."""
        return f"{self.code}: {self.label}"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Curriculum(code='{self.code}', label='{self.label}')"

    def __eq__(self, other) -> bool:
        """Compare curricula by code."""
        if isinstance(other, Curriculum):
            return self.code == other.code
        return False

    def __hash__(self) -> int:
        """Hash by code for use in sets/dicts."""
        return hash(self.code)
