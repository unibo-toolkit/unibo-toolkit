"""Parser for UniBo timetable API responses."""

import json
from hashlib import sha256
from typing import Any, Dict, List, Tuple

from unibo_toolkit.models import Classroom, TimetableEvent
from unibo_toolkit.utils.date_utils import parse_api_datetime


class TimetableParser:
    """Parser for timetable JSON responses from UniBo API."""

    @staticmethod
    def parse_classroom(aula_data: Dict[str, Any]) -> Classroom:
        """Parse classroom data from API response.

        Args:
            aula_data: Classroom dictionary from API

        Returns:
            Classroom object

        Example API data:
            {
                "des_risorsa": "Aula Magna",
                "des_indirizzo": "Via Zamboni 33, Bologna",
                "des_piano": "Piano Terra",
                "des_edificio": "Palazzo Poggi",
                "raw": {
                    "edificio": {
                        "geo": {
                            "lat": 44.487384,
                            "lng": 11.328036
                        }
                    }
                }
            }
        """
        # Extract coordinates from edificio.geo if available
        latitude = None
        longitude = None

        raw_data = aula_data.get("raw", {})
        if raw_data:
            edificio = raw_data.get("edificio", {})
            geo = edificio.get("geo", {})
            if geo:
                latitude = geo.get("lat")
                longitude = geo.get("lng")

        return Classroom(
            title=aula_data.get("des_risorsa", ""),
            address=aula_data.get("des_indirizzo"),
            additional_info=aula_data.get("des_piano"),
            latitude=latitude,
            longitude=longitude,
        )

    @staticmethod
    def parse_event(event_data: Dict[str, Any]) -> TimetableEvent:
        """Parse a single timetable event from API response.

        Args:
            event_data: Event dictionary from API

        Returns:
            TimetableEvent object

        Example API data:
            {
                "title": "PROGRAMMAZIONE / (CL.A) / (1) Modulo 1",
                "start": "2026-02-15T10:00:00+01:00",
                "end": "2026-02-15T12:00:00+01:00",
                "docente": "Mario Rossi",
                "cod_modulo": "00819-1",
                "cfu": "6",
                "periodo": "Primo Semestre",
                "aule": [...],
                "teams": "https://teams.microsoft.com/...",
                "note": "Lezione online",
                "cod_sdoppiamento": "00819_1--CL.A"
            }
        """
        # Parse dates
        start = parse_api_datetime(event_data["start"])
        end = parse_api_datetime(event_data["end"])

        # Parse classrooms
        classrooms = []
        if "aule" in event_data and event_data["aule"]:
            classrooms = [TimetableParser.parse_classroom(aula) for aula in event_data["aule"]]

        # Parse credits (might be string or int)
        credits = None
        if "cfu" in event_data and event_data["cfu"]:
            try:
                credits = int(event_data["cfu"])
            except (ValueError, TypeError):
                pass

        # Check if remote
        is_remote = False
        teams_link = None
        if "teams" in event_data and event_data["teams"]:
            is_remote = True
            teams_link = event_data["teams"]

        # Get cod_sdoppiamento for group extraction
        cod_sdoppiamento = event_data.get("cod_sdoppiamento")

        return TimetableEvent(
            title=event_data.get("title", ""),
            start=start,
            end=end,
            professor=event_data.get("docente"),
            module_code=event_data.get("cod_modulo"),
            credits=credits,
            time_display=event_data.get("orario"),
            teaching_period=event_data.get("periodo"),
            calendar_period=event_data.get("calendarioperiodo"),
            classrooms=classrooms,
            is_remote=is_remote,
            teams_link=teams_link,
            notes=event_data.get("note"),
            cod_sdoppiamento=cod_sdoppiamento,
            # group_id will be auto-extracted in __post_init__
        )

    @staticmethod
    def parse_events(events_data: List[Dict[str, Any]]) -> Tuple[List[TimetableEvent], str]:
        """Parse list of events from API response and compute content hash.

        Args:
            events_data: List of event dictionaries from API

        Returns:
            Tuple of (events_list, content_hash):
                - events_list: List of TimetableEvent objects sorted by start time
                - content_hash: SHA-256 hash (first 16 chars) of event content

        Example:
            >>> events_json = [{"title": "...", "start": "...", ...}, ...]
            >>> events, content_hash = TimetableParser.parse_events(events_json)
            >>> len(events)
            346
        """
        events = []
        hash_input = []

        for event_data in events_data:
            event = TimetableParser.parse_event(event_data)
            events.append(event)

            # Collect significant fields for hashing
            hash_input.append(
                {
                    "title": event.title,
                    "start": event.start.isoformat(),
                    "end": event.end.isoformat(),
                    "professor": event.professor,
                    "module_code": event.module_code,
                    "teaching_period": event.teaching_period,
                    "is_remote": event.is_remote,
                }
            )

        events.sort(key=lambda e: e.start)

        # Compute stable hash
        content_hash = ""
        if hash_input:
            json_str = json.dumps(hash_input, sort_keys=True, ensure_ascii=False)
            content_hash = sha256(json_str.encode("utf-8")).hexdigest()[:16]

        return events, content_hash

    @staticmethod
    def validate_response(response_data: Any) -> bool:
        """Validate that API response is valid.

        Args:
            response_data: Response from API

        Returns:
            True if valid, False otherwise
        """
        # Should be a list
        if not isinstance(response_data, list):
            return False

        # Empty list is valid
        if not response_data:
            return True

        first_event = response_data[0]
        required_fields = ["title", "start", "end"]
        return all(field in first_event for field in required_fields)
