import asyncio
from datetime import datetime, timezone

from app.dependencies import scan_repo
from app.db import get_connection
from app.domain.derive_sessions import derive_sessions
from app.domain.types import NewScanEvent

async def main():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT StationId FROM dbo.Station WHERE IsActive = 1")
        station_ids = [row[0] for row in cursor.fetchall()]

    for station_id in station_ids:
        events = await scan_repo.list_events_for_station(station_id)
        sessions = derive_sessions(events)

        if not any(s.ended_at_utc is None and s.status == "OPEN" for s in sessions):
            continue
        
        await scan_repo.record_scan(NewScanEvent(
            station_id=station_id,
            device_token="system",       # not a real device — the job wrote this
            raw_code="SHIFT_END",
            event_type="SHIFT_END",
        ))
        print(f"SHIFT_END written for station {station_id}")

asyncio.run(main())