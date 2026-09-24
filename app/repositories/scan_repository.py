from dataclasses import asdict
from datetime import datetime, timezone
from typing import Optional

from app.domain.types import ScanEvent, NewScanEvent

class InMemoryScanRepository:
    def __init__(self):
        self._events: list[ScanEvent] = []
        self._next_id = 0

        self._devices: dict[str, int] = {
            "station-1": 1,
            "station-2": 2,
        }

    async def resolve_device(self, device_token: str) -> Optional[int]:
        return self._devices.get(device_token)

    async def record_scan(self, scan: NewScanEvent) -> ScanEvent:
        self._next_id += 1

        stored = ScanEvent(

            **asdict(scan),
            id=self._next_id,
            received_at_utc=datetime.now(timezone.utc),
        )

        self._events.append(stored)
        return stored
    
    async def list_events_for_station(self, station_id: int) -> list[ScanEvent]: 
        matching = [e for e in self._events if e.station_id == station_id] # every event e in ... where station matches

        return sorted(matching, key=lambda e: e.received_at_utc)

