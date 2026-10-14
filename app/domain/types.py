from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Optional, Protocol

EventType = Literal["ORDER", "START", "FINISH", "FLAG", "UNKNOWN", "SHIFT_END", "BADGE"]

@dataclass(frozen=True)
class ParsedScan:
    type: EventType
    order_ref: Optional[str] = None
    employee_number: Optional[str] = None

@dataclass(frozen=True)
class ScanEvent:
    id: int
    station_id: int
    device_token: str
    raw_code: str
    event_type: EventType
    order_ref: Optional[str]
    reason_code: Optional[str] # to add later
    employee_id: Optional[int]
    received_at_utc: datetime
    client_reported_at_utc: Optional[datetime]
    batch_no: Optional[str] = None
    description: Optional[str] = None
    features: Optional[str] = None

@dataclass(frozen=True)
class NewScanEvent:
    station_id: int
    device_token: str
    raw_code: str
    event_type: EventType
    order_ref: Optional[str] = None
    reason_code: Optional[str] = None # to add later
    employee_id: Optional[int] = None
    client_reported_at_utc: Optional[datetime] = None
    batch_no: Optional[str] = None
    description: Optional[str] = None
    features: Optional[str] = None

# now for employees
@dataclass(frozen=True)
class Employee:
    id: int
    employee_number: int
    name: str
    pin_hash: str # hash_pin below (never reveal here)
    is_active: bool = True

@dataclass(frozen=True)
class StationAssignment:
    id: int
    employee_id: int
    station_id: int
    started_at_utc: datetime
    ended_at_utc: Optional[datetime] = None
    device_token: Optional[str] = None
    
    
class EmployeeRepository(Protocol):
    async def find_employee_by_number(self, employee_number: str) -> Optional[Employee]: ...
    async def find_open_assignment(self, employee_id: int) -> Optional[StationAssignment]: ...
    async def end_assignment(self, assignment_id: int, at_utc: datetime) -> None: ...
    async def assign_station(self, employee_id: int, station_id: int, device_token: str) -> StationAssignment: ...
    async def find_employee_at_device(self, device_token: str, at_utc: datetime) -> list[int]: ...
    async def find_employee_names(self, employee_ids: list[int]) -> list[str]: ...


class ScanRepository(Protocol): # type checking construct
    async def record_scan(self, scan: NewScanEvent) -> ScanEvent: ...
    async def resolve_device(self, device_token: str) -> Optional[int]: ...
    async def list_events_for_station(self, station_id: int) -> list[ScanEvent]: ...
    async def list_events_for_deveice(self, device_token: str) -> list[ScanEvent]: ...


SessionStatus = Literal["OPEN", "AUTOCLOSED", "CLOSED", "CORRECTED", "INCOMPLETE"]

@dataclass(frozen=True)
class TaskSession:
    order_ref: str
    station_id: int
    start_scan_event_id: int
    started_at_utc: datetime
    status: SessionStatus = "OPEN"
    end_scan_event_id: Optional[int] = None
    ended_at_utc: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    is_flagged: bool = False
    description: Optional[str] = None
    features: Optional[str] = None
    employee_id: Optional[int] = None