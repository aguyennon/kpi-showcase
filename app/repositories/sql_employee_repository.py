from datetime import datetime, timezone
from typing import Optional

from app.db import get_connection, _as_utc
from app.domain.types import Employee, StationAssignment


def _row_to_employee(row) -> Employee:
    # this maps a db row to an employee dataclass
    return Employee(
        id=row[0],
        employee_number=row[1],
        name=row[2],
        pin_hash=row[3],
        is_active=row[4],
    )


def _row_to_assignment(row) -> StationAssignment:
    # this maps a db row to a station assignment dataclass
    return StationAssignment(
        id=row[0],
        employee_id=row[1],
        station_id=row[2],
        started_at_utc=_as_utc(row[3]),
        ended_at_utc=_as_utc(row[4]),
    )

_EMPLOYEE_COLUMNS = "EmployeeId, EmployeeNumber, Name, PinHash, IsActive"
_ASSIGNMENT_COLUMNS = "StationAssignmentId, EmployeeId, StationId, StartedAtUtc, EndedAtUtc"

class SqlEmployeeRepository:

    async def find_employee_by_number(self, employee_number: str) -> Optional[Employee]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT {_EMPLOYEE_COLUMNS} FROM dbo.Employee " 
                "WHERE EmployeeNumber = ? AND IsActive = 1", 
                employee_number,
            ) 
            row = cursor.fetchone()
        return _row_to_employee(row) if row else None

    
    async def find_open_assignment(self, employee_id: int) -> Optional[StationAssignment]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT {_ASSIGNMENT_COLUMNS} FROM dbo.StationAssignment " 
                "WHERE EmployeeId = ? AND EndedAtUtc IS NULL",
                employee_id,
            )
            row = cursor.fetchone()
        return _row_to_assignment(row) if row else None

    
    async def end_assignment(self, assignment_id: int, at_utc: datetime) -> None:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE dbo.StationAssignment "
                "SET EndedAtUtc = ? "
                "WHERE StationAssignmentId = ? AND EndedAtUtc IS NULL",
                at_utc,
                assignment_id,
            )

    # doesnt break the append-only rule since it applies to ScanEvent, the immutable record of what happened.
    # StationAssignment is mutable
    async def assign_station(self, employee_id: int, station_id: int) -> StationAssignment:
        started = datetime.now(timezone.utc)

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO dbo.StationAssignment (EmployeeId, StationId, StartedAtUtc) "
                "OUTPUT INSERTED.StationAssignmentId "
                "VALUES (?, ?, ?)",
                employee_id,
                station_id,
                started,
            )
            new_id = cursor.fetchone()[0]
            conn.commit()

        return StationAssignment(
            id=new_id,
            employee_id=employee_id,
            station_id=station_id,
            started_at_utc=started,
            ended_at_utc=None,
        )

    
    async def find_employee_at_station(self, station_id: int, at_utc: datetime) -> list[int]:
        # who was at this station at what given moment etc.
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT EmployeeId FROM dbo.StationAssignment "
                "WHERE StationId = ? "
                "AND StartedAtUtc <= ? "
                "AND (EndedAtUtc IS NULL OR EndedAtUtc > ?)",
                station_id,
                at_utc,
                at_utc,
            )
            rows = cursor.fetchall()
        return [row[0] for row in rows]

    
    async def find_employee_names(self, employee_ids: list[int]) -> list[str]:
        if not employee_ids:
            return []

        placeholders = ",".join("?" * len(employee_ids))

        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT Name FROM dbo.Employee WHERE EmployeeId IN ({placeholders})",
                *employee_ids,      # * unpacks the list into separate arguments
            )
            return [row[0] for row in cursor.fetchall()]