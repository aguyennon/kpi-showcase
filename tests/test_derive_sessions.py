from datetime import datetime, timezone
from app.domain.derive_sessions import derive_sessions
from app.domain.types import ScanEvent

def _event(id: int, event_type: str, minute: int, order_ref: str | None = None) -> ScanEvent:
    
    return ScanEvent(
        id=id,
        station_id=1,
        device_token="test",
        raw_code="x",
        event_type=event_type,
        order_ref=order_ref,
        reason_code=None,
        employee_id=None,
        received_at_utc=datetime(2026, 1, 1, 8, minute, tzinfo=timezone.utc),
        client_reported_at_utc=None,
    )


def test_order_start_finish_produces_one_closed_session():
    events = [
        _event(1, "ORDER", 0, order_ref="123-45678-90-1"),
        _event(2, "START", 0),
        _event(3, "FINISH", 12) # minute, randomly chosen so the math is easy
    ]

    sessions = derive_sessions(events)

    # making sure that these check, if not error gets raised automatically (assert)
    assert len(sessions) == 1
    assert sessions[0].is_flagged is False
    assert sessions[0].duration_seconds == 720


def test_flag_marks_session_but_does_not_stop_the_clock():
    events = [
        _event(1, "ORDER", 0, order_ref="123-45678-90-1"),
        _event(2, "START", 0), 
        _event(3, "FLAG", 5),
        _event(4, "FINISH", 12),
    ]

    sessions = derive_sessions(events)

    assert len(sessions) == 1
    assert sessions[0].is_flagged == True
    assert sessions[0].duration_seconds == 720

def test_second_start_autocloses_the_first_session():
    events = [
        _event(1, "ORDER", 0, order_ref="111-11111-11-1"),
        _event(2, "START", 0),
        _event(3, "ORDER", 10, order_ref="222-22222-22-2"),
        _event(4, "START", 10), # oops forgot to scan finish for the first start
        _event(5, "FINISH", 25),
    ]

    sessions = derive_sessions(events)

    assert len(sessions) == 2
    assert sessions[0].order_ref == "111-11111-11-1"
    assert sessions[0].status == "AUTOCLOSED"
    assert sessions[0].ended_at_utc == events[3].received_at_utc
    assert sessions[1].order_ref == "222-22222-22-2"
    assert sessions[1].status == "CLOSED"

def test_start_before_order_scanned():
    events = [
        _event(1, "START", 0),
        _event(2, "ORDER", 0, order_ref="123-45678-90-1"),
        _event(3, "FINISH", 12),
    ]

    sessions = derive_sessions(events)

    assert sessions == []

def test_start_before_order_then_correct_sequence():
    events = [
        _event(1, "START", 0),
        _event(2, "ORDER", 5, order_ref="123-45678-90-1"),
        _event(3, "START", 5),
        _event(4, "FINISH", 20),
    ]

    sessions = derive_sessions(events)

    assert len(sessions) == 1
    assert sessions[0].status == "CLOSED"
    assert sessions[0].duration_seconds == 900