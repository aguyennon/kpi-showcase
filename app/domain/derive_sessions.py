from dataclasses import replace
import datetime
from time import timezone
from typing import Optional
from app.domain.types import ScanEvent, TaskSession


def _close(session: TaskSession, at_event: ScanEvent, status: str) -> TaskSession:

    ended = at_event.received_at_utc
    duration = int((ended - session.started_at_utc).total_seconds())

    return replace(
        session,
        status=status,
        ended_at_utc=ended,
        end_scan_event_id=at_event.id,
        duration_seconds=duration,
    )


def derive_sessions(events: list[ScanEvent]) -> list[TaskSession]:
    sessions: list[TaskSession] = []
    last_order: Optional[str] = None
    open_session: Optional[TaskSession] = None

    for event in events:
        if event.event_type == "ORDER": # an order scan alone wont do anything, needs the start. (intentional overwriting since 2 order scans in a row means go with newer one)
            last_order = event

        elif event.event_type == "START": # if someone forgot to scan the finish at last task then close it here and mark it autoclosed (excluded from KPI average later since time is not accurate)
            if open_session is not None:
                sessions.append(_close(open_session, event, "AUTOCLOSED"))
                open_session = None
            
            if last_order is None:
                continue

            open_session = TaskSession(
                order_ref=last_order.order_ref,
                station_id=event.station_id,
                start_scan_event_id=event.id,
                started_at_utc=event.received_at_utc,
                status="OPEN",
                description=last_order.description,
                features=last_order.features,
                employee_id=event.employee_id,
            )
            last_order = None # consume order ref so that the next scanned START cant silently reuse it hence why we wanna know 

        elif event.event_type == "FINISH":
            if open_session is not None:
                sessions.append(_close(open_session, event, "CLOSED"))
                open_session = None
        
        elif event.event_type == "SHIFT_END":
            if open_session is not None:
                sessions.append(replace(open_session, status="INCOMPLETE"))
                open_session = None

        elif event.event_type == "FLAG":
            if open_session is not None:
                open_session = replace(open_session, is_flagged=True)

    
    if open_session is not None: # to never guess an end time, if any open sessions left just append it
        sessions.append(open_session)

    return sessions



