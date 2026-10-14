from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.dependencies import scan_repo, employee_repo
from app.domain.derive_sessions import derive_sessions
from app.db import get_connection, _as_utc

router = APIRouter()

@router.get("/display")
async def display_page():
    return FileResponse("app/static/display.html")

@router.get("/api/stations/current")
async def current_state(token: str):

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT s.StationId, s.Name FROM dbo.StationDevice d "
            "JOIN dbo.Station s ON s.StationId = d.StationId "
            "WHERE d.DeviceToken = ? AND d.IsActive = 1",
            token,
        )
        row = cursor.fetchone()

    if row is None:
        raise HTTPException(status_code=404, detail="Unknown device token")
    
    station_id, station_name = row[0], row[1]

    now = datetime.now(timezone.utc)
    # returns a list of whoever is logged in
    employee_ids = await employee_repo.find_employee_at_device(token, now)

    employee_names = await employee_repo.find_employee_names(employee_ids)

    events = await scan_repo.list_events_for_device(token)
    sessions = derive_sessions(events)
    # open session means no end time yet
    open_session = next((s for s in sessions if s.status == "OPEN"), None)
    # scoped to open session instead of all time because we only care for THIS current ongoing session.
    start_at = open_session.started_at_utc if open_session else None
    flagged_at = None

    if open_session is not None:
        flagged_at = next(
            (e.received_at_utc for e in reversed(events)
            if e.event_type == "FLAG" and e.received_at_utc >= open_session.started_at_utc),
            None,
        )

    # to check whether or not a session is still running, feedback to verify that the scan landed.
    last_order = next(
        (e.order_ref for e in reversed(events) if e.event_type == "ORDER"),
        None,
    )
    # added short description aswell
    last_description = next(
            (e.description for e in reversed(events) if e.event_type == "ORDER"),
            None,
        )

    return {
        "server_now_utc": now,
        "station_id": station_id,
        "employee_ids": employee_ids,
        "employee_names": employee_names,
        "order_ref": open_session.order_ref if open_session else last_order,
        "description": last_description,
        "started_at_utc": start_at,
        "flagged_at_utc": flagged_at,
        "is_flagged": open_session.is_flagged if open_session else False,
        "is_running": open_session is not None,
        "station_name": station_name,
        "recent_durations": [
            s.duration_seconds
            for s in sessions
            if s.status == "CLOSED" and s.duration_seconds is not None
        ][-10:],
        # that takes the last ten, slicing past the end is safe in python
    }