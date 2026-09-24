from datetime import datetime, timezone
from typing import Optional
from dataclasses import replace

from app.domain.security import hash_pin
from app.domain.types import Employee, StationAssignment

class InMemoryEmployeeRepository:
    def __init__(self): 
        self._employees: list[Employee] = [ # simulate test for employees examples without the actual pain of having to sign in to test
            Employee(id=1, employee_number="1001", name="Test One",
                pin_hash=hash_pin("1234")),
            Employee(id=2, employee_number="1002", name="Test Two",
                pin_hash=hash_pin("5678")),
        ]
        self._assignments: list[StationAssignment] = []
        self._next_assignment_id = 0
    
    async def find_employee_by_number(self, employee_number: str) -> Optional[Employee]:

        return next( # pulls first item from a generator
            (e for e in self._employees
            if e.employee_number == employee_number and e.is_active),
            None,
        )
    
    async def find_open_assignment(self, employee_id: int) -> Optional[StationAssignment]:

        return next(
            (a for a in self._assignments
                if a.employee_id == employee_id and a.ended_at_utc is None),
                None,
        )

    async def end_assignment(self, assignment_id: int, at_utc: datetime) -> Optional[StationAssignment]:

        for i, a in enumerate(self._assignments):
            if a.id == assignment_id:
                self._assignments[i] = replace(a, ended_at_utc=at_utc)
                return

    async def assign_station(self, employee_id: int, station_id: int) -> StationAssignment:
        self._next_assignment_id += 1

        assignment = StationAssignment(
            id=self._next_assignment_id,
            employee_id=employee_id,
            station_id=station_id,
            started_at_utc=datetime.now(timezone.utc),
        )

        self._assignments.append(assignment)
        return assignment

    async def find_employee_at_station(self, station_id: int, at_utc: datetime) -> list[int]:
        return [
            a.employee_id
            for a in self._assignments
            if a.station_id == station_id 
            and a.started_at_utc <= at_utc 
            and (a.ended_at_utc is None or a.ended_at_utc > at_utc)
        ]






        