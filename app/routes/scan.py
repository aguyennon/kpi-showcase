from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timezone

from app.domain.parse_scan import parse_scan
from app.domain.types import NewScanEvent
from app.repositories.order_lookup import OrderLookup, detect_features
from app.dependencies import scan_repo, employee_repo
from app.domain.derive_sessions import derive_sessions

order_lookup = OrderLookup()

class ScanBody(BaseModel):
    raw_code: str = Field(max_length=100)
    device_token: str = Field(max_length=64)

router = APIRouter()



@router.post("/scan")
async def record_scan(body: ScanBody):


    station_id = await scan_repo.resolve_device(body.device_token)

    if station_id is None:
        raise HTTPException(status_code=404, detail="Unknown device token")
        
    employee_ids = await employee_repo.find_employee_at_station(station_id, datetime.now(timezone.utc))

    parsed = parse_scan(body.raw_code) # api reads the scanbody and pases the json -> validates it and hands you a typed object (code)

    if parsed.type == "BADGE":
        employee = await employee_repo.find_employee_by_number(parsed.employee_number)

        if employee is None:
            await scan_repo.record_scan(NewScanEvent(
                station_id=station_id,
                device_token=body.device_token,
                raw_code=body.raw_code,
                event_type="BADGE",
            ))
            raise HTTPException(status_code=404, detail="Unknown badge")

        now = datetime.now(timezone.utc)

        open_assignment = await employee_repo.find_open_assignment(employee.id)
        if open_assignment is not None:
            await employee_repo.end_assignment(open_assignment.id, now)

        await employee_repo.assign_station(employee.id, station_id)

    batch_no = None
    description = None
    features = None

    if parsed.type == "ORDER":
        info = await order_lookup.find_order(parsed.order_ref)
        if info is not None:
            batch_no = info.batch_no
            description = info.description
            features = ",".join(detect_features(info.description)) 

    stored = await scan_repo.record_scan( NewScanEvent( # tweaking already made placeholders for this class - body
        station_id=station_id,
        device_token=body.device_token,
        raw_code=body.raw_code,
        event_type=parsed.type,
        order_ref=parsed.order_ref,
        employee_id=employee_ids[0] if len(employee_ids) == 1 else None,
        batch_no=batch_no,
        description=description,
        features=features,
    ))

    return {"received": body.raw_code, "parsed": parsed, "stored": stored} #return dataclass, serialised into json automatically by api


@router.get("/stations/{station_id}/sessions")
async def get_sessions(station_id: int):
    events = await scan_repo.list_events_for_station(station_id)
    sessions = derive_sessions(events)
        
    return {"station_id": station_id, "sessions": sessions}

    