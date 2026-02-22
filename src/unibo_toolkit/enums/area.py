"""Academic area enumeration."""

from enum import Enum


class Area(Enum):
    """Academic areas/fields at UniBo.

    Each area represents a broad category of study programs
    with a unique identifier used in the UniBo website.
    """

    ECONOMIA_MANAGEMENT = (1, "Economia e management")
    FARMACIA_BIOTECNOLOGIE = (2, "Farmacia e biotecnologie")
    GIURISPRUDENZA = (3, "Giurisprudenza")
    INGEGNERIA_ARCHITETTURA = (4, "Ingegneria e architettura")
    LINGUE_LETTERATURE = (5, "Lingue e Letterature, Traduzione e Interpretazione")
    MEDICINA_CHIRURGIA = (6, "Medicina e Chirurgia")
    MEDICINA_VETERINARIA = (7, "Medicina veterinaria")
    PSICOLOGIA = (8, "Psicologia")
    SCIENZE = (9, "Scienze")
    SCIENZE_AGRO_ALIMENTARI = (10, "Scienze agro-alimentari")
    SCIENZE_EDUCAZIONE = (11, "Scienze dell'educazione e della formazione")
    SCIENZE_MOTORIE = (12, "Scienze motorie")
    SCIENZE_POLITICHE = (13, "Scienze politiche")
    SCIENZE_STATISTICHE = (14, "Scienze Statistiche")
    SOCIOLOGIA = (15, "Sociologia")
    STUDI_UMANISTICI = (16, "Studi umanistici")

    def __init__(self, area_id: int, title_it: str):
        self.area_id = area_id
        self.title_it = title_it

    @classmethod
    def from_id(cls, area_id: int):
        """Get Area by ID.

        Args:
            area_id: Area identifier (1-16)

        Returns:
            Area enum value or None if not found
        """
        for area in cls:
            if area.area_id == area_id:
                return area
        return None
