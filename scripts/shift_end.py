import asyncio

from app.db import get_connection
from app.dependencies import scan_repo
from app.domain.derive_sessions import derive_sessions
from app.domain.types import NewScanEvent


async def main():
    # shift end event is recorded against the same station as the device it belongs to.
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT DeviceToken, StationId FROM dbo.StationDevice WHERE IsActive = 1"
        )
        devices = [(row[0], row[1]) for row in cursor.fetchall()]

    for token, station_id in devices:
        events = await scan_repo.list_events_for_device(token)
        sessions = derive_sessions(events)

        if not any(s.status == "OPEN" for s in sessions):
            continue

        await scan_repo.record_scan(NewScanEvent(
            station_id=station_id,
            device_token=token,
            raw_code="SHIFT_END",
            event_type="SHIFT_END",
        ))
        print(f"SHIFT_END written for {token}")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE dbo.StationAssignment "
            "SET EndedAtUtc = SYSUTCDATETIME() "
            "WHERE EndedAtUtc IS NULL"
        )
        print(f"Closed {cursor.rowcount} open assignment(s)")
        conn.commit()


asyncio.run(main())